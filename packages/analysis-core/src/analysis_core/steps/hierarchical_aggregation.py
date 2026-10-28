"""Generate a convenient JSON output file."""

import json
import os
from collections import defaultdict
from typing import Any, TypedDict

import numpy as np
import polars as pl

from analysis_core.core.utils import atomic_output_path, read_input_csv, write_json_atomic
from analysis_core.steps.extraction import filter_empty_comments
from analysis_core.steps.hierarchical_translation import TRANSLATIONS_FILENAME, fresh_translations


def json_serialize_numpy(obj: Any) -> Any:
    """
    Recursively convert NumPy data types to native Python types for JSON serialization.

    Args:
        obj: Any Python object which might contain NumPy data types

    Returns:
        The same object structure with NumPy types converted to Python native types
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: json_serialize_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [json_serialize_numpy(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(json_serialize_numpy(item) for item in obj)
    else:
        return obj


_NON_PUBLIC_CONFIG_KEYS = {"user_api_key", "error_stack_trace"}


def _public_config(obj: Any) -> Any:
    """hierarchical_result.json に書き出す config から非公開のキーを再帰的に除く。

    hierarchical_result.json は公開 API・静的エクスポート・Blob 同期でそのまま配布されるため、
    ユーザー入力の API キー、サーバー内部パス（`_` 始まりのランタイムキー）、
    前回 status に含まれうるスタックトレースを残さない。
    """
    if isinstance(obj, dict):
        return {
            k: _public_config(v)
            for k, v in obj.items()
            if not (isinstance(k, str) and (k.startswith("_") or k in _NON_PUBLIC_CONFIG_KEYS))
        }
    # tuple も JSON では配列になるので、中の dict を同じく除く（書き出しは list で同じ形になる）
    if isinstance(obj, (list, tuple)):
        return [_public_config(item) for item in obj]
    return obj


class Argument(TypedDict):
    arg_id: str
    argument: str
    comment_id: str
    x: float
    y: float
    p: float
    cluster_ids: list[str]
    attributes: dict[str, str | float] | None
    url: str | None


class Cluster(TypedDict):
    level: int
    id: str
    label: str
    takeaway: str
    value: int
    parent: str
    density_rank_percentile: float | None


def hierarchical_aggregation(config) -> bool:
    """Generate the final JSON output file.

    Config should contain:
        - output_dir: output directory name
        - input: input file name (without .csv extension)
        - pipeline_dir: (optional) base directory for pipeline operations
    """
    try:
        # Get base directories from config
        output_base_dir = config.get("_output_base_dir", "outputs")
        input_base_dir = config.get("_input_base_dir", "inputs")

        path = f"{output_base_dir}/{config['output_dir']}/hierarchical_result.json"
        results = {
            "arguments": [],
            "clusters": [],
            "comments": {},
            "propertyMap": {},
            "translations": {},
            "overview": "",
            "config": _public_config(config),
        }

        arguments = pl.read_csv(f"{output_base_dir}/{config['output_dir']}/args.csv")
        arg_num = len(arguments)
        # comment-id は入力CSVの値そのもの（"001" など）なので、型推論で数値化させない
        # 古い extraction は同じ回答の中で同じ文面が繰り返されると同じ行を重複して書いていた。
        # そのまま join すると final_result_with_comments.csv の行が二重になるので、完全一致の行だけ落とす。
        relation_df = pl.read_csv(
            f"{output_base_dir}/{config['output_dir']}/relations.csv", schema_overrides={"comment-id": pl.Utf8}
        ).unique(maintain_order=True)
        comments = read_input_csv(f"{input_base_dir}/{config['input']}.csv")
        clusters = pl.read_csv(f"{output_base_dir}/{config['output_dir']}/hierarchical_clusters.csv")
        labels = read_merge_labels(f"{output_base_dir}/{config['output_dir']}/hierarchical_merge_labels.csv")

        hidden_properties_map: dict[str, list[str]] = config["hierarchical_aggregation"]["hidden_properties"]

        results["arguments"] = _build_arguments(clusters, comments, relation_df, config)
        # 無効化した後に前回の分類結果が残っていても混ぜない
        if config.get("opinion_classification", {}).get("enabled", False):
            _merge_opinion_classifications(
                results["arguments"], f"{output_base_dir}/{config['output_dir']}/opinion_classifications.csv"
            )
        if config.get("opinion_stance", {}).get("enabled", False):
            _merge_opinion_scores(
                results["arguments"],
                f"{output_base_dir}/{config['output_dir']}/opinion_stances.csv",
                "stance_score",
            )
        if config.get("opinion_novelty", {}).get("enabled", False):
            _merge_opinion_scores(
                results["arguments"],
                f"{output_base_dir}/{config['output_dir']}/opinion_novelty.csv",
                "novelty_score",
            )
        results["clusters"] = _build_cluster_value(labels, arg_num)

        # 元コメント本文は、レポート作成者が「公開してよい」と明示した場合だけ公開 JSON に入れる。
        # 入力 CSV には引用・再頒布が許されないコメントが混ざりうるため、既定では件数だけを出す。
        if config.get("enable_original_comments", False):
            results["comments"] = _build_comments_value(comments, relation_df, hidden_properties_map)
        results["comment_num"] = len(comments)
        # 属性情報のカラムは、元データに対して指定したカラムとclassificationするカテゴリを合わせたもの
        results["propertyMap"] = _build_property_map(arguments, comments, hidden_properties_map, config)

        with open(f"{output_base_dir}/{config['output_dir']}/hierarchical_overview.txt", encoding="utf-8") as f:
            overview = f.read()
        print("overview")
        print(overview)
        results["overview"] = overview

        # Convert non-serializable NumPy types to native Python types
        # （dict を作り直すので、以降 results["config"] を書き換えても呼び出し元の config は変わらない）
        results = json_serialize_numpy(results)
        # TODO: サンプリングロジックを実装したいが、現状は全件抽出
        results["config"]["intro"] = create_custom_intro(config)
        # 訳は原文（ラベル・概要・イントロなど）が確定してから、それに合うものだけを入れる
        results["translations"] = _build_translations(config, results)

        # 公開 API が読み続けるファイルなので、一時ファイルに書いてから差し替え、1 回で書き終える
        write_json_atomic(path, results)
        if config["is_pubcom"]:
            add_original_comments(labels, arguments, relation_df, clusters, config)
        return True
    except Exception as e:
        print("error")
        print(e)
        # 握り潰すと engine が成功扱いし、欠損/古い hierarchical_result.json のまま
        # ready になる。失敗は呼び出し元へ伝播させる。
        raise


def create_custom_intro(config) -> str:
    """hierarchical_result.json の config.intro に入れる、件数とモデルを添えた調査概要を返す"""
    output_base_dir = config.get("_output_base_dir", "outputs")
    input_base_dir = config.get("_input_base_dir", "inputs")

    dataset = config["output_dir"]
    args_path = f"{output_base_dir}/{dataset}/args.csv"
    comments = read_input_csv(f"{input_base_dir}/{config['input']}.csv")

    input_count = len(comments)
    args_count = len(pl.read_csv(args_path))
    # extraction と同じく、空・空白のみのコメントを除いてから limit を適用した件数を表示する
    processed_num = min(len(filter_empty_comments(comments)), config["extraction"]["limit"])

    print(f"Input count: {input_count}")
    print(f"Args count: {args_count}")

    # LLMプロバイダーとモデル名の判定
    def get_llm_provider_display():
        # configからプロバイダー情報を取得（優先）
        provider = config.get("provider", "openai")
        model = config.get("model", "unknown")

        # Azure は config のモデル名（管理画面の固定値 azure-server など）ではなく、サーバーに設定した
        # デプロイを使う。使っていないモデル名や内部値を公開される文に載せない
        if provider == "azure":
            return "Azure OpenAI API（サーバー設定のモデル）"

        # プロバイダー名をマッピング
        provider_names = {
            "openai": "OpenAI API",
            "gemini": "Google Gemini API",
            "openrouter": "OpenRouter API",
            "local": "Local LLM",
        }

        provider_name = provider_names.get(provider, f"{provider} API")
        return f"{provider_name} ({model})"

    llm_provider = get_llm_provider_display()

    base_custom_intro = """{intro}
