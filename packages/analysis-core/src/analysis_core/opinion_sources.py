"""Read and write the citation fields of a report argument."""

from collections.abc import Iterable, Mapping
from typing import NotRequired, TypedDict


class CommentReferences(TypedDict):
    comment_id: str
    comment_ids: NotRequired[list[str]]


def read_comment_ids(argument: Mapping[str, object]) -> list[str]:
    """Use the plural field when present. Convert legacy integer IDs without losing precision."""
    if "comment_ids" in argument:
        ids = argument["comment_ids"]
        if not isinstance(ids, list) or any(not isinstance(value, str) or not value for value in ids):
            raise ValueError("comment_ids must contain non-empty strings")
        return list(dict.fromkeys(ids))

    value = argument.get("comment_id")
    if value is None or isinstance(value, str):
        return [value] if value else []
    if type(value) is int:
        return [str(value)]
    if isinstance(value, float) and abs(value) <= 9007199254740991 and value.is_integer():
        return [str(int(value))]
    raise ValueError("legacy comment_id must be a string or an integer")


def comment_source_fields(ids: Iterable[str]) -> CommentReferences:
    """Keep the first source as the representative for single-source readers."""
    sources = list(dict.fromkeys(ids))
    fields: CommentReferences = {"comment_id": sources[0] if sources else ""}
    if len(sources) > 1:
        fields["comment_ids"] = sources
    return fields
