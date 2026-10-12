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


class LLMGroupingConfig(SchemaBaseModel):
    group_count: int | None = None
    discovery_sample_size: int | None = None
    assignment_batch_size: int | None = None
    discovery_prompt: str | None = None
    assignment_prompt: str | None = None


class ReportConfig(SchemaBaseModel):
    name: str | None = None  # CLI実行時は未設定の場合あり、inputから導出可能
    input: str
    question: str
    intro: str
    model: str
    provider: str | None = None
    analysis_mode: str | None = None  # "hierarchical"（既定） or "llm_grouping"
    is_pubcom: bool | None = None
    is_embedded_at_local: bool | None = None
    local_llm_address: str | None = None
    extraction: ExtractionConfig
    # NOTE: hierarchical_clustering / 初期・統合ラベリングは hierarchical モード専用。
    # llm_grouping モードの config には含まれないため optional にする。
    hierarchical_clustering: HierarchicalClusteringConfig | None = None
    hierarchical_initial_labelling: HierarchicalInitialLabellingConfig | None = None
    hierarchical_merge_labelling: HierarchicalMergeLabellingConfig | None = None
    hierarchical_overview: HierarchicalOverviewConfig
    hierarchical_aggregation: HierarchicalAggregationConfig
    # NOTE: llm_grouping モード専用。hierarchical モードの config には含まれない。
    llm_grouping: LLMGroupingConfig | None = None


class ReportConfigUpdate(SchemaBaseModel):
    """レポートのメタデータ更新用スキーマ"""

    question: str | None = None  # レポートのタイトル
    intro: str | None = None  # レポートの調査概要
