"""抽出・ラベル生成・意見分類の失敗の理由を、秘密情報を伏せてログに残す。

以前は失敗を例外の型名だけで記録していたため、モデルの拒否・安全ブロック・設定誤りが
どれも ValueError / AttributeError としか見えず、原因が分からなかった。
"""

import importlib
import json
import logging
import types
from unittest.mock import MagicMock, patch

import pytest
from google.genai import types as genai_types
from openai.types.chat import ChatCompletion, ParsedChatCompletion
from openai.types.completion_usage import CompletionUsage

from analysis_core.services import llm
from analysis_core.services.error_summary import redact_secrets, summarize_exception

extraction = importlib.import_module("analysis_core.steps.extraction")
labelling = importlib.import_module("analysis_core.steps._labelling")
classification = importlib.import_module("analysis_core.steps.opinion_classification")

FAKE_OPENAI_KEY = "sk-proj-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789"
FAKE_USER_KEY = "user-supplied-secret-value-42"
FLEX_MESSAGE = "OPENAI_FLEX_TIMEOUT_SECONDS must be a positive integer number of seconds (got '15m')"


# --- 伏せ字 -------------------------------------------------------------------


@pytest.mark.parametrize(
    "secret_text",
    [
        "Incorrect API key provided: sk-proj-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789.",
        # OpenAI は一部を伏せたキーを返すが、末尾の文字は残るので全部伏せる
        "Incorrect API key provided: sk-proj-****************************************wxyz.",
        "OpenRouter: invalid key sk-or-v1-0123456789abcdef0123456789abcdef",
        "Gemini: AIzaSyA-1234567890abcdefghijklmnopqrstu is not valid",
        "GET https://example.invalid/v1/models?key=AIzaSyA-1234567890abcdefghijk&alt=json failed",
        "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload.signature rejected",
        "api_key=plainsecretvalue rejected",
        "Azure key 0123456789abcdef0123456789abcdef was rejected",
    ],
)
def test_redact_secrets_masks_api_key_shapes(secret_text):
    redacted = redact_secrets(secret_text)
    for fragment in (
        "AbCdEfGh",
        "wxyz",
        "0123456789abcdef",
        "AIzaSyA",
        "eyJhbGci",
        "plainsecretvalue",
    ):
        assert fragment not in redacted
    assert "[REDACTED]" in redacted


def test_redact_secrets_masks_configured_key_values(monkeypatch):
    monkeypatch.setenv("USER_API_KEY", FAKE_USER_KEY)
    monkeypatch.setenv("AZURE_CHATCOMPLETION_API_KEY", "short-azure-k3y")
    assert FAKE_USER_KEY not in redact_secrets(f"rejected key {FAKE_USER_KEY}")
    assert "short-azure-k3y" not in redact_secrets("rejected key short-azure-k3y")
    # 明示的に渡した値（config の user_api_key など）も伏せる
    assert "cfg-key-value" not in redact_secrets("bad cfg-key-value", secrets=("cfg-key-value",))


def test_summarize_exception_keeps_type_and_safe_message():
    summary = summarize_exception(ValueError(FLEX_MESSAGE))
    assert summary == f"ValueError: {FLEX_MESSAGE}"


def test_summarize_exception_is_single_line_and_truncated():
    summary = summarize_exception(RuntimeError("line1\nline2 " + "x" * 2000))
    assert "\n" not in summary
    assert summary.startswith("RuntimeError: line1 line2 ")
    assert len(summary) < 400


def test_summarize_exception_redacts_before_truncating():
    # 切り詰めでキーが途中で切れると伏せ字のパターンに一致しなくなるので、先に伏せる
    message = "a" * 290 + " " + FAKE_OPENAI_KEY
    assert "sk-proj-AbCd" not in summarize_exception(RuntimeError(message))


# --- 抽出・ラベル生成・意見分類のログ ---------------------------------------


