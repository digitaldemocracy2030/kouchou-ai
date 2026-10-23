"""Regression tests for analysis_mode-aware config pruning.

These tests exercise the real ``analysis_core.validate_config`` (the same raw-config
validation that ``python -m analysis_core`` runs) so that config write-back paths
cannot silently emit mode-non-matching sections that would make the subprocess fail.
"""

import json

import pytest

from src.schemas.report_config import ReportConfig
from src.services.analysis_config import (
    HIERARCHICAL_ONLY_SECTIONS,
    LLM_GROUPING_ONLY_SECTIONS,
    prune_config_for_mode,
    resolve_analysis_mode,
)

# analysis-core is invoked as a subprocess and is only an optional import for the API.
analysis_core = pytest.importorskip("analysis_core")


def _validate_with_analysis_core(config: dict) -> None:
    from analysis_core.core import load_specs
    from analysis_core.core.orchestration import get_specs_path_for_mode, validate_config

    mode = config.get("analysis_mode", "hierarchical")
    specs = load_specs(get_specs_path_for_mode(mode))
    validate_config(config, specs)


def _hierarchical_report_config() -> ReportConfig:
    return ReportConfig(
        name="demo",
        input="demo",
        question="q",
        intro="i",
        model="gpt-4o-mini",
        provider="openai",
        analysis_mode="hierarchical",
        extraction={"prompt": "p", "workers": 1, "limit": 2},
        hierarchical_clustering={"cluster_nums": [3, 6]},
        hierarchical_initial_labelling={"prompt": "i", "sampling_num": 30, "workers": 1},
        hierarchical_merge_labelling={"prompt": "m", "sampling_num": 30, "workers": 1},
        hierarchical_overview={"prompt": "ov"},
        hierarchical_aggregation={"sampling_num": 5000},
    )


def _llm_grouping_report_config() -> ReportConfig:
    return ReportConfig(
        name="demo",
        input="demo",
        question="q",
        intro="i",
        model="gpt-4o-mini",
        provider="openai",
        analysis_mode="llm_grouping",
        extraction={"prompt": "p", "workers": 1, "limit": 2},
        hierarchical_overview={"prompt": "ov"},
        hierarchical_aggregation={"sampling_num": 5000},
        llm_grouping={
            "group_count": None,
            "discovery_sample_size": 80,
            "assignment_batch_size": 25,
            "discovery_prompt": "d",
            "assignment_prompt": "a",
        },
    )


# ---------------------------------------------------------------------------
# prune helper unit behavior
# ---------------------------------------------------------------------------


def test_resolve_analysis_mode_falls_back_to_hierarchical():
    assert resolve_analysis_mode({}) == "hierarchical"
    assert resolve_analysis_mode({"analysis_mode": None}) == "hierarchical"
    assert resolve_analysis_mode({"analysis_mode": "bogus"}) == "hierarchical"
    assert resolve_analysis_mode({"analysis_mode": "llm_grouping"}) == "llm_grouping"


def test_prune_hierarchical_drops_value_filled_llm_grouping():
    # Mirrors analysis-core *normalized* embedded config where llm_grouping is a dict.
    config = {
        "analysis_mode": "hierarchical",
        "hierarchical_clustering": {"cluster_nums": [3]},
        "llm_grouping": {"discovery_sample_size": 80, "assignment_batch_size": 25},
    }
    pruned = prune_config_for_mode(config)
    assert "llm_grouping" not in pruned
    assert pruned["hierarchical_clustering"] == {"cluster_nums": [3]}
    assert pruned["analysis_mode"] == "hierarchical"


def test_prune_llm_grouping_drops_none_hierarchical_only_sections():
    # Mirrors ReportConfig.model_dump() where hierarchical-only sections are None.
    config = {
        "analysis_mode": "llm_grouping",
        "hierarchical_clustering": None,
        "hierarchical_initial_labelling": None,
        "hierarchical_merge_labelling": None,
        "llm_grouping": {"discovery_sample_size": 80},
    }
    pruned = prune_config_for_mode(config)
    for key in HIERARCHICAL_ONLY_SECTIONS:
        assert key not in pruned
    assert pruned["llm_grouping"] == {"discovery_sample_size": 80}


