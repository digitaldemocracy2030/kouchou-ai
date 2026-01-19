"""
可視化設定のスキーマ定義

レポートの表示方法をカスタマイズするための設定を定義します。
"""

from typing import Literal

from src.schemas.base import SchemaBaseModel

ChartType = Literal["scatterAll", "scatterDensity", "treemap"]


class ScatterDensityParams(SchemaBaseModel):
    """散布図密度設定のパラメータ"""

    max_density: float | None = None
    min_value: int | None = None


class DisplayParams(SchemaBaseModel):
    """表示パラメータ"""

    show_cluster_labels: bool | None = None
    scatter_density: ScatterDensityParams | None = None


class ReportDisplayConfig(SchemaBaseModel):
    """
    レポート表示設定

    レポートの表示方法をカスタマイズするための設定。
    管理者がdraftとして保存し、publishで公開する。
    """

    version: str = "1"
    enabled_charts: list[ChartType] = ["scatterAll", "scatterDensity", "treemap"]
    default_chart: ChartType | None = "scatterAll"
    chart_order: list[ChartType] | None = None
    params: DisplayParams | None = None
    updated_at: str | None = None
    updated_by: str | None = None


# デフォルト設定
DEFAULT_REPORT_DISPLAY_CONFIG = ReportDisplayConfig(
    version="1",
    enabled_charts=["scatterAll", "scatterDensity", "treemap"],
    default_chart="scatterAll",
    params=DisplayParams(
        show_cluster_labels=True,
        scatter_density=ScatterDensityParams(
            max_density=0.2,
            min_value=5,
        ),
    ),
)
