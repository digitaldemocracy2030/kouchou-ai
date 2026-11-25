"""Regression test: the dict entrypoint must default hierarchical_clustering.cluster_nums.

Background
----------
The default hierarchical workflow's clustering step references
``${config.hierarchical_clustering.cluster_nums}`` (workflows/hierarchical_default.py).
The engine's variable resolver (``WorkflowEngine._resolve_step_config``) raises
``WorkflowExecutionError`` when a referenced nested key is absent while its parent
dict *is* present.

The file entrypoint (``from_config`` -> ``initialization``) fills ``cluster_nums=None``
from ``hierarchical_specs.json`` (treated as "auto-calculate" downstream), but the dict
entrypoint (``from_dict`` -> ``normalize_config``) used to leave it UNSET. That made
``from_dict`` + ``run_default`` crash for hierarchical mode whenever ``cluster_nums``
was not supplied. These tests pin the contract that the dict path now matches the file
path: the key resolves to ``None`` instead of raising.
"""

from analysis_core.compat import normalize_config
from analysis_core.workflow import WorkflowEngine, WorkflowExecutionError
from analysis_core.workflows import create_hierarchical_workflow


def _clustering_step_template() -> dict:
    """Return the clustering step's config template from the default workflow."""
    workflow = create_hierarchical_workflow()
    clustering_step = workflow.get_step("clustering")
    assert clustering_step is not None
    # Guard: this regression only makes sense while the template references the key.
    assert clustering_step.config["cluster_nums"] == "${config.hierarchical_clustering.cluster_nums}"
    return clustering_step.config


def test_normalize_config_defaults_cluster_nums_to_none():
    """normalize_config must emit hierarchical_clustering.cluster_nums = None (auto-calculate)."""
    result = normalize_config({}, include_source_code=False)

    assert "hierarchical_clustering" in result
    assert result["hierarchical_clustering"]["cluster_nums"] is None


def test_engine_resolves_cluster_nums_from_dict_path_without_raising():
    """The engine must resolve the clustering step template against a from_dict-style
    config to ``{"cluster_nums": None}`` instead of raising ``WorkflowExecutionError``.

    Before the fix, normalize_config left cluster_nums unset, so resolving
    ``${config.hierarchical_clustering.cluster_nums}`` raised WorkflowExecutionError
    ("Configuration key 'cluster_nums' not found ...").
    """
    normalized = normalize_config({}, include_source_code=False)
    template = _clustering_step_template()

    engine = WorkflowEngine()

    try:
        resolved = engine._resolve_step_config(template, normalized)
    except WorkflowExecutionError as exc:  # pragma: no cover - only hit on regression
        raise AssertionError(
            f"cluster_nums should resolve to None for the dict (from_dict) path, but the engine raised: {exc}"
        )

    assert resolved == {"cluster_nums": None}
