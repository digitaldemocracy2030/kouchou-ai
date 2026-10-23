"""LLM 直接グルーピングの割当に、管理画面の並列数（workers）が届くことの回帰テスト（b007）。

作成（report_launcher._build_config）・複製（report_duplicate._apply_overrides）・
埋め込み config からの復元（_build_analysis_core_config_from_embedded_config）の
どの経路でも、llm_grouping セクションに workers が入り、analysis-core の config 検証を通ること。
"""

import pytest

from src.schemas.admin_report import Comment, Prompt, ReportDuplicateOverrides, ReportInput
from src.services.analysis_config import prune_config_for_mode

analysis_core = pytest.importorskip("analysis_core")


def _validate_with_analysis_core(config: dict) -> None:
    from analysis_core.core import load_specs
    from analysis_core.core.orchestration import get_specs_path_for_mode, validate_config

    specs = load_specs(get_specs_path_for_mode(config.get("analysis_mode", "hierarchical")))
    validate_config(config, specs)


def _report_input(**overrides) -> ReportInput:
    base = {
        "input": "dummy",
        "question": "q",
        "intro": "i",
        "model": "m",
        "provider": "openai",
        "is_pubcom": False,
        "is_embedded_at_local": False,
        "local_llm_address": None,
        "prompt": Prompt(extraction="ex", initial_labelling="", merge_labelling="", overview="ov"),
        "workers": 8,
        "cluster": [1],
        "enable_source_link": False,
        "comments": [Comment(id="1", comment="hello")],
    }
    base.update(overrides)
    return ReportInput(**base)


def test_build_config_passes_workers_to_llm_grouping_assignment():
    from src.services.report_launcher import _build_config

    config = _build_config(_report_input(analysis_mode="llm_grouping", workers=8))

    assert config["llm_grouping"] == {"workers": 8}
    assert config["extraction"]["workers"] == 8
    _validate_with_analysis_core(config)


def test_build_config_hierarchical_does_not_add_llm_grouping_section():
    from src.services.report_launcher import _build_config

    config = _build_config(_report_input(workers=8))

    assert "llm_grouping" not in config
    _validate_with_analysis_core(config)


@pytest.mark.parametrize(
    "source_section",
    [
        pytest.param(None, id="no-section"),
        pytest.param({"assignment_batch_size": 10, "workers": 2}, id="existing-section"),
    ],
)
def test_duplicate_workers_override_reaches_llm_grouping(source_section):
    from src.services.report_duplicate import _apply_overrides

    config = {
        "input": "copy",
        "question": "q",
        "analysis_mode": "llm_grouping",
        "extraction": {"workers": 2, "prompt": "ex"},
    }
    if source_section is not None:
        config["llm_grouping"] = dict(source_section)

    result = prune_config_for_mode(_apply_overrides(config, ReportDuplicateOverrides(workers=6)))

    assert result["extraction"]["workers"] == 6
    assert result["llm_grouping"]["workers"] == 6
    if source_section is not None:
        assert result["llm_grouping"]["assignment_batch_size"] == 10
    _validate_with_analysis_core(result)


def test_duplicate_workers_override_on_hierarchical_report_adds_no_llm_grouping_section():
    from src.services.report_duplicate import _apply_overrides

    config = {
        "input": "copy",
        "question": "q",
        "analysis_mode": "hierarchical",
        "extraction": {"workers": 2, "prompt": "ex"},
        "hierarchical_clustering": {"cluster_nums": [2, 4]},
    }

    result = _apply_overrides(config, ReportDuplicateOverrides(workers=6))

    assert "llm_grouping" not in result


def test_embedded_llm_grouping_config_keeps_workers():
    from src.services.report_duplicate import _build_analysis_core_config_from_embedded_config

    embedded = {
        "name": "src",
        "input": "src",
        "question": "q",
        "intro": "i",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "analysis_mode": "llm_grouping",
        "extraction": {"prompt": "p", "workers": 4, "limit": 2},
        "hierarchical_overview": {"prompt": "ov"},
        "hierarchical_aggregation": {"sampling_num": 5000},
        "llm_grouping": {
            "group_count": None,
            "discovery_sample_size": 80,
            "assignment_batch_size": 25,
            "discovery_prompt": "d",
            "assignment_prompt": "a",
            "workers": 4,
            "source_code": "def llm_grouping(): ...",
        },
    }

    pruned = prune_config_for_mode(_build_analysis_core_config_from_embedded_config(embedded))

    assert pruned["llm_grouping"]["workers"] == 4
    _validate_with_analysis_core(pruned)
