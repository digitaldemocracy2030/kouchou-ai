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
from analysis_core.plugins.builtin._legacy_config import build_legacy_runtime_config


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
        - cluster_nums (optional): List of cluster counts for each level (e.g., [3, 6, 12])
    """
    from analysis_core.steps.hierarchical_clustering import (
        hierarchical_clustering as clustering_impl,
    )

    step_config = config.get("hierarchical_clustering", config)
    # reuse_umap_model は workflow template に無いため、full config から読む (#515)。
    full_clustering = {}
    if isinstance(inputs.config, dict):
        candidate = inputs.config.get("hierarchical_clustering")
        if isinstance(candidate, dict):
            full_clustering = candidate
    legacy_config = build_legacy_runtime_config(ctx, inputs)
    legacy_config["hierarchical_clustering"] = {
        "cluster_nums": step_config.get("cluster_nums"),
        "reuse_umap_model": step_config.get("reuse_umap_model") or full_clustering.get("reuse_umap_model"),
    }

    clustering_impl(legacy_config)

    # Use ctx.output_dir which already contains the full path
    return StepOutputs(
        artifacts={
            "clusters": ctx.output_dir / "hierarchical_clusters.csv",
        },
    )