def test_extraction_logs_redacted_failure_reason(monkeypatch, caplog, tmp_path):
    def extract(text, *args):
        if text == "flex":
            raise ValueError(FLEX_MESSAGE)
        raise PermissionError(f"Error code: 401 - Incorrect API key provided: {FAKE_OPENAI_KEY}")

    monkeypatch.setattr(extraction, "extract_arguments", extract)
    diagnostics = tmp_path / "diag.jsonl"
    with caplog.at_level(logging.ERROR), pytest.raises(extraction.ExtractionBatchError) as error:
        extraction.extract_batch(
            ["flex", "auth"], "p", "m", 2, config={}, comment_ids=["c1", "c2"], diagnostics_path=diagnostics
        )

    log = caplog.text
    assert "c1" in log and FLEX_MESSAGE in log
    assert "c2" in log and "PermissionError" in log and "Incorrect API key provided" in log
    assert "AbCdEfGh" not in log
    # status に入る例外メッセージと診断は、従来どおり分類名だけ（原文・応答本文を入れない）
    assert error.value.failures == {0: "ValueError", 1: "PermissionError"}
    assert "15m" not in str(error.value)
    records = [json.loads(line) for line in diagnostics.read_text(encoding="utf-8").splitlines()]
    assert [r["error_type"] for r in records] == ["ValueError", "PermissionError"]
    assert "15m" not in diagnostics.read_text(encoding="utf-8")


def test_labelling_logs_redacted_failure_reason(caplog):
    def process(cluster_id):
        raise PermissionError(f"Incorrect API key provided: {FAKE_OPENAI_KEY}")

    with caplog.at_level(logging.ERROR), pytest.raises(labelling.LabellingBatchError) as error:
        labelling.run_labelling_batch(process, ["1_0"], 1, "hierarchical_initial_labelling")

    assert "1_0" in caplog.text and "Incorrect API key provided" in caplog.text
    assert "AbCdEfGh" not in caplog.text
    assert error.value.failures == {"1_0": "PermissionError"}


def test_classification_logs_redacted_failure_reason(monkeypatch, caplog):
    def classify(*args):
        raise ValueError(FLEX_MESSAGE)

    monkeypatch.setattr(classification, "classify_argument", classify)
    with caplog.at_level(logging.ERROR), pytest.raises(classification.ClassificationBatchError) as error:
        classification.classify_batch(["a1"], ["text"], "p", ("label",), "m", 1)

    assert "a1" in caplog.text and FLEX_MESSAGE in caplog.text
    assert error.value.failures == {"a1": "ValueError"}


# --- 拒否・安全ブロックの検出 ---------------------------------------------------


def _openai_completion(message: dict, finish_reason: str = "stop") -> ChatCompletion:
    return ChatCompletion(
        id="x",
        object="chat.completion",
        created=0,
        model="m",
        choices=[{"index": 0, "finish_reason": finish_reason, "message": {"role": "assistant", **message}}],
        usage=CompletionUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )


def _parsed_completion(message: dict, finish_reason: str = "stop") -> ParsedChatCompletion:
    return ParsedChatCompletion(
        id="x",
        object="chat.completion",
        created=0,
        model="m",
        choices=[{"index": 0, "finish_reason": finish_reason, "message": {"role": "assistant", **message}}],
        usage=CompletionUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
    )


def _openai_client(completion):
    client = MagicMock()
    client.chat.completions.create.return_value = completion
    client.beta.chat.completions.parse.return_value = completion
    return client


def test_openai_refusal_raises_refusal_error(monkeypatch):
    completion = _openai_completion({"content": None, "refusal": "I can't help with that."})
    monkeypatch.setenv("OPENAI_USE_FLEX", "0")
    with patch.object(llm, "OpenAI", return_value=_openai_client(completion)):
        with pytest.raises(llm.LLMRefusalError) as error:
            llm.request_to_openai([{"role": "user", "content": "hi"}], model="gpt-4o-mini", user_api_key="k")
    # 拒否の文面（応答本文）はメッセージに入れない
    assert "I can't help" not in str(error.value)


