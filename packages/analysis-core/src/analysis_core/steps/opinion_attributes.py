"""Check that generated opinion attributes cannot overwrite input CSV attributes."""

from collections.abc import Collection, Mapping
from typing import Any

from analysis_core.steps.opinion_labels import resolve_label_spec

OPINION_SCORE_ATTRIBUTES = {"opinion_stance": "stance_score", "opinion_novelty": "novelty_score"}


def configured_opinion_attributes(config: dict[str, Any]) -> dict[str, str]:
    """Return the attribute names and their source steps for enabled opinion steps."""
    attributes = {
        attribute: step
        for step, attribute in OPINION_SCORE_ATTRIBUTES.items()
        if config.get(step, {}).get("enabled", False)
    }
    classification = config.get("opinion_classification", {})
    if classification.get("enabled", False):
        label_ids, _ = resolve_label_spec(classification.get("labels"))
        attributes.update(dict.fromkeys(label_ids, "opinion_classification"))
    return attributes


def validate_input_attribute_collisions(
    input_columns: Collection[str], generated_attributes: Mapping[str, str]
) -> None:
    """Reject any input CSV columns that would use a generated attribute key."""
    collisions = []
    for attribute, step in sorted(generated_attributes.items()):
        column = f"attribute_{attribute}"
        if column in input_columns:
            collisions.append(f"{column!r} ({step})")
    if collisions:
        raise RuntimeError(
            f"Input CSV attribute columns conflict with enabled opinion steps: {', '.join(collisions)}. "
            "Rename the conflicting input columns, change the classification label IDs, "
            "or disable the corresponding opinion steps."
        )
