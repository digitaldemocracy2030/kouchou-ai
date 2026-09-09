import json
from html.parser import HTMLParser

import pytest

from src.services.shell_export import package_shell, render_metadata


class Head(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.titles = []
        self.robots = []
        self.in_title = False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
            self.titles.append("")
        if tag == "meta" and dict(attrs).get("name") == "robots":
            self.robots.append(dict(attrs)["content"])

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.titles[-1] += data


def test_metadata_escapes_text_without_rewriting_scripts():
    script = '<script>const text = "<title>RSC marker</title>";</script>'
    source = (
        '<html><head><title>old</title><meta name="robots" content="noindex"/>'
        + script
        + "</head><body>本文</body></html>"
    )
    title = '日本語 & "引用" </title><script>alert(1)</script>'
    output = render_metadata(source, title, noindex=False)
    assert Head(output).titles == [title]
    assert Head(output).robots == ["index, follow"]
    assert script in output
    assert output.endswith("</head><body>本文</body></html>")
    assert "<script>alert(1)</script>" not in output


@pytest.fixture
def assets(tmp_path):
    root = tmp_path / "assets"
    (root / "__shell__").mkdir(parents=True)
    (root / "_next").mkdir()
    for page in [root / "index.html", root / "__shell__/index.html"]:
        page.write_text("<html><head></head><body>shared shell</body></html>", encoding="utf-8")
    (root / "_next/shared.js").write_bytes(b"shared bytes")
    return root


def inputs():
    reports = [
        {"slug": "public", "status": "ready", "visibility": "public"},
        {"slug": "unlisted", "status": "ready", "visibility": "unlisted"},
    ]
    results = {
        r["slug"]: {"config": {"question": r["slug"] + ' 日本語 & "引用"'}, "visibility": r["visibility"]}
        for r in reports
    }
    return reports, results


def test_packages_distinct_metadata_and_preserves_assets(assets, tmp_path):
    reports, results = inputs()
    output = tmp_path / "site"
    package_shell(assets, output, {"reporter": "作成者"}, reports, results)
    for slug in results:
        head = Head((output / slug / "index.html").read_text(encoding="utf-8"))
        assert head.titles == [results[slug]["config"]["question"] + " - 作成者"]
        assert head.robots == ["noindex, nofollow" if slug == "unlisted" else "index, follow"]
        assert json.loads((output / "data/reports" / f"{slug}.json").read_text()) == results[slug]
    assert [r["slug"] for r in json.loads((output / "data/reports.json").read_text())] == ["public"]
    assert (output / "_next/shared.js").read_bytes() == (assets / "_next/shared.js").read_bytes()
    assert "<title>" not in (assets / "__shell__/index.html").read_text()
    # A new report uses the same prebuilt assets without any Node/build invocation.
    reports.append({"slug": "third", "status": "ready", "visibility": "public"})
    results["third"] = {"config": {"question": "第三の質問"}, "visibility": "public"}
    package_shell(assets, tmp_path / "second-site", {"reporter": "作成者"}, reports, results)
    assert (tmp_path / "second-site/_next/shared.js").read_bytes() == b"shared bytes"


@pytest.mark.parametrize("slug", ["../outside", "__shell__", "data", "_next"])
def test_rejects_slug_collisions_before_creating_output(assets, tmp_path, slug):
    with pytest.raises(ValueError):
        package_shell(assets, tmp_path / "site", {"reporter": "作成者"}, [{"slug": slug, "status": "ready"}], {})
    assert not (tmp_path / "site").exists()


def test_rejects_private_missing_and_conflicting_data(assets, tmp_path):
    reports, results = inputs()
    for visibility in ["private", "unlisted"]:
        results["public"]["visibility"] = visibility
        with pytest.raises(ValueError):
            package_shell(assets, tmp_path / "site", {"reporter": "作成者"}, reports, results)
        assert not (tmp_path / "site").exists()
    with pytest.raises(ValueError, match="Missing report body"):
        package_shell(assets, tmp_path / "site", {"reporter": "作成者"}, reports, {})


def test_refuses_to_reuse_an_old_package(assets, tmp_path):
    output = tmp_path / "site"
    output.mkdir()
    (output / "old.json").write_text("old report")
    with pytest.raises(ValueError, match="new directory"):
        package_shell(assets, output, {"reporter": "作成者"}, [], {})
    assert (output / "old.json").read_text() == "old report"


def test_cli_packages_canonical_json_without_application_imports(assets, tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    data = tmp_path / "input"
    (data / "reports").mkdir(parents=True)
    reports, results = inputs()
    for path, value in [(data / "metadata.json", {"reporter": "作成者"}), (data / "reports.json", reports)]:
        path.write_text(json.dumps(value), encoding="utf-8")
    for slug, body in results.items():
        (data / "reports" / f"{slug}.json").write_text(json.dumps(body), encoding="utf-8")
    script = Path(__file__).parents[2] / "src/services/shell_export.py"
    # Isolate the CLI from PYTHONPATH and installed site packages.
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            str(script),
            "--assets",
            str(assets),
            "--data",
            str(data),
            "--output",
            str(tmp_path / "site"),
        ],
        check=True,
    )
    assert Head((tmp_path / "site/unlisted/index.html").read_text()).robots == ["noindex, nofollow"]


def test_refuses_assets_containing_previous_report_data(assets, tmp_path):
    (assets / "data").mkdir()
    with pytest.raises(ValueError, match="fresh shell build"):
        package_shell(assets, tmp_path / "site", {"reporter": "作成者"}, [], {})
    assert not (tmp_path / "site").exists()
