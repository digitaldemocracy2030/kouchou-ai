"""Package production-shaped fixtures through the actual Python shell exporter."""

import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "apps/api/src"))
from services.shell_export import package_shell, render_metadata  # noqa: E402

assets, fixture_dir = (Path(arg).resolve() for arg in sys.argv[1:])


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


reports = read_json(fixture_dir / "reports.json")
metadata = read_json(fixture_dir / "metadata.json")
results = {}
missing = []
for report in reports:
    if report["status"] != "ready":
        continue
    body_path = fixture_dir / f"report-{report['slug']}.json"
    if body_path.exists():
        results[report["slug"]] = read_json(body_path)
    else:
        missing.append(report)

# Reuse the real report structure; only vary metadata for these cases.
for case in read_json(fixture_dir / "shell-metadata-cases.json"):
    body = copy.deepcopy(results["test-report-1"])
    body["config"]["question"] = case["question"]
    body["visibility"] = case["visibility"]
    results[case["slug"]] = body
    reports.append(
        {
            **reports[0],
            "slug": case["slug"],
            "title": case["title"],
            "visibility": case["visibility"],
        }
    )

with tempfile.TemporaryDirectory(dir=assets.parent) as temporary:
    output = Path(temporary) / "site"
    package_shell(
        assets, output, metadata, [r for r in reports if r not in missing], results
    )
    # Only the E2E fixture intentionally creates a broken package for the 404 test.
    listed = read_json(output / "data/reports.json")
    for report in missing:
        target = output / report["slug"]
        shutil.copytree(assets / "__shell__", target)
        page = target / "index.html"
        page.write_text(
            render_metadata(page.read_text(encoding="utf-8"), "広聴AI", noindex=True),
            encoding="utf-8",
        )
        listed.append(report)
    (output / "data/reports.json").write_text(
        json.dumps(listed, ensure_ascii=False), encoding="utf-8"
    )
    shutil.rmtree(assets)
    shutil.move(str(output), str(assets))
