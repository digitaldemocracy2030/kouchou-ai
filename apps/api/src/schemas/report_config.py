from src.schemas.base import SchemaBaseModel


class ExtractionConfig(SchemaBaseModel):
    prompt: str
    workers: int | None = None
    limit: int | None = None


class HierarchicalClusteringConfig(SchemaBaseModel):
    cluster_nums: list[int]


class HierarchicalInitialLabellingConfig(SchemaBaseModel):
    prompt: str
    sampling_num: int | None = None
    workers: int | None = None


class HierarchicalMergeLabellingConfig(SchemaBaseModel):
    prompt: str
    sampling_num: int | None = None
    workers: int | None = None


class HierarchicalOverviewConfig(SchemaBaseModel):
    prompt: str


class HierarchicalAggregationConfig(SchemaBaseModel):
    sampling_num: int | None = None


class ReportConfig(SchemaBaseModel):
    name: str
    input: str
    question: str
    intro: str
    model: str
    provider: str | None = None
    is_pubcom: bool | None = None
    is_embedded_at_local: bool | None = None
    local_llm_address: str | None = None
    extraction: ExtractionConfig
    hierarchical_clustering: HierarchicalClusteringConfig
    hierarchical_initial_labelling: HierarchicalInitialLabellingConfig
    hierarchical_merge_labelling: HierarchicalMergeLabellingConfig
    hierarchical_overview: HierarchicalOverviewConfig
    hierarchical_aggregation: HierarchicalAggregationConfig


class ReportConfigUpdate(SchemaBaseModel):
    """レポートのメタデータ更新用スキーマ"""

    question: str | None = None  # レポートのタイトル
    intro: str | None = None  # レポートの調査概要
