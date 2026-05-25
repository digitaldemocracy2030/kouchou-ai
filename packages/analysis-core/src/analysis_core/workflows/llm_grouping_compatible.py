"""Workflow that uses LLM for grouping while keeping embedding-based coordinates."""

from analysis_core.workflow import WorkflowDefinition, WorkflowStep


def create_llm_grouping_workflow(include_visualization: bool = True) -> WorkflowDefinition:
    """Create the short-term compatibility workflow for LLM grouping."""
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
            id="llm_grouping",
            plugin="analysis.llm_grouping",
            depends_on=["extraction", "embedding"],
            config={
                "group_count": "${config.llm_grouping.group_count}",
                "discovery_sample_size": "${config.llm_grouping.discovery_sample_size}",
                "assignment_batch_size": "${config.llm_grouping.assignment_batch_size}",
                "discovery_prompt": "${config.llm_grouping.discovery_prompt}",
                "assignment_prompt": "${config.llm_grouping.assignment_prompt}",
                "model": "${config.llm_grouping.model}",
            },
        ),
        WorkflowStep(
            id="label_refinement",
            plugin="analysis.hierarchical_label_refinement",
            depends_on=["llm_grouping"],
            config={
                "mode": "${config.hierarchical_label_refinement.mode}",
                "prompt": "${config.hierarchical_label_refinement.prompt}",
                "model": "${config.hierarchical_label_refinement.model}",
                "max_label_length": "${config.hierarchical_label_refinement.max_label_length}",
            },
        ),
        WorkflowStep(
            id="overview",
            plugin="analysis.hierarchical_overview",
            depends_on=["label_refinement"],
            config={
                "prompt": "${config.hierarchical_overview.prompt}",
                "model": "${config.hierarchical_overview.model}",
            },
        ),
        WorkflowStep(
            id="aggregation",
            plugin="analysis.hierarchical_aggregation",
            depends_on=["extraction", "llm_grouping", "label_refinement", "overview"],
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
                config={},
            )
        )

    return WorkflowDefinition(
        id="llm-grouping-compatible",
        version="1.0.0",
        name="LLM Grouping (Compatibility)",
        description="LLM-based grouping with embedding-derived scatter coordinates for viewer compatibility",
        steps=steps,
    )


LLM_GROUPING_COMPATIBLE_WORKFLOW = create_llm_grouping_workflow(include_visualization=True)