def test_openai_content_filter_raises_safety_block_error(monkeypatch):
    completion = _openai_completion({"content": None}, finish_reason="content_filter")
    monkeypatch.setenv("OPENAI_USE_FLEX", "0")
    with patch.object(llm, "OpenAI", return_value=_openai_client(completion)):
        with pytest.raises(llm.LLMSafetyBlockError):
            llm.request_to_openai([{"role": "user", "content": "hi"}], model="gpt-4o-mini", user_api_key="k")


def test_openai_normal_response_is_returned(monkeypatch):
    completion = _openai_completion({"content": '{"ok": true}'})
    monkeypatch.setenv("OPENAI_USE_FLEX", "0")
    with patch.object(llm, "OpenAI", return_value=_openai_client(completion)):
        content, *_ = llm.request_to_openai([{"role": "user", "content": "hi"}], model="gpt-4o-mini", user_api_key="k")
    assert content == '{"ok": true}'


@pytest.fixture
def azure_env(monkeypatch):
    monkeypatch.setenv("AZURE_CHATCOMPLETION_ENDPOINT", "https://example.invalid")
    monkeypatch.setenv("AZURE_CHATCOMPLETION_DEPLOYMENT_NAME", "dep")
    monkeypatch.setenv("AZURE_CHATCOMPLETION_API_KEY", "k")
    monkeypatch.setenv("AZURE_CHATCOMPLETION_VERSION", "2024-10-21")


def test_azure_structured_refusal_raises_refusal_error(azure_env):
    completion = _parsed_completion({"content": None, "refusal": "I can't help with that.", "parsed": None})
    with patch.object(llm, "AzureOpenAI", return_value=_openai_client(completion)):
        with pytest.raises(llm.LLMRefusalError):
            llm.request_to_azure_chatcompletion(
                [{"role": "user", "content": "hi"}], json_schema=extraction.ExtractionResponse
            )


def test_azure_structured_without_parsed_raises_value_error(azure_env):
    # 拒否でも安全ブロックでもないのに parsed が無い場合も、AttributeError ではなく理由つきで止める
    completion = _parsed_completion({"content": None, "parsed": None})
    with patch.object(llm, "AzureOpenAI", return_value=_openai_client(completion)):
        with pytest.raises(ValueError, match="finish_reason=stop"):
            llm.request_to_azure_chatcompletion(
                [{"role": "user", "content": "hi"}], json_schema=extraction.ExtractionResponse
            )


def _gemini(response):
    models = MagicMock()
    models.generate_content.return_value = response
    client = MagicMock()
    client.models = models
    return types.SimpleNamespace(Client=MagicMock(return_value=client))


class _GeminiClientError(Exception):
    pass


@pytest.mark.parametrize(
    "response",
    [
        genai_types.GenerateContentResponse(
            candidates=[genai_types.Candidate(finish_reason=genai_types.FinishReason.SAFETY, content=None)]
        ),
        genai_types.GenerateContentResponse(
            prompt_feedback=genai_types.GenerateContentResponsePromptFeedback(
                block_reason=genai_types.BlockedReason.SAFETY
            )
        ),
    ],
    ids=["finish_reason", "prompt_feedback"],
)
def test_gemini_safety_block_raises_safety_block_error(monkeypatch, response):
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    with (
        patch.object(llm, "genai", _gemini(response)),
        patch.object(llm, "genai_errors", types.SimpleNamespace(ClientError=_GeminiClientError, ServerError=OSError)),
    ):
        with pytest.raises(llm.LLMSafetyBlockError, match="SAFETY"):
            llm.request_to_gemini_chatcompletion(
                [{"role": "user", "content": "hi"}], json_schema=extraction.ExtractionResponse
            )


