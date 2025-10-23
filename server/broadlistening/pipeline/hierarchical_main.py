import argparse
import json
import sys
from pathlib import Path

from hierarchical_utils import initialization, run_step, termination
from steps.embedding import embedding
from steps.extraction import extraction
from steps.hierarchical_aggregation import hierarchical_aggregation
from steps.hierarchical_clustering import hierarchical_clustering
from steps.hierarchical_initial_labelling import hierarchical_initial_labelling
from steps.hierarchical_merge_labelling import hierarchical_merge_labelling
from steps.hierarchical_overview import hierarchical_overview
from steps.hierarchical_visualization import hierarchical_visualization
from validators.config_validator import validate_config_file
from validators.input_validator import validate_input_file
from validators.output_validator import validate_output_directory


def parse_arguments():
    parser = argparse.ArgumentParser(description="Run the annotation pipeline with optional flags.")
    parser.add_argument("config", help="Path to config JSON file that defines the pipeline execution.")
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force re-run all steps regardless of previous execution.",
    )
    parser.add_argument(
        "-o",
        "--only",
        type=str,
        help="Run only the specified step (e.g., extraction, embedding, clustering, etc.).",
    )
    parser.add_argument(
        "--skip-interaction",
        action="store_true",
        help="Skip the interactive confirmation prompt and run pipeline immediately.",
    )
    parser.add_argument(
        "--without-html",
        action="store_true",
        help="Skip the html output.",
    )
    parser.add_argument(
        "--validate-input",
        action="store_true",
        help="Validate input CSV file only and exit.",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Validate config JSON file only and exit.",
    )
    parser.add_argument(
        "--validate-output",
        type=str,
        metavar="OUTPUT_DIR",
        help="Validate output directory only and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show execution plan without running the pipeline.",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()

    if args.validate_config:
        validate_config_file(args.config)
        return

    if args.validate_output:
        validate_output_directory(args.validate_output)
        return

    if args.validate_input:
        with open(args.config) as f:
            config_data = json.load(f)
        input_name = config_data.get("input")
        if not input_name:
            print("Error: Config file must contain 'input' field")
            sys.exit(1)
        csv_path = f"inputs/{input_name}.csv"
        required_properties = config_data.get("extraction", {}).get("properties", [])
        validate_input_file(csv_path, required_properties)
        return

    # Convert argparse namespace to sys.argv format for compatibility
    new_argv = [sys.argv[0], args.config]
    if args.force:
        new_argv.append("-f")
    if args.only:
        new_argv.extend(["-o", args.only])
    if args.skip_interaction or args.dry_run:
        new_argv.append("-skip-interaction")
    if args.without_html:
        new_argv.append("--without-html")

    config = initialization(new_argv)

    if args.dry_run:
        print("\nDry run mode - showing execution plan only")
        print("\nPipeline configuration:")
        print(f"  - Dataset: {config['output_dir']}")
        print(f"  - Model: {config.get('model', 'default')}")
        print(f"  - Provider: {config.get('provider', 'not set')}")
        print("\nExecution plan:")
        for step in config.get("plan", []):
            status = "✓ WILL RUN" if step["run"] else "✗ SKIP"
            print(f"  {status}: {step['step']}")
            print(f"           Reason: {step['reason']}")
        print("\nNo steps were executed (dry run mode)")
        return

    try:
        run_step("extraction", extraction, config)
        run_step("embedding", embedding, config)
        run_step("hierarchical_clustering", hierarchical_clustering, config)
        run_step("hierarchical_initial_labelling", hierarchical_initial_labelling, config)
        run_step("hierarchical_merge_labelling", hierarchical_merge_labelling, config)
        run_step("hierarchical_overview", hierarchical_overview, config)
        run_step("hierarchical_aggregation", hierarchical_aggregation, config)
        run_step("hierarchical_visualization", hierarchical_visualization, config)

        termination(config)
    except Exception as e:
        termination(config, error=e)


if __name__ == "__main__":
    main()
