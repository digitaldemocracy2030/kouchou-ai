"""embeddings.pkl の形式とメモリの扱いのテスト。

- embedding ステップは埋め込みを float32 の配列で保存する（Python float の list のまま
  保持すると 1536 次元・数万件で GB 単位のメモリを使い、OOM の原因になる）。
- 読み込み側（hierarchical_clustering / llm_grouping / hierarchical_layout_generation）は
  旧形式（list[float] の list[dict]、arg-id なし、DataFrame）も読める。
- 読み込んだ list / dict は UMAP の前に解放する。
"""

import gc
import pickle

import numpy as np
import polars as pl
import pytest

import analysis_core.steps.embedding as embedding_mod
import analysis_core.steps.hierarchical_clustering as hc_mod
import analysis_core.steps.llm_grouping as llm_grouping_mod
from analysis_core.steps._embeddings_io import stack_embedding_rows
from analysis_core.steps.hierarchical_layout_generation import _load_embeddings

# 他のテストや import で作られる list と衝突しにくい次元数
DIM = 37
N = 24


def _matrix(n=N, dim=DIM, seed=0):
    """OpenAI SDK と同じく、float32 由来の値を持つ埋め込み行列。"""
    rng = np.random.default_rng(seed)
    return rng.normal(size=(n, dim)).astype(np.float32)


def _arg_ids(n=N):
    return [f"A{i}_0" for i in range(n)]


def _write_args(ds_dir, arg_ids):
    ds_dir.mkdir(parents=True, exist_ok=True)
    pl.DataFrame({"arg-id": arg_ids, "argument": [f"意見 {a}" for a in arg_ids]}).write_csv(str(ds_dir / "args.csv"))


class _FakeSeries:
    def __init__(self, values):
        self.values = np.empty(len(values), dtype=object)
        for i, v in enumerate(values):
            self.values[i] = v


class _FakeFrame:
    """旧形式（pandas DataFrame）の代役。pandas と同じく ``df["embedding"].values`` を持つ。"""

    def __init__(self, arg_ids, rows):
        self._cols = {"arg-id": _FakeSeries(arg_ids), "embedding": _FakeSeries(rows)}

    def __getitem__(self, key):
        return self._cols[key]


def _legacy_records(arg_ids, matrix):
    """旧形式: Python float の list を持つ list[dict]。"""
    return [{"arg-id": a, "embedding": row.tolist()} for a, row in zip(arg_ids, matrix, strict=True)]


def _new_records(arg_ids, matrix):
    """現行形式: float32 の 1 次元配列を持つ list[dict]。"""
    return [{"arg-id": a, "embedding": row.copy()} for a, row in zip(arg_ids, matrix, strict=True)]


def _write_pickle(path, data):
    with open(path, "wb") as f:
        pickle.dump(data, f)


def _count_float_lists(dim):
    gc.collect()
    return sum(1 for o in gc.get_objects() if type(o) is list and len(o) == dim and o and type(o[0]) is float)


class TestEmbeddingStepStoresFloat32:
    def test_embeddings_pkl_holds_float32_arrays_in_arg_id_order(self, tmp_path, monkeypatch):
        matrix = _matrix()
        arg_ids = _arg_ids()
        _write_args(tmp_path / "ds", arg_ids)
        texts = {f"意見 {a}": i for i, a in enumerate(arg_ids)}

        def fake_embed(args, *a, **kw):
            # OpenAI SDK と同じく Python float の list を返す
            return [matrix[texts[t]].tolist() for t in args]

        monkeypatch.setattr(embedding_mod, "request_to_embed", fake_embed)
        embedding_mod.embedding(
            {
                "output_dir": "ds",
                "_output_base_dir": str(tmp_path),
                "embedding": {"model": "text-embedding-3-small"},
                "is_embedded_at_local": False,
                "provider": "openai",
            }
        )

        with open(tmp_path / "ds" / "embeddings.pkl", "rb") as f:
            data = pickle.load(f)

        assert isinstance(data, list)
        assert [item["arg-id"] for item in data] == arg_ids
        for item, expected in zip(data, matrix, strict=True):
            assert isinstance(item["embedding"], np.ndarray)
            assert item["embedding"].dtype == np.float32
            assert item["embedding"].shape == (DIM,)
            np.testing.assert_array_equal(item["embedding"], expected)

        # 旧バージョンの読み込み処理（np.asarray で積む）でも同じ値になる
        np.testing.assert_array_equal(np.asarray([item["embedding"] for item in data]), matrix)


class _CapturingUMAP:
    captured: list = []
    float_lists_alive: list = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def fit_transform(self, X):
        _CapturingUMAP.captured.append(X)
        _CapturingUMAP.float_lists_alive.append(_count_float_lists(DIM))
        return np.asarray(X, dtype=np.float64)[:, :2]


class _FakeKMeans:
    def __init__(self, n_clusters):
        self.n_clusters = n_clusters

    def fit(self, X):
        self.labels_ = np.arange(len(X)) % self.n_clusters
        self.cluster_centers_ = np.array([X[self.labels_ == k].mean(axis=0) for k in range(self.n_clusters)])
        return self


@pytest.fixture
def capturing_umap(monkeypatch):
    _CapturingUMAP.captured = []
    _CapturingUMAP.float_lists_alive = []
    _, sch, _ = hc_mod._load_clustering_dependencies()
    monkeypatch.setattr(hc_mod, "_load_clustering_dependencies", lambda: (_CapturingUMAP, sch, _FakeKMeans))
    monkeypatch.setattr(llm_grouping_mod, "_load_clustering_dependencies", lambda: (_CapturingUMAP, sch, _FakeKMeans))
    return _CapturingUMAP


