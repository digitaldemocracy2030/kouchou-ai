"""
Default hierarchical clustering workflow.

This workflow implements the standard analysis pipeline:
1. Extract opinions from comments
2. Create embeddings
3. Perform hierarchical clustering
4. Label clusters at each level
5. Generate overview summary
6. Aggregate results
7. (Optional) Generate HTML visualization
"""

from analysis_core.workflow import WorkflowDefinition, WorkflowStep


def create_hierarchical_workflow(
    include_visualization: bool = True,
) -> WorkflowDefinition:
    """
    Create a hierarchical clustering workflow.

    Args:
        include_visualization: Whether to include the HTML visualization step

    Returns:
        WorkflowDefinition for hierarchical analysis
    """
    steps = [
        WorkflowStep(
            id="extraction",
            plugin="analysis.extraction",
            config={
                "limit": "${config.extraction.limit}",
                "workers": "${config.extraction.workers}",
                "prompt": "${config.extraction.prompt}",
                "model": "${config.extraction.model}",
                "properties": "${config.extraction.properties}",
            },
        ),
        WorkflowStep(
            id="embedding",
            plugin="analysis.embedding",
            depends_on=["extraction"],
            config={
                "model": "${config.embedding.model}",
            },
        ),
        WorkflowStep(
            id="clustering",
            plugin="analysis.hierarchical_clustering",
            depends_on=["embedding"],
            config={
                "cluster_nums": "${config.hierarchical_clustering.cluster_nums}",
            },
        ),
        WorkflowStep(
            id="initial_labelling",
            plugin="analysis.hierarchical_initial_labelling",
            depends_on=["clustering"],
            config={
                "sampling_num": "${config.hierarchical_initial_labelling.sampling_num}",
                "prompt": "${config.hierarchical_initial_labelling.prompt}",
                "model": "${config.hierarchical_initial_labelling.model}",
                "workers": "${config.hierarchical_initial_labelling.workers}",
            },
        ),
        WorkflowStep(
            id="merge_labelling",
            plugin="analysis.hierarchical_merge_labelling",
            depends_on=["initial_labelling"],
            config={
                "sampling_num": "${config.hierarchical_merge_labelling.sampling_num}",
                "prompt": "${config.hierarchical_merge_labelling.prompt}",
                "model": "${config.hierarchical_merge_labelling.model}",
                "workers": "${config.hierarchical_merge_labelling.workers}",
            },
        ),
        WorkflowStep(
            id="overview",
            plugin="analysis.hierarchical_overview",
            depends_on=["merge_labelling"],
            config={
                "prompt": "${config.hierarchical_overview.prompt}",
                "model": "${config.hierarchical_overview.model}",
            },
        ),
        WorkflowStep(
            id="aggregation",
            plugin="analysis.hierarchical_aggregation",
            depends_on=["extraction", "clustering", "merge_labelling", "overview"],
            config={
                "hidden_properties": "${config.hierarchical_aggregation.hidden_properties}",
            },
        ),
    ]

    if include_visualization:
        steps.append(
            WorkflowStep(
                id="visualization",
                plugin="analysis.hierarchical_visualization",
                depends_on=["aggregation"],
                optional=True,
                condition="${not config.without_html}",
                config={
                    "report_dir": "${config.report_dir}",
                },
            )
        )

    return WorkflowDefinition(
        id="hierarchical-default",
        version="1.0.0",
        name="Hierarchical Clustering (Default)",
        description="Standard hierarchical clustering analysis workflow with multi-level clustering and LLM labeling",
        steps=steps,
    )


# Pre-instantiated default workflow
HIERARCHICAL_DEFAULT_WORKFLOW = create_hierarchical_workflow(include_visualization=True)
