"""Pydantic schemas for hierarchical_result.json validation.

These schemas define the expected structure of the pipeline output,
allowing E2E tests to validate that LLM-generated results conform
to the expected format.
"""

from pydantic import BaseModel, Field


class Argument(BaseModel):
    """Schema for an extracted argument from comments."""

    arg_id: str = Field(..., description="Unique identifier for the argument")
    argument: str = Field(..., description="The extracted argument text")
    x: float = Field(..., description="X coordinate for visualization (from UMAP)")
    y: float = Field(..., description="Y coordinate for visualization (from UMAP)")
    p: float = Field(..., description="Priority/importance score")
    cluster_ids: list[str] = Field(..., description="List of cluster IDs this argument belongs to")
    attributes: dict[str, str] | None = Field(None, description="Optional attributes from original comment")
    url: str | None = Field(None, description="Optional URL link to source")


class Cluster(BaseModel):
    """Schema for a cluster in the hierarchy."""

    level: int = Field(..., ge=0, description="Hierarchy level (0 = root)")
    id: str = Field(..., description="Unique cluster identifier")
    label: str = Field(..., description="Human-readable cluster label (LLM-generated)")
    takeaway: str = Field(..., description="Summary of the cluster (LLM-generated)")
    value: int = Field(..., ge=0, description="Number of arguments in this cluster")
    parent: str = Field(..., description="Parent cluster ID (empty for root)")
    density_rank_percentile: float | None = Field(None, description="Density ranking percentile")


class HierarchicalResult(BaseModel):
    """Schema for the complete hierarchical_result.json output."""

    arguments: list[Argument] = Field(..., description="List of all extracted arguments")
    clusters: list[Cluster] = Field(..., description="List of all clusters in the hierarchy")
    comment_num: int = Field(..., ge=0, description="Total number of original comments")
    overview: str = Field(..., description="Overall summary of the analysis (LLM-generated)")
    propertyMap: dict = Field(default_factory=dict, description="Property mappings for arguments")
    translations: dict = Field(default_factory=dict, description="Translation mappings")
    config: dict = Field(..., description="Configuration used for the analysis")

    def validate_structure(self) -> list[str]:
        """Perform additional structural validation.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        # Check that we have at least one argument
        if len(self.arguments) == 0:
            errors.append("No arguments were extracted")

        # Check that we have at least one cluster (root cluster)
        if len(self.clusters) == 0:
            errors.append("No clusters were generated")

        # Check that root cluster exists
        root_clusters = [c for c in self.clusters if c.level == 0]
        if len(root_clusters) == 0:
            errors.append("Missing root cluster (level 0)")

        # Check cluster hierarchy consistency
        cluster_ids = {c.id for c in self.clusters}
        for cluster in self.clusters:
            if cluster.parent and cluster.parent not in cluster_ids and cluster.level > 0:
                # Parent can be empty string for root or reference a valid cluster
                if cluster.parent != "":
                    errors.append(f"Cluster {cluster.id} has invalid parent: {cluster.parent}")

        # Check that all arguments have valid cluster references
        for arg in self.arguments:
            for cid in arg.cluster_ids:
                if cid not in cluster_ids and cid != "0":  # "0" is always the root
                    errors.append(f"Argument {arg.arg_id} references invalid cluster: {cid}")

        # Check that overview is not empty
        if not self.overview or len(self.overview.strip()) == 0:
            errors.append("Overview is empty")

        return errors
