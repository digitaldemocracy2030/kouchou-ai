from enum import StrEnum

from pydantic import BaseModel

from src.schemas.report import ReportStatus, ReportVisibility

REPORT_READER_PATH = "/admin/v1/reports"


class ReportStep(StrEnum):
    EXTRACTION = "extraction"
    CLASSIFICATION = "opinion_classification"
    STANCE = "opinion_stance"
    EMBEDDING = "embedding"
    NOVELTY = "opinion_novelty"
    CLUSTERING = "hierarchical_clustering"
    LLM_GROUPING = "llm_grouping"
    INITIAL_LABELLING = "hierarchical_initial_labelling"
    MERGE_LABELLING = "hierarchical_merge_labelling"
    OVERVIEW = "hierarchical_overview"
    AGGREGATION = "hierarchical_aggregation"
    VISUALIZATION = "hierarchical_visualization"


class ReportSummary(BaseModel):
    slug: str
    title: str
    created_at: str | None
    status: ReportStatus
    visibility: ReportVisibility


class ReportList(BaseModel):
    reports: list[ReportSummary]


class ReportProgress(BaseModel):
    slug: str
    status: ReportStatus
    current_step: ReportStep | None
    estimated_cost_usd: float | None
