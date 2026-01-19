"""
Hierarchical clustering step plugin.

Performs UMAP dimensionality reduction and hierarchical clustering.
"""

from typing import Any

from analysis_core.plugin import (
    StepContext,
    StepInputs,
    StepOutputs,
    step_plugin,
)


@step_plugin(
    id="analysis.hierarchical_clustering",
    version="1.0.0",
    name="Hierarchical Clustering",
    description="Perform UMAP dimensionality reduction and hierarchical clustering",
    inputs=["arguments", "embeddings"],
    outputs=["clusters"],
    use_llm=False,
)
def hierarchical_clustering_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """
    Perform hierarchical clustering on embeddings.

    Uses UMAP for dimensionality reduction and KMeans + hierarchical
    merge for multi-level clustering.

    Config options:
        - cluster_nums: List of cluster counts for each level (e.g., [3, 6, 12])
    """
    from analysis_core.steps.hierarchical_clustering import (
        hierarchical_clustering as clustering_impl,
    )

    step_config = config.get("hierarchical_clustering", config)
    legacy_config = {
        "output_dir": ctx.dataset,
        "hierarchical_clustering": {
            "cluster_nums": step_config.get("cluster_nums", [3, 6]),
        },
    }

    clustering_impl(legacy_config)

    # Use ctx.output_dir which already contains the full path
    return StepOutputs(
        artifacts={
            "clusters": ctx.output_dir / "hierarchical_clusters.csv",
        },
    )
