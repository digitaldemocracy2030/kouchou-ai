"""Schema definition for output JSON validation."""

import json
from typing import Any

from pydantic import BaseModel, Field


class ArgumentSchema(BaseModel):
    """Schema for an argument in the output."""

    arg_id: str = Field(..., description="Unique argument identifier")
    argument: str = Field(..., description="Argument text")
    comment_id: int = Field(..., description="Source comment ID")
    x: float = Field(..., description="X coordinate for visualization")
    y: float = Field(..., description="Y coordinate for visualization")
    p: int = Field(..., description="Perspective/group identifier")
    cluster_ids: list[str] = Field(..., description="List of cluster IDs this argument belongs to")


class ClusterSchema(BaseModel):
    """Schema for a cluster in the output."""

    id: str = Field(..., description="Unique cluster identifier")
    label: str = Field(..., description="Cluster label")
    description: str = Field(..., description="Cluster description")
    level: int = Field(..., description="Hierarchical level")


class HierarchicalResultSchema(BaseModel):
    """Schema for the complete hierarchical result JSON."""

    arguments: list[ArgumentSchema] = Field(..., description="List of extracted arguments")
    clusters: list[ClusterSchema] = Field(..., description="List of clusters")
    propertyMaps: dict[str, dict[str, list[str]]] = Field(
        default_factory=dict, description="Property value to argument ID mappings"
    )
    intro: str | None = Field(default=None, description="Report introduction")
    overview: str | None = Field(default=None, description="Overall overview")

    @classmethod
    def from_json_file(cls, filepath: str) -> "HierarchicalResultSchema":
        """Load and validate output from JSON file.

        Args:
            filepath: Path to JSON output file

        Returns:
            HierarchicalResultSchema instance

        Raises:
            ValueError: If validation fails
            FileNotFoundError: If file doesn't exist
        """
        try:
            with open(filepath) as f:
                data = json.load(f)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Output file not found: {filepath}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in output file: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to read output file: {e}") from e

        return cls(**data)


class StatusSchema(BaseModel):
    """Schema for the status JSON file."""

    status: str = Field(..., description="Pipeline status (running, completed, error)")
    start_time: str = Field(..., description="Pipeline start time (ISO format)")
    end_time: str | None = Field(default=None, description="Pipeline end time (ISO format)")
    total_token_usage: int = Field(default=0, description="Total tokens used")
    token_usage_input: int = Field(default=0, description="Input tokens used")
    token_usage_output: int = Field(default=0, description="Output tokens used")
    estimated_cost: float = Field(default=0.0, description="Estimated cost in USD")
    provider: str | None = Field(default=None, description="LLM provider used")
    model: str | None = Field(default=None, description="LLM model used")
    completed_jobs: list[dict[str, Any]] = Field(default_factory=list, description="List of completed jobs")
    error: str | None = Field(default=None, description="Error message if status is error")
    error_stack_trace: str | None = Field(default=None, description="Error stack trace if status is error")

    @classmethod
    def from_json_file(cls, filepath: str) -> "StatusSchema":
        """Load and validate status from JSON file.

        Args:
            filepath: Path to JSON status file

        Returns:
            StatusSchema instance

        Raises:
            ValueError: If validation fails
            FileNotFoundError: If file doesn't exist
        """
        try:
            with open(filepath) as f:
                data = json.load(f)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Status file not found: {filepath}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in status file: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to read status file: {e}") from e

        return cls(**data)


def validate_output_json(filepath: str) -> dict[str, Any]:
    """Validate output JSON file and return validation result.

    Args:
        filepath: Path to JSON output file

    Returns:
        Dictionary with validation results:
        - valid: bool
        - message: str
        - output: HierarchicalResultSchema or None
        - errors: list of error messages
    """
    try:
        output = HierarchicalResultSchema.from_json_file(filepath)
        return {
            "valid": True,
            "message": f"Output file is valid with {len(output.arguments)} arguments and {len(output.clusters)} clusters",
            "output": output,
            "errors": [],
        }
    except Exception as e:
        return {"valid": False, "message": str(e), "output": None, "errors": [str(e)]}


def validate_status_json(filepath: str) -> dict[str, Any]:
    """Validate status JSON file and return validation result.

    Args:
        filepath: Path to JSON status file

    Returns:
        Dictionary with validation results:
        - valid: bool
        - message: str
        - status: StatusSchema or None
        - errors: list of error messages
    """
    try:
        status = StatusSchema.from_json_file(filepath)
        return {
            "valid": True,
            "message": f"Status file is valid with status '{status.status}'",
            "status": status,
            "errors": [],
        }
    except Exception as e:
        return {"valid": False, "message": str(e), "status": None, "errors": [str(e)]}
