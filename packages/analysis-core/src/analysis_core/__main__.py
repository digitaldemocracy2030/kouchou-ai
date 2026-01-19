"""
CLI entry point for analysis-core.

Usage:
    python -m analysis_core --config config.json
    kouchou-analyze --config config.json
"""

import argparse
import sys
from pathlib import Path

from analysis_core import __version__
from analysis_core.orchestrator import PipelineOrchestrator


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
        default=True,
        help="Skip interactive prompts (default: True)",
    )
    parser.add_argument(
        "--without-html",
        action="store_true",
        default=True,
        help="Skip HTML visualization generation (default: True)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Base directory for outputs (default: outputs)",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        help="Base directory for inputs (default: inputs)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show execution plan without running",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    # Validate config file exists
    if not args.config.exists():
        print(f"Error: Config file not found: {args.config}", file=sys.stderr)
        return 1

    try:
        # Initialize the orchestrator
        orchestrator = PipelineOrchestrator.from_config(
            config_path=args.config,
            force=args.force,
            only=args.only,
            skip_interaction=args.skip_interaction,
            without_html=args.without_html,
            output_base_dir=args.output_dir,
            input_base_dir=args.input_dir,
        )

        # Show plan if dry-run
        if args.dry_run:
            print("Execution Plan:")
            print("-" * 40)
            for step in orchestrator.get_plan():
                status = "RUN" if step.get("run") else "SKIP"
                reason = step.get("reason", "")
                print(f"  [{status}] {step['step']}: {reason}")
            return 0

        # Execute the pipeline
        print(f"Starting pipeline execution...")
        print(f"  Config: {args.config}")
        print(f"  Output: {orchestrator.output_base_dir}")
        print()

        result = orchestrator.run()

        # Report results
        print()
        print("=" * 40)
        if result.success:
            print("Pipeline completed successfully!")
        else:
            print("Pipeline failed!")
            if result.error:
                print(f"Error: {result.error}")

        print()
        print(f"Duration: {result.total_duration_seconds:.2f} seconds")
        print(f"Total token usage: {result.total_token_usage}")

        if result.output_dir:
            print(f"Output directory: {result.output_dir}")

        # Show step summary
        if result.steps:
            print()
            print("Steps:")
            for step in result.steps:
                status = "OK" if step.success else "FAILED"
                print(f"  [{status}] {step.step_name} ({step.duration_seconds:.2f}s)")
                if step.error:
                    print(f"         Error: {step.error}")

        return 0 if result.success else 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
