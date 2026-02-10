"""MkDocs hooks for copying root-level markdown files to docs directory."""

import re
import shutil
from pathlib import Path

# Root-level files to copy to docs/
FILE_MAPPINGS = {
    # source (from repo root) -> destination (in docs/)
    "CONTRIBUTING.md": "development/contributing.md",
    "CODE_REVIEW_GUIDELINES.md": "development/code-review-guidelines.md",
    "PROJECTS.md": "misc/projects.md",
    "CLA.md": "misc/cla.md",
    # repo README files copied into docs/
    "apps/admin/README.md": "repo-readmes/apps/admin.md",
    "apps/api/README.md": "repo-readmes/apps/api.md",
    "apps/api/broadlistening/README.md": "repo-readmes/apps/api-broadlistening.md",
    "apps/public-viewer/README.md": "repo-readmes/apps/public-viewer.md",
    "packages/analysis-core/README.md": "repo-readmes/packages/analysis-core.md",
    "test/e2e/README.md": "repo-readmes/tests/e2e.md",
    "test/e2e/fixtures/client/README.md": "repo-readmes/tests/e2e-fixtures-client.md",
    "tools/scripts/README.md": "repo-readmes/tools/scripts.md",
    "utils/dummy-server/README.md": "repo-readmes/utils/dummy-server.md",
    "experiments/README.md": "repo-readmes/experiments/index.md",
    "experiments/direct_win/README.md": "repo-readmes/experiments/direct-win.md",
    "experiments/embvec_reduce_public_comment/README.md": "repo-readmes/experiments/embvec-reduce-public-comment.md",
    "experiments/evaluation_report/README.md": "repo-readmes/experiments/evaluation-report.md",
}

# Link transformations for specific files
# Pattern: (file, search_pattern, replacement)
LINK_TRANSFORMS = {
    "development/contributing.md": [
        (r"\[こちら\]\(\./PROJECTS\.md\)", "[こちら](../misc/projects.md)"),
        (r"\[こちら\]\(\./CODE_REVIEW_GUIDELINES\.md\)", "[こちら](code-review-guidelines.md)"),
        (r"\[lefthook-local\.sample\.yml\]\(\./lefthook-local\.sample\.yml\)", "`lefthook-local.sample.yml`"),
    ],
    "repo-readmes/packages/analysis-core.md": [
        (r"\(\.\./\.\./docs/user-guide/cli-quickstart\.md\)", "(../../user-guide/cli-quickstart.md)"),
        (r"\(\.\./\.\./docs/user-guide/import-quickstart\.md\)", "(../../user-guide/import-quickstart.md)"),
        (r"\(\.\./\.\./docs/development/plugin-guide\.md\)", "(../../development/plugin-guide.md)"),
    ],
    "repo-readmes/tests/e2e-fixtures-client.md": [
        (r"\(\.\./\.\./README\.md\)", "(e2e.md)"),
        (
            r"\(\.\./\.\./\.\./\.\./apps/public-viewer/type\.ts\)",
            "(https://github.com/digitaldemocracy2030/kouchou-ai/blob/main/apps/public-viewer/type.ts)",
        ),
    ],
}


def on_pre_build(config, **kwargs):
    """Copy root-level markdown files to docs directory before build."""
    repo_root = Path(config["docs_dir"]).parent
    docs_dir = Path(config["docs_dir"])

    for source, dest in FILE_MAPPINGS.items():
        source_path = repo_root / source
        dest_path = docs_dir / dest

        if source_path.exists():
            # Ensure destination directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Read content
            content = source_path.read_text(encoding="utf-8")

            # Apply link transformations if defined
            if dest in LINK_TRANSFORMS:
                for pattern, replacement in LINK_TRANSFORMS[dest]:
                    content = re.sub(pattern, replacement, content)

            # Write transformed content
            dest_path.write_text(content, encoding="utf-8")
            print(f"  Copied: {source} -> docs/{dest}")
        else:
            print(f"  Warning: Source file not found: {source}")
