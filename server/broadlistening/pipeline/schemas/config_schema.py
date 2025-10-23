"""Schema definition for config JSON validation."""

import json
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ExtractionConfig(BaseModel):
    """Configuration for extraction step."""

    limit: int = Field(default=1000, description="Maximum number of comments to process")
    workers: int = Field(default=1, description="Number of parallel workers")
    properties: list[str] = Field(default_factory=list, description="Properties to extract from CSV")
    categories: dict[str, dict[str, str]] = Field(default_factory=dict, description="Category definitions")
    category_batch_size: int = Field(default=5, description="Batch size for category classification")
    model: str | None = Field(default=None, description="LLM model to use")
    prompt: str | None = Field(default=None, description="Custom prompt")
    prompt_file: str | None = Field(default=None, description="Prompt file name")

    @field_validator("limit")
    @classmethod
    def limit_positive(cls, v: int) -> int:
        """Validate that limit is positive."""
        if v <= 0:
            raise ValueError("limit must be positive")
        return v

    @field_validator("workers")
    @classmethod
    def workers_positive(cls, v: int) -> int:
        """Validate that workers is positive."""
        if v <= 0:
            raise ValueError("workers must be positive")
        return v


class EmbeddingConfig(BaseModel):
    """Configuration for embedding step."""

    model: str = Field(default="text-embedding-3-small", description="Embedding model to use")


class HierarchicalClusteringConfig(BaseModel):
    """Configuration for hierarchical clustering step."""

    cluster_nums: list[int] = Field(default_factory=lambda: [3, 6], description="Number of clusters per level")

    @field_validator("cluster_nums")
    @classmethod
    def cluster_nums_valid(cls, v: list[int]) -> list[int]:
        """Validate that cluster numbers are positive."""
        if not v:
            raise ValueError("cluster_nums must not be empty")
        if any(n <= 0 for n in v):
            raise ValueError("All cluster numbers must be positive")
        return v


class LabellingConfig(BaseModel):
    """Configuration for labelling steps."""

    sampling_num: int = Field(default=3, description="Number of samples to use")
    workers: int = Field(default=1, description="Number of parallel workers")
    model: str | None = Field(default=None, description="LLM model to use")
    prompt: str | None = Field(default=None, description="Custom prompt")
    prompt_file: str | None = Field(default=None, description="Prompt file name")

    @field_validator("sampling_num")
    @classmethod
    def sampling_num_positive(cls, v: int) -> int:
        """Validate that sampling_num is positive."""
        if v <= 0:
            raise ValueError("sampling_num must be positive")
        return v


class AggregationConfig(BaseModel):
    """Configuration for aggregation step."""

    sampling_num: int = Field(default=5000, description="Number of samples to use")
    hidden_properties: dict[str, list[Any]] = Field(default_factory=dict, description="Properties to hide from output")


class VisualizationConfig(BaseModel):
    """Configuration for visualization step."""

    replacements: list[dict[str, str]] = Field(default_factory=list, description="Text replacements")


class PipelineConfig(BaseModel):
    """Complete pipeline configuration schema."""

    name: str = Field(..., description="Report name")
    question: str = Field(..., description="Analysis question")
    input: str = Field(..., description="Input CSV filename (without extension)")
    model: str = Field(default="gpt-4o-mini", description="Default LLM model")
    provider: str | None = Field(default=None, description="LLM provider")
    intro: str | None = Field(default=None, description="Report introduction")
    is_pubcom: bool | None = Field(default=None, description="Is public comment")
    is_embedded_at_local: bool | None = Field(default=None, description="Generate embeddings locally")
    local_llm_address: str | None = Field(default=None, description="Local LLM address")
    enable_source_link: bool | None = Field(default=None, description="Enable source links")

    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    hierarchical_clustering: HierarchicalClusteringConfig = Field(default_factory=HierarchicalClusteringConfig)
    hierarchical_initial_labelling: LabellingConfig = Field(default_factory=LabellingConfig)
    hierarchical_merge_labelling: LabellingConfig = Field(default_factory=LabellingConfig)
    hierarchical_overview: dict[str, Any] = Field(default_factory=dict)
    hierarchical_aggregation: AggregationConfig = Field(default_factory=AggregationConfig)
    hierarchical_visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)

    @field_validator("provider")
    @classmethod
    def provider_valid(cls, v: str | None) -> str | None:
        """Validate provider value."""
        if v is not None:
            valid_providers = ["openai", "azure", "gemini", "openrouter", "local"]
            if v not in valid_providers:
                raise ValueError(f"provider must be one of {valid_providers}")
        return v

    @classmethod
    def from_json_file(cls, filepath: str) -> "PipelineConfig":
        """Load and validate config from JSON file.

        Args:
            filepath: Path to JSON config file

        Returns:
            PipelineConfig instance

        Raises:
            ValueError: If validation fails
            FileNotFoundError: If file doesn't exist
        """
        try:
            with open(filepath) as f:
                data = json.load(f)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Config file not found: {filepath}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to read config file: {e}") from e

        return cls(**data)


def validate_config_json(filepath: str) -> dict[str, Any]:
    """Validate config JSON file and return validation result.

    Args:
        filepath: Path to JSON config file

    Returns:
        Dictionary with validation results:
        - valid: bool
        - message: str
        - config: PipelineConfig or None
        - errors: list of error messages
    """
    try:
        config = PipelineConfig.from_json_file(filepath)
        return {
            "valid": True,
            "message": f"Config file is valid for dataset '{config.input}'",
            "config": config,
            "errors": [],
        }
    except Exception as e:
        return {"valid": False, "message": str(e), "config": None, "errors": [str(e)]}
