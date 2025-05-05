from src.schemas.base import SchemaBaseModel


class Metadata(SchemaBaseModel):
    reporter: str | None = None
    message: str | None = None
    webLink: str | None = None
    privacyLink: str | None = None
    termsLink: str | None = None
    brandColor: str | None = None
