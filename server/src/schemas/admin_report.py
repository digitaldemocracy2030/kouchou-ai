from typing import Literal

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
    model: str  # 利用するLLMの名称
    workers: int  # LLM APIの並列実行数
    prompt: Prompt  # プロンプト
    comments: list[Comment]  # コメントのリスト
    is_pubcom: bool = False  # CSV出力モード出力フラグ
    inputType: Literal["file", "spreadsheet"] = "file"  # 入力タイプ
    is_embedded_at_local: bool = False  # エンベデッド処理をローカルで行うかどうか
    provider: str = "openai"  # LLMプロバイダー（openai, azure, openrouter, local）
    local_llm_address: str | None = None  # LocalLLM用アドレス（例: "127.0.0.1:1234"）
    skip_extraction: bool = False  # 意見抽出スキップ
    skip_initial_labelling: bool = False  # 初期ラベリングスキップ
    skip_merge_labelling: bool = False  # 統合ラベリングスキップ
    skip_overview: bool = False  # 要約プロンプトスキップ

    auto_cluster_enabled: bool = False  # 自動クラスタ数設定
    cluster_top_min: int | None = None  # 自動クラスタ範囲（上位層最小）
    cluster_top_max: int | None = None  # 自動クラスタ範囲（上位層最大）
    cluster_bottom_max: int | None = None  # 自動クラスタ範囲（下位層最大）


class ReportVisibilityUpdate(SchemaBaseModel):
    """レポートの可視性更新用スキーマ"""

    visibility: ReportVisibility  # レポートの可視性
