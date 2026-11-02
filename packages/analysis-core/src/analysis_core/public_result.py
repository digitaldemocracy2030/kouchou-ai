"""公開用レポート結果 ``public_result.json`` を組み立てる。

``hierarchical_result.json`` は分析の全部入り（再分析用）で、設定を丸ごと抱えている。
公開 API・静的書き出し・ビューアが依存してよいのは、そこから **公開してよい項目だけを
ホワイトリストで写した** ``public_result.json`` の方とする。

ホワイトリストにした理由: 集計の ``_public_config`` は非公開キーを除くブラックリストで、
新しいステップや設定が増えると、明示的に除かない限りそのまま公開側へ出る。ユーザー API キーの
漏洩（GHSA-xr6j-6w48-xh62）はこの構造で起きた。公開用 artifact は逆向きに、ここに書いた
キーしか含めない。新しい項目を公開したいときは、このモジュールと
``docs/development/public-result.md`` の両方を更新する。

契約（キーの意味・互換性の扱い）は ``docs/development/public-result.md`` を参照。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from analysis_core.core import utils as _utils

PUBLIC_RESULT_FILENAME = "public_result.json"
RESULT_FILENAME = "hierarchical_result.json"

# 互換性を壊す変更（キーの削除・意味の変更・型の変更）をしたときだけ上げる。
# 省略可能なキーを足すだけなら上げない（読み手は未知のキーを無視する）。
PUBLIC_RESULT_SCHEMA_VERSION = 1

ARGUMENT_KEYS = ("arg_id", "argument", "comment_id", "x", "y", "p", "cluster_ids", "attributes", "url")
CLUSTER_KEYS = ("level", "id", "label", "takeaway", "value", "parent", "density_rank_percentile")
PLAN_ITEM_KEYS = ("step", "run", "reason")
LAYOUT_KEYS = ("kind", "points", "meta")

# config のうち、公開ビューアが表示に使う項目だけ。
# 入れないもの: name / input / output_dir（内部の識別子）、status / previous / completed_jobs /
# lock_until / current_job*（実行状態。hierarchical_status.json の領分）、user_api_key などの秘密、
# ``_`` 始まりのランタイムキー、hidden_properties の中身（何を隠したかは公開しない）、
# replacements（表示に使っていない）、timeout や local_llm_address などの実行環境。
CONFIG_SCALAR_KEYS = (
    "question",
    "intro",
    "model",
    "provider",
    "analysis_mode",
    "is_embedded_at_local",
    "enable_source_link",
    "enable_original_comments",
)
CONFIG_STEP_KEYS: dict[str, tuple[str, ...]] = {
    "extraction": (
        "workers",
        "limit",
        "properties",
        "categories",
        "category_batch_size",
        "source_code",
        "prompt",
        "model",
    ),
    "embedding": ("model", "source_code"),
    "hierarchical_clustering": ("cluster_nums", "source_code"),
    "hierarchical_initial_labelling": ("workers", "source_code", "prompt", "model"),
    "hierarchical_merge_labelling": ("workers", "source_code", "prompt", "model"),
    "hierarchical_overview": ("source_code", "prompt", "model"),
    "hierarchical_aggregation": ("source_code",),
    "hierarchical_visualization": ("source_code",),
    "opinion_classification": ("enabled", "labels"),
}

# 翻訳のうち表示に使わない生成メタ情報（モデル名など）は入れない
TRANSLATION_DROP_KEYS = ("meta",)


def _pick(obj: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    """dict から keys にあるものだけを（順序を保って）写す。dict でなければ空。"""
    if not isinstance(obj, dict):
        return {}
    return {key: obj[key] for key in keys if key in obj}


def _public_config_view(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        return {}
    view: dict[str, Any] = _pick(config, CONFIG_SCALAR_KEYS)
    plan = config.get("plan")
    if isinstance(plan, list):
        view["plan"] = [_pick(item, PLAN_ITEM_KEYS) for item in plan if isinstance(item, dict)]
    for step, keys in CONFIG_STEP_KEYS.items():
        if isinstance(config.get(step), dict):
            view[step] = _pick(config[step], keys)
    return view


def _public_comments(comments: Any) -> dict[str, dict[str, str]]:
    if not isinstance(comments, dict):
        return {}
    public: dict[str, dict[str, str]] = {}
    for comment_id, value in comments.items():
        if isinstance(value, dict) and isinstance(value.get("comment"), str):
            public[str(comment_id)] = {"comment": value["comment"]}
    return public


def _public_translations(translations: Any) -> dict[str, Any]:
    if not isinstance(translations, dict):
        return {}
    public: dict[str, Any] = {}
    for language, entry in translations.items():
        if isinstance(entry, dict):
            public[language] = {k: v for k, v in entry.items() if k not in TRANSLATION_DROP_KEYS}
    return public


def _hidden_property_names(config: Any) -> set[str]:
    """``hierarchical_aggregation.hidden_properties`` で隠すと指定した属性名。"""
    if not isinstance(config, dict):
        return set()
    aggregation = config.get("hierarchical_aggregation")
    hidden = aggregation.get("hidden_properties") if isinstance(aggregation, dict) else None
    return {str(name) for name in hidden} if isinstance(hidden, dict) else set()


def _public_property_map(property_map: Any, config: Any) -> dict[str, dict[str, Any]]:
    """属性表を写す。``hidden_properties`` に指定した属性は列ごと外す。

    集計はこの設定で元コメント本文を隠すが、属性表には指定した属性の値を意見ごとに書いている
    （「隠す」と指定した値がそのまま公開される）。公開用では列ごと出さない。設定の意味（本文だけか、
    その値を持つコメント由来の意見ごとか）は別途決める。
    """
    if not isinstance(property_map, dict):
        return {}
    hidden = _hidden_property_names(config)
    return {
        str(prop): dict(values)
        for prop, values in property_map.items()
        if isinstance(values, dict) and str(prop) not in hidden
    }


def _public_layouts(layouts: Any) -> dict[str, Any]:
    if not isinstance(layouts, dict):
        return {}
    return {layout_id: _pick(layout, LAYOUT_KEYS) for layout_id, layout in layouts.items() if isinstance(layout, dict)}


def build_public_result(result: dict[str, Any]) -> dict[str, Any]:
    """``hierarchical_result.json`` の内容から、公開用 artifact の dict を作る。

    入力は変更しない。ここに列挙していないキーは、どの深さにあっても出力に含めない。
    """
    public: dict[str, Any] = {
        "schema_version": PUBLIC_RESULT_SCHEMA_VERSION,
        "arguments": [_pick(arg, ARGUMENT_KEYS) for arg in result.get("arguments") or [] if isinstance(arg, dict)],
        "clusters": [
            _pick(cluster, CLUSTER_KEYS) for cluster in result.get("clusters") or [] if isinstance(cluster, dict)
        ],
        "comments": _public_comments(result.get("comments")),
        "propertyMap": _public_property_map(result.get("propertyMap"), result.get("config")),
        "translations": _public_translations(result.get("translations")),
        "overview": str(result.get("overview") or ""),
        "config": _public_config_view(result.get("config")),
    }
    if isinstance(result.get("comment_num"), int):
        public["comment_num"] = result["comment_num"]
    layouts = _public_layouts(result.get("layouts"))
    if layouts:
        public["layouts"] = layouts
        default_layout_id = result.get("default_layout_id")
        if isinstance(default_layout_id, str) and default_layout_id:
            public["default_layout_id"] = default_layout_id
    return public


def public_result_path(result_path: str | Path) -> Path:
    """``hierarchical_result.json`` のパスから、隣に置く ``public_result.json`` のパスを返す。"""
    return Path(result_path).with_name(PUBLIC_RESULT_FILENAME)


def write_result_files(result_path: str | Path, result: dict[str, Any]) -> Path:
    """``hierarchical_result.json`` と、そこから作った ``public_result.json`` を書く。

    結果ファイルを書く（作り直す）場所はすべてここを通す。片方だけ更新すると公開用 artifact が
    古いままになるため、集計・レイアウト生成・翻訳のどれが結果を書いても両方をそろえる。
    どちらも一時ファイルに書いてから差し替える。戻り値は公開用 artifact のパス。
    """
    result_path = Path(result_path)
    _utils.write_json_atomic(result_path, result)
    public_path = public_result_path(result_path)
    _utils.write_json_atomic(public_path, build_public_result(result))
    return public_path
