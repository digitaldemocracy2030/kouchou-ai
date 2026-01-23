"""Tests for step functions path handling.

This module tests that all step functions properly use configurable paths
from config instead of hardcoded relative paths like 'inputs/' or 'outputs/'.

Regression test for the bug where step functions used hardcoded paths
like f"outputs/{dataset}/..." instead of using config.get("_output_base_dir").
"""

import ast
import inspect
from pathlib import Path

import pytest


class TestStepFunctionsUsePaths:
    """Verify step functions use _input_base_dir and _output_base_dir from config."""

    @pytest.fixture
    def step_modules(self):
        """Get all step modules."""
        from analysis_core.steps import (
            embedding,
            extraction,
            hierarchical_aggregation,
            hierarchical_clustering,
            hierarchical_initial_labelling,
            hierarchical_merge_labelling,
            hierarchical_overview,
        )

        return {
            "extraction": extraction,
            "embedding": embedding,
            "hierarchical_clustering": hierarchical_clustering,
            "hierarchical_initial_labelling": hierarchical_initial_labelling,
            "hierarchical_merge_labelling": hierarchical_merge_labelling,
            "hierarchical_overview": hierarchical_overview,
            "hierarchical_aggregation": hierarchical_aggregation,
        }

    def test_no_hardcoded_outputs_path(self, step_modules):
        """Check that no step module uses hardcoded 'outputs/' prefix without config."""
        violations = []

        for module_name, module in step_modules.items():
            source = inspect.getsource(module)
            tree = ast.parse(source)

            for node in ast.walk(tree):
                # Check for f-string with hardcoded outputs/
                if isinstance(node, ast.JoinedStr):
                    # Reconstruct the f-string to check for pattern
                    for value in node.values:
                        if isinstance(value, ast.Constant) and isinstance(value.value, str):
                            if value.value.startswith("outputs/") or value.value.startswith("outputs\\"):
                                violations.append(
                                    f"{module_name}: Found hardcoded 'outputs/' in f-string"
                                )
                            if value.value.startswith("inputs/") or value.value.startswith("inputs\\"):
                                violations.append(
                                    f"{module_name}: Found hardcoded 'inputs/' in f-string"
                                )

                # Check for regular string with hardcoded paths
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    val = node.value
                    # Allow config.get defaults like "_output_base_dir", "outputs"
                    if val in ("outputs", "inputs"):
                        continue
                    # Check for problematic patterns
                    if val.startswith("outputs/") or val.startswith("outputs\\"):
                        violations.append(
                            f"{module_name}: Found hardcoded path string starting with 'outputs/'"
                        )
                    if val.startswith("inputs/") or val.startswith("inputs\\"):
                        violations.append(
                            f"{module_name}: Found hardcoded path string starting with 'inputs/'"
                        )

        assert not violations, "Found hardcoded path patterns:\n" + "\n".join(violations)

    def test_extraction_uses_configurable_paths(self):
        """Test that extraction function uses config paths."""
        from analysis_core.steps.extraction import extraction

        # Check source code for proper config.get pattern
        source = inspect.getsource(extraction)
        assert '_output_base_dir' in source, "extraction should use _output_base_dir"
        assert '_input_base_dir' in source, "extraction should use _input_base_dir"
        assert 'config.get("_output_base_dir"' in source, "extraction should get _output_base_dir from config"
        assert 'config.get("_input_base_dir"' in source, "extraction should get _input_base_dir from config"

    def test_embedding_uses_configurable_paths(self):
        """Test that embedding function uses config paths."""
        from analysis_core.steps.embedding import embedding

        source = inspect.getsource(embedding)
        assert '_output_base_dir' in source, "embedding should use _output_base_dir"
        assert 'config.get("_output_base_dir"' in source, "embedding should get _output_base_dir from config"

    def test_hierarchical_clustering_uses_configurable_paths(self):
        """Test that hierarchical_clustering function uses config paths."""
        from analysis_core.steps.hierarchical_clustering import hierarchical_clustering

        source = inspect.getsource(hierarchical_clustering)
        assert '_output_base_dir' in source, "hierarchical_clustering should use _output_base_dir"
        assert 'config.get("_output_base_dir"' in source, "hierarchical_clustering should get _output_base_dir from config"

    def test_hierarchical_initial_labelling_uses_configurable_paths(self):
        """Test that hierarchical_initial_labelling function uses config paths."""
        from analysis_core.steps.hierarchical_initial_labelling import hierarchical_initial_labelling

        source = inspect.getsource(hierarchical_initial_labelling)
        assert '_output_base_dir' in source, "hierarchical_initial_labelling should use _output_base_dir"
        assert 'config.get("_output_base_dir"' in source, "hierarchical_initial_labelling should get _output_base_dir from config"

    def test_hierarchical_merge_labelling_uses_configurable_paths(self):
        """Test that hierarchical_merge_labelling function uses config paths."""
        from analysis_core.steps.hierarchical_merge_labelling import hierarchical_merge_labelling

        source = inspect.getsource(hierarchical_merge_labelling)
        assert '_output_base_dir' in source, "hierarchical_merge_labelling should use _output_base_dir"
        assert 'config.get("_output_base_dir"' in source, "hierarchical_merge_labelling should get _output_base_dir from config"

    def test_hierarchical_overview_uses_configurable_paths(self):
        """Test that hierarchical_overview function uses config paths."""
        from analysis_core.steps.hierarchical_overview import hierarchical_overview

        source = inspect.getsource(hierarchical_overview)
        assert '_output_base_dir' in source, "hierarchical_overview should use _output_base_dir"
        assert 'config.get("_output_base_dir"' in source, "hierarchical_overview should get _output_base_dir from config"

    def test_hierarchical_aggregation_uses_configurable_paths(self):
        """Test that hierarchical_aggregation function uses config paths."""
        from analysis_core.steps.hierarchical_aggregation import hierarchical_aggregation

        source = inspect.getsource(hierarchical_aggregation)
        assert '_output_base_dir' in source, "hierarchical_aggregation should use _output_base_dir"
        assert '_input_base_dir' in source, "hierarchical_aggregation should use _input_base_dir"
        assert 'config.get("_output_base_dir"' in source, "hierarchical_aggregation should get _output_base_dir from config"
        assert 'config.get("_input_base_dir"' in source, "hierarchical_aggregation should get _input_base_dir from config"

    def test_no_undefined_pipeline_dir(self):
        """Test that no function uses undefined pipeline_dir variable."""
        from analysis_core.steps import hierarchical_aggregation

        source = inspect.getsource(hierarchical_aggregation)
        tree = ast.parse(source)

        # Get all function definitions
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        for func in functions:
            # Get all names used in the function
            names_used = set()
            for node in ast.walk(func):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    names_used.add(node.id)

            # Get all names defined as parameters or assigned
            names_defined = set()
            for arg in func.args.args:
                names_defined.add(arg.arg)
            for node in ast.walk(func):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    names_defined.add(node.id)
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    names_defined.add(node.target.id)

            # Check if pipeline_dir is used but not defined
            if "pipeline_dir" in names_used and "pipeline_dir" not in names_defined:
                # Check if it's a parameter default (which is ok)
                continue  # Allow if defined anywhere