def _run_clustering(tmp_path, build_data, arg_ids):
    """build_data() で作った embeddings.pkl を書き、hierarchical_clustering を実行する。

    呼び出し側に list を残さないよう、データは関数で受け取ってこの中で作る。
    """
    ds_dir = tmp_path / "ds"
    _write_args(ds_dir, arg_ids)
    _write_pickle(ds_dir / "embeddings.pkl", build_data())
    hc_mod.hierarchical_clustering(
        {
            "output_dir": "ds",
            "_output_base_dir": str(tmp_path),
            "hierarchical_clustering": {"cluster_nums": [2, 4]},
        }
    )
    return ds_dir


FORMATS = {
    "new_float32_records": lambda ids, m: _new_records(ids, m),
    "legacy_float_list_records": lambda ids, m: _legacy_records(ids, m),
    "legacy_records_without_arg_id": lambda ids, m: [{"embedding": row.tolist()} for row in m],
    "legacy_dataframe": lambda ids, m: _FakeFrame(ids, [row.tolist() for row in m]),
}


class TestHierarchicalClusteringReadsAllFormats:
    @pytest.mark.parametrize("fmt", list(FORMATS))
    def test_umap_input_is_float32_and_identical_across_formats(self, tmp_path, capturing_umap, fmt):
        matrix = _matrix()
        arg_ids = _arg_ids()
        _run_clustering(tmp_path, lambda: FORMATS[fmt](arg_ids, matrix), arg_ids)

        (X,) = capturing_umap.captured
        assert X.dtype == np.float32
        assert X.flags["C_CONTIGUOUS"]
        np.testing.assert_array_equal(X, matrix)

    @pytest.mark.parametrize("fmt", ["new_float32_records", "legacy_float_list_records"])
    def test_records_are_reordered_by_args_csv(self, tmp_path, capturing_umap, fmt):
        matrix = _matrix()
        arg_ids = _arg_ids()
        records = FORMATS[fmt](arg_ids, matrix)
        records.reverse()
        _run_clustering(tmp_path, lambda: records, arg_ids)

        (X,) = capturing_umap.captured
        np.testing.assert_array_equal(X, matrix)

    def test_missing_arg_id_still_raises(self, tmp_path, capturing_umap):
        matrix = _matrix()
        arg_ids = _arg_ids()
        records = _legacy_records(arg_ids, matrix)[:-1]
        with pytest.raises(ValueError, match="存在しない arg-id"):
            _run_clustering(tmp_path, lambda: records, arg_ids)

    def test_legacy_python_lists_are_released_before_umap(self, tmp_path, capturing_umap):
        """旧形式を読んだときも、Python float の list を UMAP の前に解放する。"""
        matrix = _matrix()
        arg_ids = _arg_ids()
        baseline = _count_float_lists(DIM)
        _run_clustering(tmp_path, lambda: _legacy_records(arg_ids, matrix), arg_ids)

        assert capturing_umap.float_lists_alive == [baseline]


class TestLlmGroupingProjection:
    @pytest.mark.parametrize("fmt", list(FORMATS))
    def test_projection_input_is_float32_and_lists_are_released(self, tmp_path, capturing_umap, fmt):
        matrix = _matrix()
        arg_ids = _arg_ids()
        ds_dir = tmp_path / "ds"
        ds_dir.mkdir()
        _write_pickle(ds_dir / "embeddings.pkl", FORMATS[fmt](arg_ids, matrix))
        baseline = _count_float_lists(DIM)

        llm_grouping_mod._project_embeddings_to_xy(str(tmp_path), "ds", arg_ids)

        (X,) = capturing_umap.captured
        assert X.dtype == np.float32
        np.testing.assert_array_equal(X, matrix)
        assert capturing_umap.float_lists_alive == [baseline]


class TestLayoutGenerationLoader:
    @pytest.mark.parametrize("fmt", ["new_float32_records", "legacy_float_list_records", "legacy_dataframe"])
    def test_loads_all_formats_as_float64_with_same_values(self, tmp_path, fmt):
        matrix = _matrix()
        arg_ids = _arg_ids()
        path = tmp_path / "embeddings.pkl"
        _write_pickle(path, FORMATS[fmt](arg_ids, matrix))

        # 表示順を入れ替えても arg-id で引く
        order = list(reversed(arg_ids)) if fmt != "legacy_dataframe" else arg_ids
        loaded = _load_embeddings(path, order)

        assert loaded.dtype == np.float64
        expected = matrix[[arg_ids.index(a) for a in order]].astype(np.float64)
        np.testing.assert_array_equal(loaded, expected)


class TestStackEmbeddingRows:
    def test_empty(self):
        assert stack_embedding_rows([]).shape == (0, 0)

    def test_inconsistent_dimension_raises(self):
        with pytest.raises(ValueError):
            stack_embedding_rows([[0.0, 1.0], [0.0, 1.0, 2.0]])

    def test_matches_np_asarray(self):
        rows = [[0.1, 0.2, 0.3], np.array([1.5, 2.5, 3.5], dtype=np.float32)]
        out = stack_embedding_rows(rows)
        assert out.dtype == np.float32
        np.testing.assert_array_equal(out, np.asarray(rows, dtype=np.float32))
