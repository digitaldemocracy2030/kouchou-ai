"""MkDocs hooks for copying root-level markdown files to docs directory."""

import re
import shutil
from pathlib import Path

# Root-level files to copy to docs/
FILE_MAPPINGS = {
    # source (from repo root) -> destination (in docs/)
    "CONTRIBUTING.md": "development/contributing.md",
    "CODE_REVIEW_GUIDELINES.md": "development/code-review-guidelines.md",
    "Azure.md": "deployment/azure.md",
    "PROJECTS.md": "misc/projects.md",
    "CLA.md": "misc/cla.md",
}

# Link transformations for specific files
# Pattern: (file, search_pattern, replacement)
LINK_TRANSFORMS = {
    "development/contributing.md": [
        (r"\[こちら\]\(\./PROJECTS\.md\)", "[こちら](../misc/projects.md)"),
        (r"\[こちら\]\(\./CODE_REVIEW_GUIDELINES\.md\)", "[こちら](code-review-guidelines.md)"),
        (r"\[lefthook-local\.sample\.yml\]\(\./lefthook-local\.sample\.yml\)", "`lefthook-local.sample.yml`"),
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
