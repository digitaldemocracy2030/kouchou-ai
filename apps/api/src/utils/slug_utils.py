import re

from fastapi import HTTPException

# Slug validation pattern: alphanumeric, underscore, hyphen only
SLUG_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def validate_slug(slug: str) -> None:
    """Validate slug to prevent path traversal attacks.

    Args:
        slug: The slug to validate

    Raises:
        HTTPException: If slug contains invalid characters or path traversal attempts
    """
    if not slug or not SLUG_PATTERN.match(slug):
        raise HTTPException(status_code=400, detail="Invalid slug format")
