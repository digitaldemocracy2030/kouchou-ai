"""
Plugin interface definitions for analysis steps.

This module defines the core interfaces that all analysis step plugins must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StepContext:
    """
    Execution context provided to each step.

    Attributes:
        output_dir: Directory for step outputs
        input_dir: Directory containing input files
        dataset: Dataset identifier (used for file naming)
        provider: LLM provider name (e.g., "openai", "gemini")
        model: Default model name for LLM calls
        local_llm_address: Optional address for local LLM server
        user_api_key: Optional user-provided API key
    """

    output_dir: Path
    input_dir: Path
    dataset: str
    provider: str
    model: str
    local_llm_address: str | None = None
    user_api_key: str | None = None


@dataclass
class StepInputs:
    """
    Inputs provided to a step.

    Attributes:
        artifacts: Mapping of artifact IDs to their file paths
        config: Full pipeline configuration (for backward compatibility)
    """

    artifacts: dict[str, Path] = field(default_factory=dict)
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepOutputs:
    """
    Outputs produced by a step.

    Attributes:
        artifacts: Mapping of artifact IDs to their file paths
        token_usage: Total tokens used (input + output)
        token_input: Input tokens used
        token_output: Output tokens generated
        metadata: Additional step-specific metadata
    """

    artifacts: dict[str, Path] = field(default_factory=dict)
    token_usage: int = 0
    token_input: int = 0
    token_output: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginMetadata:
    """
    Metadata describing a plugin.

    Attributes:
        id: Unique plugin identifier (e.g., "analysis.extraction")
        version: Plugin version (semver format)
        name: Human-readable name
        description: Plugin description
        inputs: List of required input artifact IDs
        outputs: List of produced output artifact IDs
        use_llm: Whether this step uses LLM calls
        config_schema: JSON Schema for step configuration (optional)
    """

    id: str
    version: str
    name: str = ""
    description: str = ""
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    use_llm: bool = False
    config_schema: dict[str, Any] | None = None


class AnalysisStepPlugin(ABC):
    """
    Abstract base class for analysis step plugins.

    All analysis steps should inherit from this class and implement
    the required abstract methods.

    Example:
        class ExtractionPlugin(AnalysisStepPlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    id="analysis.extraction",
                    version="1.0.0",
                    name="Extraction",
                    description="Extract opinions from comments",
                    inputs=["comments"],
                    outputs=["arguments", "relations"],
                    use_llm=True,
                )

            def run(self, ctx, inputs, config):
                # Implementation here
                ...
    """

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass

    @property
    def id(self) -> str:
        """Plugin ID (convenience property)."""
        return self.metadata.id

    @property
    def version(self) -> str:
        """Plugin version (convenience property)."""
        return self.metadata.version

    @abstractmethod
    def run(
        self,
        ctx: StepContext,
        inputs: StepInputs,
        config: dict[str, Any],
    ) -> StepOutputs:
        """
        Execute the step.

        Args:
            ctx: Execution context with paths and settings
            inputs: Input artifacts and configuration
            config: Step-specific configuration

        Returns:
            StepOutputs with produced artifacts and usage statistics
        """
        pass

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """
        Validate step configuration.

        Override this method to add custom validation logic.

        Args:
            config: Step-specific configuration to validate

        Returns:
            List of error messages (empty if valid)
        """
        return []

    def validate_inputs(self, inputs: StepInputs) -> list[str]:
        """
        Validate step inputs.

        Override this method to add custom input validation.

        Args:
            inputs: Input artifacts to validate

        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        for required_input in self.metadata.inputs:
            if required_input not in inputs.artifacts:
                errors.append(f"Missing required input: {required_input}")
        return errors