def test_prune_llm_grouping_drops_none_or_empty_active_section():
    # Regression for the create->edit->re-aggregate crash: the create flow omits the
    # active-mode ``llm_grouping`` section to rely on analysis-core defaults, but a later
    # ReportConfig.model_dump() round-trip re-emits it as ``llm_grouping: null`` (or {}).
    # prune must drop it, otherwise analysis-core's ``for key in config.get("llm_grouping", {})``
    # iterates ``None`` and raises ``TypeError: 'NoneType' object is not iterable``.
    for empty_value in (None, {}):
        config = {
            "analysis_mode": "llm_grouping",
            "extraction": {"prompt": "p", "workers": 1, "limit": 2},
            "llm_grouping": empty_value,
        }
        pruned = prune_config_for_mode(config)
        assert "llm_grouping" not in pruned, f"null/empty active section leaked for {empty_value!r}"
        assert pruned["analysis_mode"] == "llm_grouping"


def test_prune_hierarchical_drops_none_or_empty_active_sections():
    # Symmetric guard: a hierarchical section that round-trips to null/empty must also be
    # dropped so analysis-core falls back to defaults instead of iterating ``None``.
    config = {
        "analysis_mode": "hierarchical",
        "hierarchical_clustering": None,
        "hierarchical_initial_labelling": {},
        "hierarchical_merge_labelling": {"prompt": "m", "sampling_num": 30, "workers": 1},
    }
    pruned = prune_config_for_mode(config)
    assert "hierarchical_clustering" not in pruned
    assert "hierarchical_initial_labelling" not in pruned
    # value-filled active-mode sections are preserved.
    assert pruned["hierarchical_merge_labelling"] == {"prompt": "m", "sampling_num": 30, "workers": 1}


def test_prune_normalizes_missing_or_null_analysis_mode():
    # Old reports have no analysis_mode key; must never leak None to get_specs_path_for_mode.
    assert prune_config_for_mode({})["analysis_mode"] == "hierarchical"
    assert prune_config_for_mode({"analysis_mode": None})["analysis_mode"] == "hierarchical"


# ---------------------------------------------------------------------------
# section mapping must agree with real analysis-core specs
# ---------------------------------------------------------------------------


def test_section_mapping_matches_analysis_core_specs():
    from analysis_core.core import load_specs
    from analysis_core.core.orchestration import get_specs_path_for_mode

    hierarchical_steps = {s["step"] for s in load_specs(get_specs_path_for_mode("hierarchical"))}
    llm_grouping_steps = {s["step"] for s in load_specs(get_specs_path_for_mode("llm_grouping"))}

    # llm_grouping-only sections must be absent from the hierarchical pipeline.
    for section in LLM_GROUPING_ONLY_SECTIONS:
        assert section not in hierarchical_steps
        assert section in llm_grouping_steps
    # hierarchical-only sections must be absent from the llm_grouping pipeline.
    for section in HIERARCHICAL_ONLY_SECTIONS:
        assert section not in llm_grouping_steps
        assert section in hierarchical_steps


# ---------------------------------------------------------------------------
# ReportConfig round-trip must pass real validate_config after pruning
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("make_config", [_hierarchical_report_config, _llm_grouping_report_config])
def test_reportconfig_roundtrip_validates_after_prune(make_config):
    dumped = make_config().model_dump()

    # Without pruning, model_dump() leaks mode-non-matching sections and analysis-core rejects it.
    with pytest.raises(Exception, match="Unknown field"):
        _validate_with_analysis_core(dumped)

    # After pruning it must validate cleanly.
    _validate_with_analysis_core(prune_config_for_mode(dumped))


# ---------------------------------------------------------------------------
# update_json (metadata edit -> re-aggregation) must not poison config
# ---------------------------------------------------------------------------


def test_update_json_does_not_inject_mode_mismatched_sections(tmp_path, monkeypatch):
    from src.repositories.config_repository import ConfigRepository
    from src.schemas.report_config import ReportConfigUpdate

    monkeypatch.setattr("src.repositories.config_repository.settings.CONFIG_DIR", tmp_path)
    slug = "demo"
    # A clean hierarchical config file as written by the create flow (no llm_grouping key).
    (tmp_path / f"{slug}.json").write_text(
        json.dumps(
            {
                "name": slug,
                "input": slug,
                "question": "old",
                "intro": "i",
                "model": "gpt-4o-mini",
                "provider": "openai",
                "analysis_mode": "hierarchical",
                "extraction": {"prompt": "p", "workers": 1, "limit": 2},
                "hierarchical_clustering": {"cluster_nums": [3, 6]},
                "hierarchical_initial_labelling": {"prompt": "i", "sampling_num": 30, "workers": 1},
                "hierarchical_merge_labelling": {"prompt": "m", "sampling_num": 30, "workers": 1},
                "hierarchical_overview": {"prompt": "ov"},
                "hierarchical_aggregation": {"sampling_num": 5000},
            }
        ),
        encoding="utf-8",
    )

    assert ConfigRepository(slug).update_json(ReportConfigUpdate(question="new title")) is True

    written = json.loads((tmp_path / f"{slug}.json").read_text(encoding="utf-8"))
    assert "llm_grouping" not in written
    assert written["analysis_mode"] == "hierarchical"
    assert written["question"] == "new title"
    _validate_with_analysis_core(written)


