import os
import pickle

import polars as pl
from tqdm import tqdm

from analysis_core.services.llm import request_to_embed
from analysis_core.steps._embeddings_io import build_embedding_records, to_embedding_rows


def embedding(config):
    model = config["embedding"]["model"]
    is_embedded_at_local = config["is_embedded_at_local"]
    user_api_key = config.get("user_api_key") or os.getenv("USER_API_KEY")
    # print("start embedding")
    # print(f"embedding model: {model}, is_embedded_at_local: {is_embedded_at_local}")

    dataset = config["output_dir"]
    output_base_dir = config.get("_output_base_dir", "outputs")
    path = f"{output_base_dir}/{dataset}/embeddings.pkl"
    arguments = pl.read_csv(f"{output_base_dir}/{dataset}/args.csv", columns=["arg-id", "argument"])
    embeddings = []
    batch_size = 1000
    arg_ids = arguments["arg-id"].to_list()
    arg_texts = arguments["argument"].to_list()
    for i in tqdm(range(0, len(arguments), batch_size)):
        args = arg_texts[i : i + batch_size]
        embeds = request_to_embed(
            args,
            model,
            is_embedded_at_local,
            config["provider"],
            local_llm_address=config.get("local_llm_address"),
            user_api_key=user_api_key,
        )
        # Python float の list のまま溜めると 1 値あたり約 32 バイトになり、
        # 数万件で GB 単位になる。バッチごとに float32 の配列へ変換する。
        embeddings.extend(to_embedding_rows(embeds))
        del embeds
    # list[dict]（"embedding" は float32 の 1 次元配列）で保存する。形式は _embeddings_io を参照
    embedding_data = build_embedding_records(arg_ids, embeddings)
    with open(path, "wb") as f:
        pickle.dump(embedding_data, f)
