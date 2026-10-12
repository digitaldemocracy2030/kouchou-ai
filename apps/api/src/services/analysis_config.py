"""Helpers for building analysis-core config payloads that respect analysis_mode.

analysis-core validates the *raw* config (before normalization) against the
specs for the configured ``analysis_mode`` and rejects any config section that
does not belong to that mode's pipeline (``Unknown field '<section>'``).

Several code paths in the API serialize a :class:`ReportConfig` (or an
analysis-core *normalized* embedded config) back into a config dict that is then
handed to ``python -m analysis_core``. Because ``ReportConfig`` now carries both
hierarchical-only and llm_grouping-only sections as known fields,
``model_dump()`` emits the sections that do not belong to the resolved mode
(``llm_grouping`` as ``null`` for hierarchical reports, the hierarchical
labelling/clustering sections as ``null`` for llm_grouping reports, or
value-filled dicts when the source config was already normalized). Writing such
a config back poisons it and makes the next analysis-core run fail.

``prune_config_for_mode`` strips the sections that do not belong to the resolved
mode and normalizes ``analysis_mode`` to a concrete, valid value so that
``get_specs_path_for_mode`` never receives ``None``.

NOTE: analysis-core is invoked as a subprocess and is only an optional import
for the API, so the section mapping is intentionally hardcoded here rather than
derived from ``analysis_core`` specs. ``tests/services/test_analysis_config.py``
cross-checks this mapping against the real analysis-core specs / ``validate_config``.
"""

from typing import Any

VALID_ANALYSIS_MODES = ("hierarchical", "llm_grouping")
DEFAULT_ANALYSIS_MODE = "hierarchical"

# Config sections that only belong to a specific analysis_mode's pipeline.
HIERARCHICAL_ONLY_SECTIONS = (
    "hierarchical_clustering",
    "hierarchical_initial_labelling",
    "hierarchical_merge_labelling",
)
LLM_GROUPING_ONLY_SECTIONS = ("llm_grouping",)
ALL_MODE_SECTIONS = HIERARCHICAL_ONLY_SECTIONS + LLM_GROUPING_ONLY_SECTIONS


def resolve_analysis_mode(config: dict[str, Any]) -> str:
    """Return a concrete, valid analysis_mode for ``config``.

    Missing / ``None`` / unknown values fall back to ``"hierarchical"`` so that
    downstream ``get_specs_path_for_mode`` never receives an invalid value.
    """
    mode = config.get("analysis_mode")
    if mode in VALID_ANALYSIS_MODES:
        return mode
    return DEFAULT_ANALYSIS_MODE


def prune_config_for_mode(config: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of ``config`` safe to hand to analysis-core.

    - ``analysis_mode`` is normalized to a concrete valid value.
    - Config sections that do not belong to the resolved mode are removed
      (regardless of whether they are ``None`` or value-filled dicts), so the
      raw-config validation in analysis-core does not reject them.
    - Sections that *do* belong to the resolved mode but are ``None`` / empty
      are also removed. ``_build_config`` intentionally omits an active-mode
      section to rely on analysis-core defaults, but a later ``model_dump()``
      round-trip (e.g. ``ConfigRepository.update_json``) re-emits it as
      ``<section>: null``. analysis-core's ``validate_config`` then runs
      ``for key in config.get(step, {})`` against a *present-but-``None``*
      section and raises ``TypeError: 'NoneType' object is not iterable``.
      Dropping the empty section restores the "use defaults" behaviour.
    """
    mode = resolve_analysis_mode(config)
    pruned = dict(config)
    pruned["analysis_mode"] = mode

    keep = LLM_GROUPING_ONLY_SECTIONS if mode == "llm_grouping" else HIERARCHICAL_ONLY_SECTIONS
    for section in ALL_MODE_SECTIONS:
        if section not in pruned:
            continue
        value = pruned[section]
        if section not in keep or value is None or value == {}:
            pruned.pop(section, None)

    return pruned
