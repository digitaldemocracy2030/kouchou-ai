"""
CLI entry point for analysis-core.

Usage:
    python -m analysis_core --config config.json
    kouchou-analyze --config config.json
"""

import argparse
import sys
from pathlib import Path


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="kouchou-analyze",
        description="広聴AI分析パイプライン - Broadlistening Analysis Pipeline",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        required=True,
        help="Path to the configuration JSON file",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force re-run all steps even if already completed",
    )
    parser.add_argument(
        "--only",
        "-o",
        type=str,
        help="Run only a specific step",
    )
    parser.add_argument(
        "--skip-interaction",
        action="store_true",
        help="Skip interactive prompts",
    )
    parser.add_argument(
        "--without-html",
        action="store_true",
        default=True,
        help="Skip HTML visualization generation (default: True)",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="%(prog)s 0.1.0",
    )

    args = parser.parse_args()

    # TODO: Implement pipeline execution
    # For now, delegate to the legacy hierarchical_main.py
    print(f"Config: {args.config}")
    print(f"Force: {args.force}")
    print(f"Only: {args.only}")
    print("Pipeline execution not yet implemented in analysis-core.")
    print("Use the legacy pipeline at apps/api/broadlistening/pipeline/hierarchical_main.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
