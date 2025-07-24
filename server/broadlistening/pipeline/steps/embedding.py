import os

import pandas as pd
from tqdm import tqdm

from services.llm import request_to_embed


def embedding(config):
    model = config["embedding"]["model"]
    is_embedded_at_local = config["is_embedded_at_local"]
    # print("start embedding")
    # print(f"embedding model: {model}, is_embedded_at_local: {is_embedded_at_local}")

    dataset = config["output_dir"]
    path = f"outputs/{dataset}/embeddings.pkl"
    arguments = pd.read_csv(f"outputs/{dataset}/args.csv", usecols=["arg-id", "argument"])
    embeddings = []
    batch_size = 1000
    for i in tqdm(range(0, len(arguments), batch_size)):
        args = arguments["argument"].tolist()[i : i + batch_size]
        embeds = request_to_embed(
            args,
            model,
            is_embedded_at_local,
            config["provider"],
            local_llm_address=config.get("local_llm_address"),
            user_api_key=os.getenv("USER_API_KEY"),
        )
        embeddings.extend(embeds)
    df = pd.DataFrame([{"arg-id": arguments.iloc[i]["arg-id"], "embedding": e} for i, e in enumerate(embeddings)])
    df.to_pickle(path)
