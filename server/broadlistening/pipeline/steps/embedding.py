import os
import pickle

import polars as pl
from tqdm import tqdm

from services.llm import request_to_embed


def embedding(config):
    model = config["embedding"]["model"]
    is_embedded_at_local = config["is_embedded_at_local"]
    # print("start embedding")
    # print(f"embedding model: {model}, is_embedded_at_local: {is_embedded_at_local}")

    dataset = config["output_dir"]
    path = f"outputs/{dataset}/embeddings.pkl"
    arguments = pl.read_csv(f"outputs/{dataset}/args.csv", columns=["arg-id", "argument"])
    embeddings = []
    batch_size = 1000
    argument_values = arguments["argument"].to_list()
    arg_ids = arguments["arg-id"].to_list()
    for i in tqdm(range(0, len(argument_values), batch_size)):
        args = argument_values[i : i + batch_size]
        embeds = request_to_embed(
            args,
            model,
            is_embedded_at_local,
            config["provider"],
            local_llm_address=config.get("local_llm_address"),
            user_api_key=os.getenv("USER_API_KEY"),
        )
        embeddings.extend(embeds)
    embedding_records = [{"arg-id": arg_ids[i], "embedding": e} for i, e in enumerate(embeddings)]
    with open(path, "wb") as f:
        pickle.dump(embedding_records, f)
