"""Tests for orchestration module."""

import json

import pytest


class TestInitialization:
    """Test initialization function."""

    def test_initialization_creates_output_dir(self, tmp_path):
        """Test that initialization creates output directory."""
        from analysis_core.core import initialization

        # Create a minimal config file
        config_path = tmp_path / "test_job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test_input",
                    "question": "What are the main themes?",
                    "provider": "local",
                }
            )
        )

        # Create input and output directories
        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        # Run initialization
        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        # Check output directory was created
        assert (output_dir / "test_job").exists()

        # Check config was populated
        assert config["output_dir"] == "test_job"
        assert config["input"] == "test_input"
        assert config["question"] == "What are the main themes?"
        assert config["model"] == "gpt-4o-mini"  # default
        assert "plan" in config

    def test_initialization_loads_specs(self, tmp_path):
        """Test that initialization loads step specs."""
        from analysis_core.core import get_specs, initialization

        # Create config file
        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "local",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        specs = get_specs()
        assert len(specs) == 9
        step_names = [s["step"] for s in specs]
        assert "extraction" in step_names
        assert "embedding" in step_names
        assert "hierarchical_clustering" in step_names

    def test_initialization_sets_default_options(self, tmp_path):
        """Test that initialization sets default options for steps."""
        from analysis_core.core import initialization

        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "local",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        # Check default options were set
        assert "extraction" in config
        assert config["extraction"]["limit"] == 1000
        assert config["extraction"]["workers"] == 1

        assert "hierarchical_clustering" in config
        assert config["hierarchical_clustering"]["cluster_nums"] is None

    def test_initialization_force_flag(self, tmp_path):
        """Test that force flag is set in config."""
        from analysis_core.core import initialization

        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "local",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        config = initialization(
            config_path=config_path,
            force=True,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        assert config.get("force") is True

    def test_initialization_only_step(self, tmp_path):
        """Test that only step is set in config."""
        from analysis_core.core import initialization

        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "local",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        config = initialization(
            config_path=config_path,
            only="extraction",
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        assert config.get("only") == "extraction"

    def test_initialization_without_html(self, tmp_path):
        """Test that without_html flag is set."""
        from analysis_core.core import initialization

        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "local",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        config = initialization(
            config_path=config_path,
            without_html=True,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        assert config.get("without-html") is True

    def test_initialization_prefers_legacy_without_html_key(self, tmp_path):
        """Test conflicting without_html flags are reconciled to the legacy key."""
        from analysis_core.core import initialization

        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "local",
                    "without_html": False,
                    "without-html": True,
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        assert config["without-html"] is True
        assert config["without_html"] is True

    def test_initialization_uses_runtime_user_api_key_for_validation(self, tmp_path, monkeypatch):
        """Test USER_API_KEY satisfies fail-fast provider validation without persisting it."""
        from analysis_core.core import initialization

        monkeypatch.setenv("OPENAI_API_KEY", "")
        monkeypatch.setenv("USER_API_KEY", "runtime-user-key")

        config_path = tmp_path / "job.json"

        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "openai",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        assert "user_api_key" not in config
        status = json.loads((output_dir / "job" / "hierarchical_status.json").read_text())
        assert "user_api_key" not in status

    def test_initialization_can_seed_from_previous_output(self, tmp_path):
        """Test reuse_from seeds reusable artifacts and skips upstream steps."""
        from analysis_core.core import initialization
        from analysis_core.prompts import get_default_prompt

        config_path = tmp_path / "compare_job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "local",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        source_dir = output_dir / "source_job"
        source_dir.mkdir(parents=True)
        (source_dir / "args.csv").write_text("arg-id,argument\nA1,test\n", encoding="utf-8")
        (source_dir / "relations.csv").write_text("arg-id,comment-id\nA1,1\n", encoding="utf-8")
        (source_dir / "embeddings.pkl").write_bytes(b"pickle-placeholder")
        report_dir = source_dir / "report"
        report_dir.mkdir()
        (report_dir / "index.html").write_text("<html></html>", encoding="utf-8")
        (source_dir / "hierarchical_status.json").write_text(
            json.dumps(
                {
                    "status": "completed",
                    "completed_jobs": [
                        {
                            "step": "extraction",
                            "params": {
                                "limit": 1000,
                                "model": "gpt-4o-mini",
                                "prompt": get_default_prompt("extraction"),
                            },
                        },
                        {"step": "embedding", "params": {"model": "text-embedding-3-small"}},
                        {"step": "hierarchical_visualization", "params": {}},
                    ],
                }
            ),
            encoding="utf-8",
        )
        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
            reuse_from="source_job",
        )

        seeded_dir = output_dir / "compare_job"
        assert (seeded_dir / "args.csv").exists()
        assert (seeded_dir / "relations.csv").exists()
        assert (seeded_dir / "embeddings.pkl").exists()
        # Visualization embeds the source job's config, so it is regenerated instead of reused.
        assert not (seeded_dir / "report").exists()
        assert config["previous"]["reused_from"].endswith("source_job")

        plan_by_step = {item["step"]: item for item in config["plan"]}
        assert plan_by_step["extraction"]["run"] is False
        assert plan_by_step["embedding"]["run"] is False
        assert plan_by_step["hierarchical_clustering"]["run"] is True
        previous_jobs = {job["step"]: job for job in config["previous"]["completed_jobs"]}
        assert previous_jobs["extraction"]["params"] == {
            "limit": 1000,
            "model": "gpt-4o-mini",
            "prompt": get_default_prompt("extraction"),
        }
        assert previous_jobs["embedding"]["params"] == {"model": "text-embedding-3-small"}

    def test_initialization_only_seeds_steps_completed_in_source_status(self, tmp_path):
        """Test reuse_from ignores artifacts for steps not completed in source status."""
        from analysis_core.core import initialization
        from analysis_core.prompts import get_default_prompt

        config_path = tmp_path / "compare_job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "local",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        source_dir = output_dir / "source_job"
        source_dir.mkdir(parents=True)
        (source_dir / "args.csv").write_text("arg-id,argument\nA1,test\n", encoding="utf-8")
        (source_dir / "relations.csv").write_text("arg-id,comment-id\nA1,1\n", encoding="utf-8")
        (source_dir / "embeddings.pkl").write_bytes(b"pickle-placeholder")
        (source_dir / "hierarchical_status.json").write_text(
            json.dumps(
                {
                    "status": "completed",
                    "completed_jobs": [
                        {
                            "step": "extraction",
                            "params": {
                                "limit": 1000,
                                "model": "gpt-4o-mini",
                                "prompt": get_default_prompt("extraction"),
                            },
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )

        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
            reuse_from="source_job",
        )

        seeded_dir = output_dir / "compare_job"
        assert (seeded_dir / "args.csv").exists()
        assert (seeded_dir / "relations.csv").exists()
        assert not (seeded_dir / "embeddings.pkl").exists()

        plan_by_step = {item["step"]: item for item in config["plan"]}
        assert plan_by_step["extraction"]["run"] is False
        assert plan_by_step["embedding"]["run"] is True

    @pytest.mark.parametrize("provider_entry", [{}, {"provider": None}], ids=["missing", "null"])
    def test_initialization_defaults_missing_provider_to_openai(self, tmp_path, monkeypatch, provider_entry):
        """provider の無い古い config（v2.0.x の API が作ったもの）は openai として扱う

        provider が無いまま status に "provider": None を書くと、ステップに渡る config の
        provider が None になり、LLM 呼び出しが「Unknown provider: None」で失敗していた。
        """
        from analysis_core.compat import create_step_context_from_config
        from analysis_core.core import initialization

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        config_path = tmp_path / "legacy_job.json"
        # v2.0.0 の API の _build_config が書く形（provider キーが無い）を最小化したもの
        config_path.write_text(
            json.dumps(
                {
                    "name": "legacy_job",
                    "input": "legacy_job",
                    "question": "Q",
                    "intro": "intro",
                    "model": "gpt-4o-mini",
                    "is_pubcom": True,
                    "extraction": {"prompt": "e", "workers": 2, "limit": 60},
                    "hierarchical_clustering": {"cluster_nums": [3, 6]},
                    **provider_entry,
                }
            ),
            encoding="utf-8",
        )
        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        assert config["provider"] == "openai"
        status = json.loads((output_dir / "legacy_job" / "hierarchical_status.json").read_text(encoding="utf-8"))
        assert status["provider"] == "openai"
        assert create_step_context_from_config(config, output_base_dir=output_dir).provider == "openai"


class TestValidateApiKeys:
    """Test API key validation."""

    def test_validate_api_keys_openai_missing(self, monkeypatch):
        """Test validation fails for missing OpenAI API key."""
        from analysis_core.core.orchestration import validate_api_keys

        # Set to empty string to prevent load_dotenv from loading it
        monkeypatch.setenv("OPENAI_API_KEY", "")

        with pytest.raises(RuntimeError, match="OPENAI_API_KEY environment variable is not set"):
            validate_api_keys("openai")

    def test_validate_api_keys_openai_with_env(self, monkeypatch):
        """Test validation passes when OpenAI API key is set."""
        from analysis_core.core.orchestration import validate_api_keys

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        validate_api_keys("openai")

    def test_validate_api_keys_openai_with_user_key(self, monkeypatch):
        """Test validation passes with user-provided API key."""
        from analysis_core.core.orchestration import validate_api_keys

        # Set to empty string to prevent load_dotenv from loading it
        monkeypatch.setenv("OPENAI_API_KEY", "")

        validate_api_keys("openai", user_api_key="user-provided-key")

    def test_validate_api_keys_gemini_missing(self, monkeypatch):
        """Test validation fails for missing Gemini API key."""
        from analysis_core.core.orchestration import validate_api_keys

        # Set to empty string to prevent load_dotenv from loading it
        monkeypatch.setenv("GEMINI_API_KEY", "")

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY environment variable is not set"):
            validate_api_keys("gemini")

    def test_validate_api_keys_azure_missing(self, monkeypatch):
        """Test validation fails for missing Azure environment variables."""
        from analysis_core.core.orchestration import validate_api_keys

        # Set to empty strings instead of deleting to prevent load_dotenv from loading them
        monkeypatch.setenv("AZURE_CHATCOMPLETION_ENDPOINT", "")
        monkeypatch.setenv("AZURE_CHATCOMPLETION_DEPLOYMENT_NAME", "")
        monkeypatch.setenv("AZURE_CHATCOMPLETION_API_KEY", "")
        monkeypatch.setenv("AZURE_CHATCOMPLETION_VERSION", "")

        with pytest.raises(RuntimeError, match="Azure OpenAI environment variables not set"):
            validate_api_keys("azure")

    def test_validate_api_keys_openrouter_missing(self, monkeypatch):
        """Test validation fails for missing OpenRouter API key."""
        from analysis_core.core.orchestration import validate_api_keys

        # Set to empty string to prevent load_dotenv from loading it
        monkeypatch.setenv("OPENROUTER_API_KEY", "")

        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY environment variable is not set"):
            validate_api_keys("openrouter")

    def test_validate_api_keys_local_no_key_needed(self):
        """Test validation passes for local provider without any keys."""
        from analysis_core.core.orchestration import validate_api_keys

        validate_api_keys("local")

    def test_validate_api_keys_unknown_provider(self):
        """Test validation fails for unknown provider."""
        from analysis_core.core.orchestration import validate_api_keys

        with pytest.raises(RuntimeError, match="Unknown provider"):
            validate_api_keys("unknown_provider")


AZURE_CHAT_ENV = {
    "AZURE_CHATCOMPLETION_ENDPOINT": "https://chat.invalid",
    "AZURE_CHATCOMPLETION_DEPLOYMENT_NAME": "chat-deployment",
    "AZURE_CHATCOMPLETION_API_KEY": "chat-key",
    "AZURE_CHATCOMPLETION_VERSION": "2024-06-01",
}
AZURE_EMBEDDING_ENV = {
    "AZURE_EMBEDDING_ENDPOINT": "https://embedding.invalid",
    "AZURE_EMBEDDING_DEPLOYMENT_NAME": "embedding-deployment",
    "AZURE_EMBEDDING_API_KEY": "embedding-key",
    "AZURE_EMBEDDING_VERSION": "2024-06-01",
}


def _set_azure_env(monkeypatch, *, embedding: dict[str, str] | None = None):
    """Chat の 4 変数だけを設定する。埋め込み側は空文字にして .env からの読み込みも防ぐ。"""
    for key, value in AZURE_CHAT_ENV.items():
        monkeypatch.setenv(key, value)
    for key in AZURE_EMBEDDING_ENV:
        monkeypatch.setenv(key, (embedding or {}).get(key, ""))
    monkeypatch.setenv("USER_API_KEY", "")


class TestValidateEmbeddingKeys:
    """埋め込みを API で行う時の、開始前の環境変数チェック。"""

    def test_azure_without_embedding_env_fails(self, monkeypatch):
        from analysis_core.core.orchestration import validate_embedding_keys

        _set_azure_env(monkeypatch)

        with pytest.raises(RuntimeError, match="AZURE_EMBEDDING_ENDPOINT") as excinfo:
            validate_embedding_keys("azure", is_embedded_at_local=False)
        message = str(excinfo.value)
        for key in AZURE_EMBEDDING_ENV:
            assert key in message
        assert "is_embedded_at_local" in message

    def test_azure_with_embedding_env_passes(self, monkeypatch):
        from analysis_core.core.orchestration import validate_embedding_keys

        _set_azure_env(monkeypatch, embedding=AZURE_EMBEDDING_ENV)

        validate_embedding_keys("azure", is_embedded_at_local=False)

    def test_azure_user_api_key_replaces_embedding_api_key(self, monkeypatch):
        from analysis_core.core.orchestration import validate_embedding_keys

        _set_azure_env(monkeypatch, embedding={**AZURE_EMBEDDING_ENV, "AZURE_EMBEDDING_API_KEY": ""})

        validate_embedding_keys("azure", is_embedded_at_local=False, user_api_key="user-key")
        with pytest.raises(RuntimeError, match="AZURE_EMBEDDING_API_KEY"):
            validate_embedding_keys("azure", is_embedded_at_local=False)

    def test_local_embedding_needs_no_provider_env(self, monkeypatch):
        from analysis_core.core.orchestration import validate_embedding_keys

        _set_azure_env(monkeypatch)

        validate_embedding_keys("azure", is_embedded_at_local=True)
        validate_embedding_keys("openrouter", is_embedded_at_local=True)

    def test_openrouter_without_local_embedding_fails(self):
        from analysis_core.core.orchestration import validate_embedding_keys

        with pytest.raises(RuntimeError, match="is_embedded_at_local"):
            validate_embedding_keys("openrouter", is_embedded_at_local=False)

    def test_other_providers_reuse_chat_credentials(self):
        from analysis_core.core.orchestration import validate_embedding_keys

        for provider in ("openai", "gemini", "local"):
            validate_embedding_keys(provider, is_embedded_at_local=False)


class TestInitializationEmbeddingKeys:
    """initialization / from_dict は、埋め込みを実行する計画の時だけ埋め込み側も開始前に確かめる。"""

    @staticmethod
    def _write_config(tmp_path, **overrides):
        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps({"input": "test", "question": "Test?", "provider": "azure", **overrides}),
            encoding="utf-8",
        )
        (tmp_path / "inputs").mkdir(exist_ok=True)
        return config_path

    def test_azure_without_embedding_env_fails_before_running(self, tmp_path, monkeypatch):
        from analysis_core.core import initialization

        _set_azure_env(monkeypatch)
        config_path = self._write_config(tmp_path, is_embedded_at_local=False)

        with pytest.raises(RuntimeError, match="AZURE_EMBEDDING_"):
            initialization(
                config_path=config_path,
                skip_interaction=True,
                output_base_dir=tmp_path / "outputs",
                input_base_dir=tmp_path / "inputs",
            )
        # 開始前に止まるので、running の状態は書かれない
        assert not (tmp_path / "outputs" / "job" / "hierarchical_status.json").exists()

    def test_azure_with_local_embedding_passes(self, tmp_path, monkeypatch):
        from analysis_core.core import initialization

        _set_azure_env(monkeypatch)
        config_path = self._write_config(tmp_path, is_embedded_at_local=True)

        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )
        assert next(step for step in config["plan"] if step["step"] == "embedding")["run"] is True

    def test_azure_only_other_step_does_not_need_embedding_env(self, tmp_path, monkeypatch):
        from analysis_core.core import initialization

        _set_azure_env(monkeypatch)
        config_path = self._write_config(tmp_path, is_embedded_at_local=False)

        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
            only="extraction",
        )
        assert next(step for step in config["plan"] if step["step"] == "embedding")["run"] is False

    def test_validation_disabled_skips_embedding_check(self, tmp_path, monkeypatch):
        from analysis_core.core import initialization

        _set_azure_env(monkeypatch)
        config_path = self._write_config(tmp_path, is_embedded_at_local=False)

        initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
            validate_api_keys_early=False,
        )

    def test_from_dict_azure_without_embedding_env_fails(self, tmp_path, monkeypatch):
        from analysis_core import PipelineOrchestrator

        _set_azure_env(monkeypatch)

        with pytest.raises(RuntimeError, match="AZURE_EMBEDDING_"):
            PipelineOrchestrator.from_dict(
                config={"name": "demo", "input": "demo", "question": "Test?", "provider": "azure"},
                output_dir="demo",
                output_base_dir=tmp_path / "outputs",
                input_base_dir=tmp_path / "inputs",
            )

    def test_from_dict_skips_check_when_embedding_does_not_run(self, tmp_path, monkeypatch):
        from analysis_core import PipelineOrchestrator

        _set_azure_env(monkeypatch)
        plan = [{"step": "embedding", "run": False, "reason": "nothing changed"}]

        orchestrator = PipelineOrchestrator.from_dict(
            config={"name": "demo", "input": "demo", "question": "Test?", "provider": "azure", "plan": plan},
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )
        assert orchestrator.get_plan() == plan

    def test_from_dict_reads_user_api_key_from_env_like_initialization(self, tmp_path, monkeypatch):
        """from_dict も initialization と同じく、config に無ければ環境変数 USER_API_KEY を鍵として使う。"""
        from analysis_core import PipelineOrchestrator

        _set_azure_env(
            monkeypatch,
            embedding={**AZURE_EMBEDDING_ENV, "AZURE_EMBEDDING_API_KEY": ""},
        )
        monkeypatch.setenv("AZURE_CHATCOMPLETION_API_KEY", "")
        config = {"name": "demo", "input": "demo", "question": "Test?", "provider": "azure"}

        with pytest.raises(RuntimeError, match="AZURE_CHATCOMPLETION_API_KEY"):
            PipelineOrchestrator.from_dict(
                config=dict(config),
                output_dir="demo",
                output_base_dir=tmp_path / "outputs",
                input_base_dir=tmp_path / "inputs",
            )

        monkeypatch.setenv("USER_API_KEY", "user-key-from-env")
        PipelineOrchestrator.from_dict(
            config=dict(config),
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )


class TestValidateConfig:
    """Test config validation."""

    def test_validate_config_missing_input(self):
        """Test validation fails for missing input."""
        from analysis_core.core import load_specs, validate_config
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")

        with pytest.raises(Exception, match="Missing required field 'input'"):
            validate_config({"question": "Test?"}, specs)

    def test_validate_config_missing_question(self):
        """Test validation fails for missing question."""
        from analysis_core.core import load_specs, validate_config
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")

        with pytest.raises(Exception, match="Missing required field 'question'"):
            validate_config({"input": "test"}, specs)

    def test_validate_config_valid(self):
        """Test validation passes for valid config."""
        from analysis_core.core import load_specs, validate_config
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")

        # Should not raise
        validate_config(
            {
                "input": "test",
                "question": "Test?",
                "model": "gpt-4o-mini",
                "provider": "openai",
            },
            specs,
        )


class TestValidateInputFile:
    """Test input preflight validation."""

    def test_validate_input_file_missing_csv(self, tmp_path):
        """Validation should fail when the input CSV does not exist."""
        from analysis_core.core.orchestration import validate_input_file

        with pytest.raises(RuntimeError, match="Input CSV not found"):
            validate_input_file({"input": "missing"}, tmp_path)

    def test_validate_input_file_missing_required_columns(self, tmp_path):
        """Validation should fail when required columns are missing."""
        from analysis_core.core.orchestration import validate_input_file

        input_path = tmp_path / "demo.csv"
        input_path.write_text("comment-id,text\n1,hello\n", encoding="utf-8")

        with pytest.raises(RuntimeError, match="missing required columns"):
            validate_input_file({"input": "demo"}, tmp_path)

    def test_validate_input_file_missing_property_columns(self, tmp_path):
        """Validation should fail when extraction.properties columns are missing."""
        from analysis_core.core.orchestration import validate_input_file

        input_path = tmp_path / "demo.csv"
        input_path.write_text("comment-id,comment-body\n1,hello\n", encoding="utf-8")

        with pytest.raises(RuntimeError, match="extraction.properties"):
            validate_input_file({"input": "demo", "extraction": {"properties": ["source"]}}, tmp_path)

    def test_validate_input_file_accepts_mixed_type_property_column(self, tmp_path):
        """Validation should treat input property columns as categorical strings."""
        from analysis_core.core.orchestration import validate_input_file

        input_path = tmp_path / "demo.csv"
        input_path.write_text(
            "comment-id,comment-body,attribute_group\n1,first,1\n2,second,label-a\n",
            encoding="utf-8",
        )

        path = validate_input_file({"input": "demo", "extraction": {"properties": ["attribute_group"]}}, tmp_path)

        assert path == input_path

    def test_validate_input_file_skips_when_plan_does_not_need_input(self, tmp_path):
        """Visualization-only runs should not require the input CSV."""
        from analysis_core.core.orchestration import validate_input_file

        path = validate_input_file(
            {"input": "demo"},
            tmp_path,
            plan=[{"step": "hierarchical_visualization", "run": True}],
        )

        assert path == tmp_path / "demo.csv"


class TestDecideWhatToRun:
    """Test decide_what_to_run function."""

    def test_decide_first_run(self, tmp_path):
        """Test plan for first run (no previous status)."""
        from analysis_core.core import decide_what_to_run, load_specs
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")

        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
        }

        plan = decide_what_to_run(config, None, specs, tmp_path)

        # All steps run on first execution, except the opt-in opinion classification
        assert len(plan) == 9
        by_step = {step["step"]: step for step in plan}
        assert by_step["opinion_classification"]["run"] is False
        assert all(step["run"] for step in plan if step["step"] != "opinion_classification")

    def test_decide_skip_html(self, tmp_path):
        """Test that visualization step is skipped with without-html."""
        from analysis_core.core import decide_what_to_run, load_specs
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")

        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
            "without-html": True,
        }

        plan = decide_what_to_run(config, None, specs, tmp_path)

        # Visualization step should be skipped
        viz_step = next(s for s in plan if s["step"] == "hierarchical_visualization")
        assert viz_step["run"] is False
        assert "skipping html" in viz_step["reason"]


