from src.schemas.base import SchemaBaseModel


class PublicReportConfig(SchemaBaseModel):
    question: str


class PublicReportResult(SchemaBaseModel):
    overview: str
    clusters: list
    arguments: list
    config: PublicReportConfig
