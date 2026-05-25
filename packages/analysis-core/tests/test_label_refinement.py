import csv
import importlib

from analysis_core.plugin import StepContext, StepInputs
from analysis_core.plugins.builtin.hierarchical_label_refinement import (
    hierarchical_label_refinement_plugin,
)
from analysis_core.steps.hierarchical_label_refinement import build_refinement_prompt


def _write_merge_labels(path):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["level", "id", "label", "description", "value", "parent"])
        writer.writerow([1, "1_1", "現状ラベルA", "現状説明A", 50, "0"])
        writer.writerow([1, "1_2", "現状ラベルB", "現状説明B", 40, "0"])
        writer.writerow([2, "2_1", "子ラベルA1", "子説明A1", 20, "1_1"])
        writer.writerow([2, "2_2", "子ラベルA2", "子説明A2", 30, "1_1"])
        writer.writerow([2, "2_3", "子ラベルB1", "子説明B1", 18, "1_2"])


def test_build_refinement_prompt_adds_short_constraint():
    prompt = build_refinement_prompt("setwise_refine_short", 18)
    assert "18 文字以内" in prompt
    assert "scan しやすい" in prompt


def test_label_refinement_none_mode_writes_refined_copy(tmp_path):
    output_dir = tmp_path / "out" / "demo"
    input_dir = tmp_path / "in"
    output_dir.mkdir(parents=True)
    input_dir.mkdir()
    labels_path = output_dir / "hierarchical_merge_labels.csv"
    _write_merge_labels(labels_path)

    ctx = StepContext(output_dir=output_dir, input_dir=input_dir, dataset="demo", provider="local", model="dummy")
    outputs = hierarchical_label_refinement_plugin.run(
        ctx,
        StepInputs(artifacts={"merge_labels": labels_path}, config={}),
        {
            "hierarchical_label_refinement": {
                "mode": "none",
                "prompt": "",
                "model": "dummy",
                "max_label_length": 24,
            }
        },
    )

    assert outputs.artifacts["merge_labels"] == labels_path
    refined_path = output_dir / "hierarchical_refined_labels.csv"
    assert refined_path.exists()
    assert labels_path.read_text(encoding="utf-8") == refined_path.read_text(encoding="utf-8")


def test_label_refinement_rewrites_level1_labels(tmp_path, monkeypatch):
    output_dir = tmp_path / "out" / "demo"
    input_dir = tmp_path / "in"
    output_dir.mkdir(parents=True)
    input_dir.mkdir()
    labels_path = output_dir / "hierarchical_merge_labels.csv"
    _write_merge_labels(labels_path)

    seen = {}

    def fake_request_to_chat_ai(*, messages, model, json_schema, provider, local_llm_address, user_api_key):
        seen["messages"] = messages
        seen["model"] = model
        return (
            {
                "clusters": [
                    {
                        "cluster_id": "1_1",
                        "label": "短い上位ラベルA",
                        "description": "A側の代表性を保ちながら差分を明確化した説明。",
                    },
                    {
                        "cluster_id": "1_2",
                        "label": "短い上位ラベルB",
                        "description": "B側の代表性を保ちながら差分を明確化した説明。",
                    },
                ]
            },
            10,
            5,
            15,
        )

    module = importlib.import_module("analysis_core.steps.hierarchical_label_refinement")
    monkeypatch.setattr(module, "request_to_chat_ai", fake_request_to_chat_ai)

    ctx = StepContext(output_dir=output_dir, input_dir=input_dir, dataset="demo", provider="openai", model="gpt-4o-mini")
    outputs = hierarchical_label_refinement_plugin.run(
        ctx,
        StepInputs(artifacts={"merge_labels": labels_path}, config={}),
        {
            "hierarchical_label_refinement": {
                "mode": "setwise_refine_short",
                "prompt": build_refinement_prompt("setwise_refine_short", 18),
                "model": "gpt-4o-mini",
                "max_label_length": 18,
            }
        },
    )

    content = labels_path.read_text(encoding="utf-8")
    assert "短い上位ラベルA" in content
    assert "短い上位ラベルB" in content
    assert "子ラベルA1" in content
    assert (output_dir / "hierarchical_merge_labels.original.csv").exists()
    assert outputs.token_usage == 15
    assert outputs.token_input == 10
    assert outputs.token_output == 5
    assert "cluster_id: 1_1" in seen["messages"][1]["content"]
