"""旧形式（pandas の DataFrame）の embeddings.pkl の扱いのテスト。

v2.0.0〜v4.0.0 の embedding ステップは embeddings.pkl を ``pd.DataFrame(...).to_pickle`` で書いていた。
今の analysis-core と API の依存には pandas が無いので、この pickle は unpickle の段階で
「No module named 'pandas'」になり、クラスタ数を変える再利用が必ず失敗していた。

- 実行計画: 埋め込みを読むステップ（クラスタリング・LLM grouping）が走るときは、embedding を
  再実行して現行形式で作り直す。読むステップが走らないなら、そのまま使う（不要な再課金をしない）。
- 読み込み側: pandas が無い環境では、ModuleNotFoundError ではなく、原因と対処が分かるエラーにする。

fixture の ``fixtures/legacy_embeddings_pandas_dataframe.pkl`` は、v4.0.0 のタグの API で実際に作った
レポートの embeddings.pkl（列は arg-id と embedding）の先頭 3 行を、pandas で書き直したもの。
"""

import json
import pickle
from pathlib import Path

import numpy as np
import polars as pl
import pytest

import analysis_core.steps._embeddings_io as embeddings_io
import analysis_core.steps.hierarchical_clustering as hc_mod
import analysis_core.steps.llm_grouping as llm_grouping_mod
from analysis_core.core import decide_what_to_run, initialization, load_specs
from analysis_core.core.orchestration import _PACKAGE_DIR
from analysis_core.steps._embeddings_io import (
    LegacyEmbeddingsFormatError,
    is_pandas_embeddings_pickle,
)
from analysis_core.steps.hierarchical_layout_generation import _load_embeddings

FIXTURE = Path(__file__).parent / "fixtures" / "legacy_embeddings_pandas_dataframe.pkl"
FIXTURE_ARG_IDS = ["Ac0_0", "Ac1_0", "Ac2_0"]
HIERARCHICAL_SPECS = _PACKAGE_DIR / "specs" / "hierarchical_specs.json"
LLM_GROUPING_SPECS = _PACKAGE_DIR / "specs" / "llm_grouping_specs.json"

# protocol 2 の pickle（GLOBAL opcode で module を参照する）。古い Python の pandas が書く形
PROTOCOL2_DATAFRAME_PICKLE = b"\x80\x02cpandas.core.frame\nDataFrame\nq\x00)\x81q\x01}q\x02b."


@pytest.fixture
def without_pandas(monkeypatch):
    """pandas の入っていない環境（API のイメージ）と同じにする。"""
    monkeypatch.setattr(embeddings_io, "_pandas_available", lambda: False)


class TestDetectPandasPickle:
    def test_detects_dataframe_pickle_written_by_old_version(self):
        assert is_pandas_embeddings_pickle(FIXTURE) is True

    def test_detects_protocol2_global(self, tmp_path):
        path = tmp_path / "embeddings.pkl"
        path.write_bytes(PROTOCOL2_DATAFRAME_PICKLE)
        assert is_pandas_embeddings_pickle(path) is True

    @pytest.mark.parametrize(
        "data",
        [
            [{"arg-id": "A1_0", "embedding": np.zeros(3, dtype=np.float32)}],
            [{"arg-id": "A1_0", "embedding": [0.1, 0.2, 0.3]}],
            [{"embedding": [0.1, 0.2, 0.3]}],
            [],
        ],
        ids=["current", "legacy-float-list", "legacy-without-arg-id", "empty-list"],
    )
    def test_current_and_list_formats_are_not_pandas(self, tmp_path, data):
        path = tmp_path / "embeddings.pkl"
        path.write_bytes(pickle.dumps(data))
        assert is_pandas_embeddings_pickle(path) is False

    def test_missing_or_broken_file_is_not_pandas(self, tmp_path):
        assert is_pandas_embeddings_pickle(tmp_path / "missing.pkl") is False
        broken = tmp_path / "broken.pkl"
        broken.write_bytes(b"not a pickle")
        assert is_pandas_embeddings_pickle(broken) is False


def _dataset_with_legacy_embeddings(tmp_path):
    ds_dir = tmp_path / "ds"
    ds_dir.mkdir()
    pl.DataFrame({"arg-id": FIXTURE_ARG_IDS, "argument": ["a", "b", "c"]}).write_csv(str(ds_dir / "args.csv"))
    (ds_dir / "embeddings.pkl").write_bytes(FIXTURE.read_bytes())
    return ds_dir


class TestLoadersExplainLegacyFormat:
    """pandas が無い環境では、ModuleNotFoundError ではなく対処の分かるエラーにする"""

    def test_hierarchical_clustering(self, tmp_path, without_pandas):
        _dataset_with_legacy_embeddings(tmp_path)
        config = {
            "output_dir": "ds",
            "_output_base_dir": str(tmp_path),
            "hierarchical_clustering": {"cluster_nums": [2]},
        }
        with pytest.raises(LegacyEmbeddingsFormatError, match="embedding"):
            hc_mod.hierarchical_clustering(config)

    def test_llm_grouping_projection(self, tmp_path, without_pandas):
        _dataset_with_legacy_embeddings(tmp_path)
        with pytest.raises(LegacyEmbeddingsFormatError, match="embedding"):
            llm_grouping_mod._project_embeddings_to_xy(str(tmp_path), "ds", FIXTURE_ARG_IDS)

    def test_layout_generation(self, tmp_path, without_pandas):
        ds_dir = _dataset_with_legacy_embeddings(tmp_path)
        with pytest.raises(LegacyEmbeddingsFormatError, match="embedding"):
            _load_embeddings(ds_dir / "embeddings.pkl", FIXTURE_ARG_IDS)

    def test_reads_dataframe_when_pandas_is_installed(self, tmp_path):
        """pandas のある環境（CLI 利用者）では、これまでどおり読める"""
        pytest.importorskip("pandas")
        ds_dir = _dataset_with_legacy_embeddings(tmp_path)
        assert _load_embeddings(ds_dir / "embeddings.pkl", FIXTURE_ARG_IDS).shape == (3, 16)


