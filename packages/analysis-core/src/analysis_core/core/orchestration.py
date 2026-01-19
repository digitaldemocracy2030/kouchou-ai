"""
Pipeline orchestration utilities.

Migrated from apps/api/broadlistening/pipeline/hierarchical_utils.py
with configurable paths and reduced external dependencies.
"""

import json
import os
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

# Default specs - can be overridden
_specs: list[dict[str, Any]] = []


def load_specs(specs_path: Path) -> list[dict[str, Any]]:
    """Load pipeline step specifications from a JSON file."""
    global _specs
    with open(specs_path, "r", encoding="utf-8") as f:
        _specs = json.load(f)
    return _specs


def get_specs() -> list[dict[str, Any]]:
    """Get the currently loaded specs."""
    return _specs


def validate_config(config: dict[str, Any], specs: list[dict[str, Any]] | None = None) -> None:
    """
    Validate a pipeline configuration.

    Args:
        config: The configuration dictionary to validate
        specs: Optional specs to validate against (uses loaded specs if not provided)

    Raises:
        Exception: If validation fails
    """
    if specs is None:
        specs = _specs

    if "input" not in config:
        raise Exception("Missing required field 'input' in config")
    if "question" not in config:
        raise Exception("Missing required field 'question' in config")

    valid_fields = [
        "input",
        "question",
        "model",
        "name",
        "intro",
        "is_pubcom",
        "is_embedded_at_local",
        "provider",
        "local_llm_address",
        "enable_source_link",
    ]
    step_names = [x["step"] for x in specs]

    for key in config:
        if key not in valid_fields and key not in step_names:
            raise Exception(f"Unknown field '{key}' in config")

    for step_spec in specs:
        valid_options = list(step_spec.get("options", {}).keys())
        if step_spec.get("use_llm"):
            valid_options = valid_options + ["prompt", "model", "prompt_file"]
        for key in config.get(step_spec["step"], {}):
            if key not in valid_options:
                raise Exception(f"Unknown option '{key}' for step '{step_spec['step']}' in config")


