"""Assemble prebuilt viewer assets and public API JSON without Node or an API connection."""

import argparse
import html
import json
import re
import shutil
from html.parser import HTMLParser
from pathlib import Path

SHELL_SLUG = "__shell__"


class _HeadParser(HTMLParser):
    """Locate head metadata without rewriting scripts, RSC payloads or other HTML."""

    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.lines = [0]
        for match in re.finditer("\n", source):
            self.lines.append(match.end())
        self.in_head = False
        self.head_end: int | None = None
        self.title_start: int | None = None
        self.removals: list[tuple[int, int]] = []
        self.feed(source)

    def _position(self) -> int:
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag == "head":
            self.in_head = True
        if not self.in_head:
            return
        if tag == "title":
            self.title_start = self._position()
        if tag == "meta" and (dict(attrs).get("name") or "").lower() == "robots":
            self.removals.append((self._position(), self._position() + len(self.get_starttag_text())))

    def handle_endtag(self, tag):
        if self.in_head and tag == "title" and self.title_start is not None:
            end = self.source.index(">", self._position()) + 1
            self.removals.append((self.title_start, end))
            self.title_start = None
        if tag == "head":
            self.head_end = self._position()
            self.in_head = False


def render_metadata(source: str, title: str, *, noindex: bool) -> str:
    parser = _HeadParser(source)
    if parser.head_end is None:
        raise ValueError("Shell HTML must contain a closing head tag")
    robots = "noindex, nofollow" if noindex else "index, follow"
    tags = f'<title>{html.escape(title)}</title><meta name="robots" content="{robots}"/>'
    edits = [(start, end, "") for start, end in parser.removals]
    edits.append((parser.head_end, parser.head_end, tags))
    for start, end, replacement in sorted(edits, reverse=True):
        source = source[:start] + replacement + source[end:]
    return source


def package_shell(assets: Path, output: Path, metadata: dict, reports: list[dict], results: dict[str, dict]) -> None:
    """Write a NEW directory from selected ready reports; exclude unlisted from the index.

    `metadata`, `reports`, and `results` use the public API JSON shapes. The caller
    supplies selected unlisted results explicitly; private reports are rejected.
    The normal /build endpoint is not switched to this opt-in export service.
    """
    assets, output = assets.resolve(), output.resolve()
    if output.exists() or output == assets or output in assets.parents or assets in output.parents:
        raise ValueError("Output must be a new directory outside the assets directory")
    template = (assets / SHELL_SLUG / "index.html").read_text(encoding="utf-8")
    index = (assets / "index.html").read_text(encoding="utf-8")
    reporter = metadata.get("reporter")
    if not isinstance(reporter, str):
        raise ValueError("metadata.reporter must be a string")
    if (assets / "data").exists():
        raise ValueError("Assets must be a fresh shell build without report data")
    reserved = {path.name.casefold() for path in assets.iterdir()} | {"data"}
    prepared = []
    seen: set[str] = set()
    for report in reports:
        if report.get("status") != "ready":
            continue
        slug = report.get("slug", "")
        if not isinstance(slug, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", slug):
            raise ValueError(f"Invalid report slug: {slug!r}")
        if slug.casefold() in seen or slug.casefold() in reserved:
            raise ValueError(f"Report slug collides with another output: {slug}")
        seen.add(slug.casefold())
        result = results.get(slug)
        if (
            not isinstance(result, dict)
            or not isinstance(result.get("config"), dict)
            or not isinstance(result["config"].get("question"), str)
        ):
            raise ValueError(f"Missing report body or config.question: {slug}")
        visibility = result.get("visibility", report.get("visibility", "public"))
        if visibility not in {"public", "unlisted"}:
            raise ValueError(f"Report is not exportable: {slug}")
        if "visibility" in report and report["visibility"] != visibility:
            raise ValueError(f"Conflicting visibility: {slug}")
        title = f"{result['config']['question']} - {reporter}"
        prepared.append((slug, {**report, "visibility": visibility}, {**result, "visibility": visibility}, title))

    # Validate metadata and inputs before creating output. Never reuse an older
    # package: otherwise a deleted or newly private report could remain on disk.
    index = render_metadata(index, "広聴AI", noindex=False)
    pages = {
        slug: render_metadata(template, title, noindex=body["visibility"] == "unlisted")
        for slug, _, body, title in prepared
    }
    shutil.copytree(assets, output)
    (output / "index.html").write_text(index, encoding="utf-8")
    data = output / "data"
    (data / "reports").mkdir(parents=True)

    def write_json(path: Path, value):
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    write_json(data / "metadata.json", metadata)
    write_json(data / "reports.json", [report for _, report, _, _ in prepared if report["visibility"] == "public"])
    for slug, _, body, _ in prepared:
        shutil.copytree(assets / SHELL_SLUG, output / slug)
        (output / slug / "index.html").write_text(pages[slug], encoding="utf-8")
        write_json(data / "reports" / f"{slug}.json", body)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", required=True, type=Path, help="Fresh build:shell output")
    parser.add_argument("--data", required=True, type=Path, help="metadata.json, reports.json, reports/<slug>.json")
    parser.add_argument("--output", required=True, type=Path, help="New package directory")
    args = parser.parse_args()

    def read_json(path):
        return json.loads(path.read_text(encoding="utf-8"))

    reports = read_json(args.data / "reports.json")
    results = {}
    for report in reports:
        if report.get("status") == "ready":
            slug = report.get("slug", "")
            if not isinstance(slug, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", slug):
                raise ValueError("Invalid report slug")
            results[slug] = read_json(args.data / "reports" / f"{slug}.json")
    package_shell(args.assets, args.output, read_json(args.data / "metadata.json"), reports, results)


if __name__ == "__main__":
    main()
