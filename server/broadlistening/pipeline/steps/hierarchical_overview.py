"""Create summaries for the clusters."""

import pandas as pd

from services.llm import request_to_chat_openai


def hierarchical_overview(config):
    dataset = config["output_dir"]
    path = f"outputs/{dataset}/hierarchical_overview.txt"

    hierarchical_label_df = pd.read_csv(f"outputs/{dataset}/hierarchical_merge_labels.csv")

    prompt = config["hierarchical_overview"]["prompt"]
    model = config["hierarchical_overview"]["model"]

    # TODO: level1で固定にしているが、設定で変えられるようにする
    target_level = 1
    target_records = hierarchical_label_df[hierarchical_label_df["level"] == target_level]
    ids = target_records["id"].to_list()
    labels = target_records["label"].to_list()
    descriptions = target_records["description"].to_list()
    target_records.set_index("id", inplace=True)

    input = ""
    for i, _ in enumerate(ids):
        input += f"# Cluster {i}/{len(ids)}: {labels[i]}\n\n"
        input += descriptions[i] + "\n\n"

    messages = [{"role": "user", "content": prompt}, {"role": "user", "content": input}]
    response = request_to_chat_openai(messages=messages, model=model, provider=config.get("provider"))

    with open(path, "w") as file:
        file.write(response)