分析対象となったデータの件数は{processed_num}件で、これらのデータに対して{llm_provider}を用いて{args_count}件の意見（議論）を抽出し、クラスタリングを行った。
"""

    intro = config["intro"]
    return base_custom_intro.format(
        intro=intro, processed_num=processed_num, args_count=args_count, llm_provider=llm_provider
    )


def add_original_comments(labels, arguments, relation_df, clusters, config):
    output_base_dir = config.get("_output_base_dir", "outputs")
    input_base_dir = config.get("_input_base_dir", "inputs")

    # 大カテゴリ（cluster-level-1）に該当するラベルだけ抽出
    labels_lv1 = (
        labels.filter(pl.col("level") == 1)
        .select(["id", "label"])
        .rename({"id": "cluster-level-1-id", "label": "category_label"})
    )

    # arguments と clusters をマージ（カテゴリ情報付与）
    merged = arguments.join(clusters.select(["arg-id", "cluster-level-1-id"]), on="arg-id").join(
        labels_lv1, on="cluster-level-1-id", how="left"
    )

    # relation_df と結合
    merged = merged.join(relation_df, on="arg-id", how="left")

    # 元コメント取得
    comments = read_input_csv(f"{input_base_dir}/{config['input']}.csv")
    comments = comments.with_columns(pl.col("comment-id").cast(pl.Utf8))
    merged = merged.with_columns(pl.col("comment-id").cast(pl.Utf8))

    # 元コメント本文などとマージ
    final_df = merged.join(comments, on="comment-id", how="left")

    # 必要カラムのみ整形
    final_cols = ["comment-id", "comment-body", "arg-id", "argument", "cluster-level-1-id", "category_label"]

    # 基本カラム
    for col in ["x", "y", "source", "url"]:
        if col in comments.columns:
            final_cols.append(col)

    # 属性カラムを追加
    attribute_columns = []
    for col in comments.columns:
        # attributeプレフィックスが付いたカラムを探す
        if col.startswith("attribute_"):
            attribute_columns.append(col)
            final_cols.append(col)

    print(f"属性カラム検出: {attribute_columns}")

    # 必要なカラムだけ選択
    final_df = final_df.select(final_cols)
    final_df = final_df.rename(
        {
            "cluster-level-1-id": "category_id",
            "category_label": "category",
            "arg-id": "arg_id",
            "argument": "argument",
            "comment-body": "original-comment",
        }
    )

    # 保存
    with atomic_output_path(f"{output_base_dir}/{config['output_dir']}/final_result_with_comments.csv") as tmp_path:
        final_df.write_csv(tmp_path)


def _build_arguments(
    clusters: pl.DataFrame, comments: pl.DataFrame, relation_df: pl.DataFrame, config: dict
) -> list[Argument]:
    """
    Build the arguments list including attribute information from original comments

    Args:
        clusters: DataFrame containing cluster information for each argument
        comments: DataFrame containing original comments with attribute columns
        relation_df: DataFrame relating arguments to original comments
        config: Configuration dictionary containing enable_source_link setting
    """
    cluster_columns = [col for col in clusters.columns if col.startswith("cluster-level-") and "id" in col]

    # Prepare for merging with original comments to get attributes
    comments_copy = comments.with_columns(pl.col("comment-id").cast(pl.Utf8))

    # Get argument to comment mapping
    arg_comment_map = {}
    if "comment-id" in relation_df.columns:
        relation_df_copy = relation_df.with_columns(pl.col("comment-id").cast(pl.Utf8))
        arg_comment_map = dict(
            zip(relation_df_copy["arg-id"].to_list(), relation_df_copy["comment-id"].to_list(), strict=False)
        )

    # Find attribute columns in comments dataframe
    attribute_columns = [col for col in comments.columns if col.startswith("attribute_")]
    print(f"属性カラム検出: {attribute_columns}")

    # Build comments lookup
    comments_lookup = {row["comment-id"]: row for row in comments_copy.iter_rows(named=True)}

    arguments: list[Argument] = []
    for row in clusters.iter_rows(named=True):
        cluster_ids = ["0"]
        for cluster_column in cluster_columns:
            cluster_ids.append(str(row[cluster_column]))  # Convert to string to ensure serializable

        # Create base argument
        comment_id = arg_comment_map.get(row["arg-id"], "")
        argument: Argument = {
            "arg_id": str(row["arg-id"]),  # Convert to string to ensure serializable
            "argument": str(row["argument"]),
            "comment_id": str(comment_id) if comment_id else "",
            "x": float(row["x"]),  # Convert to native float
            "y": float(row["y"]),  # Convert to native float
            "p": 0,  # NOTE: 一旦全部0でいれる
            "cluster_ids": cluster_ids,
            "attributes": None,
            "url": None,
        }

        # Add attributes and URL if available
        if row["arg-id"] in arg_comment_map:
            comment_id = arg_comment_map[row["arg-id"]]
            comment_row = comments_lookup.get(comment_id)

            if comment_row is not None:
                # Add URL if available and enabled
                if config.get("enable_source_link", False) and "url" in comment_row and comment_row["url"] is not None:
                    argument["url"] = str(comment_row["url"])

                # Add attributes if available
                if attribute_columns:
                    attributes = {}
                    for attr_col in attribute_columns:
                        # Remove "attribute_" prefix for cleaner attribute names
                        attr_name = attr_col[len("attribute_") :]
                        # Convert potential numpy types to Python native types
                        attr_value = comment_row.get(attr_col, None)
                        if attr_value is not None:
                            if isinstance(attr_value, np.integer):
                                attr_value = int(attr_value)
                            elif isinstance(attr_value, np.floating):
                                attr_value = float(attr_value)
                            elif isinstance(attr_value, np.ndarray):
                                attr_value = attr_value.tolist()
                        attributes[attr_name] = attr_value

                    # Only add non-empty attributes
                    if any(v is not None for v in attributes.values()):
                        argument["attributes"] = attributes

        arguments.append(argument)
    return arguments


def _merge_opinion_classifications(arguments: list[Argument], path: str) -> int:
    """Attach opinion classification labels (yes/no per label) to ``arguments[].attributes``.

    The labels come from the optional ``opinion_classification`` step. They are added
    next to any comment-level ``attribute_*`` values so the viewer's attribute filter
    can use them without further changes. Returns the number of arguments updated.
    """
    if not os.path.exists(path):
        return 0

    classifications = pl.read_csv(path, infer_schema_length=0)
    label_columns = [col for col in classifications.columns if col != "arg-id"]
    if not label_columns:
        return 0
    lookup = {
        str(row["arg-id"]): {col: row[col] for col in label_columns} for row in classifications.iter_rows(named=True)
    }

    updated = 0
    for argument in arguments:
        labels = lookup.get(argument["arg_id"])
        if labels is None:
            continue
        attributes = dict(argument["attributes"] or {})
        attributes.update(labels)
        argument["attributes"] = attributes
        updated += 1

    print(f"意見分類ラベルを付与: {updated}/{len(arguments)}件 ({', '.join(label_columns)})")
    return updated


def _merge_opinion_scores(arguments: list[Argument], path: str, column: str) -> int:
    """Attach one numeric per-opinion score (``stance_score`` / ``novelty_score``) to ``arguments[].attributes``.

    The scores come from the optional ``opinion_stance`` / ``opinion_novelty`` steps. Empty values
    (e.g. a stance that could not be judged) are left out so the viewer's numeric range filter
    only sees real numbers. Returns the number of arguments updated.
    """
    if not os.path.exists(path):
        return 0

    scores = pl.read_csv(path, infer_schema_length=0)
    if column not in scores.columns:
        return 0
    lookup: dict[str, float] = {}
    for row in scores.iter_rows(named=True):
        value = row[column]
        if value is None or str(value).strip() == "":
            continue
        lookup[str(row["arg-id"])] = float(value)

    updated = 0
    for argument in arguments:
        score = lookup.get(argument["arg_id"])
        if score is None:
            continue
        attributes = dict(argument["attributes"] or {})
        attributes[column] = score
        argument["attributes"] = attributes
        updated += 1

    print(f"意見スコアを付与: {updated}/{len(arguments)}件 ({column})")
    return updated


def read_merge_labels(path) -> pl.DataFrame:
    """hierarchical_merge_labels.csv を読む。

    管理画面のラベル編集（apps/api の ClusterRepository.update_csv）は csv モジュールで全行を書き直すので、
    空の label / description は引用符なしの空欄になる。polars の既定ではこれが null になり、
    公開 JSON に文字列 'None' が出てしまうため、空欄は空文字列として読む。
    read_csv の missing_utf8_is_empty_string は polars 2 で無くなったので、読んだ後に null を空文字列にする。
    """
    labels = pl.read_csv(path, schema_overrides={"label": pl.Utf8, "description": pl.Utf8})
    return labels.with_columns(pl.col("label", "description").fill_null(""))


def _text_or_empty(value) -> str:
    return "" if value is None else str(value)


def _build_cluster_value(melted_labels: pl.DataFrame, total_num: int) -> list[Cluster]:
    results: list[Cluster] = [
        Cluster(
            level=0,
            id="0",
            label="全体",
            takeaway="",
            value=int(total_num),  # Convert to native int
            parent="",
            density_rank_percentile=0,
        )
    ]

    for melted_label in melted_labels.iter_rows(named=True):
        # Convert potential NumPy types to native Python types
        level = (
            int(melted_label["level"]) if isinstance(melted_label["level"], int | np.integer) else melted_label["level"]
        )
        cluster_id = str(melted_label["id"])
        label = _text_or_empty(melted_label["label"])
        takeaway = _text_or_empty(melted_label["description"])
        value = (
            int(melted_label["value"]) if isinstance(melted_label["value"], int | np.integer) else melted_label["value"]
        )
        parent = str(melted_label.get("parent", "全体"))

        # Handle density_rank_percentile which might be None or a numeric value
        density_rank = melted_label.get("density_rank_percentile")
        if density_rank is not None:
            if isinstance(density_rank, float | np.floating):
                density_rank = float(density_rank)
            elif isinstance(density_rank, int | np.integer):
                density_rank = int(density_rank)

        cluster_value = Cluster(
            level=level,
            id=cluster_id,
            label=label,
            takeaway=takeaway,
            value=value,
            parent=parent,
            density_rank_percentile=density_rank,
        )
        results.append(cluster_value)
    return results


def _build_comments_value(
    comments: pl.DataFrame,
    relation_df: pl.DataFrame,
    hidden_properties_map: dict[str, list[str]],
) -> dict[str, dict[str, str]]:
    """公開 JSON の comments（comment-id → 元コメント本文）を組み立てる。

    - 意見（argument）に紐づいたコメントだけを入れる。抽出で意見が出なかったコメントは公開しない
    - comment-id は入力 CSV の文字列のまま使う（"001" のような先頭ゼロや数値精度外の ID を崩さない）
    - hidden_properties で非公開にした属性値を持つコメントは、本文も出さない
    """
    comment_dict: dict[str, dict[str, str]] = {}
    if "comment-id" not in relation_df.columns:
        return comment_dict
    useful_comment_ids = set(relation_df.with_columns(pl.col("comment-id").cast(pl.Utf8))["comment-id"].to_list())
    comments_copy = comments.with_columns(pl.col("comment-id").cast(pl.Utf8))
    for row in comments_copy.iter_rows(named=True):
        comment_id = row["comment-id"]
        if comment_id not in useful_comment_ids:
            continue
        should_skip = any(
            prop in row and row[prop] in hidden_values for prop, hidden_values in hidden_properties_map.items()
        )
        if should_skip:
            continue
        body = row.get("comment-body")
        if body is None:
            continue
        comment_dict[str(comment_id)] = {"comment": str(body)}

    return comment_dict


def _build_translations(config, results):
    """出力ディレクトリの translations.json から、今の原文に合う訳を取り出す。

    kouchou-translate は訳を translations.json にも残す。集計は hierarchical_result.json を毎回作り直すので、
    ここで読み直さないと、編集後の再集計で訳が消える。原文が変わった項目の訳は fresh_translations が落とす。
    """
    output_base_dir = config.get("_output_base_dir", "outputs")
    path = f"{output_base_dir}/{config['output_dir']}/{TRANSLATIONS_FILENAME}"

    languages = list(config.get("translation", {}).get("languages", []))
    if not os.path.exists(path):
        if len(languages) > 0:
            raise FileNotFoundError(f"config.translation.languages is set but {path} does not exist")
        return {}
    with open(path, encoding="utf-8") as f:
        stored = json.load(f)
    if not isinstance(stored, dict):
        return {}
    return fresh_translations(stored, results)


def _build_property_map(
    arguments: pl.DataFrame, comments: pl.DataFrame, hidden_properties_map: dict[str, list[str]], config: dict
) -> dict[str, dict[str, str]]:
    property_columns = list(hidden_properties_map.keys()) + list(config["extraction"]["categories"].keys())
    property_map = defaultdict(dict)

    # 指定された property_columns が arguments に存在するかチェック
    missing_cols = [col for col in property_columns if col not in arguments.columns]
    if missing_cols:
        raise ValueError(
            f"指定されたカラム {missing_cols} が args.csv に存在しません。"
            "設定ファイルaggregation / hidden_propertiesから該当カラムを取り除いてください。"
        )

    for row in arguments.iter_rows(named=True):
        arg_id = row["arg-id"]
        for prop in property_columns:
            value = row[prop]

            # Convert NumPy types to Python native types
            if value is not None:
                if isinstance(value, np.integer):
                    value = int(value)
                elif isinstance(value, np.floating):
                    value = float(value)
                elif isinstance(value, np.ndarray):
                    value = value.tolist()
                else:
                    # Convert any other types to string to ensure serialization
                    try:
                        value = str(value)
                    except Exception as e:
                        print(f"Error converting value to string: {e}")
                        value = None

            # Make sure arg_id is string
            str_arg_id = str(arg_id)
            property_map[prop][str_arg_id] = value

    return property_map
