"""Cluster the arguments using UMAP + HDBSCAN and GPT-4."""

import os
import pickle
from importlib import import_module

import numpy as np
import polars as pl

from analysis_core.steps._embeddings_io import stack_embedding_rows

# 保存する UMAP model payload のフォーマット版数。
# 将来 model 保存形式を変える時に後方互換を判断するための marker。
UMAP_MODEL_FORMAT_VERSION = 1
UMAP_MODEL_FILENAME = "umap_model.pkl"
# 散布図の座標は 2 次元
UMAP_N_COMPONENTS = 2
# UMAP の fit（spectral 初期化）は k = n_components + 1 < 件数 を要する。
# これを下回ると「Cannot use scipy.linalg.eigh ... k >= N」などライブラリ内部の文言で落ちる
MIN_ARGUMENTS_FOR_UMAP_FIT = UMAP_N_COMPONENTS + 2


def too_few_arguments_message(argument_count: int) -> str:
    return (
        f"抽出された意見が {argument_count} 件のため、意見を分類できません。"
        f"{MIN_ARGUMENTS_FOR_UMAP_FIT} 件以上必要です。入力のコメントを増やしてください。"
    )


def _load_clustering_dependencies():
    error_message = (
        "Hierarchical clustering requires the optional 'clustering' dependencies. "
        "Install with: pip install 'kouchou-ai-analysis-core[clustering]'"
    )

    try:
        UMAP = import_module("umap").UMAP
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on install profile
        raise RuntimeError(error_message) from exc

    try:
        sch = import_module("scipy.cluster.hierarchy")
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on install profile
        raise RuntimeError(error_message) from exc

    try:
        KMeans = import_module("sklearn.cluster").KMeans
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on install profile
        raise RuntimeError(error_message) from exc

    return UMAP, sch, KMeans


def calculate_recommended_cluster_nums(argument_count: int) -> list[int]:
    """Calculate cluster counts with a cube-root rule.

    The recommendation is derived from extracted argument count:
    - lv1 = round(cuberoot(argument_count))
    - lv2 = lv1^2

    Examples:
    - 1000 -> [10, 100]
    - 125 -> [5, 25]
    """
    if argument_count < 2:
        raise ValueError("argument_count must be at least 2")

    lv1 = max(2, min(10, round(argument_count ** (1 / 3))))
    lv2 = max(2, min(1000, argument_count, lv1 * lv1))
    return sorted(set([lv1, lv2]))


def normalize_cluster_nums(cluster_nums, argument_count: int) -> list[int]:
    """Return a normalized copy of ``cluster_nums`` for hierarchical clustering.

    - 各要素は正の整数でなければならない (それ以外は ValueError)
    - 意見 (argument) 件数を超えるクラスタ数は件数に clamp し、warning を出す
      (``calculate_recommended_cluster_nums`` や LLM grouping と同じく件数で上限を切る)
    - 昇順に並べ、重複を取り除く
    - 入力のリストは書き換えない (config の params-diff / 再実行判定に影響させない)
    """
    if not cluster_nums:
        raise ValueError("cluster_nums must be a non-empty list of positive integers")
    if argument_count < 1:
        raise ValueError("argument_count must be at least 1")

    values: list[int] = []
    for value in cluster_nums:
        if isinstance(value, bool) or not isinstance(value, int | np.integer):
            raise ValueError(f"cluster_nums must contain positive integers only: {list(cluster_nums)}")
        if value < 1:
            raise ValueError(f"cluster_nums must contain positive integers only: {list(cluster_nums)}")
        values.append(int(value))

    clamped = [min(value, argument_count) for value in values]
    if clamped != values:
        print(
            f"Warning: cluster_nums {values} exceed the number of arguments ({argument_count}); "
            f"clamping to {argument_count}"
        )

    normalized = sorted(set(clamped))
    if normalized != values:
        print(f"cluster_nums normalized: {list(cluster_nums)} -> {normalized}")
    return normalized


def save_umap_model(path: str, model, n_features_in: int, n_components: int) -> None:
    """fit 済み UMAP model を metadata 付きで永続化する。

    別レポートの embeddings を同じ平面へ ``.transform`` で投影し直せるようにする
    (#515)。再現性/次元整合のため、学習時の入力次元 (n_features_in) と
    出力次元 (n_components) を一緒に保存しておき、読み込み側で検証する。
    """
    payload = {
        "format_version": UMAP_MODEL_FORMAT_VERSION,
        "model": model,
        "n_features_in": int(n_features_in),
        "n_components": int(n_components),
    }
    with open(path, "wb") as f:
        pickle.dump(payload, f)


