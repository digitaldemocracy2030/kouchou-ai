"""
Pipeline orchestration utilities.

Migrated from apps/api/broadlistening/pipeline/hierarchical_utils.py
with configurable paths and reduced external dependencies.
"""

import inspect
import json
import os
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

# Default specs - can be overridden
_specs: list[dict[str, Any]] = []

# Default package directory for finding specs
_PACKAGE_DIR = Path(__file__).parent.parent


def load_specs(specs_path: Path) -> list[dict[str, Any]]:
    """Load pipeline step specifications from a JSON file."""
    global _specs
    with open(specs_path, "r", encoding="utf-8") as f:
        _specs = json.load(f)
    return _specs


def get_specs() -> list[dict[str, Any]]:
    """Get the currently loaded specs."""
    return _specs


def validate_api_keys(provider: str, user_api_key: str | None = None) -> None:
    """
    Validate that required API keys are set for the specified provider.

    This function performs fail-fast validation to ensure API keys are configured
    before starting the pipeline, rather than failing after N API calls.

    Args:
        provider: The LLM provider name (openai, azure, gemini, local, openrouter)
        user_api_key: Optional user-provided API key (overrides environment variable)

    Raises:
        RuntimeError: If required API keys are not set
    """
    load_dotenv(override=False)

    if provider == "openai":
        api_key = user_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY environment variable is not set. "
                "Please set it in your .env file or environment."
            )

    elif provider == "azure":
        missing_vars = []
        if not os.getenv("AZURE_CHATCOMPLETION_ENDPOINT"):
            missing_vars.append("AZURE_CHATCOMPLETION_ENDPOINT")
        if not os.getenv("AZURE_CHATCOMPLETION_DEPLOYMENT_NAME"):
            missing_vars.append("AZURE_CHATCOMPLETION_DEPLOYMENT_NAME")
        if not (user_api_key or os.getenv("AZURE_CHATCOMPLETION_API_KEY")):
            missing_vars.append("AZURE_CHATCOMPLETION_API_KEY")
        if not os.getenv("AZURE_CHATCOMPLETION_VERSION"):
            missing_vars.append("AZURE_CHATCOMPLETION_VERSION")

        if missing_vars:
            raise RuntimeError(
                f"Azure OpenAI environment variables not set: {', '.join(missing_vars)}. "
                f"Note: Use AZURE_CHATCOMPLETION_* variables, not AZURE_OPENAI_*. "
                f"See .env.example for correct variable names."
            )

    elif provider == "gemini":
        api_key = user_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not set. "
                "Please set it in your .env file or environment."
            )

    elif provider == "openrouter":
        api_key = user_api_key or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY environment variable is not set. "
                "Please set it in your .env file or environment."
            )

    elif provider == "local":
        pass

    else:
        raise RuntimeError(f"Unknown provider: {provider}")


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
            print(
                f"(!) {step['step']} step parameter '{key}' changed from '{prev.get(key)}' to '{next_params.get(key)}'"
            )
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
        output_base_dir: Base directory for outputs (falls back to config._output_base_dir)
    """
    if output_base_dir is None:
        # Read from config if available, otherwise use default
        config_base_dir = config.get("_output_base_dir")
        if config_base_dir:
            output_base_dir = Path(config_base_dir)
        else:
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


def initialization(
    config_path: Path | str,
    force: bool = False,
    only: str | None = None,
    skip_interaction: bool = False,
    without_html: bool = True,
    output_base_dir: Path | None = None,
    input_base_dir: Path | None = None,
    specs_path: Path | None = None,
    steps_module: Any = None,
) -> dict[str, Any]:
    """
    Initialize pipeline configuration.

    Args:
        config_path: Path to config JSON file
        force: Force re-run all steps
        only: Run only specified step
        skip_interaction: Skip interactive prompts
        without_html: Skip HTML visualization
        output_base_dir: Base directory for outputs (default: outputs/)
        input_base_dir: Base directory for inputs (default: inputs/)
        specs_path: Path to specs JSON file (default: package specs)
        steps_module: Module containing step functions (for source code extraction)

    Returns:
        Initialized configuration dictionary
    """
    config_path = Path(config_path)

    # Set default directories
    if output_base_dir is None:
        output_base_dir = Path("outputs")
    if input_base_dir is None:
        input_base_dir = Path("inputs")
    if specs_path is None:
        specs_path = _PACKAGE_DIR / "specs" / "hierarchical_specs.json"

    # Load specs
    specs = load_specs(specs_path)

    # Load config
    job_name = config_path.stem
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Validate config
    validate_config(config, specs)

    # Validate API keys early (fail-fast)
    # This ensures we catch missing API keys before starting any pipeline steps
    provider = config.get("provider", "openai")
    validate_api_keys(provider)

    # Set output directory
    config["output_dir"] = job_name

    # Store base directories in config for later use
    config["_output_base_dir"] = str(output_base_dir)
    config["_input_base_dir"] = str(input_base_dir)

    # Set options from arguments
    if force:
        config["force"] = True
    if only:
        config["only"] = only
    if skip_interaction:
        config["skip-interaction"] = True
    if without_html:
        config["without-html"] = True

    output_dir = config["output_dir"]

    # Check if job has run before
    previous: dict[str, Any] | bool = False
    status_file = output_base_dir / output_dir / "hierarchical_status.json"
    if status_file.exists():
        with open(status_file, "r", encoding="utf-8") as f:
            previous = json.load(f)
        config["previous"] = previous

    # Crash if job is already running and locked
    if previous and isinstance(previous, dict) and previous.get("status") == "running":
        lock_until = previous.get("lock_until")
        if lock_until and datetime.fromisoformat(lock_until) > datetime.now():
            print("Job already running and locked. Try again in 5 minutes.")
            raise Exception("Job already running.")
        else:
            print("Hum, the last Job crashed a while ago...Proceeding!")

    # Set default LLM model
    if "model" not in config:
        config["model"] = "gpt-4o-mini"

    # Prepare configs for each step
    for step_spec in specs:
        step = step_spec["step"]
        if step not in config:
            config[step] = {}

        # Set default option values
        if "options" in step_spec:
            for key, value in step_spec["options"].items():
                if key not in config[step]:
                    config[step][key] = value

        # Try to include source code from steps module
        if steps_module is not None:
            try:
                step_func = getattr(steps_module, step, None)
                if step_func is not None:
                    config[step]["source_code"] = inspect.getsource(step_func)
            except Exception:
                print(f"Warning: could not get source code for step '{step}'")

        # Resolve common options for LLM-based jobs
        if step_spec.get("use_llm", False):
            # Resolve model - use step-specific or global
            if "model" not in config[step]:
                if "model" in config:
                    config[step]["model"] = config["model"]

            # Resolve prompt - use step-specific or default
            if "prompt" not in config[step]:
                from analysis_core.prompts import get_default_prompt

                default_prompt = get_default_prompt(step)
                if default_prompt:
                    config[step]["prompt"] = default_prompt

    # Create output directory if needed
    output_path = output_base_dir / output_dir
    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)

    # Decide what to run
    plan = decide_what_to_run(config, previous if isinstance(previous, dict) else None, specs, output_base_dir)
    config["plan"] = plan

    # Interactive confirmation (unless skipped)
    if "skip-interaction" not in config:
        print("So, here is what I am planning to run:")
        for step_plan in plan:
            print(step_plan)
        print("Looks good? Press enter to continue or Ctrl+C to abort.")
        input()

    # Ready to start - update status
    update_status(
        config,
        {
            "plan": plan,
            "status": "running",
            "start_time": datetime.now().isoformat(),
            "completed_jobs": [],
            "total_token_usage": 0,
            "token_usage_input": 0,
            "token_usage_output": 0,
            "provider": config.get("provider"),
            "model": config.get("model"),
        },
        output_base_dir,
    )

    return config


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