def test_update_json_llm_grouping_report_does_not_poison_config(tmp_path, monkeypatch):
    # End-to-end reproduction of the #987 blocker: an llm_grouping report created with the
    # ``llm_grouping`` section omitted (defaults), then edited via the admin config endpoint.
    # update_json round-trips through ReportConfig.model_dump(), which re-emits
    # ``llm_grouping: null``; before the fix prune kept it and the next analysis-core run
    # crashed with ``TypeError: 'NoneType' object is not iterable``.
    from src.repositories.config_repository import ConfigRepository
    from src.schemas.report_config import ReportConfigUpdate

    monkeypatch.setattr("src.repositories.config_repository.settings.CONFIG_DIR", tmp_path)
    slug = "grouping"
    # As written by the create flow for analysis_mode=llm_grouping: no llm_grouping key.
    (tmp_path / f"{slug}.json").write_text(
        json.dumps(
            {
                "name": slug,
                "input": slug,
                "question": "old",
                "intro": "i",
                "model": "gpt-4o-mini",
                "provider": "openai",
                "analysis_mode": "llm_grouping",
                "extraction": {"prompt": "p", "workers": 1, "limit": 2},
                "hierarchical_overview": {"prompt": "ov"},
                "hierarchical_aggregation": {"sampling_num": 5000},
            }
        ),
        encoding="utf-8",
    )

    assert ConfigRepository(slug).update_json(ReportConfigUpdate(question="new title")) is True

    written = json.loads((tmp_path / f"{slug}.json").read_text(encoding="utf-8"))
    assert written["analysis_mode"] == "llm_grouping"
    assert written["question"] == "new title"
    # The active-mode section must be absent, not present-but-null.
    assert "llm_grouping" not in written
    for key in HIERARCHICAL_ONLY_SECTIONS:
        assert key not in written
    # The written config must survive the exact raw-config validation the subprocess runs.
    _validate_with_analysis_core(written)


def test_update_json_normalizes_legacy_config_without_analysis_mode(tmp_path, monkeypatch):
    from src.repositories.config_repository import ConfigRepository
    from src.schemas.report_config import ReportConfigUpdate

    monkeypatch.setattr("src.repositories.config_repository.settings.CONFIG_DIR", tmp_path)
    slug = "legacy"
    # Legacy config predating analysis_mode: no analysis_mode key at all.
    (tmp_path / f"{slug}.json").write_text(
        json.dumps(
            {
                "name": slug,
                "input": slug,
                "question": "old",
                "intro": "i",
                "model": "gpt-4o-mini",
                "provider": "openai",
                "extraction": {"prompt": "p", "workers": 1, "limit": 2},
                "hierarchical_clustering": {"cluster_nums": [3, 6]},
                "hierarchical_initial_labelling": {"prompt": "i", "sampling_num": 30, "workers": 1},
                "hierarchical_merge_labelling": {"prompt": "m", "sampling_num": 30, "workers": 1},
                "hierarchical_overview": {"prompt": "ov"},
                "hierarchical_aggregation": {"sampling_num": 5000},
            }
        ),
        encoding="utf-8",
    )

    assert ConfigRepository(slug).update_json(ReportConfigUpdate(intro="new intro")) is True

    written = json.loads((tmp_path / f"{slug}.json").read_text(encoding="utf-8"))
    # Must never write analysis_mode:null (get_specs_path_for_mode(None) would raise).
    assert written["analysis_mode"] == "hierarchical"
    assert "llm_grouping" not in written
    _validate_with_analysis_core(written)


# ---------------------------------------------------------------------------
# duplicate fallback (embedded normalized config) must not poison config
# ---------------------------------------------------------------------------


