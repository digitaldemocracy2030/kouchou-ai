"""起動時の検証・ロック・API キーの確認で、管理画面と CLI が頼っている振る舞いを固定する。"""

import json
from datetime import datetime, timedelta

import pytest

from analysis_core.core import initialization, load_specs
from analysis_core.core.orchestration import (
    _PACKAGE_DIR,
    plan_requires_input,
    update_progress,
    validate_api_keys,
    validate_config,
)

HIERARCHICAL_SPECS = _PACKAGE_DIR / "specs" / "hierarchical_specs.json"
LLM_GROUPING_SPECS = _PACKAGE_DIR / "specs" / "llm_grouping_specs.json"


def _admin_config(analysis_mode="hierarchical"):
    """管理画面（apps/api の report_launcher._build_config）が書く config と同じ形。"""
    config = {
        "name": "report",
        "input": "report",
        "question": "Q?",
        "intro": "intro",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "analysis_mode": analysis_mode,
        "is_pubcom": True,
        "is_embedded_at_local": False,
        "local_llm_address": None,
        "extraction": {"prompt": "p", "workers": 3, "limit": 10},
        "hierarchical_overview": {"prompt": "p"},
        "embedding": {"model": "text-embedding-3-small"},
        "hierarchical_aggregation": {"sampling_num": 3},
        "enable_source_link": False,
        "enable_original_comments": False,
    }
    if analysis_mode == "llm_grouping":
        config["llm_grouping"] = {"workers": 3}
    else:
        config["hierarchical_clustering"] = {"cluster_nums": [3, 6]}
    return config


class TestAdminConfigIsAccepted:
    @pytest.mark.parametrize(
        ("analysis_mode", "specs_path"),
        [("hierarchical", HIERARCHICAL_SPECS), ("llm_grouping", LLM_GROUPING_SPECS)],
    )
    def test_admin_config_passes_validation(self, analysis_mode, specs_path):
        validate_config(_admin_config(analysis_mode), load_specs(specs_path))

    def test_misspelled_step_option_is_rejected(self):
        config = _admin_config()
        config["extraction"]["limt"] = 10
        with pytest.raises(Exception, match="Unknown option 'limt' for step 'extraction'"):
            validate_config(config, load_specs(HIERARCHICAL_SPECS))


def _write_config(tmp_path, name="job", **fields):
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps({"input": "comments", "question": "Q?", "provider": "local", **fields}), "utf-8")
    return path


def _write_status(tmp_path, status, name="job"):
    out = tmp_path / "outputs" / name
    out.mkdir(parents=True, exist_ok=True)
    (out / "hierarchical_status.json").write_text(json.dumps(status), encoding="utf-8")
    return out / "hierarchical_status.json"


def _initialize(tmp_path, config_path, **kwargs):
    return initialization(
        config_path=config_path,
        skip_interaction=True,
        output_base_dir=tmp_path / "outputs",
        input_base_dir=tmp_path / "inputs",
        **kwargs,
    )


class TestRunningLock:
    def test_expired_lock_of_crashed_run_does_not_block(self, tmp_path):
        """OOM などで落ちた実行の status（running・期限切れのロック）が、再実行を止めない。"""
        expired = (datetime.now() - timedelta(hours=1)).isoformat()
        _write_status(tmp_path, {"status": "running", "lock_until": expired})
        config = _initialize(tmp_path, _write_config(tmp_path), persist_status=False)
        assert config["plan"]

    def test_running_status_without_lock_does_not_block(self, tmp_path):
        _write_status(tmp_path, {"status": "running"})
        config = _initialize(tmp_path, _write_config(tmp_path), persist_status=False)
        assert config["plan"]

    def test_status_written_at_start_holds_a_future_lock(self, tmp_path):
        _initialize(tmp_path, _write_config(tmp_path))
        status = json.loads((tmp_path / "outputs" / "job" / "hierarchical_status.json").read_text("utf-8"))
        assert status["status"] == "running"
        assert datetime.fromisoformat(status["lock_until"]) > datetime.now()

    def test_progress_update_extends_the_lock(self, tmp_path):
        """進捗の更新でロックを延ばす。延ばさないと 5 分を超える抽出の途中でロックが切れる。"""
        status_file = _write_status(
            tmp_path, {"status": "running", "lock_until": (datetime.now() - timedelta(minutes=1)).isoformat()}
        )
        config = {"output_dir": "job", "_output_base_dir": str(tmp_path / "outputs")}
        update_progress(config, total=3)
        status = json.loads(status_file.read_text(encoding="utf-8"))
        assert status["current_jop_tasks"] == 3
        assert datetime.fromisoformat(status["lock_until"]) > datetime.now()


