"""レポート本文の翻訳ステップと CLI（LLM は偽物で置き換える）。"""

import json

import pytest

from analysis_core import translate as translate_cli
from analysis_core.steps.hierarchical_translation import (
    TRANSLATION_SCHEMA,
    TranslationError,
    assemble_translation,
    build_translation_items,
    merge_translations,
    parse_translation_response,
    translate_items,
    translate_result,
)


def sample_result():
    return {
        "arguments": [
            {"arg_id": "A1", "argument": "バスを増やしてほしい", "cluster_ids": ["0", "1"]},
            {"arg_id": "A2", "argument": "駐輪場が欲しい", "cluster_ids": ["0", "2"]},
        ],
        "clusters": [
            {"level": 0, "id": "0", "label": "全体", "takeaway": "", "value": 2, "parent": ""},
            {"level": 1, "id": "1", "label": "交通", "takeaway": "交通の説明", "value": 1, "parent": "0"},
            {"level": 1, "id": "2", "label": "自転車", "takeaway": "自転車の説明", "value": 1, "parent": "0"},
        ],
        "comments": {},
        "propertyMap": {},
        "translations": {"ko": {"overview": "기존 번역"}},
        "overview": "全体の概要",
        "config": {"question": "まちの課題は？", "intro": "イントロ", "provider": "openai", "model": "m"},
        "comment_num": 2,
    }


def fake_request(language_marker="EN"):
    """入力の texts に印を付けて返す偽 LLM。呼び出し内容も記録する。"""
    calls = []
    prompts = []

    def request(messages, json_schema):
        assert json_schema is TRANSLATION_SCHEMA
        assert messages[0]["role"] == "system"
        prompts.append(messages[0]["content"])
        payload = json.loads(messages[1]["content"])
        calls.append(payload)
        return json.dumps(
            {
                "items": [
                    {"id": item["id"], "texts": [f"{language_marker}:{t}" if t else "" for t in item["texts"]]}
                    for item in payload["items"]
                ]
            },
            ensure_ascii=False,
        )

    request.calls = calls
    request.prompts = prompts
    return request


def test_build_translation_items_skips_empty_and_arguments_by_default():
    items = build_translation_items(sample_result())
    assert [i["id"] for i in items] == ["cluster:0", "cluster:1", "cluster:2", "overview", "question", "intro"]
    assert items[0]["texts"] == ["全体", ""]
    assert items[3] == {"id": "overview", "kind": "overview", "texts": ["全体の概要"]}
    with_args = build_translation_items(sample_result(), include_arguments=True)
    assert [i["id"] for i in with_args][-2:] == ["argument:A1", "argument:A2"]


def test_parse_translation_response_accepts_dict_list_and_think_tags():
    text = '<think>考え中</think>\n前置き {"items": [{"id": "a", "texts": ["x"]}, {"id": 1}, {"id": "b", "texts": "y"}]} 後書き'
    assert parse_translation_response(text) == {"a": ["x"], "b": ["y"]}
    assert parse_translation_response({"items": [{"id": "a", "texts": ["x"]}]}) == {"a": ["x"]}
    assert parse_translation_response([{"id": "a", "texts": ["x"]}]) == {"a": ["x"]}
    with pytest.raises(ValueError):
        parse_translation_response("not json at all")
    with pytest.raises(ValueError):
        parse_translation_response({"foo": "bar"})


def test_translate_items_batches_and_keeps_empty_texts_empty():
    request = fake_request()
    items = build_translation_items(sample_result())
    translated = translate_items(items, "en", request, batch_size=4, workers=2)
    assert len(request.calls) == 2
    assert [len(call["items"]) for call in request.calls] == [4, 2]
    assert translated["cluster:1"] == ["EN:交通", "EN:交通の説明"]
    assert translated["cluster:0"] == ["EN:全体", ""]
    # 言語名はシステムプロンプト側にあり、ペイロードには id / kind / texts だけを入れる
    assert "英語" in request.prompts[0]
    assert set(request.calls[0]["items"][0]) == {"id", "kind", "texts"}


def test_translate_items_retries_missing_items_one_by_one():
    attempts = []

    def request(messages, json_schema):
        payload = json.loads(messages[1]["content"])
        attempts.append([i["id"] for i in payload["items"]])
        items = payload["items"]
        # 1回目のバッチでは cluster:2 を落とし、overview の要素数を間違える
        if len(items) > 1:
            out = []
            for item in items:
                if item["id"] == "cluster:2":
                    continue
                texts = ["a", "b"] if item["id"] == "overview" else [f"T:{t}" if t else "" for t in item["texts"]]
                out.append({"id": item["id"], "texts": texts})
            return json.dumps({"items": out})
        return json.dumps(
            {"items": [{"id": i["id"], "texts": [f"R:{t}" if t else "" for t in i["texts"]]} for i in items]}
        )

    items = build_translation_items(sample_result())
    translated = translate_items(items, "en", request, batch_size=10, workers=1)
    assert translated["cluster:1"] == ["T:交通", "T:交通の説明"]
    assert translated["cluster:2"] == ["R:自転車", "R:自転車の説明"]
    assert translated["overview"] == ["R:全体の概要"]
    assert attempts[0] == [i["id"] for i in items]
    assert sorted(a[0] for a in attempts[1:]) == ["cluster:2", "overview"]