def load_umap_model(path: str) -> dict:
    """``save_umap_model`` で保存した payload を読み込む。

    後方互換: 生の UMAP model object が pickle されているだけの場合でも、
    payload dict 形式へ正規化して返す。その場合 ``n_features_in`` は model の
    属性から best-effort で復元する。
    """
    with open(path, "rb") as f:
        loaded = pickle.load(f)

    if isinstance(loaded, dict) and "model" in loaded:
        return loaded

    # 生 model のみが保存されていた場合のフォールバック
    model = loaded
    n_features_in = _infer_model_n_features(model)
    n_components = getattr(model, "n_components", None)
    return {
        "format_version": None,
        "model": model,
        "n_features_in": n_features_in,
        "n_components": n_components,
    }


def _infer_model_n_features(model) -> int | None:
    """fit 済み UMAP model から学習時の入力次元を best-effort で推定する。"""
    n_features = getattr(model, "n_features_in_", None)
    if isinstance(n_features, int):
        return n_features
    raw = getattr(model, "_raw_data", None)
    if raw is not None and getattr(raw, "ndim", 0) == 2:
        return int(raw.shape[1])
    return None


def _resolve_reuse_model_path(reuse_value, output_base_dir: str, dataset: str) -> str | None:
    """config の ``reuse_umap_model`` を実ファイルパスへ解決する (#515)。

    CLI から別レポートの平面を使い回すことを主用途に、次の順で解決する:

    - 空/None             -> None (従来通り fit_transform)
    - 絶対パス            -> そのまま (存在しなければ FileNotFoundError)
    - 相対パス/レポート名  -> 以下の候補を順に探し、最初に存在するファイルを使う:
        1. ``<output_base_dir>/<reuse_value>``                (例: "report_a/umap_model.pkl")
        2. ``<output_base_dir>/<reuse_value>/umap_model.pkl`` (例: レポート名 "report_a")
        3. ``<output_base_dir>/<dataset>/<reuse_value>``      (自レポート dir 内。複製フロー互換)

    reuse が指定されているのに候補ファイルが1つも存在しない場合は、黙って新規 fit に
    フォールバックせず ``FileNotFoundError`` を送出する (CLI での指定ミスに早く気づけるように)。
    """
    if not reuse_value:
        # None / "" / False / 0 は「使い回さない」の意味として扱う。
        return None
    if not isinstance(reuse_value, str):
        # 真値だが文字列でない指定 (例: true, 数値, list) は設定ミスとみなし、
        # 黙って新規 fit にフォールバックせずエラーにする。
        raise TypeError(
            "reuse_umap_model には文字列（レポート名または umap_model.pkl へのパス）を指定してください: "
            f"{type(reuse_value).__name__}={reuse_value!r}"
        )

    if os.path.isabs(reuse_value):
        if os.path.isfile(reuse_value):
            return reuse_value
        raise FileNotFoundError(f"reuse_umap_model に指定された UMAP model が見つかりません: {reuse_value}")

    candidates = [
        os.path.join(output_base_dir, reuse_value),
        os.path.join(output_base_dir, reuse_value, UMAP_MODEL_FILENAME),
        os.path.join(output_base_dir, dataset, reuse_value),
    ]
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    tried = "\n  ".join(candidates)
    raise FileNotFoundError(
        f"reuse_umap_model に指定した UMAP model が見つかりません: {reuse_value!r}\n"
        f"  探索したパス:\n  {tried}\n"
        "  別レポートの output ディレクトリ名、または umap_model.pkl への相対/絶対パスを指定してください。"
    )


def compute_umap_embeddings(
    embeddings_array: np.ndarray,
    n_neighbors: int,
    n_components: int = 2,
    reuse_model_path: str | None = None,
    umap_factory=None,
):
    """UMAP 2D 埋め込みを計算し、使用した model と入力次元を返す。

    reuse_model_path が指定され、かつファイルが存在する場合は、別レポートで fit 済みの
    UMAP model を読み込み、新しい embeddings に ``.transform`` を適用する
    (別データ/時系列データを同一平面へ投影する #515 のコア)。
    それ以外は従来通り ``fit_transform`` を行う (既定挙動は不変)。

    Returns:
        (umap_embeds, model, n_features_in)
    """
    n_features_in = int(embeddings_array.shape[1])

    if reuse_model_path:
        # reuse を要求された以上、存在しないパスで黙って新規 fit に落とさない。
        # (step 経由では resolver が存在保証するが、helper 単体利用時の保険)
        if not os.path.exists(reuse_model_path):
            raise FileNotFoundError(f"reuse_umap_model に指定された UMAP model が見つかりません: {reuse_model_path}")
        payload = load_umap_model(reuse_model_path)
        model = payload["model"]
        expected = payload.get("n_features_in")
        if expected is not None and int(expected) != n_features_in:
            raise ValueError(
                "再利用する UMAP model の学習次元と新しい embeddings の次元が一致しません: "
                f"model={expected}, embeddings={n_features_in}. "
                "同じ embedding model で生成した embeddings を使ってください。"
            )
        print(f"reuse existing UMAP model for projection: {reuse_model_path}")
        umap_embeds = model.transform(embeddings_array)
        return np.asarray(umap_embeds), model, n_features_in

    if umap_factory is None:
        UMAP, _, _ = _load_clustering_dependencies()

        def umap_factory(**kwargs):
            return UMAP(**kwargs)

    model = umap_factory(n_components=n_components, n_neighbors=n_neighbors)
    umap_embeds = model.fit_transform(embeddings_array)
    return np.asarray(umap_embeds), model, n_features_in