class TestInitializationDefaults:
    def test_default_directories(self, tmp_path, monkeypatch):
        """CLI で --output-dir / --input-dir を省いたときは、作業ディレクトリの outputs / inputs を使う。"""
        monkeypatch.chdir(tmp_path)
        config = initialization(config_path=_write_config(tmp_path), skip_interaction=True, persist_status=False)
        assert config["_output_base_dir"] == "outputs"
        assert config["_input_base_dir"] == "inputs"

    def test_from_config_records_step_source_code(self, tmp_path):
        """公開ビューアの「分析手順」に出す各工程のソースコードを config に入れる。"""
        from analysis_core.orchestrator import PipelineOrchestrator

        orchestrator = PipelineOrchestrator.from_config(
            config_path=_write_config(tmp_path),
            persist_status=False,
            validate_api_keys_early=False,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )
        assert "def extraction" in orchestrator.config["extraction"]["source_code"]

    def test_llm_grouping_keeps_user_prompts(self, tmp_path):
        config_path = _write_config(
            tmp_path,
            analysis_mode="llm_grouping",
            llm_grouping={"discovery_prompt": "my discovery", "assignment_prompt": "my assignment"},
        )
        config = _initialize(tmp_path, config_path, persist_status=False)
        assert config["llm_grouping"]["discovery_prompt"] == "my discovery"
        assert config["llm_grouping"]["assignment_prompt"] == "my assignment"


class TestPlanRequiresInput:
    def test_running_extraction_or_aggregation_needs_input(self):
        assert plan_requires_input([{"step": "extraction", "run": True}])
        assert plan_requires_input([{"step": "hierarchical_aggregation", "run": True}])

    def test_other_steps_alone_do_not_need_input(self):
        plan = [
            {"step": "extraction", "run": False},
            {"step": "embedding", "run": True},
            {"step": "hierarchical_aggregation", "run": False},
        ]
        assert not plan_requires_input(plan)


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """作業ディレクトリの .env を読まないようにし、関係する変数を空にする。"""
    monkeypatch.chdir(tmp_path)
    for name in ("GEMINI_API_KEY", "OPENROUTER_API_KEY", "USER_API_KEY"):
        monkeypatch.setenv(name, "")
    return monkeypatch


class TestApiKeysAreFound:
    @pytest.mark.parametrize(
        ("provider", "env_name"), [("gemini", "GEMINI_API_KEY"), ("openrouter", "OPENROUTER_API_KEY")]
    )
    def test_environment_key_is_enough(self, isolated_env, provider, env_name):
        isolated_env.setenv(env_name, "env-key")
        validate_api_keys(provider)

    @pytest.mark.parametrize("provider", ["gemini", "openrouter"])
    def test_user_key_is_enough(self, isolated_env, provider):
        validate_api_keys(provider, user_api_key="user-key")


class TestEmbeddingPreflight:
    def test_openrouter_without_local_embedding_stops_before_extraction(self, tmp_path, isolated_env):
        """is_embedded_at_local を省いた config は API で埋め込む扱い。OpenRouter には埋め込み API が無いので先に止める。"""
        isolated_env.setenv("OPENROUTER_API_KEY", "env-key")
        with pytest.raises(RuntimeError, match="OpenRouter has no embedding API"):
            _initialize(tmp_path, _write_config(tmp_path, provider="openrouter"), persist_status=False)

    def test_azure_user_key_covers_embedding_key(self, tmp_path, isolated_env):
        """Azure でユーザーのキーだけを渡したときは、埋め込みのキーとしても使う。"""
        for name, value in {
            "AZURE_CHATCOMPLETION_ENDPOINT": "https://chat.invalid",
            "AZURE_CHATCOMPLETION_DEPLOYMENT_NAME": "chat",
            "AZURE_CHATCOMPLETION_API_KEY": "",
            "AZURE_CHATCOMPLETION_VERSION": "2024-06-01",
            "AZURE_EMBEDDING_ENDPOINT": "https://embedding.invalid",
            "AZURE_EMBEDDING_DEPLOYMENT_NAME": "embedding",
            "AZURE_EMBEDDING_API_KEY": "",
            "AZURE_EMBEDDING_VERSION": "2024-06-01",
            "USER_API_KEY": "user-key",
        }.items():
            isolated_env.setenv(name, value)
        config = _initialize(tmp_path, _write_config(tmp_path, provider="azure"), persist_status=False)
        assert config["plan"]
