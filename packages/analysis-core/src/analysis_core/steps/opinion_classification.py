"""Classify each extracted opinion with independent yes/no labels using an LLM.

The labels (by default ``hate_or_insult`` and ``policy_proposal``) are written to
``opinion_classifications.csv`` and merged into ``arguments[].attributes`` by the
aggregation step, so the public viewer's attribute filter can restrict a map to,
for example, policy proposals without any viewer change. Nothing is removed from
the analysis; the labels only add information.
"""

import concurrent.futures
import json
import os
from typing import Any

import polars as pl
from pydantic import BaseModel, create_model

from analysis_core.core import update_progress
from analysis_core.services.llm import request_to_chat_ai
from analysis_core.services.timeouts import DEFAULT_REQUEST_TIMEOUT_SECONDS, resolve_timeout
from analysis_core.steps._labelling import record_usage
from analysis_core.steps.opinion_labels import (
    DEFAULT_LABEL_IDS,
    InvalidClassificationResponse,
    compute_label_ratios,
    format_label_value,
    parse_classification_response,
)

CLASSIFICATIONS_FILENAME = "opinion_classifications.csv"
SUMMARY_FILENAME = "opinion_classification_summary.json"
SUMMARY_NOTE = (
    "ラベルはLLMの判定で、人手による検証はしていません。比率は抽出された意見のうち各ラベルの定義に該当すると"
    "判定された件数の割合であり、投稿者や世論の代表値ではありません。定義はプロンプトを参照してください。"
)


class ClassificationBatchError(RuntimeError):
    """Some opinions could not be classified; partial results are not written."""

    def __init__(self, failures: dict[str, str]):
        self.failures = failures
        super().__init__(
            f"意見分類に失敗した意見が{len(failures)}件あります。分析を中断しました。 (arg-id / error: {failures})"
        )


def build_response_model(label_ids: tuple[str, ...] | list[str]) -> type[BaseModel]:
    """Create a pydantic model with one required boolean field per label."""
    fields: dict[str, Any] = {label_id: (bool, ...) for label_id in label_ids}
    return create_model("OpinionClassificationResponse", **fields)


def classify_argument(
    text: str,
    prompt: str,
    label_ids: tuple[str, ...] | list[str],
    model: str,
    provider: str = "openai",
    local_llm_address: str | None = None,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    user_api_key: str | None = None,
) -> tuple[dict[str, bool], int, int, int]:
    """Send one opinion to the LLM and return its labels with token usage."""
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": text},
    ]
    response, token_input, token_output, token_total = request_to_chat_ai(
        messages=messages,
        model=model,
        is_json=False,
        json_schema=build_response_model(label_ids),
        provider=provider,
        local_llm_address=local_llm_address,
        user_api_key=user_api_key or os.getenv("USER_API_KEY"),
        timeout_seconds=timeout_seconds,
    )
    labels = parse_classification_response(response, label_ids)
    return labels, token_input, token_output, token_total


def classify_batch(
    arg_ids: list[str],
    texts: list[str],
    prompt: str,
    label_ids: tuple[str, ...] | list[str],
    model: str,
    workers: int,
    provider: str = "openai",
    local_llm_address: str | None = None,
    config: dict | None = None,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    user_api_key: str | None = None,
) -> list[dict[str, bool]]:
    """Classify a batch concurrently. Any failure aborts the batch with the failed arg-ids."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                classify_argument,
                text,
                prompt,
                label_ids,
                model,
                provider,
                local_llm_address,
                timeout_seconds,
                user_api_key,
            )
            for text in texts
        ]
        done, not_done = concurrent.futures.wait(futures, timeout=timeout_seconds)
        for future in not_done:
            future.cancel()

        results: list[dict[str, bool]] = [{} for _ in texts]
        failures: dict[str, str] = {}
        for arg_id, future in zip(arg_ids, futures, strict=True):
            if future not in done:
                failures[arg_id] = "TimeoutError"
                continue
            try:
                labels, token_input, token_output, token_total = future.result()
            except InvalidClassificationResponse:
                failures[arg_id] = "invalid_response"
                continue
            except Exception as exc:
                failures[arg_id] = type(exc).__name__
                continue
            record_usage(config, token_input, token_output, token_total)
            results[arg_ids.index(arg_id)] = labels

    if failures:
        raise ClassificationBatchError(failures)
    return results


def write_classifications(path: str, arg_ids: list[str], rows: list[dict[str, bool]], label_ids) -> pl.DataFrame:
    """Write ``arg-id`` plus one ``yes``/``no`` column per label."""
    data: dict[str, list[str]] = {"arg-id": list(arg_ids)}
    for label_id in label_ids:
        data[label_id] = [format_label_value(row[label_id]) for row in rows]
    frame = pl.DataFrame(data)
    frame.write_csv(path)
    return frame


def build_summary(rows: list[dict[str, bool]], label_ids, *, provider: str, model: str) -> dict[str, Any]:
    summary = compute_label_ratios(rows, label_ids)
    summary.update({"provider": provider, "model": model, "label_ids": list(label_ids), "note": SUMMARY_NOTE})
    return summary


def opinion_classification(config: dict) -> None:
    """Classify every row of ``args.csv`` and write the CSV and summary files.

    Config should contain:
        - output_dir / _output_base_dir: where ``args.csv`` lives
        - provider, local_llm_address, user_api_key (optional)
        - opinion_classification: model, prompt, workers, timeout_seconds, labels (optional list of IDs)
    """
    dataset = config["output_dir"]
    output_base_dir = config.get("_output_base_dir", "outputs")
    step_config = config["opinion_classification"]
    model = step_config["model"]
    prompt = step_config["prompt"]
    workers = int(step_config.get("workers") or 1)
    label_ids = tuple(step_config.get("labels") or DEFAULT_LABEL_IDS)
    timeout_seconds = resolve_timeout(step_config.get("timeout_seconds"))
    user_api_key = config.get("user_api_key") or os.getenv("USER_API_KEY")

    if "provider" not in config:
        raise RuntimeError("provider is not set")
    provider = config["provider"]

    # 失敗したときに前回の結果（古い arg-id のラベル）が集計へ混ざらないよう、先に消しておく
    for filename in (CLASSIFICATIONS_FILENAME, SUMMARY_FILENAME):
        stale_path = f"{output_base_dir}/{dataset}/{filename}"
        if os.path.exists(stale_path):
            os.remove(stale_path)

    arguments = pl.read_csv(f"{output_base_dir}/{dataset}/args.csv", infer_schema_length=0)
    arg_ids = [str(value) for value in arguments["arg-id"].to_list()]
    texts = [str(value) for value in arguments["argument"].to_list()]
    update_progress(config, total=len(arg_ids))

    rows: list[dict[str, bool]] = []
    for start in range(0, len(arg_ids), workers):
        batch_ids = arg_ids[start : start + workers]
        batch_texts = texts[start : start + workers]
        rows.extend(
            classify_batch(
                batch_ids,
                batch_texts,
                prompt,
                label_ids,
                model,
                workers,
                provider,
                config.get("local_llm_address"),
                config,
                timeout_seconds,
                user_api_key,
            )
        )
        update_progress(config, incr=len(batch_ids))

    write_classifications(f"{output_base_dir}/{dataset}/{CLASSIFICATIONS_FILENAME}", arg_ids, rows, label_ids)
    summary = build_summary(rows, label_ids, provider=provider, model=model)
    with open(f"{output_base_dir}/{dataset}/{SUMMARY_FILENAME}", "w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
