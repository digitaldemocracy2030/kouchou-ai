"""
Workflow execution engine.

This module provides the WorkflowEngine class for executing workflows
based on their definitions and configurations.
"""

from pathlib import Path
from typing import Any, Callable

from analysis_core.plugin import (
    PluginRegistry,
    StepContext,
    StepInputs,
    get_registry,
)
from analysis_core.workflow.definition import (
    StepResult,
    WorkflowDefinition,
    WorkflowResult,
)
from analysis_core.workflow.resolver import (
    evaluate_condition,
    resolve_execution_order,
    validate_dependencies,
)


class WorkflowExecutionError(Exception):
    """Raised when workflow execution fails."""

    pass


class WorkflowEngine:
    """
    Engine for executing workflows.

    The engine takes a workflow definition and executes its steps
    in dependency order, passing artifacts between steps.

    Example:
        engine = WorkflowEngine()
        result = engine.run(workflow, config, ctx)
    """

    def __init__(self, registry: PluginRegistry | None = None):
        """
        Initialize the workflow engine.

        Args:
            registry: Plugin registry to use (defaults to global registry)
        """
        self.registry = registry or get_registry()
        self.registry.register_builtin_plugins()

    def run(
        self,
        workflow: WorkflowDefinition,
        config: dict[str, Any],
        ctx: StepContext,
        on_step_start: Callable[[str], None] | None = None,
        on_step_complete: Callable[[str, StepResult], None] | None = None,
        skip_steps: set[str] | None = None,
    ) -> WorkflowResult:
        """
        Execute a workflow.

        Args:
            workflow: Workflow definition to execute
            config: Full configuration including step configs
            ctx: Execution context (paths, provider, model)

        Returns:
            WorkflowResult with step results and aggregated statistics
        """
        # Validate workflow
        errors = validate_dependencies(workflow)
        if errors:
            raise WorkflowExecutionError(f"Invalid workflow: {'; '.join(errors)}")

        # Resolve execution order
        execution_order = resolve_execution_order(workflow)

        # Initialize result
        result = WorkflowResult(workflow_id=workflow.id)

        # Track artifacts produced by each step
        artifacts = self._build_initial_artifacts(config, ctx)

        # Execute steps in order
        for step_id in execution_order:
            step = workflow.get_step(step_id)
            if step is None:
                continue
            if on_step_start:
                on_step_start(step_id)

            if skip_steps and step_id in skip_steps:
                result.step_results[step_id] = StepResult(
                    step_id=step_id,
                    success=True,
                    skipped=True,
                )
                if on_step_complete:
                    on_step_complete(step_id, result.step_results[step_id])
                continue

            # Check condition
            if not evaluate_condition(step.condition, config, result.step_results):
                result.step_results[step_id] = StepResult(
                    step_id=step_id,
                    success=True,
                    skipped=True,
                )
                if on_step_complete:
                    on_step_complete(step_id, result.step_results[step_id])
                continue

            # Get plugin
            plugin = self.registry.get_or_none(step.plugin)
            if plugin is None:
                if step.optional:
                    result.step_results[step_id] = StepResult(
                        step_id=step_id,
                        success=True,
                        skipped=True,
                        error=f"Plugin '{step.plugin}' not found (optional step)",
                    )
                    if on_step_complete:
                        on_step_complete(step_id, result.step_results[step_id])
                    continue
                else:
                    raise WorkflowExecutionError(f"Plugin '{step.plugin}' not found for step '{step_id}'")

            # Build step inputs from previous step artifacts
            step_artifacts = {}
            for input_id in plugin.metadata.inputs:
                # Look for artifact from any previous step that produces it
                if input_id in artifacts:
                    step_artifacts[input_id] = artifacts[input_id]

            inputs = StepInputs(
                artifacts=step_artifacts,
                config=config,
            )

            # Get step-specific config
            step_config = self._resolve_step_config(step.config, config)

            # Validate inputs and config before execution
            input_errors = plugin.validate_inputs(inputs)
            config_errors = plugin.validate_config(step_config)

            if input_errors or config_errors:
                all_errors = input_errors + config_errors
                error_msg = f"Step '{step_id}' validation failed: {'; '.join(all_errors)}"
                print(f"Validation error: {error_msg}")

                if step.optional:
                    result.step_results[step_id] = StepResult(
                        step_id=step_id,
                        success=False,
                        error=error_msg,
                        skipped=True,
                    )
                    if on_step_complete:
                        on_step_complete(step_id, result.step_results[step_id])
                    continue
                else:
                    result.step_results[step_id] = StepResult(
                        step_id=step_id,
                        success=False,
                        error=error_msg,
                    )
                    if on_step_complete:
                        on_step_complete(step_id, result.step_results[step_id])
                    result.success = False
                    break

            try:
                # Execute step
                print(f"Executing step: {step_id} ({step.plugin})")
                outputs = plugin.run(ctx, inputs, step_config)

                # Store artifacts for downstream steps
                for artifact_id, artifact_path in outputs.artifacts.items():
                    artifacts[artifact_id] = artifact_path

                # Update token counts
                result.total_token_usage += outputs.token_usage
                result.total_token_input += outputs.token_input
                result.total_token_output += outputs.token_output

                result.step_results[step_id] = StepResult(
                    step_id=step_id,
                    success=True,
                    outputs=outputs,
                )
                if on_step_complete:
                    on_step_complete(step_id, result.step_results[step_id])

            except Exception as e:
                error_msg = f"Step '{step_id}' failed: {str(e)}"
                print(f"Error: {error_msg}")

                if step.optional:
                    result.step_results[step_id] = StepResult(
                        step_id=step_id,
                        success=False,
                        error=error_msg,
                        skipped=True,
                    )
                    if on_step_complete:
                        on_step_complete(step_id, result.step_results[step_id])
                else:
                    result.step_results[step_id] = StepResult(
                        step_id=step_id,
                        success=False,
                        error=error_msg,
                    )
                    if on_step_complete:
                        on_step_complete(step_id, result.step_results[step_id])
                    result.success = False
                    break

        return result

    def _build_initial_artifacts(
        self,
        config: dict[str, Any],
        ctx: StepContext,
    ) -> dict[str, Path]:
        """
        Seed workflow artifacts that exist before any plugin executes.

        The legacy pipeline treats the input CSV as an implicit starting point.
        To preserve that behavior for the workflow engine, expose the resolved
        comments CSV as the initial ``comments`` artifact when ``config["input"]``
        is available.
        """
        artifacts: dict[str, Path] = {}

        input_name = config.get("input")
        if isinstance(input_name, str) and input_name:
            input_path = Path(input_name)
            if input_path.suffix:
                artifacts["comments"] = ctx.input_dir / input_path
            else:
                artifacts["comments"] = ctx.input_dir / input_path.with_suffix(".csv")

        output_artifacts = {
            "arguments": "args.csv",
            "relations": "relations.csv",
            "embeddings": "embeddings.pkl",
            "clusters": "hierarchical_clusters.csv",
            "initial_labels": "hierarchical_initial_labels.csv",
            "merge_labels": "hierarchical_merge_labels.csv",
            "overview": "hierarchical_overview.txt",
            "result": "hierarchical_result.json",
            "html": "report.html",
        }
        for artifact_id, filename in output_artifacts.items():
            artifact_path = ctx.output_dir / filename
            if artifact_path.exists():
                artifacts[artifact_id] = artifact_path

        return artifacts

    def _resolve_step_config(
        self,
        step_config: dict[str, Any],
        full_config: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Resolve step configuration by replacing variable references.

        Handles patterns like ${config.extraction.limit}.

        Args:
            step_config: Step-specific configuration with potential variables
            full_config: Full workflow configuration

        Returns:
            Resolved configuration with variables replaced
        """

        def resolve_value(value: Any) -> Any:
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                # Extract path: ${config.extraction.limit} -> extraction.limit
                path = value[2:-1]
                original_path = path
                if path.startswith("config."):
                    path = path[7:]  # Remove "config." prefix

                # Navigate the config hierarchy
                result = full_config
                for key in path.split("."):
                    if isinstance(result, dict):
                        if key not in result:
                            raise WorkflowExecutionError(
                                f"Configuration key '{key}' not found while resolving '${{{original_path}}}'"
                            )
                        result = result[key]
                    else:
                        return value  # Can't resolve, return original
                return result

            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}

            elif isinstance(value, list):
                return [resolve_value(v) for v in value]

            return value

        return resolve_value(step_config)