def hierarchical_clustering(config):
    UMAP, _, KMeans = _load_clustering_dependencies()

    dataset = config["output_dir"]
    output_base_dir = config.get("_output_base_dir", "outputs")
    path = f"{output_base_dir}/{dataset}/hierarchical_clusters.csv"
    arguments_df = pl.read_csv(f"{output_base_dir}/{dataset}/args.csv", columns=["arg-id", "argument"])
    arg_ids = arguments_df["arg-id"].to_list()

    with open(f"{output_base_dir}/{dataset}/embeddings.pkl", "rb") as f:
        embeddings_data = pickle.load(f)

    # Handle both old (pandas DataFrame) and new (list[dict]) formats
    # 旧形式の list[float] も読めるよう、float32 の配列を先に確保して 1 行ずつ埋める
    # （UMAP は入力を float32 に変換して使うので、UMAP の入力は変わらない）。
    if isinstance(embeddings_data, list):
        # list[dict] 形式の場合、arg-id で並べ替えて順序を保証
        if embeddings_data and "arg-id" in embeddings_data[0]:
            embed_by_id = {item["arg-id"]: item["embedding"] for item in embeddings_data}
            missing = [arg_id for arg_id in arg_ids if arg_id not in embed_by_id]
            if missing:
                raise ValueError(f"embeddings.pkl に存在しない arg-id があります: {missing[:5]} ...")
            embeddings_array = stack_embedding_rows([embed_by_id[arg_id] for arg_id in arg_ids])
            del embed_by_id
        else:
            embeddings_array = stack_embedding_rows([item["embedding"] for item in embeddings_data])
    else:
        # Old pandas DataFrame format for backward compatibility
        # pandas DataFrame は直接イテレートするとカラム名が返されるため、
        # ["embedding"] カラムから値を取得する
        embeddings_array = stack_embedding_rows(embeddings_data["embedding"].values.tolist())
    # 読み込んだ list / dict（旧形式では Python float の list）を UMAP の前に解放する。
    # 残すと UMAP の間も配列版と二重にメモリに載り、数万件で OOM の原因になる。
    del embeddings_data

    # 件数一致の検証
    if embeddings_array.shape[0] != len(arg_ids):
        raise ValueError(
            f"args.csv と embeddings.pkl の件数が一致しません: args={len(arg_ids)}, embeddings={embeddings_array.shape[0]}"
        )

    # #515: 別レポートで fit 済みの UMAP model があれば、それを使い回して
    # 新しい embeddings を同一平面へ投影 (transform) する。無ければ従来通り fit_transform。
    reuse_value = config["hierarchical_clustering"].get("reuse_umap_model")
    reuse_model_path = _resolve_reuse_model_path(reuse_value, output_base_dir, dataset)

    # fit は少数件だと UMAP 内部のエラーで落ちるので、先に分かる文言で止める。
    # transform（reuse_umap_model）は少数件でも投影できるので対象外。
    if reuse_model_path is None and len(arg_ids) < MIN_ARGUMENTS_FOR_UMAP_FIT:
        raise ValueError(too_few_arguments_message(len(arg_ids)))

    cluster_nums = config["hierarchical_clustering"].get("cluster_nums")
    if not cluster_nums:
        cluster_nums = calculate_recommended_cluster_nums(len(arg_ids))
        config["hierarchical_clustering"]["cluster_nums"] = cluster_nums
        print(f"cluster_nums not provided; using recommended cluster counts based on arg count: {cluster_nums}")
    # UMAP の前に検証・正規化しておく (config 自体は書き換えない)
    cluster_nums = normalize_cluster_nums(cluster_nums, len(arg_ids))

    n_samples = embeddings_array.shape[0]
    # デフォルト設定は15
    default_n_neighbors = 15

    # テスト等サンプルが少なすぎる場合、n_neighborsの設定値を下げる
    if n_samples <= default_n_neighbors:
        n_neighbors = max(2, n_samples - 1)  # 最低2以上
    else:
        n_neighbors = default_n_neighbors

    def _umap_factory(**kwargs):
        return UMAP(**kwargs)

    umap_embeds, umap_model, n_features_in = compute_umap_embeddings(
        embeddings_array,
        n_neighbors=n_neighbors,
        n_components=UMAP_N_COMPONENTS,
        reuse_model_path=reuse_model_path,
        umap_factory=_umap_factory,
    )

    # fit / reuse のいずれでも、使用した model を自レポートの output dir へ保存し、
    # このレポート自体も別レポートの投影元として再利用できるようにする。
    model_path = f"{output_base_dir}/{dataset}/{UMAP_MODEL_FILENAME}"
    save_umap_model(model_path, umap_model, n_features_in=n_features_in, n_components=UMAP_N_COMPONENTS)

    cluster_results = hierarchical_clustering_embeddings(
        umap_embeds=umap_embeds,
        cluster_nums=cluster_nums,
        kmeans_class=KMeans,
    )
    result_df = pl.DataFrame(
        {
            "arg-id": arguments_df["arg-id"].to_list(),
            "argument": arguments_df["argument"].to_list(),
            "x": umap_embeds[:, 0].tolist(),
            "y": umap_embeds[:, 1].tolist(),
        }
    )

    for cluster_level, final_labels in enumerate(cluster_results.values(), start=1):
        result_df = result_df.with_columns(
            pl.Series(
                name=f"cluster-level-{cluster_level}-id", values=[f"{cluster_level}_{label}" for label in final_labels]
            )
        )

    result_df.write_csv(path)


