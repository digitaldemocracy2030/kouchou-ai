"""
Pipeline orchestration utilities.

Migrated from apps/api/broadlistening/pipeline/hierarchical_utils.py
with configurable paths and reduced external dependencies.
"""

import inspect
import json
import os
import shutil
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from analysis_core.core.utils import read_input_csv
from analysis_core.env_file import load_env_file

# Default specs - can be overridden
_specs: list[dict[str, Any]] = []

# Default package directory for finding specs
_PACKAGE_DIR = Path(__file__).parent.parent


def get_specs_path_for_mode(analysis_mode: str) -> Path:
    """Return the pipeline specs file for the requested analysis mode."""
    if analysis_mode not in {"hierarchical", "llm_grouping"}:
        raise ValueError(f"Unknown analysis_mode: {analysis_mode}")
    specs_name = "llm_grouping_specs.json" if analysis_mode == "llm_grouping" else "hierarchical_specs.json"
    return _PACKAGE_DIR / "specs" / specs_name


def sync_without_html_keys(config: dict[str, Any]) -> None:
    """Keep ``without_html`` and ``without-html`` aligned in-place."""
    if "without-html" in config:
        canonical = config["without-html"]
    elif "without_html" in config:
        canonical = config["without_html"]
    else:
        return

    config["without-html"] = canonical
    config["without_html"] = canonical


def resolve_user_api_key(config: dict[str, Any] | None = None) -> str | None:
    """Resolve the runtime user-provided API key without persisting it."""
    if config:
        user_api_key = config.get("user_api_key")
        if user_api_key:
            return str(user_api_key)
    return os.getenv("USER_API_KEY") or None


# Top-level config keys that steps may depend on (see "global_params" in specs).
GLOBAL_PARAM_KEYS = ("input", "question", "intro", "is_pubcom", "enable_source_link")

# Steps whose outputs embed the job's own config and must be regenerated instead of reused.
_NON_REUSABLE_STEPS = {"hierarchical_aggregation", "hierarchical_visualization"}


def snapshot_global_params(config: dict[str, Any]) -> dict[str, Any]:
    """Return the top-level params recorded with each completed job."""
    return {key: config.get(key) for key in GLOBAL_PARAM_KEYS}


def _step_files(step_spec: dict[str, Any]) -> list[str]:
    """Return the files a step leaves for later steps: its spec filename plus its extra_files."""
    return [step_spec["filename"], *step_spec.get("extra_files", [])]