def _initialized_config(tmp_path, specs_path, **overrides):
    config_path = tmp_path / "job.json"
    base = {"input": "comments", "question": "Q?", "provider": "local"}
    if specs_path == LLM_GROUPING_SPECS:
        base["analysis_mode"] = "llm_grouping"
    config_path.write_text(json.dumps(base), encoding="utf-8")
    config = initialization(
        config_path=config_path,
        skip_interaction=True,
        persist_status=False,
        output_base_dir=tmp_path / "outputs",
        input_base_dir=tmp_path / "inputs",
    )
    for key, value in overrides.items():
        config[key] = {**config[key], **value}
    return config


def _previous_run(tmp_path, config, specs):
    """全ステップが完了した旧バージョンのレポート。embeddings.pkl だけが pandas の pickle。"""
    out = tmp_path / "outputs" / config["output_dir"]
    out.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        for filename in [spec["filename"], *spec.get("extra_files", [])]:
            (out / filename).write_text("x", encoding="utf-8")
    (out / "embeddings.pkl").write_bytes(FIXTURE.read_bytes())
    return {
        "status": "completed",
        "completed_jobs": [
            {"step": spec["step"], "completed": "2026-01-01T00:00:00", "params": dict(config[spec["step"]])}
            for spec in specs
        ],
        "previously_completed_jobs": [],
    }


def _plan(tmp_path, config, previous, specs):
    config = {**config, "previous": previous}
    return {p["step"]: p for p in decide_what_to_run(config, previous, specs, tmp_path / "outputs")}


class TestPlanRegeneratesLegacyEmbeddings:
    def test_cluster_change_reruns_embedding_but_not_extraction(self, tmp_path):
        specs = load_specs(HIERARCHICAL_SPECS)
        previous = _previous_run(tmp_path, _initialized_config(tmp_path, HIERARCHICAL_SPECS), specs)

        changed = _initialized_config(tmp_path, HIERARCHICAL_SPECS, hierarchical_clustering={"cluster_nums": [2, 4]})
        plan = _plan(tmp_path, changed, previous, specs)

        assert plan["extraction"]["run"] is False
        assert plan["embedding"]["run"] is True
        assert "pandas" in plan["embedding"]["reason"]
        assert plan["hierarchical_clustering"]["run"] is True

    def test_unchanged_reuse_keeps_legacy_embeddings(self, tmp_path):
        """埋め込みを読むステップが走らないなら、作り直さない（ラベル付けを再課金しない）"""
        specs = load_specs(HIERARCHICAL_SPECS)
        config = _initialized_config(tmp_path, HIERARCHICAL_SPECS)
        previous = _previous_run(tmp_path, config, specs)

        changed = _initialized_config(tmp_path, HIERARCHICAL_SPECS, hierarchical_overview={"prompt": "new"})
        plan = _plan(tmp_path, changed, previous, specs)

        assert plan["embedding"]["run"] is False
        assert plan["hierarchical_clustering"]["run"] is False
        assert plan["hierarchical_overview"]["run"] is True

    def test_llm_grouping_rerun_regenerates_embedding(self, tmp_path):
        specs = load_specs(LLM_GROUPING_SPECS)
        previous = _previous_run(tmp_path, _initialized_config(tmp_path, LLM_GROUPING_SPECS), specs)

        changed = _initialized_config(tmp_path, LLM_GROUPING_SPECS, llm_grouping={"discovery_prompt": "new"})
        plan = _plan(tmp_path, changed, previous, specs)

        assert plan["extraction"]["run"] is False
        assert plan["embedding"]["run"] is True
        assert plan["llm_grouping"]["run"] is True

    def test_reuse_from_legacy_output_regenerates_embedding(self, tmp_path):
        """CLI の --reuse-from に v4.0.0 以前の outputs を渡した場合も、embedding から作り直す"""
        specs = load_specs(HIERARCHICAL_SPECS)
        source_config = _initialized_config(tmp_path, HIERARCHICAL_SPECS)
        source_status = _previous_run(tmp_path, source_config, specs)
        source_dir = tmp_path / "outputs" / source_config["output_dir"]
        (source_dir / "hierarchical_status.json").write_text(json.dumps(source_status), encoding="utf-8")

        config_path = tmp_path / "copy.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "comments",
                    "question": "Q?",
                    "provider": "local",
                    "hierarchical_clustering": {"cluster_nums": [2, 4]},
                }
            ),
            encoding="utf-8",
        )
        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
            reuse_from=str(source_dir),
        )

        plan = {p["step"]: p for p in config["plan"]}
        assert plan["extraction"]["run"] is False
        assert plan["embedding"]["run"] is True