def generate_cluster_count_list(min_clusters: int, max_clusters: int):
    cluster_counts = []
    current = min_clusters
    cluster_counts.append(current)

    if min_clusters == max_clusters:
        return cluster_counts

    while True:
        next_double = current * 2
        next_triple = current * 3

        if next_double >= max_clusters:
            if cluster_counts[-1] != max_clusters:
                cluster_counts.append(max_clusters)
            break

        # 次の倍はまだ max_clusters に収まるが、3倍だと超える
        # -> (次の倍は細かすぎるので)スキップして max_clusters に飛ぶ
        if next_triple > max_clusters:
            cluster_counts.append(max_clusters)
            break

        cluster_counts.append(next_double)
        current = next_double

    return cluster_counts


def merge_clusters_with_hierarchy(
    cluster_centers: np.ndarray,
    kmeans_labels: np.ndarray,
    umap_array: np.ndarray,
    n_cluster_cut: int,
):
    _, sch, _ = _load_clustering_dependencies()
    Z = sch.linkage(cluster_centers, method="ward")
    cluster_labels_merged = sch.fcluster(Z, t=n_cluster_cut, criterion="maxclust")

    n_samples = umap_array.shape[0]
    final_labels = np.zeros(n_samples, dtype=int)

    for i in range(n_samples):
        original_label = kmeans_labels[i]
        final_labels[i] = cluster_labels_merged[original_label]

    return final_labels


def hierarchical_clustering_embeddings(
    umap_embeds,
    cluster_nums,
    kmeans_class=None,
):
    if kmeans_class is None:
        _, _, kmeans_class = _load_clustering_dependencies()

    # 呼び出し元の config を書き換えないよう、正規化したコピーを使う。
    # 最大分割数は必ず正規化 (昇順・重複除去・件数で clamp) 後の末尾から取る。
    cluster_nums = normalize_cluster_nums(cluster_nums, len(umap_embeds))

    # 最大分割数でクラスタリングを実施
    print("start initial clustering")
    initial_cluster_num = cluster_nums[-1]
    kmeans_model = kmeans_class(n_clusters=initial_cluster_num)
    kmeans_model.fit(umap_embeds)
    print("end initial clustering")

    results = {}
    print("start hierarchical clustering")
    print(cluster_nums)
    for n_cluster_cut in cluster_nums[:-1]:
        print("n_cluster_cut: ", n_cluster_cut)
        final_labels = merge_clusters_with_hierarchy(
            cluster_centers=kmeans_model.cluster_centers_,
            kmeans_labels=kmeans_model.labels_,
            umap_array=umap_embeds,
            n_cluster_cut=n_cluster_cut,
        )
        results[n_cluster_cut] = final_labels

    results[initial_cluster_num] = kmeans_model.labels_
    print("end hierarchical clustering")

    return results
