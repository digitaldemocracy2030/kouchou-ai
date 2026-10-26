from enum import Enum

from src.schemas.base import SchemaBaseModel


class ReportStatus(Enum):
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    DELETED = "deleted"


class ReportVisibility(Enum):
    PUBLIC = "public"
    UNLISTED = "unlisted"
    PRIVATE = "private"


class AnalysisData(SchemaBaseModel):
    comment_num: int
    arguments_num: int
    cluster_num: int


class Report(SchemaBaseModel):
    slug: str
    source_slug: str | None = None
    title: str
    description: str
    status: ReportStatus
    visibility: ReportVisibility
    is_pubcom: bool = False
    created_at: str | None = None  # 作成日時
    token_usage: int | None = None  # トークン使用量（合計）
    token_usage_input: int | None = None  # 入力トークン使用量
    token_usage_output: int | None = None  # 出力トークン使用量
    estimated_cost: float | None = None  # 推定コスト（USD）
    provider: str | None = None  # LLMプロバイダー（openai, azure, openrouter, gemini, local）
    model: str | None = None  # LLMモデル
    analysis: AnalysisData | None = None
    # 作成はできたが結果が想定と違いうることを示す警告コード（例: source_input_reconstructed）
    warnings: list[str] | None = None

    @property
    def is_publicly_visible(self) -> bool:
        """レポートが一般ユーザーに公開表示可能かどうかを返す"""
        return self.visibility == ReportVisibility.PUBLIC


class PublicReport(SchemaBaseModel):
    """公開 API (GET /reports) 用のレポート一覧項目

    複製元の slug（限定公開レポートの推測不能な slug でありうる）や、トークン使用量・
    推定コスト・プロバイダー・モデルといった管理用の情報は含めない。
    """

    slug: str
    title: str
    description: str
    status: ReportStatus
    visibility: ReportVisibility
    is_pubcom: bool = False
    created_at: str | None = None

    @classmethod
    def from_report(cls, report: Report) -> "PublicReport":
        return cls(
            slug=report.slug,
            title=report.title,
            description=report.description,
            status=report.status,
            visibility=report.visibility,
            is_pubcom=report.is_pubcom,
            created_at=report.created_at,
        )
