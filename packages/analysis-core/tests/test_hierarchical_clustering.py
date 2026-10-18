"""Tests for hierarchical clustering helpers."""

import numpy as np
import pytest

from analysis_core.steps.hierarchical_clustering import (
    calculate_recommended_cluster_nums,
    hierarchical_clustering_embeddings,
    normalize_cluster_nums,
)


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


class _FakeKMeans:
    """Deterministic stand-in for sklearn KMeans that records n_clusters."""

    instances: list["_FakeKMeans"] = []

    def __init__(self, n_clusters):
        self.n_clusters = n_clusters
        _FakeKMeans.instances.append(self)

    def fit(self, X):
        n_samples = len(X)
        if self.n_clusters > n_samples:
            raise ValueError(f"n_samples={n_samples} should be >= n_clusters={self.n_clusters}.")
        self.labels_ = np.arange(n_samples) % self.n_clusters
        self.cluster_centers_ = np.array([X[self.labels_ == k].mean(axis=0) for k in range(self.n_clusters)])
        return self


def _embeds(n=60):
    rng = np.random.default_rng(0)
    return rng.normal(size=(n, 2))


class TestHierarchicalClusteringEmbeddingsClusterNums:
    """Regression tests: cluster_nums order / duplicates / mutation / upper bound."""

    def setup_method(self):
        _FakeKMeans.instances = []

    def test_descending_input_uses_max_for_initial_kmeans(self):
        """[50, 5] must run KMeans with 50 and keep both levels (not silently drop 50)."""
        cluster_nums = [50, 5]
        results = hierarchical_clustering_embeddings(_embeds(), cluster_nums, kmeans_class=_FakeKMeans)

        assert [k.n_clusters for k in _FakeKMeans.instances] == [50]
        assert list(results.keys()) == [5, 50]
        assert len(set(results[50].tolist())) == 50
        assert len(set(results[5].tolist())) == 5

    def test_does_not_mutate_caller_config(self):
        """In-place sort would change config (params diff / rerun detection)."""
        cluster_nums = [50, 5]
        hierarchical_clustering_embeddings(_embeds(), cluster_nums, kmeans_class=_FakeKMeans)
        assert cluster_nums == [50, 5]

    def test_duplicates_are_collapsed(self):
        results = hierarchical_clustering_embeddings(_embeds(), [10, 10], kmeans_class=_FakeKMeans)
        assert list(results.keys()) == [10]
        assert len(set(results[10].tolist())) == 10

    def test_cluster_count_above_argument_count_is_clamped(self, capsys):
        results = hierarchical_clustering_embeddings(_embeds(8), [3, 20], kmeans_class=_FakeKMeans)
        assert [k.n_clusters for k in _FakeKMeans.instances] == [8]
        assert list(results.keys()) == [3, 8]
        assert "Warning" in capsys.readouterr().out


class TestNormalizeClusterNums:
    def test_sorts_dedupes_and_clamps_without_mutation(self):
        original = [50, 5, 5, 200]
        assert normalize_cluster_nums(original, 100) == [5, 50, 100]
        assert original == [50, 5, 5, 200]

    def test_accepts_numpy_integers(self):
        assert normalize_cluster_nums([np.int64(3), np.int64(9)], 100) == [3, 9]

    @pytest.mark.parametrize("bad", [[], [0, 5], [-1], [2.5], ["5"], [True, 5]])
    def test_rejects_invalid_values(self, bad):
        with pytest.raises(ValueError):
            normalize_cluster_nums(bad, 100)
