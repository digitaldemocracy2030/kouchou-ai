"""複製でプロバイダを替えたときの埋め込みモデルの扱い

複製は複製元の embedding.model を引き継ぐ（同じベクトル空間を保つため）。プロバイダを替えた複製では、
新しいプロバイダで使える埋め込みモデルに揃えるか、起動前に 400 で止める。
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

SOURCE_SLUG = "source"


@pytest.fixture
def duplicate_env(monkeypatch, tmp_path):
    """一時ディレクトリの中で複製し、analysis-core は起動せずに config のパスだけを記録する"""
    from src.services import report_duplicate

    env = SimpleNamespace(
        reports=tmp_path / "reports",
        configs=tmp_path / "configs",
        inputs=tmp_path / "inputs",
        launched=[],
    )
    monkeypatch.setattr(report_duplicate.settings, "REPORT_DIR", env.reports)
    monkeypatch.setattr(report_duplicate.settings, "CONFIG_DIR", env.configs)
    monkeypatch.setattr(report_duplicate.settings, "INPUT_DIR", env.inputs)
    monkeypatch.setattr(report_duplicate, "ReportSyncService", MagicMock())
    monkeypatch.setattr(report_duplicate, "slug_exists", lambda slug: False)
    monkeypatch.setattr(report_duplicate, "add_new_report_to_status_from_config", lambda *args, **kwargs: None)
    monkeypatch.setattr(report_duplicate, "delete_report_from_status", lambda slug: None)
    monkeypatch.setattr(
        report_duplicate,
        "launch_report_generation_from_config",
        lambda config_path, slug, user_api_key=None: env.launched.append(config_path),
    )
    return env


def _apply(source_config: dict, **overrides) -> dict:
    from src.schemas.admin_report import ReportDuplicateOverrides
    from src.services import report_duplicate

    return report_duplicate._apply_overrides(
        json.loads(json.dumps(source_config)), ReportDuplicateOverrides(**overrides)
    )


def test_duplicate_gemini_to_openai_replaces_gemini_embedding_model():
    """Gemini のレポートを OpenAI に替えて複製すると、OpenAI で使える埋め込みモデルに置き換える。

    複製元の gemini-embedding-001 のままだと、抽出を全件やり直した後に
    OpenAI の埋め込みで『Invalid embedding model』になる。
    """
    source = {"provider": "gemini", "model": "gemini-2.5-flash", "embedding": {"model": "gemini-embedding-001"}}

    config = _apply(source, provider="openai", model="gpt-4o-mini")

    assert config["provider"] == "openai"
    assert config["embedding"] == {"model": "text-embedding-3-small"}


def test_duplicate_openai_to_gemini_uses_gemini_embedding_model_explicitly():
    """OpenAI→Gemini でも、別名の読み替えに頼らず Gemini の埋め込みモデルを明示する"""
    source = {"provider": "openai", "model": "gpt-4o-mini", "embedding": {"model": "text-embedding-3-large"}}

    config = _apply(source, provider="gemini", model="gemini-2.5-flash")

    assert config["embedding"] == {"model": "gemini-embedding-001"}


def test_duplicate_azure_to_openai_sets_openai_embedding_model():
    """Azure のレポート（config に embedding が無い）を OpenAI に替えると、OpenAI の既定を入れる"""
    source = {"provider": "azure", "model": "azure-server"}

    config = _apply(source, provider="openai", model="gpt-4o-mini")

    assert config["embedding"] == {"model": "text-embedding-3-small"}


def test_duplicate_to_azure_drops_embedding_section_like_create():
    """Azure はサーバー設定のデプロイで埋め込むので、新規作成と同じく embedding セクションを省く"""
    source = {"provider": "gemini", "model": "gemini-2.5-flash", "embedding": {"model": "gemini-embedding-001"}}

    config = _apply(source, provider="azure", model="azure-server")

    assert "embedding" not in config


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(
            {"provider": "openai", "model": "gpt-4o-mini", "embedding": {"model": "text-embedding-3-large"}},
            id="openai",
        ),
        pytest.param(
            {"provider": "gemini", "model": "gemini-2.5-flash", "embedding": {"model": "gemini-embedding-001"}},
            id="gemini",
        ),
    ],
)
@pytest.mark.parametrize("send_same_provider", [False, True], ids=["provider-omitted", "same-provider"])
def test_duplicate_without_provider_change_keeps_source_embedding_model(source, send_same_provider):
    """プロバイダを替えない複製では、複製元の埋め込みモデル（同じベクトル空間）を引き継ぐ"""
    overrides = {"model": "other-chat-model"}
    if send_same_provider:
        overrides["provider"] = source["provider"]

    config = _apply(source, **overrides)

    assert config["embedding"] == source["embedding"]


def test_duplicate_provider_change_respects_explicit_embedding_model():
    """埋め込みモデルを明示した場合は、その指定をそのまま使う"""
    source = {"provider": "gemini", "model": "gemini-2.5-flash", "embedding": {"model": "gemini-embedding-001"}}

    config = _apply(source, provider="openai", model="gpt-4o-mini", embedding_model="text-embedding-3-large")

    assert config["embedding"] == {"model": "text-embedding-3-large"}


def test_duplicate_to_openai_keeps_valid_openai_embedding_model():
    """新しいプロバイダでもそのまま使える埋め込みモデルなら替えない（OpenRouter のサーバ内埋め込み→OpenAI など）"""
    source = {
        "provider": "openrouter",
        "model": "openai/gpt-4o-mini-2024-07-18",
        "is_embedded_at_local": True,
        "embedding": {"model": "text-embedding-3-large"},
    }

    config = _apply(source, provider="openai", model="gpt-4o-mini", is_embedded_at_local=False)

    assert config["embedding"] == {"model": "text-embedding-3-large"}


@pytest.mark.parametrize("new_provider", ["openrouter", "local"])
def test_duplicate_to_provider_without_embedding_api_requires_local_embedding(new_provider):
    """OpenRouter・local に替えるとき、サーバ内埋め込みが無効なら起動前に 400 で止める。

    OpenRouter は埋め込み API が未実装で、local は選べる埋め込みモデルが無い
    （新規作成画面でもサーバ内埋め込みを求める）。抽出の課金後に失敗させない。
    """
    from fastapi import HTTPException

    source = {"provider": "openai", "model": "gpt-4o-mini", "embedding": {"model": "text-embedding-3-small"}}

    with pytest.raises(HTTPException) as exc_info:
        _apply(source, provider=new_provider, model="some-model")

    assert exc_info.value.status_code == 400
    assert "is_embedded_at_local" in exc_info.value.detail


@pytest.mark.parametrize("new_provider", ["openrouter", "local"])
def test_duplicate_to_provider_without_embedding_api_with_local_embedding(new_provider):
    """サーバ内埋め込みを有効にすれば、OpenRouter・local にも替えられる（埋め込みモデル名は使われない）"""
    source = {"provider": "openai", "model": "gpt-4o-mini", "embedding": {"model": "text-embedding-3-small"}}

    config = _apply(source, provider=new_provider, model="some-model", is_embedded_at_local=True)

    assert config["provider"] == new_provider
    assert config["is_embedded_at_local"] is True


def test_duplicate_to_local_with_explicit_embedding_model_is_allowed():
    """local では、埋め込みモデルを明示すればローカルサーバーの埋め込みを使える（CLI と同じ使い方）"""
    source = {"provider": "openai", "model": "gpt-4o-mini", "embedding": {"model": "text-embedding-3-small"}}

    config = _apply(source, provider="local", model="llama3", embedding_model="nomic-embed-text")

    assert config["embedding"] == {"model": "nomic-embed-text"}


def test_duplicate_gemini_to_openai_end_to_end_writes_valid_embedding_and_rejects_openrouter(duplicate_env):
    """config ファイルの経路（本番の通常経路）で、複製後の config と 400 時の後始末を確かめる"""
    from fastapi import HTTPException

    duplicate_env.configs.mkdir(parents=True)
    duplicate_env.inputs.mkdir(parents=True)
    (duplicate_env.reports / SOURCE_SLUG).mkdir(parents=True)
    source_config = {
        "name": SOURCE_SLUG,
        "input": SOURCE_SLUG,
        "question": "Q",
        "intro": "I",
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "is_embedded_at_local": False,
        "extraction": {"prompt": "ex", "workers": 1},
        "embedding": {"model": "gemini-embedding-001"},
    }
    (duplicate_env.configs / f"{SOURCE_SLUG}.json").write_text(json.dumps(source_config), encoding="utf-8")
    (duplicate_env.inputs / f"{SOURCE_SLUG}.csv").write_text("comment-id,comment-body\n1,hello\n", encoding="utf-8")

    from src.schemas.admin_report import ReportDuplicateOverrides, ReportDuplicateRequest
    from src.services import report_duplicate

    report_duplicate.duplicate_report(
        SOURCE_SLUG,
        ReportDuplicateRequest(
            new_slug="copy", overrides=ReportDuplicateOverrides(provider="openai", model="gpt-4o-mini")
        ),
    )
    written = json.loads(duplicate_env.launched[-1].read_text(encoding="utf-8"))
    assert written["embedding"] == {"model": "text-embedding-3-small"}

    payload = ReportDuplicateRequest(
        new_slug="copy-openrouter",
        overrides=ReportDuplicateOverrides(provider="openrouter", model="openai/gpt-4o-mini-2024-07-18"),
    )
    with pytest.raises(HTTPException) as exc_info:
        report_duplicate.duplicate_report(SOURCE_SLUG, payload)
    assert exc_info.value.status_code == 400
    # 起動前に止め、途中まで作った複製先は残さない
    assert not (duplicate_env.configs / "copy-openrouter.json").exists()
    assert not (duplicate_env.inputs / "copy-openrouter.csv").exists()
    assert len(duplicate_env.launched) == 1
