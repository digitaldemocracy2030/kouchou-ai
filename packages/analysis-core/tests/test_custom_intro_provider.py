"""集計が書く冒頭の文（create_custom_intro）のプロバイダ・モデル表記のテスト

Azure は config のモデル名（管理画面の固定値 azure-server など）ではなく、サーバーに設定した
デプロイを使う。使っていないモデル名や内部値を、公開される冒頭の文に載せない。
"""

import json

import pytest

from analysis_core.steps.hierarchical_aggregation import create_custom_intro


def _intro(tmp_path, provider, model):
    outputs = tmp_path / "outputs"
    inputs = tmp_path / "inputs"
    (outputs / "r").mkdir(parents=True)
    inputs.mkdir()
    (inputs / "r.csv").write_text("comment-id,comment-body\n1,a\n2,b\n", encoding="utf-8")
    (outputs / "r" / "args.csv").write_text("arg-id,argument\nA1_0,x\n", encoding="utf-8")
    (outputs / "r" / "hierarchical_result.json").write_text(json.dumps({"config": {}}), encoding="utf-8")
    config = {
        "_output_base_dir": str(outputs),
        "_input_base_dir": str(inputs),
        "output_dir": "r",
        "input": "r",
        "intro": "はじめに",
        "extraction": {"limit": 10},
        "model": model,
    }
    if provider is not None:
        config["provider"] = provider
    create_custom_intro(config)
    result = json.loads((outputs / "r" / "hierarchical_result.json").read_text(encoding="utf-8"))
    return result["config"]["intro"]


@pytest.mark.parametrize("model", ["azure-server", "gpt-4o"])
def test_azure_intro_does_not_show_unused_model_name(tmp_path, model):
    intro = _intro(tmp_path, "azure", model)
    assert "Azure OpenAI API（サーバー設定のモデル）を用いて" in intro
    assert model not in intro


@pytest.mark.parametrize(
    ("provider", "model", "expected"),
    [
        ("openai", "gpt-4o-mini", "OpenAI API (gpt-4o-mini)"),
        (None, "gpt-4o-mini", "OpenAI API (gpt-4o-mini)"),
        ("gemini", "gemini-2.5-flash", "Google Gemini API (gemini-2.5-flash)"),
        ("openrouter", "openai/gpt-4o-mini", "OpenRouter API (openai/gpt-4o-mini)"),
        ("local", "llama3", "Local LLM (llama3)"),
    ],
)
def test_intro_shows_provider_and_model(tmp_path, provider, model, expected):
    intro = _intro(tmp_path, provider, model)
    assert f"{expected}を用いて" in intro
    assert "分析対象となったデータの件数は2件" in intro