def collect_previous_jobs(previous: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return completed jobs from a status dict, newest record first, one per step.

    ``completed_jobs`` of a status file are newer than its ``previously_completed_jobs``,
    which are newer than anything in a nested ``previous`` (left behind by interrupted runs
    of older versions).
    """
    jobs: list[dict[str, Any]] = []
    seen: set[str] = set()
    current = previous
    while current:
        for job in current.get("completed_jobs", []) + current.get("previously_completed_jobs", []):
            step = job.get("step")
            if step and step not in seen:
                seen.add(step)
                jobs.append(job)
        current = current.get("previous")
    return jobs


def _resolve_reuse_source(output_base_dir: Path, reuse_from: str) -> Path:
    """Resolve a reusable output directory from a job name or explicit path."""
    candidate = Path(reuse_from).expanduser()
    if candidate.exists():
        return candidate.resolve()
    return (output_base_dir / reuse_from).resolve()


def _seed_reused_outputs(
    *,
    config: dict[str, Any],
    output_base_dir: Path,
    specs: list[dict[str, Any]],
    persist: bool = True,
) -> tuple[dict[str, Any], set[str]] | None:
    """Copy reusable step outputs from another job into the current output dir.

    With ``persist=False`` nothing is copied or written; the seeded status and the
    artifact filenames that would be copied are returned so the plan can be computed.
    """
    reuse_from = config.get("reuse_from")
    if not reuse_from:
        return None

    dest_dir = output_base_dir / config["output_dir"]
    status_file = dest_dir / "hierarchical_status.json"
    source_dir = _resolve_reuse_source(output_base_dir, reuse_from)
    if status_file.exists():
        try:
            with open(status_file, encoding="utf-8") as f:
                reused_from = json.load(f).get("reused_from")
        except (OSError, ValueError):
            reused_from = None
        if reused_from != str(source_dir):
            print(
                f"Warning: reuse_from '{reuse_from}' is ignored because {status_file} already exists"
                f" (reused_from: {reused_from}). Remove the output directory to seed from {source_dir}."
            )
        return None

    if not source_dir.exists():
        raise RuntimeError(f"reuse_from source not found: {reuse_from}")
    if not source_dir.is_dir():
        raise RuntimeError(f"reuse_from must point to a directory: {source_dir}")

    source_status_file = source_dir / "hierarchical_status.json"
    source_status: dict[str, Any] = {}
    if source_status_file.exists():
        with open(source_status_file, encoding="utf-8") as f:
            source_status = json.load(f)

    # Newest record of each step: a source killed mid-run also lists the older records of the
    # steps it re-ran, while its artifacts are the new ones.
    status_by_step = {job["step"]: job for job in collect_previous_jobs(source_status)}
    reusable_steps = []
    seeded_files: set[str] = set()
    for step_spec in specs:
        step_name = step_spec["step"]
        if step_name in _NON_REUSABLE_STEPS:
            continue
        source_job = status_by_step.get(step_name)
        if not source_job:
            continue

        copied_files = [source_dir / filename for filename in _step_files(step_spec)]
        if not all(artifact.exists() for artifact in copied_files):
            continue

        for artifact in copied_files:
            seeded_files.add(artifact.name)
            if not persist:
                continue
            target = dest_dir / artifact.name
            if artifact.is_dir():
                shutil.copytree(artifact, target, dirs_exist_ok=True)
            else:
                shutil.copy2(artifact, target)
        reusable_steps.append(step_name)

    if not reusable_steps:
        raise RuntimeError(f"No reusable artifacts found in {source_dir}")

    seeded_jobs = []
    for step_spec in specs:
        step_name = step_spec["step"]
        if step_name not in reusable_steps:
            continue
        source_job = status_by_step.get(step_name, {})
        seeded_job = {
            "step": step_name,
            "params": source_job.get("params", {}),
        }
        for key in ("completed", "global_params"):
            if key in source_job:
                seeded_job[key] = source_job[key]
        seeded_jobs.append(seeded_job)

    seeded_status = {
        "status": "completed",
        "completed_jobs": seeded_jobs,
        "previously_completed_jobs": [],
        "reused_from": str(source_dir),
    }
    if not persist:
        print(
            f"Would seed outputs for {config['output_dir']} from {source_dir.name}: {', '.join(reusable_steps)}"
            " (nothing is copied without persisting status)"
        )
        return seeded_status, seeded_files

    _write_json_atomic(status_file, seeded_status)

    print(f"Seeded outputs for {config['output_dir']} from {source_dir.name}: {', '.join(reusable_steps)}")
    return None


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    """Write JSON via a temp file + os.replace so readers never see a partial file."""
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


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
    load_env_file(override=False)

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
        "analysis_mode",
        "local_llm_address",
        "enable_source_link",
        "without_html",
        "without-html",
        "reuse_from",
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


def plan_requires_input(plan: list[dict[str, Any]] | None) -> bool:
    """Return True when the current execution plan needs the input CSV."""
    if not plan:
        return True

    input_required_steps = {"extraction", "hierarchical_aggregation"}
    return any(step.get("run", True) and step.get("step") in input_required_steps for step in plan)


def validate_input_file(config: dict[str, Any], input_base_dir: Path, plan: list[dict[str, Any]] | None = None) -> Path:
    """Validate the CSV input path and required columns for the current plan."""
    input_path = input_base_dir / f"{config['input']}.csv"
    if not plan_requires_input(plan):
        return input_path

    if not input_path.exists():
        raise RuntimeError(f"Input CSV not found: {input_path}")

    try:
        comments = read_input_csv(input_path, n_rows=0)
    except Exception as exc:
        raise RuntimeError(f"Failed to read input CSV header: {input_path}") from exc

    required_columns = {"comment-id", "comment-body"}
    missing_columns = sorted(required_columns - set(comments.columns))
    if missing_columns:
        raise RuntimeError(
            f"Input CSV is missing required columns {missing_columns}. "
            f"Expected at least: ['comment-id', 'comment-body']"
        )

    property_columns = config.get("extraction", {}).get("properties", [])
    missing_properties = [column for column in property_columns if column not in comments.columns]
    if missing_properties:
        raise RuntimeError(
            f"Input CSV is missing extraction.properties columns {missing_properties}. "
            f"Available columns: {comments.columns}"
        )

    return input_path


def _disabled_reason(stepname: str, config: dict[str, Any]) -> str | None:
    """Return why the config turns a step off (its output is not part of the report), if it does."""
    if stepname == "hierarchical_visualization" and config.get("without-html", False):
        return "skipping html output"
    if stepname == "opinion_classification" and not config.get(stepname, {}).get("enabled", False):
        return "opinion_classification is disabled (set opinion_classification.enabled to true)"
    return None


def decide_what_to_run(
    config: dict[str, Any],
    previous: dict[str, Any] | None,
    specs: list[dict[str, Any]] | None = None,
    output_base_dir: Path | None = None,
    seeded_files: set[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Determine which pipeline steps need to be executed.

    Args:
        config: Current pipeline configuration
        previous: Previous run status (if any)
        specs: Step specifications
        output_base_dir: Base directory for outputs
        seeded_files: Artifact filenames treated as present (reuse_from without persisting)

    Returns:
        List of step plans with run/skip decisions
    """
    if specs is None:
        specs = _specs
    if output_base_dir is None:
        output_base_dir = Path("outputs")

    # Latest tracked record of each step (newest wins, including interrupted runs)
    previous_jobs = collect_previous_jobs(config.get("previous", None))
    previous_by_step = {job["step"]: job for job in previous_jobs}

    def different_params(step: dict[str, Any]) -> list[str]:
        """Check if step parameters changed from previous run."""
        keys = step["dependencies"]["params"]
        if step.get("use_llm", False):
            keys = keys + ["prompt", "model"]
        match = previous_by_step.get(step["step"])
        if not match:
            return []
        prev = match["params"]
        next_params = config.get(step["step"], {})
        defaults = step.get("options", {})

        def unchanged_default(key: str) -> bool:
            # A key missing from an older record was at its default value back then.
            return key not in prev and key in defaults and next_params.get(key, None) == defaults[key]

        diff = [key for key in keys if prev.get(key, None) != next_params.get(key, None) and not unchanged_default(key)]
        for key in diff:
            print(
                f"(!) {step['step']} step parameter '{key}' changed from '{prev.get(key)}' to '{next_params.get(key)}'"
            )
        # Records written before global params were tracked are not compared.
        prev_globals = match.get("global_params")
        if prev_globals is not None:
            for key in step["dependencies"].get("global_params", []):
                if prev_globals.get(key) != config.get(key):
                    print(
                        f"(!) {step['step']} global parameter '{key}' changed from '{prev_globals.get(key)}' to '{config.get(key)}'"
                    )
                    diff.append(key)
        return diff

    def newer_deps(step: dict[str, Any]) -> list[str]:
        """Dependencies whose latest output is newer than this step's output."""
        completed = previous_by_step.get(step["step"], {}).get("completed")
        if not completed:
            return []
        newer = []
        for dep in step["dependencies"]["steps"]:
            dep_completed = previous_by_step.get(dep, {}).get("completed")
            if dep_completed and datetime.fromisoformat(dep_completed) > datetime.fromisoformat(completed):
                newer.append(dep)
        return newer

    # Figure out which steps need to run
    plan: list[dict[str, Any]] = []
    for step in specs:
        stepname = step["step"]
        run = True
        reason = None
        found_prev = stepname in previous_by_step
        artifact_exists = all(
            (seeded_files is not None and filename in seeded_files)
            or os.path.exists(output_base_dir / config["output_dir"] / filename)
            for filename in _step_files(step)
        )
        disabled_reason = _disabled_reason(stepname, config)

        if disabled_reason:
            reason = disabled_reason
            run = False
        elif config.get("only", None) is not None and config["only"] != stepname:
            run = False
            reason = "forced another step with -o"
        elif config.get("force", False):
            reason = "forced with -f"
        elif config.get("only") == stepname:
            reason = "forced this step with -o"
        elif not found_prev:
            reason = "no trace of previous run"
        elif not artifact_exists:
            reason = "previous data not found"
        else:
            deps = step["dependencies"]["steps"]
            changing_deps = [x["step"] for x in plan if (x["step"] in deps and x["run"])]
            stale_deps = newer_deps(step)
            if len(changing_deps) > 0:
                reason = "some dependent steps will re-run: " + (", ".join(changing_deps))
            elif len(stale_deps) > 0:
                reason = "some dependent steps have newer outputs: " + (", ".join(stale_deps))
            else:
                diff_params = different_params(step)
                if len(diff_params) > 0:
                    reason = "some parameters changed: " + ", ".join(diff_params)
                else:
                    run = False
                    reason = "nothing changed"

        plan.append({"step": stepname, "run": run, "reason": reason})

    return plan


def carried_over_token_usage(
    previous: dict[str, Any] | None,
    plan: list[dict[str, Any]] | None,
    config: dict[str, Any] | None = None,
) -> dict[str, int]:
    """
    Compute the token usage to carry over from the previous run.

    When only a subset of steps is (re)run (e.g. ``--only hierarchical_aggregation``
    after a label edit), the outputs of skipped steps are kept, so the tokens spent
    on them still belong to the report. Add up the latest recorded tokens of those
    steps: steps that run again are re-counted, and steps the config turns off (e.g. a
    disabled opinion_classification) or that are not in the plan (another analysis_mode)
    are no longer part of the report. Subtracting the re-run steps from the previous
    totals instead would subtract them twice after a failed partial rerun, whose totals
    already left them out.

    The previous totals stay an upper bound: job records copied from another report
    (admin duplicate) were never counted in them.

    Returns:
        Dict with ``total_token_usage``, ``token_usage_input`` and ``token_usage_output``.
    """
    zero = {"total_token_usage": 0, "token_usage_input": 0, "token_usage_output": 0}
    if not isinstance(previous, dict):
        return zero

    prev_total = int(previous.get("total_token_usage") or 0)
    prev_input = int(previous.get("token_usage_input") or 0)
    prev_output = int(previous.get("token_usage_output") or 0)
    if prev_total <= 0 and prev_input <= 0 and prev_output <= 0:
        return zero

    # Latest job record per step. A crashed run leaves a nested "previous" whose
    # jobs are not yet merged into previously_completed_jobs, so walk the chain.
    jobs_by_step: dict[str, dict[str, Any]] = {}
    status: Any = previous
    while isinstance(status, dict):
        for job in status.get("completed_jobs", []) + status.get("previously_completed_jobs", []):
            step = job.get("step") if isinstance(job, dict) else None
            if step and step not in jobs_by_step:
                jobs_by_step[step] = job
        status = status.get("previous")

    kept_steps = {
        step["step"]
        for step in (plan or [])
        if not step.get("run", True) and (config is None or not _disabled_reason(step["step"], config))
    }
    total, token_input, token_output = 0, 0, 0
    for step in kept_steps:
        job = jobs_by_step.get(step)
        if not job:
            continue
        step_total = int(job.get("token_usage") or 0)
        if step_total <= 0:
            continue
        total += step_total
        if "token_input" in job or "token_output" in job:
            token_input += int(job.get("token_input") or 0)
            token_output += int(job.get("token_output") or 0)
        elif prev_total > 0:
            # Older status files do not record the per-step input/output split.
            token_input += round(step_total * prev_input / prev_total)
            token_output += round(step_total * prev_output / prev_total)

    total = min(total, prev_total)
    if total <= 0:
        return zero
    return {
        "total_token_usage": total,
        "token_usage_input": min(token_input, prev_input),
        "token_usage_output": min(token_output, prev_output),
    }


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

    if updates.get("status") == "error":
        # Failed requests may have consumed tokens without returning usage.
        config["token_usage_complete"] = False
        config["estimated_cost"] = None
    elif updates.get("status") == "running":
        config.pop("token_usage_complete", None)

    config["lock_until"] = (datetime.now() + timedelta(minutes=5)).isoformat()

    status_file = output_base_dir / output_dir / "hierarchical_status.json"
    # Do not nest "previous" in the file; keep its jobs in previously_completed_jobs instead
    # so an interrupted run still leaves the full history for the next run.
    status = {key: value for key, value in config.items() if key != "previous"}
    if "previous" in config:
        status["previously_completed_jobs"] = collect_previous_jobs(config["previous"])
    _write_json_atomic(status_file, status)


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
    pricing_calculator: Callable[[str, str, int, int], float | None] | None = None,
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
    token_input_before = config.get("token_usage_input", 0)
    token_output_before = config.get("token_usage_output", 0)
    func(config)
    token_usage_after = config.get("total_token_usage", token_usage_before)
    token_usage_step = token_usage_after - token_usage_before
    token_input_step = config.get("token_usage_input", token_input_before) - token_input_before
    token_output_step = config.get("token_usage_output", token_output_before) - token_output_before

    # Calculate estimated cost
    estimated_cost = None
    provider = config.get("provider")
    model = config.get("model")
    token_usage_input = config.get("token_usage_input", 0)
    token_usage_output = config.get("token_usage_output", 0)

    if provider and model and token_usage_input > 0 and token_usage_output > 0:
        if pricing_calculator:
            estimated_cost = pricing_calculator(provider, model, token_usage_input, token_usage_output)
            print(f"Estimated cost: {estimated_cost if estimated_cost is not None else 'unknown'} ({provider} {model})")

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
                    "global_params": snapshot_global_params(config),
                    "token_usage": token_usage_step,
                    "token_input": token_input_step,
                    "token_output": token_output_step,
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
    validate_api_keys_early: bool = True,
    persist_status: bool = True,
    output_base_dir: Path | None = None,
    input_base_dir: Path | None = None,
    specs_path: Path | None = None,
    steps_module: Any = None,
    reuse_from: str | None = None,
) -> dict[str, Any]:
    """
    Initialize pipeline configuration.

    Args:
        config_path: Path to config JSON file
        force: Force re-run all steps
        only: Run only specified step
        skip_interaction: Skip interactive prompts
        without_html: Skip HTML visualization
        validate_api_keys_early: Validate provider credentials during initialization
        persist_status: Persist running/completed status to hierarchical_status.json
        output_base_dir: Base directory for outputs (default: outputs/)
        input_base_dir: Base directory for inputs (default: inputs/)
        specs_path: Path to specs JSON file (default: package specs)
        steps_module: Module containing step functions (for source code extraction)
        reuse_from: Reuse intermediate outputs from another job directory

    Returns:
        Initialized configuration dictionary
    """
    config_path = Path(config_path)

    # Set default directories
    if output_base_dir is None:
        output_base_dir = Path("outputs")
    if input_base_dir is None:
        input_base_dir = Path("inputs")
    # Load config
    job_name = config_path.stem
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    if specs_path is None:
        specs_path = get_specs_path_for_mode(config.get("analysis_mode", "hierarchical"))

    # Load specs
    specs = load_specs(specs_path)

    # Validate config
    validate_config(config, specs)
    step_names = [step_spec["step"] for step_spec in specs]
    if only and only not in step_names:
        raise ValueError(f"Unknown step for --only: '{only}'. Valid steps: {', '.join(step_names)}")

    # Validate API keys early (fail-fast)
    # This ensures we catch missing API keys before starting any pipeline steps
    provider = config.get("provider", "openai")
    if validate_api_keys_early:
        validate_api_keys(provider, resolve_user_api_key(config))

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
    if reuse_from:
        config["reuse_from"] = reuse_from
    if skip_interaction:
        config["skip-interaction"] = True
    if without_html:
        config["without-html"] = True
        config["without_html"] = True

    # Keep both naming variants in sync while workflow and legacy paths coexist.
    sync_without_html_keys(config)

    output_dir = config["output_dir"]

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

        if step == "llm_grouping":
            from analysis_core.prompts import get_default_prompt

            if not config[step].get("discovery_prompt"):
                config[step]["discovery_prompt"] = get_default_prompt("llm_grouping_discovery") or ""
            if not config[step].get("assignment_prompt"):
                config[step]["assignment_prompt"] = get_default_prompt("llm_grouping_assignment") or ""

    # Create output directory if needed
    output_path = output_base_dir / output_dir
    if persist_status and not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)

    seeded = _seed_reused_outputs(config=config, output_base_dir=output_base_dir, specs=specs, persist=persist_status)
    seeded_files: set[str] | None = None

    # Check if job has run before
    previous: dict[str, Any] | bool = False
    status_file = output_base_dir / output_dir / "hierarchical_status.json"
    if seeded is not None:
        previous, seeded_files = seeded
    elif status_file.exists():
        with open(status_file, "r", encoding="utf-8") as f:
            previous = json.load(f)
    if previous:
        config["previous"] = previous

    # Crash if job is already running and locked
    if previous and isinstance(previous, dict) and previous.get("status") == "running":
        lock_until = previous.get("lock_until")
        if lock_until and datetime.fromisoformat(lock_until) > datetime.now():
            print("Job already running and locked. Try again in 5 minutes.")
            raise Exception("Job already running.")
        else:
            print("Hum, the last Job crashed a while ago...Proceeding!")

    # Decide what to run
    plan = decide_what_to_run(
        config, previous if isinstance(previous, dict) else None, specs, output_base_dir, seeded_files
    )
    config["plan"] = plan
    if only:
        only_plan = next(step_plan for step_plan in plan if step_plan["step"] == only)
        if not only_plan["run"]:
            raise ValueError(f"Step '{only}' given to --only will not run: {only_plan['reason']}")

    # Interactive confirmation (unless skipped)
    if "skip-interaction" not in config:
        print("So, here is what I am planning to run:")
        for step_plan in plan:
            print(step_plan)
        print("Looks good? Press enter to continue or Ctrl+C to abort.")
        input()

    # Ready to start - update status
    if persist_status:
        update_status(
            config,
            {
                "plan": plan,
                "status": "running",
                "start_time": datetime.now().isoformat(),
                "completed_jobs": [],
                **carried_over_token_usage(previous if isinstance(previous, dict) else None, plan, config),
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
        old_jobs = collect_previous_jobs(config["previous"])
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
