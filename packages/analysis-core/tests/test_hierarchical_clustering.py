"""Tests for hierarchical clustering helpers."""

from analysis_core.steps.hierarchical_clustering import calculate_recommended_cluster_nums


class TestCalculateRecommendedClusterNums:
    """Tests for automatic cluster count recommendation."""

    def test_returns_expected_counts_for_1000_arguments(self):
        """1000 arguments should map to the issue's target recommendation."""
        assert calculate_recommended_cluster_nums(1000) == [10, 100]

    def test_uses_cube_root_based_scaling(self):
        """Smaller datasets should follow the same scaling rule."""
        assert calculate_recommended_cluster_nums(125) == [5, 25]
        assert calculate_recommended_cluster_nums(400) == [7, 49]

    def test_enforces_minimum_cluster_counts(self):
        """Very small datasets should still get a valid two-level hierarchy."""
        assert calculate_recommended_cluster_nums(2) == [2]
        assert calculate_recommended_cluster_nums(3) == [2, 3]
