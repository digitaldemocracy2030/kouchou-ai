import os
import pickle

import polars as pl
from tqdm import tqdm

from analysis_core.services.llm import request_to_embed


def embedding(config):
    model = config["embedding"]["model"]
    is_embedded_at_local = config["is_embedded_at_local"]
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
            user_api_key=os.getenv("USER_API_KEY"),
        )
        embeddings.extend(embeds)
    # Store as list[dict] for polars compatibility
    embedding_data = [{"arg-id": arg_ids[i], "embedding": e} for i, e in enumerate(embeddings)]
    with open(path, "wb") as f:
        pickle.dump(embedding_data, f)
