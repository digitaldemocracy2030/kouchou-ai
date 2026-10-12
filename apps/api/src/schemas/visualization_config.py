"""
可視化設定のスキーマ定義

レポートの表示方法をカスタマイズするための設定を定義します。
"""

from copy import deepcopy

from pydantic import Field, ValidationError

from src.schemas.base import SchemaBaseModel

ChartType = str


class ScatterDensityParams(SchemaBaseModel):
    """散布図密度設定のパラメータ"""

    max_density: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    min_value: int | None = Field(default=None, ge=0, strict=True)


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


def parse_saved_visualization_config(raw_config: object) -> ReportDisplayConfig:
    """保存済み設定の不正な密度項目だけを補い、元データと他の設定を保持する。

    新規保存には通常のモデル検証を使い、範囲外の値を引き続き拒否する。
    密度以外の検証エラーは呼び出し元へ伝える。
    """
    try:
        return ReportDisplayConfig.model_validate(raw_config)
    except ValidationError as error:
        if not isinstance(raw_config, dict):
            raise
        recovered = deepcopy(raw_config)
        defaults = DEFAULT_REPORT_DISPLAY_CONFIG.model_dump()["params"]["scatter_density"]
        field_names = {
            "max_density": "max_density",
            "maxDensity": "max_density",
            "min_value": "min_value",
            "minValue": "min_value",
        }
        repaired = False
        for detail in error.errors():
            loc = detail["loc"]
            if (
                len(loc) == 3
                and loc[0] == "params"
                and loc[1] in ("scatter_density", "scatterDensity")
                and loc[2] in field_names
            ):
                recovered[loc[0]][loc[1]][loc[2]] = defaults[field_names[loc[2]]]
                repaired = True
        if not repaired:
            raise
        return ReportDisplayConfig.model_validate(recovered)
