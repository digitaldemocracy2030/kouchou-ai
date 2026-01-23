import os
import pickle
from pathlib import Path

import polars as pl
from tqdm import tqdm

from services.llm import request_to_embed

PIPELINE_DIR = Path(__file__).parent.parent


def embedding(config):
    model = config["embedding"]["model"]
    is_embedded_at_local = config["is_embedded_at_local"]
    # print("start embedding")
    # print(f"embedding model: {model}, is_embedded_at_local: {is_embedded_at_local}")

    dataset = config["output_dir"]
    path = PIPELINE_DIR / f"outputs/{dataset}/embeddings.pkl"
    arguments = pl.read_csv(PIPELINE_DIR / f"outputs/{dataset}/args.csv", columns=["arg-id", "argument"])
    arg_ids = arguments["arg-id"].to_list()
    arg_texts = arguments["argument"].to_list()
    embeddings = []
    batch_size = 1000
    for i in tqdm(range(0, len(arg_texts), batch_size)):
        args = arg_texts[i : i + batch_size]
        embeds = request_to_embed(
            args,
            model,
            is_embedded_at_local,
            config["provider"],
            local_llm_address=config.get("local_llm_address"),
            user_api_key=os.getenv("USER_API_KEY"),
        )
        embeddings.extend(embeds)
    # list[dict] 形式で保存（polars互換）
    embedding_data = [{"arg-id": arg_ids[i], "embedding": e} for i, e in enumerate(embeddings)]
    with open(path, "wb") as f:
        pickle.dump(embedding_data, f)
