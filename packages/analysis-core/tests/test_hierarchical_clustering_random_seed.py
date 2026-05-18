"""Regression tests for random seed usage in hierarchical clustering."""

import ast
from pathlib import Path


def _load_module_tree():
    module_path = Path(__file__).parent.parent / "src/analysis_core/steps/hierarchical_clustering.py"
    return ast.parse(module_path.read_text()), module_path


def test_hierarchical_clustering_does_not_fix_random_seed():
    """UMAP and KMeans should not receive a fixed random_state=42."""
    tree, module_path = _load_module_tree()
    fixed_seed_calls = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func
        if not isinstance(func, ast.Name) or func.id not in {"UMAP", "KMeans"}:
            continue

        for keyword in node.keywords:
            if keyword.arg != "random_state":
                continue
            if isinstance(keyword.value, ast.Constant) and keyword.value.value == 42:
                fixed_seed_calls.append(func.id)

    assert not fixed_seed_calls, f"{module_path} still fixes random_state=42 for {fixed_seed_calls}"
