"""provider=local の構造化出力（strict な json_schema）のテスト

社内の OpenAI 互換ゲートウェイ（URL 形式のアドレス）は、OpenAI 本体や Azure OpenAI の
strict 構造化出力へそのまま中継することがある。strict:true では、すべての object に
additionalProperties:false が要り、properties のキーはすべて required に入っていなければならない。
ここでは OpenAI の公開仕様どおりに strict を検査する偽ゲートウェイを httpx.MockTransport で立て、
パイプラインで使う 7 つのスキーマを実 SDK（OpenAI クライアント）経由で送って確かめる。
外部には接続しない。
"""

import json

try:  # openai 2.x までは httpx を使う
    import httpx
except ModuleNotFoundError:  # 新しめの openai は httpx2 を同梱する
    import httpx2 as httpx

import pytest
from openai import OpenAI
from pydantic import BaseModel

from analysis_core.services import llm
from analysis_core.steps.extraction import ExtractionResponse
from analysis_core.steps.hierarchical_initial_labelling import LabellingFromat as InitialLabellingFormat
from analysis_core.steps.hierarchical_merge_labelling import LabellingFromat as MergeLabellingFormat
from analysis_core.steps.hierarchical_overview import OverviewResponse
from analysis_core.steps.llm_grouping import GroupAssignmentResponse, GroupDiscoveryResponse
from analysis_core.steps.opinion_classification import build_response_model

PIPELINE_SCHEMAS = [
    pytest.param(ExtractionResponse, id="extraction"),
    pytest.param(InitialLabellingFormat, id="initial_labelling"),
    pytest.param(MergeLabellingFormat, id="merge_labelling"),
    pytest.param(OverviewResponse, id="overview"),
    pytest.param(GroupDiscoveryResponse, id="group_discovery"),
    pytest.param(GroupAssignmentResponse, id="group_assignment"),
    pytest.param(build_response_model(("A", "B")), id="opinion_classification"),
]


def strict_violations(schema: dict, path: str = "$") -> list[str]:
    """OpenAI の strict 構造化出力の規則に反する箇所を列挙する（偽ゲートウェイの検査）"""
    violations: list[str] = []
    if isinstance(schema, dict):
        if schema.get("type") == "object" or "properties" in schema:
            if schema.get("additionalProperties") is not False:
                violations.append(f"{path}: additionalProperties is required to be supplied and to be false")
            properties = schema.get("properties") or {}
            missing = set(properties) - set(schema.get("required") or [])
            if missing:
                violations.append(f"{path}: required is missing {sorted(missing)}")
        for key, value in schema.items():
            if isinstance(value, dict):
                if key in ("properties", "$defs", "definitions"):
                    for name, child in value.items():
                        violations += strict_violations(child, f"{path}.{key}.{name}")
                else:
                    violations += strict_violations(value, f"{path}.{key}")
            elif isinstance(value, list):
                for i, child in enumerate(value):
                    violations += strict_violations(child, f"{path}.{key}[{i}]")
    return violations


@pytest.fixture
def gateway(monkeypatch):
    """strict を検査して 400 を返す偽の OpenAI 互換ゲートウェイ"""
    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        response_format = body.get("response_format") or {}
        if response_format.get("type") == "json_schema" and response_format["json_schema"].get("strict"):
            violations = strict_violations(response_format["json_schema"]["schema"])
            if violations:
                name = response_format["json_schema"].get("name")
                return httpx.Response(
                    400,
                    json={
                        "error": {
                            "message": f"Invalid schema for response_format '{name}': {violations[0]}",
                            "type": "invalid_request_error",
                            "param": "response_format",
                            "code": None,
                        }
                    },
                )
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": body.get("model"),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "{}"},
                        "finish_reason": "stop",
                        "logprobs": None,
                    }
                ],
                "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
            },
        )

    transport = httpx.MockTransport(handler)

    def make_client(**kwargs):
        return OpenAI(**kwargs, http_client=httpx.Client(transport=transport), max_retries=0)

    monkeypatch.setattr(llm, "OpenAI", make_client)
    return sent


MESSAGES = [{"role": "user", "content": "hello"}]
GATEWAY = "https://llm-gateway.example.invalid/"


def test_validator_accepts_openai_sdk_conversion():
    """偽ゲートウェイの検査が、OpenAI SDK の parse と同じ変換を通すこと（検査自体の妥当性）"""
    # SDK の private API なので、場所が変わったら検査の確認だけを飛ばす
    parsing = pytest.importorskip("openai.lib._parsing._completions")
    type_to_response_format_param = parsing.type_to_response_format_param
    for param in PIPELINE_SCHEMAS:
        model = param.values[0]
        converted = type_to_response_format_param(model)
        assert strict_violations(converted["json_schema"]["schema"]) == [], param.id


@pytest.mark.parametrize("schema", PIPELINE_SCHEMAS)
def test_local_strict_json_schema_is_accepted_by_strict_gateway(gateway, schema):
    """パイプラインの全スキーマが、strict を検査するゲートウェイで 400 にならない"""
    content, *_ = llm.request_to_local_llm(MESSAGES, "gpt-4o-mini", json_schema=schema, address=GATEWAY)

    assert content == "{}"
    response_format = gateway[0]["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    assert response_format["json_schema"]["name"] == schema.__name__
    assert strict_violations(response_format["json_schema"]["schema"]) == []


def test_local_strict_schema_covers_nested_defs(gateway):
    """$defs 内の object（ProposedGroup・GroupAssignment）にも additionalProperties:false が付く"""
    llm.request_to_local_llm(MESSAGES, "m", json_schema=GroupDiscoveryResponse, address=GATEWAY)
    llm.request_to_local_llm(MESSAGES, "m", json_schema=GroupAssignmentResponse, address=GATEWAY)

    discovery = gateway[0]["response_format"]["json_schema"]["schema"]
    assignment = gateway[1]["response_format"]["json_schema"]["schema"]
    assert discovery["$defs"]["ProposedGroup"]["additionalProperties"] is False
    assert assignment["$defs"]["GroupAssignment"]["additionalProperties"] is False


def test_local_strict_schema_requires_fields_with_defaults(gateway):
    """既定値つきのフィールドも required に入れる（strict は全 property が required であることを求める）"""

    class WithDefault(BaseModel):
        name: str
        note: str = ""

    llm.request_to_local_llm(MESSAGES, "m", json_schema=WithDefault, address=GATEWAY)

    schema = gateway[0]["response_format"]["json_schema"]["schema"]
    assert sorted(schema["required"]) == ["name", "note"]
    assert strict_violations(schema) == []


def test_local_strict_schema_does_not_mutate_pydantic_schema(gateway):
    """変換はコピーに対して行い、pydantic が返すスキーマ（キャッシュされうる）を書き換えない"""
    before = json.dumps(GroupDiscoveryResponse.model_json_schema(), sort_keys=True)
    llm.request_to_local_llm(MESSAGES, "m", json_schema=GroupDiscoveryResponse, address=GATEWAY)
    assert json.dumps(GroupDiscoveryResponse.model_json_schema(), sort_keys=True) == before


def test_local_plain_and_json_object_requests_are_unchanged(gateway):
    """スキーマなし・json_object の要求は従来どおり（接続確認と同じ形）"""
    llm.request_to_local_llm(MESSAGES, "m", address=GATEWAY)
    llm.request_to_local_llm(MESSAGES, "m", is_json=True, address=GATEWAY)

    assert "response_format" not in gateway[0]
    assert gateway[1]["response_format"] == {"type": "json_object"}