class TestPipelineOrchestrator:
    """Test PipelineOrchestrator class."""

    def test_orchestrator_init(self, tmp_path):
        """Test orchestrator initialization with config dict."""
        from analysis_core import PipelineOrchestrator

        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
            "plan": [{"step": "extraction", "run": True}],
        }

        orchestrator = PipelineOrchestrator(
            config=config,
            output_base_dir=tmp_path,
        )

        assert orchestrator.config == config
        assert orchestrator.output_base_dir == tmp_path
        assert len(orchestrator.steps) == 9

    def test_orchestrator_from_config(self, tmp_path):
        """Test orchestrator creation from config file."""
        from analysis_core import PipelineOrchestrator

        # Create config file
        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "local",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        orchestrator = PipelineOrchestrator.from_config(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        assert orchestrator.config["input"] == "test"
        assert orchestrator.config["question"] == "Test?"
        assert "plan" in orchestrator.config

    def test_orchestrator_register_step(self, tmp_path):
        """Test registering a custom step."""
        from analysis_core import PipelineOrchestrator

        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
        }

        orchestrator = PipelineOrchestrator(config=config, output_base_dir=tmp_path)

        def custom_step(config):
            pass

        orchestrator.register_step("custom", custom_step)

        assert "custom" in orchestrator._step_functions
        assert orchestrator._step_functions["custom"] is custom_step

    def test_orchestrator_get_plan(self, tmp_path):
        """Test getting execution plan."""
        from analysis_core import PipelineOrchestrator

        plan = [
            {"step": "extraction", "run": True, "reason": "first run"},
            {"step": "embedding", "run": True, "reason": "first run"},
        ]

        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
            "plan": plan,
        }

        orchestrator = PipelineOrchestrator(config=config, output_base_dir=tmp_path)

        assert orchestrator.get_plan() == plan

    def test_orchestrator_get_status(self, tmp_path):
        """Test getting status."""
        from analysis_core import PipelineOrchestrator

        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
            "status": "running",
            "current_job": "extraction",
            "completed_jobs": [],
            "total_token_usage": 100,
            "plan": [],
        }

        orchestrator = PipelineOrchestrator(config=config, output_base_dir=tmp_path)
        status = orchestrator.get_status()

        assert status["status"] == "running"
        assert status["current_job"] == "extraction"
        assert status["total_token_usage"] == 100

    def test_from_dict_uses_previous_status_for_plan(self, tmp_path):
        """Test from_dict loads previous status and computes rerun plan."""
        from analysis_core import PipelineOrchestrator

        output_dir = tmp_path / "outputs" / "demo"
        output_dir.mkdir(parents=True)
        (output_dir / "args.csv").write_text("arg-id,argument\nA1,test\n", encoding="utf-8")
        (output_dir / "relations.csv").write_text("arg-id,comment-id\nA1,1\n", encoding="utf-8")
        (output_dir / "hierarchical_status.json").write_text(
            json.dumps(
                {
                    "completed_jobs": [
                        {
                            "step": "extraction",
                            "params": {
                                "limit": 1000,
                                "workers": 3,
                                "prompt": "",
                                "model": "dummy",
                                "properties": [],
                            },
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        orchestrator = PipelineOrchestrator.from_dict(
            config={
                "name": "demo",
                "input": "demo",
                "question": "Test?",
                "provider": "local",
                "model": "dummy",
                "extraction": {"limit": 1000, "workers": 3, "prompt": "", "model": "dummy", "properties": []},
            },
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        extraction_plan = next(step for step in orchestrator.get_plan() if step["step"] == "extraction")
        assert extraction_plan["run"] is False
        assert extraction_plan["reason"] == "nothing changed"
        assert "previous" in orchestrator.config

    def test_from_dict_prefers_legacy_without_html_key(self, tmp_path):
        """Test from_dict reconciles conflicting without_html variants."""
        from analysis_core import PipelineOrchestrator

        orchestrator = PipelineOrchestrator.from_dict(
            config={
                "name": "demo",
                "input": "demo",
                "question": "Test?",
                "provider": "local",
                "model": "dummy",
                "without_html": False,
                "without-html": True,
            },
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        assert orchestrator.config["without-html"] is True
        assert orchestrator.config["without_html"] is True

    def test_from_dict_preserves_explicit_plan(self, tmp_path):
        """Test from_dict keeps caller-provided plan instead of recomputing it."""
        from analysis_core import PipelineOrchestrator

        explicit_plan = [
            {"step": "extraction", "run": True, "reason": "scoped test"},
            {"step": "embedding", "run": False, "reason": "scoped test"},
        ]

        orchestrator = PipelineOrchestrator.from_dict(
            config={
                "name": "demo",
                "input": "demo",
                "question": "Test?",
                "provider": "local",
                "model": "dummy",
                "plan": explicit_plan,
            },
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        assert orchestrator.get_plan() == explicit_plan

    def test_run_workflow_persists_status_file(self, tmp_path, monkeypatch):
        """Test workflow mode writes hierarchical_status.json with completed jobs."""
        from analysis_core import PipelineOrchestrator
        from analysis_core.plugin import StepOutputs
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult
        from analysis_core.workflow.definition import WorkflowResult

        config = {
            "name": "demo",
            "input": "demo",
            "question": "Test?",
            "provider": "local",
            "model": "dummy",
            "extraction": {},
        }

        orchestrator = PipelineOrchestrator.from_dict(
            config=config,
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                result = WorkflowResult(
                    workflow_id="test",
                    total_token_usage=12,
                    total_token_input=5,
                    total_token_output=7,
                )
                step_result = WorkflowStepResult(
                    step_id="extraction",
                    success=True,
                    outputs=StepOutputs(
                        artifacts={"arguments": ctx.output_dir / "args.csv"},
                        token_usage=12,
                        token_input=5,
                        token_output=7,
                    ),
                )
                if on_step_start:
                    on_step_start("extraction")
                if on_step_complete:
                    on_step_complete("extraction", step_result)
                result.step_results["extraction"] = step_result
                return result

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)

        result = orchestrator.run_workflow()

        assert result.success is True
        status_path = tmp_path / "outputs" / "demo" / "hierarchical_status.json"
        assert status_path.exists()

        status_data = json.loads(status_path.read_text(encoding="utf-8"))
        assert status_data["status"] == "completed"
        assert status_data["total_token_usage"] == 12
        assert status_data["token_usage_input"] == 5
        assert status_data["token_usage_output"] == 7
        assert len(status_data["completed_jobs"]) == 1
        assert status_data["completed_jobs"][0]["step"] == "extraction"

    def test_run_workflow_carries_forward_previously_completed_jobs(self, tmp_path, monkeypatch):
        """Test workflow mode preserves older completed jobs in previously_completed_jobs."""
        from analysis_core import PipelineOrchestrator
        from analysis_core.plugin import StepOutputs
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult
        from analysis_core.workflow.definition import WorkflowResult

        output_dir = tmp_path / "outputs" / "demo"
        output_dir.mkdir(parents=True)
        (output_dir / "hierarchical_status.json").write_text(
            json.dumps(
                {
                    "completed_jobs": [
                        {"step": "extraction", "params": {}},
                        {"step": "embedding", "params": {}},
                    ]
                }
            ),
            encoding="utf-8",
        )

        orchestrator = PipelineOrchestrator.from_dict(
            config={
                "name": "demo",
                "input": "demo",
                "question": "Test?",
                "provider": "local",
                "model": "dummy",
            },
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                result = WorkflowResult(workflow_id="test")
                step_result = WorkflowStepResult(
                    step_id="embedding",
                    success=True,
                    outputs=StepOutputs(artifacts={"embeddings": ctx.output_dir / "embeddings.pkl"}),
                )
                if on_step_start:
                    on_step_start("embedding")
                if on_step_complete:
                    on_step_complete("embedding", step_result)
                result.step_results["embedding"] = step_result
                return result

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)

        orchestrator.run_workflow()

        status_data = json.loads((output_dir / "hierarchical_status.json").read_text(encoding="utf-8"))
        assert any(job["step"] == "embedding" for job in status_data["completed_jobs"])
        assert any(job["step"] == "extraction" for job in status_data["previously_completed_jobs"])

    def test_run_workflow_records_failed_step_error_and_keeps_current_job(self, tmp_path, monkeypatch):
        """Test workflow failures preserve the failed step in status and expose its error."""
        from analysis_core import PipelineOrchestrator
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult
        from analysis_core.workflow.definition import WorkflowResult

        output_dir = tmp_path / "outputs" / "demo"
        output_dir.mkdir(parents=True)

        orchestrator = PipelineOrchestrator.from_dict(
            config={
                "name": "demo",
                "input": "demo",
                "question": "Test?",
                "provider": "local",
                "model": "dummy",
            },
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                result = WorkflowResult(workflow_id="test", success=False)
                step_result = WorkflowStepResult(
                    step_id="embedding",
                    success=False,
                    error="Step 'embedding' failed: boom",
                )
                if on_step_start:
                    on_step_start("embedding")
                if on_step_complete:
                    on_step_complete("embedding", step_result)
                result.step_results["embedding"] = step_result
                return result

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)

        result = orchestrator.run_workflow()

        assert result.success is False
        assert result.error == "Step 'embedding' failed: boom"

        status_data = json.loads((output_dir / "hierarchical_status.json").read_text(encoding="utf-8"))
        assert status_data["status"] == "error"
        assert status_data["current_job"] == "embedding"
        assert status_data["error"] == "Step 'embedding' failed: boom"

    def test_run_workflow_exception_carries_forward_previous_jobs_and_stack_trace(self, tmp_path, monkeypatch):
        """Test unexpected workflow exceptions still preserve rerun history and traceback."""
        from analysis_core import PipelineOrchestrator

        output_dir = tmp_path / "outputs" / "demo"
        output_dir.mkdir(parents=True)
        (output_dir / "hierarchical_status.json").write_text(
            json.dumps(
                {
                    "completed_jobs": [
                        {"step": "extraction", "params": {}},
                    ]
                }
            ),
            encoding="utf-8",
        )

        orchestrator = PipelineOrchestrator.from_dict(
            config={
                "name": "demo",
                "input": "demo",
                "question": "Test?",
                "provider": "local",
                "model": "dummy",
            },
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                if on_step_start:
                    on_step_start("embedding")
                raise RuntimeError("engine exploded")

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)

        result = orchestrator.run_workflow()

        assert result.success is False
        assert result.error == "engine exploded"

        status_data = json.loads((output_dir / "hierarchical_status.json").read_text(encoding="utf-8"))
        assert status_data["status"] == "error"
        assert status_data["current_job"] == "embedding"
        assert status_data["error"] == "engine exploded"
        assert "RuntimeError: engine exploded" in status_data["error_stack_trace"]
        assert any(job["step"] == "extraction" for job in status_data["previously_completed_jobs"])

    def test_run_workflow_exception_preserves_accumulated_token_usage(self, tmp_path, monkeypatch):
        """Test engine exceptions keep token usage already recorded by completed steps."""
        from analysis_core import PipelineOrchestrator
        from analysis_core.plugin import StepOutputs
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult

        output_dir = tmp_path / "outputs" / "demo"
        output_dir.mkdir(parents=True)

        orchestrator = PipelineOrchestrator.from_dict(
            config={
                "name": "demo",
                "input": "demo",
                "question": "Test?",
                "provider": "local",
                "model": "dummy",
            },
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                step_result = WorkflowStepResult(
                    step_id="embedding",
                    success=True,
                    outputs=StepOutputs(
                        artifacts={"embeddings": ctx.output_dir / "embeddings.pkl"},
                        token_usage=9,
                        token_input=4,
                        token_output=5,
                    ),
                )
                if on_step_start:
                    on_step_start("embedding")
                if on_step_complete:
                    on_step_complete("embedding", step_result)
                raise RuntimeError("engine exploded after embedding")

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)

        result = orchestrator.run_workflow()

        assert result.success is False
        assert result.error == "engine exploded after embedding"
        assert result.total_token_usage == 9

        status_data = json.loads((output_dir / "hierarchical_status.json").read_text(encoding="utf-8"))
        assert status_data["total_token_usage"] == 9
        assert status_data["token_usage_input"] == 4
        assert status_data["token_usage_output"] == 5


def test_run_step_preserves_unknown_cost(monkeypatch):
    from analysis_core.core import orchestration

    updates = []
    monkeypatch.setattr(
        orchestration,
        "update_status",
        lambda config, status, output_dir: (updates.append(status), config.update(status)),
    )
    config = {
        "provider": "unknown",
        "model": "new",
        "token_usage_input": 10,
        "token_usage_output": 10,
        "plan": [{"step": "test", "run": True}],
        "test": {},
    }
    orchestration.run_step("test", lambda config: None, config, pricing_calculator=lambda *args: None)
    assert updates[-1]["estimated_cost"] is None


class TestTokenUsageCarryOver:
    """Token usage must survive partial reruns (e.g. aggregation-only after a label edit)."""

    PREVIOUS_STATUS = {
        "status": "completed",
        "total_token_usage": 1000,
        "token_usage_input": 600,
        "token_usage_output": 400,
        "completed_jobs": [
            {"step": "hierarchical_initial_labelling", "params": {}, "token_usage": 300},
            {"step": "hierarchical_aggregation", "params": {}, "token_usage": 0},
        ],
        "previously_completed_jobs": [
            {
                "step": "extraction",
                "params": {},
                "token_usage": 700,
                "token_input": 420,
                "token_output": 280,
            },
        ],
    }

    @staticmethod
    def _plan(run_steps):
        steps = [
            "extraction",
            "embedding",
            "hierarchical_clustering",
            "hierarchical_initial_labelling",
            "hierarchical_merge_labelling",
            "hierarchical_overview",
            "hierarchical_aggregation",
        ]
        return [{"step": step, "run": step in run_steps, "reason": None} for step in steps]

    def test_carried_over_token_usage_without_previous(self):
        from analysis_core.core.orchestration import carried_over_token_usage

        assert carried_over_token_usage(None, self._plan({"extraction"})) == {
            "total_token_usage": 0,
            "token_usage_input": 0,
            "token_usage_output": 0,
        }

    def test_carried_over_token_usage_keeps_totals_when_only_aggregation_runs(self):
        from analysis_core.core.orchestration import carried_over_token_usage

        carried = carried_over_token_usage(self.PREVIOUS_STATUS, self._plan({"hierarchical_aggregation"}))
        assert carried == {"total_token_usage": 1000, "token_usage_input": 600, "token_usage_output": 400}

    def test_carried_over_token_usage_drops_rerun_steps(self):
        from analysis_core.core.orchestration import carried_over_token_usage

        # Labelling job has no input/output split (older status) -> apportioned 60/40.
        carried = carried_over_token_usage(
            self.PREVIOUS_STATUS, self._plan({"hierarchical_initial_labelling", "hierarchical_aggregation"})
        )
        assert carried == {"total_token_usage": 700, "token_usage_input": 420, "token_usage_output": 280}

        # Full rerun (e.g. --force) starts from zero.
        all_steps = {step["step"] for step in self._plan(set())}
        assert carried_over_token_usage(self.PREVIOUS_STATUS, self._plan(all_steps)) == {
            "total_token_usage": 0,
            "token_usage_input": 0,
            "token_usage_output": 0,
        }

    def test_carried_over_token_usage_after_failed_partial_rerun(self):
        """A failed partial rerun already left the steps it re-ran out of its totals."""
        from analysis_core.core.orchestration import carried_over_token_usage

        # Labelling was re-run after PREVIOUS_STATUS and failed: that run started from
        # 1000 - 300 and completed nothing, so labelling's latest record is still the old one.
        failed_rerun = {
            "status": "error",
            "total_token_usage": 700,
            "token_usage_input": 420,
            "token_usage_output": 280,
            "completed_jobs": [],
            "previously_completed_jobs": self.PREVIOUS_STATUS["completed_jobs"]
            + self.PREVIOUS_STATUS["previously_completed_jobs"],
        }

        carried = carried_over_token_usage(
            failed_rerun, self._plan({"hierarchical_initial_labelling", "hierarchical_aggregation"})
        )
        assert carried == {"total_token_usage": 700, "token_usage_input": 420, "token_usage_output": 280}

    def test_carried_over_token_usage_skips_steps_no_longer_in_the_report(self):
        """Tokens of disabled steps and of steps outside the current plan are not carried."""
        from analysis_core.core.orchestration import carried_over_token_usage

        def job(step, tokens):
            return {
                "step": step,
                "params": {},
                "token_usage": tokens,
                "token_input": tokens * 3 // 5,
                "token_output": tokens * 2 // 5,
            }

        previous = {
            "status": "completed",
            "total_token_usage": 500,
            "token_usage_input": 300,
            "token_usage_output": 200,
            "completed_jobs": [
                job("extraction", 100),
                job("opinion_classification", 100),
                job("embedding", 0),
                job("hierarchical_clustering", 0),
                job("hierarchical_initial_labelling", 100),
                job("hierarchical_merge_labelling", 100),
                job("hierarchical_overview", 100),
                job("hierarchical_aggregation", 0),
            ],
        }
        hierarchical = [j["step"] for j in previous["completed_jobs"]]
        disabled = {"opinion_classification": {"enabled": False}}

        # opinion_classification turned off and everything else forced to re-run
        forced = [{"step": s, "run": s != "opinion_classification"} for s in hierarchical]
        assert carried_over_token_usage(previous, forced, disabled) == {
            "total_token_usage": 0,
            "token_usage_input": 0,
            "token_usage_output": 0,
        }

        # opinion_classification turned off and only aggregation re-runs
        aggregation_only = [{"step": s, "run": s == "hierarchical_aggregation"} for s in hierarchical]
        assert carried_over_token_usage(previous, aggregation_only, disabled) == {
            "total_token_usage": 400,
            "token_usage_input": 240,
            "token_usage_output": 160,
        }

        # Switched to llm_grouping in the same output dir: only extraction / embedding are kept
        llm_grouping = ["extraction", "embedding", "llm_grouping", "hierarchical_overview", "hierarchical_aggregation"]
        plan = [{"step": s, "run": s not in ("extraction", "embedding")} for s in llm_grouping]
        assert carried_over_token_usage(previous, plan, {}) == {
            "total_token_usage": 100,
            "token_usage_input": 60,
            "token_usage_output": 40,
        }

    def test_carried_over_token_usage_never_exceeds_previous_totals(self):
        """Job records copied from another report (admin duplicate) were never counted here."""
        from analysis_core.core.orchestration import carried_over_token_usage

        duplicated = {
            "status": "completed",
            # The duplicate started from zero and only re-ran the overview.
            "total_token_usage": 100,
            "token_usage_input": 60,
            "token_usage_output": 40,
            "completed_jobs": [
                {
                    "step": "hierarchical_overview",
                    "params": {},
                    "token_usage": 100,
                    "token_input": 60,
                    "token_output": 40,
                },
                {"step": "hierarchical_aggregation", "params": {}, "token_usage": 0},
            ],
            "previously_completed_jobs": self.PREVIOUS_STATUS["previously_completed_jobs"]
            + [self.PREVIOUS_STATUS["completed_jobs"][0]],
        }

        carried = carried_over_token_usage(duplicated, self._plan({"hierarchical_aggregation"}))
        assert carried == {"total_token_usage": 100, "token_usage_input": 60, "token_usage_output": 40}

    def test_run_workflow_aggregation_only_preserves_token_usage(self, tmp_path, monkeypatch):
        """Regression: admin label/config edits rerun aggregation only and used to reset tokens to 0."""
        from analysis_core import PipelineOrchestrator
        from analysis_core.plugin import StepOutputs
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult
        from analysis_core.workflow.definition import WorkflowResult

        output_dir = tmp_path / "outputs" / "demo"
        output_dir.mkdir(parents=True)
        (output_dir / "hierarchical_status.json").write_text(json.dumps(self.PREVIOUS_STATUS), encoding="utf-8")

        orchestrator = PipelineOrchestrator.from_dict(
            config={
                "name": "demo",
                "input": "demo",
                "question": "Test?",
                "provider": "local",
                "model": "dummy",
                "plan": self._plan({"hierarchical_aggregation"}),
            },
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                result = WorkflowResult(workflow_id="test")
                step_result = WorkflowStepResult(
                    step_id="aggregation",
                    success=True,
                    outputs=StepOutputs(artifacts={"result": ctx.output_dir / "hierarchical_result.json"}),
                )
                if on_step_start:
                    on_step_start("aggregation")
                if on_step_complete:
                    on_step_complete("aggregation", step_result)
                result.step_results["aggregation"] = step_result
                return result

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)

        result = orchestrator.run_workflow()

        assert result.success is True
        assert result.total_token_usage == 1000
        status_data = json.loads((output_dir / "hierarchical_status.json").read_text(encoding="utf-8"))
        assert status_data["status"] == "completed"
        assert status_data["total_token_usage"] == 1000
        assert status_data["token_usage_input"] == 600
        assert status_data["token_usage_output"] == 400

    def test_run_workflow_rerun_step_replaces_its_previous_tokens(self, tmp_path, monkeypatch):
        """A re-run step's new tokens replace its old ones; skipped steps keep theirs."""
        from analysis_core import PipelineOrchestrator
        from analysis_core.plugin import StepOutputs
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult
        from analysis_core.workflow.definition import WorkflowResult

        output_dir = tmp_path / "outputs" / "demo"
        output_dir.mkdir(parents=True)
        (output_dir / "hierarchical_status.json").write_text(json.dumps(self.PREVIOUS_STATUS), encoding="utf-8")

        orchestrator = PipelineOrchestrator.from_dict(
            config={
                "name": "demo",
                "input": "demo",
                "question": "Test?",
                "provider": "local",
                "model": "dummy",
                "plan": self._plan({"hierarchical_initial_labelling"}),
            },
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                result = WorkflowResult(
                    workflow_id="test", total_token_usage=250, total_token_input=150, total_token_output=100
                )
                step_result = WorkflowStepResult(
                    step_id="initial_labelling",
                    success=True,
                    outputs=StepOutputs(
                        artifacts={"labels": ctx.output_dir / "hierarchical_initial_labels.csv"},
                        token_usage=250,
                        token_input=150,
                        token_output=100,
                    ),
                )
                if on_step_start:
                    on_step_start("initial_labelling")
                if on_step_complete:
                    on_step_complete("initial_labelling", step_result)
                result.step_results["initial_labelling"] = step_result
                return result

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)

        result = orchestrator.run_workflow()

        assert result.total_token_usage == 950
        status_data = json.loads((output_dir / "hierarchical_status.json").read_text(encoding="utf-8"))
        assert status_data["total_token_usage"] == 950
        assert status_data["token_usage_input"] == 570
        assert status_data["token_usage_output"] == 380
        labelling_job = next(
            job for job in status_data["completed_jobs"] if job["step"] == "hierarchical_initial_labelling"
        )
        assert labelling_job["token_usage"] == 250
        assert labelling_job["token_input"] == 150
        assert labelling_job["token_output"] == 100

    def test_initialization_only_step_keeps_previous_token_usage_in_status(self, tmp_path):
        """The CLI path (--only) must not zero the persisted totals while the run starts."""
        from analysis_core.core import initialization

        config_path = tmp_path / "job.json"
        config_path.write_text(json.dumps({"input": "test", "question": "Test?", "provider": "local"}))
        input_dir = tmp_path / "inputs"
        input_dir.mkdir()
        output_base = tmp_path / "outputs"
        (output_base / "job").mkdir(parents=True)
        status_path = output_base / "job" / "hierarchical_status.json"
        status_path.write_text(json.dumps(self.PREVIOUS_STATUS), encoding="utf-8")

        config = initialization(
            config_path=config_path,
            only="hierarchical_aggregation",
            skip_interaction=True,
            output_base_dir=output_base,
            input_base_dir=input_dir,
        )

        assert config["total_token_usage"] == 1000
        status_data = json.loads(status_path.read_text(encoding="utf-8"))
        assert status_data["status"] == "running"
        assert status_data["total_token_usage"] == 1000
        assert status_data["token_usage_input"] == 600
        assert status_data["token_usage_output"] == 400

    LLM_WORKFLOW_STEPS = {"extraction", "opinion_classification", "initial_labelling", "merge_labelling", "overview"}

    def _run_cli_job(self, tmp_path, monkeypatch, step_configs, fail_step=None, force=False):
        """Run job "job" the way the CLI does; each LLM step uses 100 tokens (60 in / 40 out)."""
        from analysis_core import PipelineOrchestrator
        from analysis_core.plugin import StepOutputs
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult
        from analysis_core.workflow.definition import WorkflowResult

        llm_steps = self.LLM_WORKFLOW_STEPS
        output_dir = tmp_path / "outputs" / "job"
        output_dir.mkdir(parents=True, exist_ok=True)
        for filename in (
            "args.csv",
            "relations.csv",
            "opinion_classifications.csv",
            "embeddings.pkl",
            "hierarchical_clusters.csv",
            "hierarchical_initial_labels.csv",
            "hierarchical_merge_labels.csv",
            "hierarchical_overview.txt",
            "hierarchical_result.json",
        ):
            (output_dir / filename).write_text("x", encoding="utf-8")
        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps({"input": "job", "question": "Q?", "provider": "local", **step_configs}), encoding="utf-8"
        )

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                result = WorkflowResult(workflow_id=workflow.id)
                for step in workflow.steps:
                    if step.id in skip_steps:
                        continue
                    on_step_start(step.id)
                    if step.id == fail_step:
                        step_result = WorkflowStepResult(step_id=step.id, success=False, error="simulated failure")
                        on_step_complete(step.id, step_result)
                        result.step_results[step.id] = step_result
                        result.success = False
                        break
                    tokens = 100 if step.id in llm_steps else 0
                    outputs = StepOutputs(token_usage=tokens, token_input=tokens * 3 // 5, token_output=tokens * 2 // 5)
                    result.total_token_usage += outputs.token_usage
                    result.total_token_input += outputs.token_input
                    result.total_token_output += outputs.token_output
                    step_result = WorkflowStepResult(step_id=step.id, success=True, outputs=outputs)
                    on_step_complete(step.id, step_result)
                    result.step_results[step.id] = step_result
                return result

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)
        orchestrator = PipelineOrchestrator.from_config(
            config_path,
            force=force,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )
        orchestrator.run_default()
        return json.loads((output_dir / "hierarchical_status.json").read_text(encoding="utf-8"))

    def test_cli_retry_after_failed_partial_rerun_counts_every_kept_step(self, tmp_path, monkeypatch):
        first = self._run_cli_job(tmp_path, monkeypatch, {"hierarchical_overview": {"prompt": "v1"}})
        assert first["total_token_usage"] == 400

        failed = self._run_cli_job(
            tmp_path, monkeypatch, {"hierarchical_overview": {"prompt": "v2"}}, fail_step="overview"
        )
        assert failed["status"] == "error"
        assert failed["total_token_usage"] == 300

        retried = self._run_cli_job(tmp_path, monkeypatch, {"hierarchical_overview": {"prompt": "v2"}})
        assert retried["status"] == "completed"
        assert [job["step"] for job in retried["completed_jobs"]] == [
            "hierarchical_overview",
            "hierarchical_aggregation",
        ]
        assert (retried["total_token_usage"], retried["token_usage_input"], retried["token_usage_output"]) == (
            400,
            240,
            160,
        )

    def test_cli_force_after_disabling_a_step_drops_its_tokens(self, tmp_path, monkeypatch):
        first = self._run_cli_job(tmp_path, monkeypatch, {"opinion_classification": {"enabled": True}})
        assert first["total_token_usage"] == 500

        forced = self._run_cli_job(tmp_path, monkeypatch, {"opinion_classification": {"enabled": False}}, force=True)
        assert (forced["total_token_usage"], forced["token_usage_input"], forced["token_usage_output"]) == (
            400,
            240,
            160,
        )
