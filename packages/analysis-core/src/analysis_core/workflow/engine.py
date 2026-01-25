"""
Workflow execution engine.

This module provides the WorkflowEngine class for executing workflows
based on their definitions and configurations.
"""

from pathlib import Path
from typing import Any

from analysis_core.plugin import (
    PluginRegistry,
    StepContext,
    StepInputs,
    StepOutputs,
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
        artifacts: dict[str, Path] = {}

        # Execute steps in order
        for step_id in execution_order:
            step = workflow.get_step(step_id)
            if step is None:
                continue

            # Check condition
            if not evaluate_condition(step.condition, config, result.step_results):
                result.step_results[step_id] = StepResult(
                    step_id=step_id,
                    success=True,
                    skipped=True,
                )
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
                    continue
                else:
                    result.step_results[step_id] = StepResult(
                        step_id=step_id,
                        success=False,
                        error=error_msg,
                    )
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
                else:
                    result.step_results[step_id] = StepResult(
                        step_id=step_id,
                        success=False,
                        error=error_msg,
                    )
                    result.success = False
                    break

        return result

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
                if path.startswith("config."):
                    path = path[7:]  # Remove "config." prefix

                # Navigate the config hierarchy
                result = full_config
                for key in path.split("."):
                    if isinstance(result, dict):
                        result = result.get(key)
                    else:
                        return value  # Can't resolve, return original
                return result

            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}

            elif isinstance(value, list):
                return [resolve_value(v) for v in value]

            return value

        return resolve_value(step_config)
