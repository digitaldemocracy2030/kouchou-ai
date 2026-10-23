"""Tests for reusing a fitted UMAP model across reports (#515).

These cover both the pure helpers (with an injected fake UMAP) and a real
round-trip with umap-learn to validate that a model fit on report A can project
report B's embeddings onto the same plane via ``.transform``.
"""

import pickle

import numpy as np
import polars as pl
import pytest

from analysis_core.steps.hierarchical_clustering import (
    UMAP_MODEL_FILENAME,
    _resolve_reuse_model_path,
    compute_umap_embeddings,
    hierarchical_clustering,
    load_umap_model,
    save_umap_model,
)


class _FakeUMAP:
    """Minimal UMAP stand-in recording whether fit/transform was used."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.fitted = False
        self.transform_called = False

    def fit_transform(self, X):
        self.fitted = True
        X = np.asarray(X)
        # Deterministic 2D projection: first two columns.
        return X[:, :2]

    def transform(self, X):
        self.transform_called = True
        X = np.asarray(X)
        return X[:, :2] + 100.0  # distinct marker so we can detect reuse


class TestResolveReuseModelPath:
    def test_none_returns_none(self, tmp_path):
        base = str(tmp_path)
        assert _resolve_reuse_model_path(None, base, "ds") is None
        assert _resolve_reuse_model_path("", base, "ds") is None

    def test_report_name_resolves_to_its_umap_model(self, tmp_path):
        # CLI-native flow: point at another report by name, no copy needed.
        model = tmp_path / "report_a" / UMAP_MODEL_FILENAME
        model.parent.mkdir(parents=True)
        model.write_bytes(b"x")
        assert _resolve_reuse_model_path("report_a", str(tmp_path), "report_b") == str(model)

    def test_relative_path_under_output_base(self, tmp_path):
        model = tmp_path / "report_a" / UMAP_MODEL_FILENAME
        model.parent.mkdir(parents=True)
        model.write_bytes(b"x")
        resolved = _resolve_reuse_model_path(f"report_a/{UMAP_MODEL_FILENAME}", str(tmp_path), "report_b")
        assert resolved == str(model)

    def test_own_dir_backcompat(self, tmp_path):
        # Back-compat: a file already copied into the current report's own dir.
        model = tmp_path / "ds" / UMAP_MODEL_FILENAME
        model.parent.mkdir(parents=True)
        model.write_bytes(b"x")
        assert _resolve_reuse_model_path(UMAP_MODEL_FILENAME, str(tmp_path), "ds") == str(model)

    def test_absolute_passthrough_when_file_exists(self, tmp_path):
        abs_path = tmp_path / "m.pkl"
        abs_path.write_bytes(b"x")
        assert _resolve_reuse_model_path(str(abs_path), str(tmp_path), "ds") == str(abs_path)

    def test_missing_relative_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="見つかりません"):
            _resolve_reuse_model_path("no_such_report", str(tmp_path), "ds")

    def test_missing_absolute_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="見つかりません"):
            _resolve_reuse_model_path(str(tmp_path / "nope.pkl"), str(tmp_path), "ds")

    def test_non_string_truthy_raises(self, tmp_path):
        # A config typo like `"reuse_umap_model": true` must not silently fit fresh.
        with pytest.raises(TypeError, match="文字列"):
            _resolve_reuse_model_path(True, str(tmp_path), "ds")
        with pytest.raises(TypeError, match="文字列"):
            _resolve_reuse_model_path(123, str(tmp_path), "ds")

    def test_falsy_non_string_means_no_reuse(self, tmp_path):
        assert _resolve_reuse_model_path(False, str(tmp_path), "ds") is None
        assert _resolve_reuse_model_path(0, str(tmp_path), "ds") is None


class TestConfigSpecAllowsReuseUmapModel:
    """Guard the end-to-end path: both the CLI and the orchestrator call
    ``validate_config`` during initialization. The step-level tests bypass it,
    so without this guard a missing spec option silently breaks every real run
    with ``Unknown option 'reuse_umap_model'`` (#515)."""

    def test_validate_config_accepts_reuse_umap_model(self):
        from analysis_core.core.orchestration import (
            get_specs_path_for_mode,
            load_specs,
            validate_config,
        )

        specs = load_specs(get_specs_path_for_mode("hierarchical"))
        config = {
            "input": "report_b",
            "question": "q",
            "analysis_mode": "hierarchical",
            "hierarchical_clustering": {"cluster_nums": [2, 4], "reuse_umap_model": "report_a"},
        }
        # Must not raise. Before the spec fix this raised "Unknown option ...".
        validate_config(config, specs)


class TestConfigSpecAllowsSaveUmapModel:
    """``save_umap_model``（umap_model.pkl を保存するか）も config で指定できる。"""

    def test_validate_config_accepts_save_umap_model(self):
        from analysis_core.core.orchestration import (
            get_specs_path_for_mode,
            load_specs,
            validate_config,
        )

        specs = load_specs(get_specs_path_for_mode("hierarchical"))
        config = {
            "input": "report_b",
            "question": "q",
            "analysis_mode": "hierarchical",
            "hierarchical_clustering": {"cluster_nums": [2, 4], "save_umap_model": False},
        }
        validate_config(config, specs)

    def test_save_umap_model_defaults_to_true_and_is_not_a_rerun_dependency(self):
        from analysis_core.core.orchestration import get_specs_path_for_mode, load_specs

        specs = load_specs(get_specs_path_for_mode("hierarchical"))
        (spec,) = [s for s in specs if s["step"] == "hierarchical_clustering"]
        # CLI の既定は従来どおり保存する（#515 の使い回し元になれる）
        assert spec["options"]["save_umap_model"] is True
        # 保存するかどうかはクラスタリングの結果を変えないので、変えても再実行しない
        assert "save_umap_model" not in spec["dependencies"]["params"]


class TestSaveLoadUmapModel:
    def test_round_trip_with_metadata(self, tmp_path):
        model = _FakeUMAP()
        path = str(tmp_path / UMAP_MODEL_FILENAME)
        save_umap_model(path, model, n_features_in=8, n_components=2)

        payload = load_umap_model(path)
        assert payload["n_features_in"] == 8
        assert payload["n_components"] == 2
        assert isinstance(payload["model"], _FakeUMAP)

    def test_backward_compat_raw_model(self, tmp_path):
        # Old-style pickle: just the model object, no metadata wrapper.
        model = _FakeUMAP()
        model.n_features_in_ = 5
        path = str(tmp_path / "raw.pkl")
        with open(path, "wb") as f:
            pickle.dump(model, f)

        payload = load_umap_model(path)
        assert isinstance(payload["model"], _FakeUMAP)
        assert payload["n_features_in"] == 5


class TestComputeUmapEmbeddings:
    def test_fit_path_uses_factory(self):
        X = np.random.rand(6, 4)
        created = {}

        def factory(**kwargs):
            m = _FakeUMAP(**kwargs)
            created["model"] = m
            return m

        embeds, model, n_features = compute_umap_embeddings(
            X, n_neighbors=3, reuse_model_path=None, umap_factory=factory
        )
        assert created["model"].fitted is True
        assert model.transform_called is False
        assert n_features == 4
        assert embeds.shape == (6, 2)

    def test_reuse_path_uses_transform(self, tmp_path):
        X = np.random.rand(6, 4)
        model = _FakeUMAP()
        model_path = str(tmp_path / UMAP_MODEL_FILENAME)
        save_umap_model(model_path, model, n_features_in=4, n_components=2)

        embeds, used_model, n_features = compute_umap_embeddings(
            X, n_neighbors=3, reuse_model_path=model_path, umap_factory=None
        )
        assert used_model.transform_called is True
        assert used_model.fitted is False
        # Transform marker (+100) proves transform (not fit_transform) was used.
        assert np.allclose(embeds, X[:, :2] + 100.0)
        assert n_features == 4

    def test_reuse_dimension_mismatch_raises(self, tmp_path):
        model = _FakeUMAP()
        model_path = str(tmp_path / UMAP_MODEL_FILENAME)
        save_umap_model(model_path, model, n_features_in=99, n_components=2)

        X = np.random.rand(6, 4)  # dim 4 != 99
        with pytest.raises(ValueError, match="次元が一致しません"):
            compute_umap_embeddings(X, n_neighbors=3, reuse_model_path=model_path)

    def test_reuse_missing_path_raises_not_silent_fit(self, tmp_path):
        # Standalone helper: a truthy-but-missing reuse path must error, not fit.
        X = np.random.rand(5, 4)
        with pytest.raises(FileNotFoundError, match="見つかりません"):
            compute_umap_embeddings(X, n_neighbors=3, reuse_model_path=str(tmp_path / "nope.pkl"))


class TestReuseModelReRunDecision:
    """``reuse_umap_model`` is in ``dependencies.params``, so editing it on an
    already-run report must re-run clustering instead of silently skipping
    ("nothing changed") and leaving the old plane in place (#515)."""

    def _setup(self, tmp_path, prev_reuse):
        from analysis_core.core.orchestration import get_specs_path_for_mode, load_specs

        specs = load_specs(get_specs_path_for_mode("hierarchical"))
        outdir = tmp_path / "report_x"
        outdir.mkdir(parents=True, exist_ok=True)
        for fn in ("args.csv", "relations.csv", "embeddings.pkl", "hierarchical_clusters.csv"):
            (outdir / fn).write_text("x")
        prev_jobs = [
            {"step": "extraction", "params": {"limit": 10, "workers": 1, "properties": []}},
            {"step": "embedding", "params": {"model": "text-embedding-3-small"}},
            {"step": "hierarchical_clustering", "params": {"cluster_nums": [2, 4], "reuse_umap_model": prev_reuse}},
        ]
        return specs, prev_jobs

    def _plan_by_step(self, tmp_path, specs, prev_jobs, next_reuse):
        from analysis_core.core.orchestration import decide_what_to_run

        config = {
            "input": "report_x",
            "question": "q",
            "output_dir": "report_x",
            "extraction": {"limit": 10, "workers": 1, "properties": []},
            "embedding": {"model": "text-embedding-3-small"},
            "hierarchical_clustering": {"cluster_nums": [2, 4], "reuse_umap_model": next_reuse},
            "previous": {"completed_jobs": prev_jobs},
        }
        plan = decide_what_to_run(config, config["previous"], specs, output_base_dir=tmp_path)
        return {p["step"]: p for p in plan}

    def test_changing_reuse_model_reruns_clustering(self, tmp_path):
        specs, prev_jobs = self._setup(tmp_path, prev_reuse=None)
        by_step = self._plan_by_step(tmp_path, specs, prev_jobs, next_reuse="report_a")
        assert by_step["hierarchical_clustering"]["run"] is True

    def test_unchanged_reuse_model_skips_clustering(self, tmp_path):
        specs, prev_jobs = self._setup(tmp_path, prev_reuse="report_a")
        by_step = self._plan_by_step(tmp_path, specs, prev_jobs, next_reuse="report_a")
        assert by_step["hierarchical_clustering"]["run"] is False


class TestPluginWiring:
    """Guard the runtime glue. The orchestrator passes the resolved workflow
    template (``cluster_nums`` only) as ``config`` and the full user config as
    ``inputs.config``. ``reuse_umap_model`` is not in the template, so the plugin
    must forward it to the legacy step from ``inputs.config`` (#515)."""

    def test_plugin_forwards_reuse_umap_model_from_full_config(self, tmp_path, monkeypatch):
        import importlib

        from analysis_core.plugin import StepContext, StepInputs
        from analysis_core.plugins.builtin.hierarchical_clustering import hierarchical_clustering_plugin

        # Use import_module: the ``analysis_core.steps`` package re-exports the
        # ``hierarchical_clustering`` function, which shadows the submodule
        # attribute, so ``import ... as step_mod`` can bind the function instead.
        step_mod = importlib.import_module("analysis_core.steps.hierarchical_clustering")

        captured = {}

        def fake_impl(legacy_config):
            captured["legacy"] = legacy_config

        # The plugin imports clustering_impl from this module at call time.
        monkeypatch.setattr(step_mod, "hierarchical_clustering", fake_impl)

        output_dir = tmp_path / "outputs" / "report_b"
        output_dir.mkdir(parents=True)
        ctx = StepContext(
            output_dir=output_dir,
            input_dir=tmp_path / "inputs",
            dataset="report_b",
            provider="openai",
            model="gpt-4o-mini",
        )
        # Resolved workflow template: only cluster_nums (no reuse_umap_model).
        step_template_config = {"cluster_nums": [2, 4]}
        # Full user config carrying reuse_umap_model, as the engine supplies it.
        inputs = StepInputs(
            artifacts={},
            config={"hierarchical_clustering": {"cluster_nums": [2, 4], "reuse_umap_model": "report_a"}},
        )

        hierarchical_clustering_plugin.run(ctx, inputs, step_template_config)

        assert captured["legacy"]["hierarchical_clustering"]["reuse_umap_model"] == "report_a"
        assert captured["legacy"]["hierarchical_clustering"]["cluster_nums"] == [2, 4]


class TestPluginForwardsSaveUmapModel:
    @pytest.mark.parametrize(
        ("full_clustering", "expected"),
        [
            ({"cluster_nums": [2, 4], "save_umap_model": False}, False),
            ({"cluster_nums": [2, 4]}, True),
        ],
    )
    def test_plugin_forwards_save_umap_model_from_full_config(self, tmp_path, monkeypatch, full_clustering, expected):
        import importlib

        from analysis_core.plugin import StepContext, StepInputs
        from analysis_core.plugins.builtin.hierarchical_clustering import hierarchical_clustering_plugin

        step_mod = importlib.import_module("analysis_core.steps.hierarchical_clustering")
        captured = {}
        monkeypatch.setattr(step_mod, "hierarchical_clustering", lambda legacy: captured.update(legacy=legacy))

        output_dir = tmp_path / "outputs" / "report_b"
        output_dir.mkdir(parents=True)
        ctx = StepContext(
            output_dir=output_dir,
            input_dir=tmp_path / "inputs",
            dataset="report_b",
            provider="openai",
            model="gpt-4o-mini",
        )
        inputs = StepInputs(artifacts={}, config={"hierarchical_clustering": full_clustering})
        hierarchical_clustering_plugin.run(ctx, inputs, {"cluster_nums": [2, 4]})

        assert captured["legacy"]["hierarchical_clustering"]["save_umap_model"] is expected


def _write_dataset(base_dir, dataset, arg_ids, embeddings):
    ds_dir = base_dir / dataset
    ds_dir.mkdir(parents=True, exist_ok=True)
    pl.DataFrame({"arg-id": arg_ids, "argument": [f"arg {i}" for i in arg_ids]}).write_csv(str(ds_dir / "args.csv"))
    embedding_data = [{"arg-id": aid, "embedding": list(map(float, emb))} for aid, emb in zip(arg_ids, embeddings)]
    with open(ds_dir / "embeddings.pkl", "wb") as f:
        pickle.dump(embedding_data, f)
    return ds_dir


class TestHierarchicalClusteringReuseRealUmap:
    """End-to-end round trip with real umap-learn (#515 core use case)."""

    def test_fit_saves_model_and_reuse_projects_same_plane(self, tmp_path):
        rng = np.random.default_rng(42)
        dim = 16
        n = 40
        base = tmp_path / "outputs"

        # Report A: fit UMAP, saving umap_model.pkl.
        emb_a = rng.random((n, dim))
        ds_a = _write_dataset(base, "report_a", list(range(n)), emb_a)
        config_a = {
            "output_dir": "report_a",
            "_output_base_dir": str(base),
            "hierarchical_clustering": {"cluster_nums": [2, 4]},
        }
        hierarchical_clustering(config_a)

        model_path = ds_a / UMAP_MODEL_FILENAME
        assert model_path.exists(), "fit path must persist umap_model.pkl"

        result_a = pl.read_csv(str(ds_a / "hierarchical_clusters.csv"))
        xy_a = result_a.select(["x", "y"]).to_numpy()

        # Report B: NEW data (different rows), reuse A's model via transform.
        import shutil

        emb_b = rng.random((n, dim))
        ds_b = _write_dataset(base, "report_b", list(range(n)), emb_b)
        shutil.copy2(model_path, ds_b / UMAP_MODEL_FILENAME)
        config_b = {
            "output_dir": "report_b",
            "_output_base_dir": str(base),
            "hierarchical_clustering": {
                "cluster_nums": [2, 4],
                "reuse_umap_model": UMAP_MODEL_FILENAME,
            },
        }
        hierarchical_clustering(config_b)

        result_b = pl.read_csv(str(ds_b / "hierarchical_clusters.csv"))
        assert result_b.height == n

        # Re-feeding report A's OWN embeddings through the reused model must
        # reproduce A's coordinates (same plane), proving transform reuse works.
        emb_a_again = _write_dataset(base, "report_a2", list(range(n)), emb_a)
        shutil.copy2(model_path, emb_a_again / UMAP_MODEL_FILENAME)
        config_a2 = {
            "output_dir": "report_a2",
            "_output_base_dir": str(base),
            "hierarchical_clustering": {
                "cluster_nums": [2, 4],
                "reuse_umap_model": UMAP_MODEL_FILENAME,
            },
        }
        hierarchical_clustering(config_a2)
        result_a2 = pl.read_csv(str(emb_a_again / "hierarchical_clusters.csv"))
        xy_a2 = result_a2.select(["x", "y"]).to_numpy()
        assert np.allclose(xy_a, xy_a2, atol=1e-4), "reused model must project same data to same plane"

    def test_reuse_by_report_name_without_copy(self, tmp_path):
        """CLI-native flow: reference report A by name (no manual copy of the
        model into B's dir). ``reuse_umap_model: "report_a"`` must resolve to
        report A's umap_model.pkl and project B onto A's plane."""
        rng = np.random.default_rng(7)
        dim = 16
        n = 30
        base = tmp_path / "outputs"

        emb_a = rng.random((n, dim))
        ds_a = _write_dataset(base, "report_a", list(range(n)), emb_a)
        hierarchical_clustering(
            {
                "output_dir": "report_a",
                "_output_base_dir": str(base),
                "hierarchical_clustering": {"cluster_nums": [2, 4]},
            }
        )
        xy_a = pl.read_csv(str(ds_a / "hierarchical_clusters.csv")).select(["x", "y"]).to_numpy()

        # Report D reuses A by NAME only (no shutil.copy2 of the model).
        ds_d = _write_dataset(base, "report_d", list(range(n)), emb_a)
        hierarchical_clustering(
            {
                "output_dir": "report_d",
                "_output_base_dir": str(base),
                "hierarchical_clustering": {
                    "cluster_nums": [2, 4],
                    "reuse_umap_model": "report_a",
                },
            }
        )
        xy_d = pl.read_csv(str(ds_d / "hierarchical_clusters.csv")).select(["x", "y"]).to_numpy()
        assert np.allclose(xy_a, xy_d, atol=1e-4), "name-based reuse must project same data to same plane"

    def test_save_umap_model_false_skips_writing_model(self, tmp_path):
        """Web 経路（API）は #515 を使わないので、umap_model.pkl を書かない。"""
        rng = np.random.default_rng(3)
        base = tmp_path / "outputs"
        ds = _write_dataset(base, "report_web", list(range(20)), rng.random((20, 16)))
        hierarchical_clustering(
            {
                "output_dir": "report_web",
                "_output_base_dir": str(base),
                "hierarchical_clustering": {"cluster_nums": [2, 4], "save_umap_model": False},
            }
        )
        assert (ds / "hierarchical_clusters.csv").exists()
        assert not (ds / UMAP_MODEL_FILENAME).exists()

    def test_save_umap_model_false_removes_stale_model_from_previous_run(self, tmp_path):
        """前回の実行（保存あり）で残った umap_model.pkl は、今回の座標と食い違うので消す。"""
        rng = np.random.default_rng(4)
        base = tmp_path / "outputs"
        ds = _write_dataset(base, "report_web", list(range(20)), rng.random((20, 16)))
        (ds / UMAP_MODEL_FILENAME).write_bytes(b"stale")
        hierarchical_clustering(
            {
                "output_dir": "report_web",
                "_output_base_dir": str(base),
                "hierarchical_clustering": {"cluster_nums": [2, 4], "save_umap_model": False},
            }
        )
        assert not (ds / UMAP_MODEL_FILENAME).exists()

    def test_save_umap_model_false_keeps_own_dir_model_used_for_reuse(self, tmp_path):
        """自レポートの umap_model.pkl を投影元に使う場合は、保存しない設定でも消さない。"""
        rng = np.random.default_rng(5)
        base = tmp_path / "outputs"
        emb = rng.random((20, 16))
        ds = _write_dataset(base, "report_own", list(range(20)), emb)
        hierarchical_clustering(
            {
                "output_dir": "report_own",
                "_output_base_dir": str(base),
                "hierarchical_clustering": {"cluster_nums": [2, 4]},
            }
        )
        before = (ds / UMAP_MODEL_FILENAME).read_bytes()
        hierarchical_clustering(
            {
                "output_dir": "report_own",
                "_output_base_dir": str(base),
                "hierarchical_clustering": {
                    "cluster_nums": [2, 4],
                    "reuse_umap_model": UMAP_MODEL_FILENAME,
                    "save_umap_model": False,
                },
            }
        )
        assert (ds / UMAP_MODEL_FILENAME).read_bytes() == before

    @pytest.mark.parametrize("value", ["false", 0, "no"])
    def test_save_umap_model_rejects_non_boolean(self, tmp_path, value):
        rng = np.random.default_rng(6)
        base = tmp_path / "outputs"
        _write_dataset(base, "report_x", list(range(20)), rng.random((20, 16)))
        with pytest.raises(ValueError, match="save_umap_model"):
            hierarchical_clustering(
                {
                    "output_dir": "report_x",
                    "_output_base_dir": str(base),
                    "hierarchical_clustering": {"cluster_nums": [2, 4], "save_umap_model": value},
                }
            )

    def test_missing_reuse_model_raises_not_silent_fit(self, tmp_path):
        """A requested-but-missing reuse model must error, not silently fit a
        fresh plane (otherwise the user gets a different plane without warning)."""
        rng = np.random.default_rng(1)
        base = tmp_path / "outputs"
        emb = rng.random((20, 16))
        _write_dataset(base, "report_x", list(range(20)), emb)
        with pytest.raises(FileNotFoundError, match="見つかりません"):
            hierarchical_clustering(
                {
                    "output_dir": "report_x",
                    "_output_base_dir": str(base),
                    "hierarchical_clustering": {
                        "cluster_nums": [2, 4],
                        "reuse_umap_model": "no_such_report",
                    },
                }
            )

    def test_model_fit_on_legacy_embeddings_reused_by_float32_embeddings(self, tmp_path):
        """旧形式（list[float]）の embeddings.pkl で fit した model を、現行形式
        （float32 の配列）の embeddings.pkl のレポートから使い回しても同じ平面になる。
        UMAP は入力を float32 に変換して使うので、保存形式の変更で座標は変わらない。"""
        rng = np.random.default_rng(11)
        dim = 16
        n = 30
        base = tmp_path / "outputs"

        emb = rng.random((n, dim))
        ds_old = _write_dataset(base, "report_old", list(range(n)), emb)
        hierarchical_clustering(
            {
                "output_dir": "report_old",
                "_output_base_dir": str(base),
                "hierarchical_clustering": {"cluster_nums": [2, 4]},
            }
        )
        xy_old = pl.read_csv(str(ds_old / "hierarchical_clusters.csv")).select(["x", "y"]).to_numpy()

        ds_new = base / "report_new"
        ds_new.mkdir(parents=True)
        pl.DataFrame({"arg-id": list(range(n)), "argument": [f"arg {i}" for i in range(n)]}).write_csv(
            str(ds_new / "args.csv")
        )
        new_records = [{"arg-id": i, "embedding": row} for i, row in enumerate(emb.astype(np.float32))]
        with open(ds_new / "embeddings.pkl", "wb") as f:
            pickle.dump(new_records, f)
        hierarchical_clustering(
            {
                "output_dir": "report_new",
                "_output_base_dir": str(base),
                "hierarchical_clustering": {"cluster_nums": [2, 4], "reuse_umap_model": "report_old"},
            }
        )
        xy_new = pl.read_csv(str(ds_new / "hierarchical_clusters.csv")).select(["x", "y"]).to_numpy()
        assert np.allclose(xy_old, xy_new, atol=1e-4)
