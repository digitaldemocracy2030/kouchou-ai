from pydantic import field_validator

from src.schemas.base import SchemaBaseModel
from src.schemas.report import ReportVisibility


class Comment(SchemaBaseModel):
    id: str
    comment: str
    source: str | None = None
    url: str | None = None

    class Config:
        extra = "allow"


class Prompt(SchemaBaseModel):
    extraction: str
    initial_labelling: str
    merge_labelling: str
    overview: str


class ReportInput(SchemaBaseModel):
    input: str  # レポートのID
    question: str  # レポートのタイトル
    intro: str  # レポートの調査概要
    cluster: list[int]  # 層ごとのクラスタ数定義
    model: str  # 利用するLLMの名称（チャット用）
    embedding_model: str | None = None  # 利用する埋め込みモデル名（未指定時はサーバー既定）
    workers: int  # LLM APIの並列実行数
    prompt: Prompt  # プロンプト
    comments: list[Comment]  # コメントのリスト
    is_pubcom: bool = False  # CSV出力モード出力フラグ
    inputType: str = "file"  # 入力タイプ（"file", "spreadsheet", "plugin:xxx"）
    is_embedded_at_local: bool = False  # エンベデッド処理をローカルで行うかどうか

    # 分析方式。"hierarchical"=埋め込みベースの階層クラスタリング（既定）、
    # "llm_grouping"=LLM 直接グルーピング（LLM による group discovery + batch assignment）
    analysis_mode: str = "hierarchical"

    @field_validator("inputType")
    @classmethod
    def validate_input_type(cls, v: str) -> str:
        """Validate input type: file, spreadsheet, or plugin:xxx format."""
        valid_types = {"file", "spreadsheet"}
        if v in valid_types or v.startswith("plugin:"):
            return v
        raise ValueError(f"inputType must be 'file', 'spreadsheet', or 'plugin:xxx', got '{v}'")

    @field_validator("analysis_mode")
    @classmethod
    def validate_analysis_mode(cls, v: str) -> str:
        """Validate analysis mode: hierarchical (embedding-based) or llm_grouping."""
        valid_modes = {"hierarchical", "llm_grouping"}
        if v in valid_modes:
            return v
        raise ValueError(f"analysis_mode must be 'hierarchical' or 'llm_grouping', got '{v}'")

    provider: str = "openai"  # LLMプロバイダー（openai, azure, openrouter, gemini, local）
    local_llm_address: str | None = None  # LocalLLM用アドレス（例: "127.0.0.1:1234"）

    # NOTE: team-mirai feature
    enable_source_link: bool = False  # ソースリンク機能を有効にするかどうか。有効にする場合はtrue
    # 元コメント本文を公開レポート (hierarchical_result.json) に含めるかどうか。
    # 入力データの引用・再頒布が許されている場合だけ true にする
    enable_original_comments: bool = False


class ReportVisibilityUpdate(SchemaBaseModel):
    """レポートの可視性更新用スキーマ"""

    visibility: ReportVisibility  # レポートの可視性


class PromptOverride(SchemaBaseModel):
    extraction: str | None = None
    initial_labelling: str | None = None
    merge_labelling: str | None = None
    overview: str | None = None


class ReportDuplicateOverrides(SchemaBaseModel):
    question: str | None = None
    intro: str | None = None
    cluster: list[int] | None = None
    model: str | None = None
    embedding_model: str | None = None
    provider: str | None = None
    workers: int | None = None
    is_pubcom: bool | None = None
    enable_source_link: bool | None = None
    enable_original_comments: bool | None = None
    is_embedded_at_local: bool | None = None
    local_llm_address: str | None = None
    prompt: PromptOverride | None = None


class ReportDuplicateReuse(SchemaBaseModel):
    enabled: bool = True


class ReportDuplicateRequest(SchemaBaseModel):
    new_slug: str | None = None
    overrides: ReportDuplicateOverrides | None = None
    reuse: ReportDuplicateReuse | None = None