def test_duplicate_embedded_fallback_pruned_config_validates():
    from src.services.report_duplicate import _build_analysis_core_config_from_embedded_config

    # analysis-core *normalized* embedded config: hierarchical report, but llm_grouping is a
    # value-filled dict (exclude_none would NOT remove it).
    embedded = {
        "name": "src",
        "input": "src",
        "question": "q",
        "intro": "i",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "analysis_mode": "hierarchical",
        "extraction": {"prompt": "p", "workers": 1, "limit": 2},
        "hierarchical_clustering": {"cluster_nums": [3, 6]},
        "hierarchical_initial_labelling": {"prompt": "i", "sampling_num": 30, "workers": 1},
        "hierarchical_merge_labelling": {"prompt": "m", "sampling_num": 30, "workers": 1},
        "hierarchical_overview": {"prompt": "ov"},
        "hierarchical_aggregation": {"sampling_num": 5000},
        "llm_grouping": {
            "group_count": None,
            "discovery_sample_size": 80,
            "assignment_batch_size": 25,
            "discovery_prompt": "d",
            "assignment_prompt": "a",
        },
    }

    built = _build_analysis_core_config_from_embedded_config(embedded)
    # The fallback itself still carries the value-filled llm_grouping dict (the bug surface).
    assert isinstance(built.get("llm_grouping"), dict)

    # duplicate_report prunes before writing; the pruned config must validate.
    pruned = prune_config_for_mode(built)
    assert "llm_grouping" not in pruned
    _validate_with_analysis_core(pruned)


def test_duplicate_config_does_not_save_umap_model():
    """複製（Web 経路）でも umap_model.pkl を保存させない。llm_grouping には hierarchical_clustering を足さない。"""
    from src.services.report_duplicate import _build_analysis_core_config_from_embedded_config

    base = {
        "name": "src",
        "input": "src",
        "question": "q",
        "intro": "i",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "extraction": {"prompt": "p", "workers": 1, "limit": 2},
        "hierarchical_overview": {"prompt": "ov"},
        "hierarchical_aggregation": {"sampling_num": 5000},
    }
    hierarchical = {
        **base,
        "analysis_mode": "hierarchical",
        "hierarchical_clustering": {"cluster_nums": [3, 6]},
        "hierarchical_initial_labelling": {"prompt": "i", "sampling_num": 30, "workers": 1},
        "hierarchical_merge_labelling": {"prompt": "m", "sampling_num": 30, "workers": 1},
    }
    built = prune_config_for_mode(_build_analysis_core_config_from_embedded_config(hierarchical))
    assert built["hierarchical_clustering"] == {"cluster_nums": [3, 6], "save_umap_model": False}
    _validate_with_analysis_core(built)

    llm_grouping = {**base, "analysis_mode": "llm_grouping"}
    built = prune_config_for_mode(_build_analysis_core_config_from_embedded_config(llm_grouping))
    assert "hierarchical_clustering" not in built


def test_update_json_preserves_keys_not_defined_in_report_config(tmp_path, monkeypatch):
    # タイトル・説明の編集で ReportConfig に定義のないキー（enable_source_link・embedding）が
    # 消えると、再集計で出典リンクや埋め込みモデルの指定が黙って失われる。
    from src.repositories.config_repository import ConfigRepository
    from src.schemas.report_config import ReportConfigUpdate

    monkeypatch.setattr("src.repositories.config_repository.settings.CONFIG_DIR", tmp_path)
    slug = "source-link"
    (tmp_path / f"{slug}.json").write_text(
        json.dumps(
            {
                "name": slug,
                "input": slug,
                "question": "old",
                "intro": "i",
                "model": "gpt-4o-mini",
                "provider": "openai",
                "analysis_mode": "hierarchical",
                "extraction": {"prompt": "p", "workers": 1, "limit": 2},
                "embedding": {"model": "text-embedding-3-large"},
                "hierarchical_clustering": {"cluster_nums": [3, 6]},
                "hierarchical_initial_labelling": {"prompt": "i", "sampling_num": 30, "workers": 1},
                "hierarchical_merge_labelling": {"prompt": "m", "sampling_num": 30, "workers": 1},
                "hierarchical_overview": {"prompt": "ov"},
                "hierarchical_aggregation": {"sampling_num": 5000},
                "enable_source_link": True,
            }
        ),
        encoding="utf-8",
    )

    assert ConfigRepository(slug).update_json(ReportConfigUpdate(question="new title", intro="new intro")) is True

    written = json.loads((tmp_path / f"{slug}.json").read_text(encoding="utf-8"))
    assert written["question"] == "new title"
    assert written["intro"] == "new intro"
    assert written["enable_source_link"] is True
    assert written["embedding"] == {"model": "text-embedding-3-large"}
    _validate_with_analysis_core(written)
