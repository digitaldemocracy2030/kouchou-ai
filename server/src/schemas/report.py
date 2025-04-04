from enum import Enum

from src.schemas.base import SchemaBaseModel


class ReportStatus(Enum):
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"


class Report(SchemaBaseModel):
    slug: str
    title: str
    description: str
    status: ReportStatus
    is_pubcom: bool = False