def decide_what_to_run(
    config: dict[str, Any],
    previous: dict[str, Any] | None,
    specs: list[dict[str, Any]] | None = None,
    output_base_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """
    Determine which pipeline steps need to be executed.

    Args:
        config: Current pipeline configuration
        previous: Previous run status (if any)
        specs: Step specifications
        output_base_dir: Base directory for outputs

    Returns:
        List of step plans with run/skip decisions
    """
    if specs is None:
        specs = _specs
    if output_base_dir is None:
        output_base_dir = Path("outputs")

    # Find last previously tracked jobs
    previous_jobs: list[dict[str, Any]] = []
    _previous = config.get("previous", None)
    while _previous and _previous.get("previous", None) is not None:
        _previous = _previous["previous"]
    if _previous:
        previous_jobs = _previous.get("completed_jobs", []) + _previous.get("previously_completed_jobs", [])

    def different_params(step: dict[str, Any]) -> list[str]:
        """Check if step parameters changed from previous run."""
        keys = step["dependencies"]["params"]
        if step.get("use_llm", False):
            keys = keys + ["prompt", "model"]
        match = [x for x in previous_jobs if x["step"] == step["step"]]
        if not match:
            return []
        prev = match[0]["params"]
        next_params = config.get(step["step"], {})
        diff = [key for key in keys if prev.get(key, None) != next_params.get(key, None)]
        for key in diff:
            print(f"(!) {step['step']} step parameter '{key}' changed from '{prev.get(key)}' to '{next_params.get(key)}'")
        return diff

    # Figure out which steps need to run
    plan: list[dict[str, Any]] = []
    for step in specs:
        stepname = step["step"]
        run = True
        reason = None
        found_prev = len([x for x in previous_jobs if x["step"] == step["step"]]) > 0

        if stepname == "hierarchical_visualization" and config.get("without-html", False):
            reason = "skipping html output"
            run = False
        elif config.get("force", False):
            reason = "forced with -f"
        elif config.get("only", None) is not None and config["only"] != stepname:
            run = False
            reason = "forced another step with -o"
        elif config.get("only") == stepname:
            reason = "forced this step with -o"
        elif not found_prev:
            reason = "no trace of previous run"
        elif not os.path.exists(output_base_dir / config["output_dir"] / step["filename"]):
            reason = "previous data not found"
        else:
            deps = step["dependencies"]["steps"]
            changing_deps = [x["step"] for x in plan if (x["step"] in deps and x["run"])]
            if len(changing_deps) > 0:
                reason = "some dependent steps will re-run: " + (", ".join(changing_deps))
            else:
                diff_params = different_params(step)
                if len(diff_params) > 0:
                    reason = "some parameters changed: " + ", ".join(diff_params)
                else:
                    run = False
                    reason = "nothing changed"

        plan.append({"step": stepname, "run": run, "reason": reason})

    return plan


def update_status(
    config: dict[str, Any],
    updates: dict[str, Any],
    output_base_dir: Path | None = None,
) -> None:
    """
    Update pipeline status file.

    Args:
        config: Pipeline configuration (modified in place)
        updates: Status updates to apply
        output_base_dir: Base directory for outputs
    """
    if output_base_dir is None:
        output_base_dir = Path("outputs")

    output_dir = config["output_dir"]

    for key, value in updates.items():
        if value is None and key in config:
            del config[key]
        else:
            config[key] = value

    config["lock_until"] = (datetime.now() + timedelta(minutes=5)).isoformat()

    status_file = output_base_dir / output_dir / "hierarchical_status.json"
    with open(status_file, "w", encoding="utf-8") as file:
        json.dump(config, file, indent=2, ensure_ascii=False)


def update_progress(
    config: dict[str, Any],
    incr: int | None = None,
    total: int | None = None,
    output_base_dir: Path | None = None,
) -> None:
    """
    Update step progress.

    Args:
        config: Pipeline configuration
        incr: Increment current progress by this amount
        total: Set total number of tasks
        output_base_dir: Base directory for outputs
    """
    if total is not None:
        update_status(config, {"current_job_progress": 0, "current_jop_tasks": total}, output_base_dir)
    elif incr is not None:
        update_status(config, {"current_job_progress": config["current_job_progress"] + incr}, output_base_dir)


def run_step(
    step: str,
    func: Callable[[dict[str, Any]], None],
    config: dict[str, Any],
    output_base_dir: Path | None = None,
    pricing_calculator: Callable[[str, str, int, int], float] | None = None,
) -> None:
    """
    Execute a pipeline step with status tracking.

    Args:
        step: Step name
        func: Step function to execute
        config: Pipeline configuration
        output_base_dir: Base directory for outputs
        pricing_calculator: Optional function to calculate LLM costs
    """
    # Check the plan before running
    plan = [x for x in config["plan"] if x["step"] == step][0]
    if not plan["run"]:
        print(f"Skipping '{step}'")
        return

    # Update status before running
    update_status(
        config,
        {
            "current_job": step,
            "current_job_started": datetime.now().isoformat(),
        },
        output_base_dir,
    )
    print("Running step:", step)

    # Run the step
    token_usage_before = config.get("total_token_usage", 0)
    func(config)
    token_usage_after = config.get("total_token_usage", token_usage_before)
    token_usage_step = token_usage_after - token_usage_before

    # Calculate estimated cost
    estimated_cost = 0.0
    provider = config.get("provider")
    model = config.get("model")
    token_usage_input = config.get("token_usage_input", 0)
    token_usage_output = config.get("token_usage_output", 0)

    if provider and model and token_usage_input > 0 and token_usage_output > 0:
        if pricing_calculator:
            estimated_cost = pricing_calculator(provider, model, token_usage_input, token_usage_output)
            print(f"Estimated cost: ${estimated_cost:.4f} ({provider} {model})")

    # Update status after running
    update_status(
        config,
        {
            "current_job_progress": None,
            "current_jop_tasks": None,
            "completed_jobs": config.get("completed_jobs", [])
            + [
                {
                    "step": step,
                    "completed": datetime.now().isoformat(),
                    "duration": (
                        datetime.now() - datetime.fromisoformat(config["current_job_started"])
                    ).total_seconds(),
                    "params": config[step],
                    "token_usage": token_usage_step,
                }
            ],
            "estimated_cost": estimated_cost,
        },
        output_base_dir,
    )


def termination(
    config: dict[str, Any],
    error: Exception | None = None,
    output_base_dir: Path | None = None,
) -> None:
    """
    Finalize pipeline execution.

    Args:
        config: Pipeline configuration
        error: Error that occurred (if any)
        output_base_dir: Base directory for outputs

    Raises:
        Exception: Re-raises the error if one occurred
    """
    if "previous" in config:
        # Remember all previously completed jobs
        old_jobs = config["previous"].get("completed_jobs", []) + config["previous"].get(
            "previously_completed_jobs", []
        )
        newly_completed = [j["step"] for j in config.get("completed_jobs", [])]
        config["previously_completed_jobs"] = [o for o in old_jobs if o["step"] not in newly_completed]
        del config["previous"]

    if error is None:
        print(f"Total token usage: {config.get('total_token_usage', 0)}")
        update_status(
            config,
            {
                "status": "completed",
                "end_time": datetime.now().isoformat(),
            },
            output_base_dir,
        )
        print("Pipeline completed.")
    else:
        update_status(
            config,
            {
                "status": "error",
                "end_time": datetime.now().isoformat(),
                "error": f"{type(error).__name__}: {error}",
                "error_stack_trace": traceback.format_exc(),
            },
            output_base_dir,
        )
        raise error