def test_extraction_records_refusal_as_its_own_failure_type(monkeypatch):
    def extract(text, *args):
        raise llm.LLMRefusalError("OpenAI: the model refused to answer")

    monkeypatch.setattr(extraction, "extract_arguments", extract)
    with pytest.raises(extraction.ExtractionBatchError) as error:
        extraction.extract_batch(["x"], "p", "m", 1, config={}, comment_ids=["c1"])
    assert error.value.failures == {0: "LLMRefusalError"}


# --- OPENAI_FLEX_TIMEOUT_SECONDS の起動時検証 ---------------------------------


def test_invalid_flex_timeout_fails_fast_with_variable_name(monkeypatch):
    from analysis_core.core.orchestration import validate_api_keys

    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("OPENAI_FLEX_TIMEOUT_SECONDS", "15m")
    with pytest.raises(ValueError, match="OPENAI_FLEX_TIMEOUT_SECONDS"):
        validate_api_keys("openai")


@pytest.mark.parametrize("value", ["", "  ", "900"])
def test_valid_or_blank_flex_timeout_passes_validation(monkeypatch, value):
    from analysis_core.core.orchestration import validate_api_keys

    monkeypatch.setenv("OPENAI_API_KEY", "k")
    monkeypatch.setenv("OPENAI_FLEX_TIMEOUT_SECONDS", value)
    validate_api_keys("openai")


def test_summarize_validation_error_omits_response_text():
    from pydantic import BaseModel

    class Label(BaseModel):
        label: str

    with pytest.raises(Exception) as error:
        Label.model_validate({"label": ["private opinion text"]})
    summary = summarize_exception(error.value)
    assert summary.startswith("ValidationError: label:")
    assert "private opinion text" not in summary


def test_openai_auth_error_log_is_redacted(monkeypatch, caplog):
    import httpx
    import openai

    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    error = openai.AuthenticationError(
        f"Error code: 401 - Incorrect API key provided: {FAKE_OPENAI_KEY}",
        response=httpx.Response(401, request=request),
        body=None,
    )
    client = MagicMock()
    client.chat.completions.create.side_effect = error
    monkeypatch.setenv("OPENAI_USE_FLEX", "0")
    with caplog.at_level(logging.ERROR), patch.object(llm, "OpenAI", return_value=client):
        with pytest.raises(openai.AuthenticationError):
            llm.request_to_openai([{"role": "user", "content": "hi"}], model="gpt-4o-mini", user_api_key="k")
    assert "Incorrect API key provided" in caplog.text
    assert "AbCdEfGh" not in caplog.text


# --- status のエラー文・スタックトレースの伏せ字 ---------------------------------

USER_KEY_MARKER = "ukey-MARKER-7f3a9c51"
SERVER_KEY_MARKER = "srv-MARKER-c0ffee42"


def _status_config(tmp_path):
    report = tmp_path / "outputs" / "report"
    report.mkdir(parents=True)
    return report, {
        "output_dir": "report",
        "provider": "openai",
        "_output_base_dir": str(tmp_path / "outputs"),
        "user_api_key": USER_KEY_MARKER,
    }


def _raise_sdk_like_error():
    # プロバイダ SDK の認証エラーは、受け取ったキー（の一部）をメッセージに含めることがある
    raise RuntimeError(
        f"Error code: 401 - Incorrect API key provided: {USER_KEY_MARKER}. "
        f"server key {SERVER_KEY_MARKER}, masked sk-proj-abcd************************wxyz"
    )


