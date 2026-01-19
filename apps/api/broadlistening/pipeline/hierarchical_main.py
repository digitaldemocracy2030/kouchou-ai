import argparse
import sys

from hierarchical_utils import initialization, run_step, termination
from steps.embedding import embedding
from steps.extraction import extraction
from steps.hierarchical_aggregation import hierarchical_aggregation
from steps.hierarchical_clustering import hierarchical_clustering
from steps.hierarchical_initial_labelling import hierarchical_initial_labelling
from steps.hierarchical_merge_labelling import hierarchical_merge_labelling
from steps.hierarchical_overview import hierarchical_overview
from steps.hierarchical_visualization import hierarchical_visualization


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
    return parser.parse_args()


def main():
    args = parse_arguments()

    # Convert argparse namespace to sys.argv format for compatibility
    new_argv = [sys.argv[0], args.config]
    if args.force:
        new_argv.append("-f")
    if args.only:
        new_argv.extend(["-o", args.only])
    if args.skip_interaction:
        new_argv.append("-skip-interaction")
    if args.without_html:
        new_argv.append("--without-html")

    config = initialization(new_argv)

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