@pytest.mark.parametrize(
    "response,kind",
    [
        (RuntimeError("private API failure"), "RuntimeError"),
        (TimeoutError("private timeout"), "timeout"),
        ("broken JSON", "invalid_response"),
        ('{"items": []}', "missing"),
        ('{"items": [{"id": "cluster:1", "texts": [" ", "x"]}]}', "invalid_response"),
    ],
)
def test_translate_items_reports_failures_without_source_text(response, kind):
    def request(messages, json_schema):
        if isinstance(response, Exception):
            raise response
        return response

    items = [{"id": "cluster:1", "kind": "cluster", "texts": ["交通", "private 説明"]}]
    with pytest.raises(TranslationError) as error:
        translate_items(items, "en", request, batch_size=5, workers=1)
    assert error.value.failures == {"cluster:1": kind}
    assert "1件" in str(error.value)
    assert "private" not in str(error.value)
    assert "交通" not in str(error.value)


def test_assemble_translation_builds_viewer_shape():
    items = build_translation_items(sample_result(), include_arguments=True)
    translated = {
        "cluster:0": ["All", ""],
        "cluster:1": ["Transport", "About transport"],
        "overview": ["Overview"],
        "question": ["Question"],
        "argument:A1": ["More buses"],
    }
    assert assemble_translation(items, translated) == {
        "clusters": {"0": {"label": "All", "takeaway": ""}, "1": {"label": "Transport", "takeaway": "About transport"}},
        "overview": "Overview",
        "question": "Question",
        "arguments": {"A1": "More buses"},
    }


def test_translate_result_and_merge_keep_existing_languages():
    result = sample_result()
    translations = translate_result(result, ["en"], fake_request(), meta={"model": "m"})
    assert set(translations) == {"en"}
    en = translations["en"]
    assert en["clusters"]["1"] == {"label": "EN:交通", "takeaway": "EN:交通の説明"}
    assert en["overview"] == "EN:全体の概要"
    assert en["question"] == "EN:まちの課題は？"
    assert en["intro"] == "EN:イントロ"
    assert "arguments" not in en
    assert en["meta"]["model"] == "m"
    assert en["meta"]["include_arguments"] is False
    assert "generated_at" in en["meta"]

    merged = merge_translations(result, translations)
    assert merged["translations"]["ko"] == {"overview": "기존 번역"}
    assert merged["translations"]["en"] is en
    assert result["translations"] == {"ko": {"overview": "기존 번역"}}  # 元は変更しない
    assert merged["clusters"] == result["clusters"]


def test_cli_writes_output_without_touching_input(tmp_path, capsys):
    source = tmp_path / "hierarchical_result.json"
    source.write_text(json.dumps(sample_result(), ensure_ascii=False), encoding="utf-8")
    before = source.read_text(encoding="utf-8")
    output = tmp_path / "out" / "translated.json"

    code = translate_cli.main(
        ["--result", str(source), "--languages", "en, ko", "--output", str(output), "--batch-size", "3"],
        request=fake_request("X"),
    )
    assert code == 0
    assert source.read_text(encoding="utf-8") == before
    written = json.loads(output.read_text(encoding="utf-8"))
    assert set(written["translations"]) == {"en", "ko"}
    assert written["translations"]["en"]["clusters"]["2"]["label"] == "X:自転車"
    assert written["translations"]["ko"]["clusters"]["2"]["label"] == "X:自転車"
    assert written["translations"]["en"]["meta"]["provider"] == "openai"
    out = capsys.readouterr().out
    assert "clusters=3" in out
    assert "Wrote translations for en, ko" in out


def test_cli_dry_run_and_errors(tmp_path, capsys):
    source = tmp_path / "hierarchical_result.json"
    source.write_text(json.dumps(sample_result(), ensure_ascii=False), encoding="utf-8")

    def never(messages, json_schema):
        pytest.fail("dry-run must not call the LLM")

    assert translate_cli.main(["--result", str(source), "--languages", "en", "--dry-run"], request=never) == 0
    assert "clusters=3, texts=3, arguments=0" in capsys.readouterr().out
    assert translate_cli.main(["--result", str(tmp_path / "missing.json"), "--languages", "en"], request=never) == 1
    assert translate_cli.main(["--result", str(source), "--languages", " , "], request=never) == 1

    def failing(messages, json_schema):
        raise RuntimeError("private API failure")

    assert translate_cli.main(["--result", str(source), "--languages", "en"], request=failing) == 1
    err = capsys.readouterr().err
    assert "翻訳に失敗" in err
    assert "private" not in err
    # 失敗時は入力を書き換えない
    assert json.loads(source.read_text(encoding="utf-8"))["translations"] == {"ko": {"overview": "기존 번역"}}


def test_make_llm_request_passes_schema_and_records_usage(monkeypatch):
    from analysis_core.steps import hierarchical_translation as module

    seen = {}

    def fake_request_to_chat_ai(**kwargs):
        seen.update(kwargs)
        return '{"items": []}', 2, 1, 3

    monkeypatch.setattr("analysis_core.services.llm.request_to_chat_ai", fake_request_to_chat_ai)
    usage = {}
    request = module.make_llm_request(provider="local", model="m", local_llm_address="host:1234", usage=usage)
    assert request([{"role": "user", "content": "x"}], TRANSLATION_SCHEMA) == '{"items": []}'
    assert seen["provider"] == "local"
    assert seen["model"] == "m"
    assert seen["local_llm_address"] == "host:1234"
    assert seen["json_schema"] is TRANSLATION_SCHEMA
    assert usage == {"total_token_usage": 3, "token_usage_input": 2, "token_usage_output": 1}