def test_termination_redacts_keys_in_error_and_stack_trace(tmp_path, monkeypatch):
    from analysis_core.core.orchestration import termination

    monkeypatch.setenv("OPENAI_API_KEY", SERVER_KEY_MARKER)
    report, config = _status_config(tmp_path)

    with pytest.raises(RuntimeError):
        try:
            _raise_sdk_like_error()
        except RuntimeError as error:
            termination(config, error)

    text = (report / "hierarchical_status.json").read_text(encoding="utf-8")
    status = json.loads(text)
    assert USER_KEY_MARKER not in text
    assert SERVER_KEY_MARKER not in text
    assert "sk-proj-abcd" not in text
    assert "user_api_key" not in status
    assert status["status"] == "error"
    assert status["error"].startswith("RuntimeError: Error code: 401")
    assert "[REDACTED]" in status["error"]
    assert "[REDACTED]" in status["error_stack_trace"]
    assert "_raise_sdk_like_error" in status["error_stack_trace"]
    # 呼び出し元の config（実行中に使う値）にも伏せ字済みの文面だけが残る
    assert USER_KEY_MARKER not in config["error"]
    assert USER_KEY_MARKER not in config["error_stack_trace"]


def test_update_status_redacts_user_api_key_from_env(tmp_path, monkeypatch):
    """PipelineOrchestrator の失敗時（update_status に直接エラーを渡す経路）も伏せ字にする。"""
    import traceback

    from analysis_core.core.orchestration import update_status

    monkeypatch.setenv("USER_API_KEY", USER_KEY_MARKER)
    report, config = _status_config(tmp_path)
    del config["user_api_key"]

    try:
        _raise_sdk_like_error()
    except RuntimeError as error:
        update_status(
            config,
            {"status": "error", "error": str(error), "error_stack_trace": traceback.format_exc()},
        )

    text = (report / "hierarchical_status.json").read_text(encoding="utf-8")
    assert USER_KEY_MARKER not in text
    assert "sk-proj-abcd" not in text
    assert json.loads(text)["error"].startswith("Error code: 401")


def test_update_status_leaves_non_error_fields_untouched(tmp_path):
    from analysis_core.core.orchestration import update_status

    report, config = _status_config(tmp_path)
    long_slug = "a" * 40  # 伏せ字のパターン（32 文字以上のトークン）に当たる値でも、エラー以外は変えない
    update_status(config, {"status": "running", "current_job": long_slug})

    status = json.loads((report / "hierarchical_status.json").read_text(encoding="utf-8"))
    assert status["current_job"] == long_slug


def test_workflow_step_error_is_redacted_in_output_and_status(tmp_path, monkeypatch, capsys):
    """API が使う workflow 経路でも、ステップの例外メッセージは伏せ字にしてから出力・status に書く。

    出力（analysis.log）は API が error_log_excerpt として status に写すので、ここも塞ぐ。
    """
    from analysis_core.orchestrator import PipelineOrchestrator

    # analysis_core.steps は同名の関数 extraction を再エクスポートするので、モジュールは sys.modules から取る
    extraction_module = importlib.import_module("analysis_core.steps.extraction")

    monkeypatch.setenv("USER_API_KEY", USER_KEY_MARKER)
    monkeypatch.setenv("OPENAI_API_KEY", SERVER_KEY_MARKER)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    (inputs / "input.csv").write_text("comment-id,comment-body\nc1,good\n")
    report = tmp_path / "outputs" / "report"
    report.mkdir(parents=True)
    config = {
        "input": "input",
        "output_dir": "report",
        "provider": "openai",
        "_input_base_dir": str(inputs),
        "_output_base_dir": str(tmp_path / "outputs"),
        "extraction": {"model": "m", "prompt": "p", "workers": 1, "limit": 1, "properties": []},
        "plan": [{"step": "extraction", "run": True}],
    }
    monkeypatch.setattr(extraction_module, "extraction", lambda *args, **kwargs: _raise_sdk_like_error())

    result = PipelineOrchestrator(config).run_default()

    assert not result.success
    output = capsys.readouterr()
    text = (report / "hierarchical_status.json").read_text(encoding="utf-8")
    for written in (output.out, output.err, text, result.error):
        assert USER_KEY_MARKER not in written
        assert SERVER_KEY_MARKER not in written
        assert "sk-proj-abcd" not in written
    assert "Error code: 401" in json.loads(text)["error"]
