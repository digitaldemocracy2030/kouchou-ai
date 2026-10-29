"""抽出した意見 1 件ごとに、対象（既定はレポートの question）への賛否スコアを LLM で付ける任意ステップ。

スコア（-1.0〜+1.0）は ``opinion_stances.csv`` に書き、``hierarchical_aggregation`` が
``arguments[].attributes.stance_score`` に数値として入れる。公開ビューアの属性フィルタは数値属性を
範囲で絞れるので、ビューアを変えずに「賛成だけ」「反対だけ」の地図が見られる。

同じトピックで賛成と反対が混ざったクラスタは、ラベルを読んでも洞察にならない（書籍 13.4.3 の
センチメント次元の問題意識）。埋め込みを変える前に、まず意見ごとの属性として賛否を持つ。
意見を削除・書き換えることはなく、スコアは情報を足すだけ。
"""

import json
import math
import os
import re
from collections.abc import Callable
from typing import Any

import polars as pl
from pydantic import BaseModel

from analysis_core.core import update_progress
from analysis_core.services.llm import request_to_chat_ai
from analysis_core.services.timeouts import DEFAULT_REQUEST_TIMEOUT_SECONDS, resolve_timeout
from analysis_core.steps._per_opinion import PerOpinionBatchError, run_per_opinion

STANCES_FILENAME = "opinion_stances.csv"
SUMMARY_FILENAME = "opinion_stance_summary.json"
SCORE_COLUMN = "stance_score"
SUMMARY_NOTE = (
    "スコアはLLMの判定で、人手による検証はしていません。対象（target）に対する各意見の賛否の度合いであり、"
    "投稿者や世論の代表値ではありません。対象が意見から判断できないものは判定不能として数えず、"
    "属性にも入れていません。"
)

_CODE_FENCE = re.compile(r"```(?:json)?", re.IGNORECASE)

STANCE_PROMPT = """あなたは意見の賛否判定の補助者です。userのinputには「対象」と、ある文章から抽出された1件の「意見」が入っています。
この意見が対象に対してどの程度賛成か反対かを判定し、JSONで返してください。

# 判定のルール
- stance_score は -1.0（明確に反対）から +1.0（明確に賛成）までの数値です。0.0 は賛否が中立、または賛否を述べていないことを表します。
- 意見が対象と無関係で、対象への賛否を読み取れない場合は applicable を false にし、stance_score は 0.0 にしてください。
- 意見の内容を書き換えたり、要約したり、良し悪しを評価したりしないでください。対象への賛否の向きと強さだけを判定します。
- 意見の主張が正しいかどうかは判定に影響させないでください。
- 出力はJSONオブジェクトのみとし、applicable（true / false）と stance_score（数値）の2つのキーだけを含めてください。説明文は出力しないでください。

# 入出力の例（説明用に作成した架空の例です。実際の入力と混同しないでください）
/human
対象: 市内に新しい図書館を建設する計画
意見: 図書館は子どもの学びの場になるので、ぜひ進めてほしい。
/ai
{"applicable": true, "stance_score": 0.9}
/human
対象: 市内に新しい図書館を建設する計画
意見: 財政が厳しい中で新しい箱物を作るのは反対だ。
/ai
{"applicable": true, "stance_score": -0.9}
/human
対象: 市内に新しい図書館を建設する計画
意見: 建てるなら駅の近くにしてほしい。
/ai
{"applicable": true, "stance_score": 0.3}
/human
対象: 市内に新しい図書館を建設する計画
意見: バスの本数を増やしてほしい。
/ai
{"applicable": false, "stance_score": 0.0}
"""


class InvalidStanceResponse(ValueError):
    """LLM の応答が賛否スコアとして読めない（JSON でない、キーが欠ける、範囲外など）。"""


class StanceBatchError(PerOpinionBatchError):
    """Some opinions could not be scored; partial results are not written."""

    task_name = "賛否スコア"


class StanceResponse(BaseModel):
    """1 件の意見に対する応答。applicable=false は対象への賛否を読み取れない（判定不能）。"""

    applicable: bool
    stance_score: float


def build_stance_input(target: str, text: str) -> str:
    """user メッセージを組み立てる。対象はプロンプトではなく毎回の入力に入れる（プロンプトは固定文でよい）。"""
    return f"対象: {target}\n意見: {text}"


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
        return value.strip().lower() == "true"
    raise InvalidStanceResponse("applicable が真偽値ではありません")


def parse_stance_response(response: str | dict) -> float | None:
    """応答から賛否スコアを取り出す。判定不能（applicable=false）は None。

    範囲外・非数値・キー欠落は ``InvalidStanceResponse``。「どちらでもない」と見なして 0.0 にはしない。
    """
    data: Any = response
    if isinstance(data, str):
        text = _CODE_FENCE.sub("", data).strip()
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end < start:
            raise InvalidStanceResponse("賛否応答にJSONオブジェクトが含まれていません")
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            raise InvalidStanceResponse("賛否応答のJSONが不正です") from None
    if not isinstance(data, dict):
        raise InvalidStanceResponse("賛否応答がオブジェクトではありません")
    if "applicable" not in data or "stance_score" not in data:
        raise InvalidStanceResponse("賛否応答に applicable / stance_score がありません")
    applicable = _coerce_bool(data["applicable"])
    score = data["stance_score"]
    if isinstance(score, bool) or not isinstance(score, (int, float, str)):
        raise InvalidStanceResponse("stance_score が数値ではありません")
    try:
        value = float(score)
    except ValueError:
        raise InvalidStanceResponse("stance_score が数値ではありません") from None
    if math.isnan(value) or not -1.0 <= value <= 1.0:
        raise InvalidStanceResponse("stance_score が -1.0〜1.0 の範囲外です")
    return value if applicable else None


def score_argument(
    text: str,
    prompt: str,
    target: str,
    model: str,
    provider: str = "openai",
    local_llm_address: str | None = None,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    user_api_key: str | None = None,
) -> tuple[float | None, int, int, int]:
    """Send one opinion to the LLM and return its stance score (None = 判定不能) with token usage."""
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": build_stance_input(target, text)},
    ]
    response, token_input, token_output, token_total = request_to_chat_ai(
        messages=messages,
        model=model,
        is_json=False,
        json_schema=StanceResponse,
        provider=provider,
        local_llm_address=local_llm_address,
        user_api_key=user_api_key or os.getenv("USER_API_KEY"),
        timeout_seconds=timeout_seconds,
    )
    return parse_stance_response(response), token_input, token_output, token_total


def score_batch(
    arg_ids: list[str],
    texts: list[str],
    prompt: str,
    target: str,
    model: str,
    workers: int,
    provider: str = "openai",
    local_llm_address: str | None = None,
    config: dict | None = None,
    timeout_seconds: int = DEFAULT_REQUEST_TIMEOUT_SECONDS,
    user_api_key: str | None = None,
    on_progress: Callable[[int], None] | None = None,
) -> list[float | None]:
    """Score opinions with a pool of ``workers`` threads. Any failure aborts with the failed arg-ids."""

    def run(text: str):
        return score_argument(text, prompt, target, model, provider, local_llm_address, timeout_seconds, user_api_key)

    return run_per_opinion(
        arg_ids,
        texts,
        run,
        workers,
        config=config,
        user_api_key=user_api_key,
        invalid_response_type=InvalidStanceResponse,
        error_type=StanceBatchError,
        task_name="賛否スコア",
        on_progress=on_progress,
    )


def write_stances(path: str, arg_ids: list[str], scores: list[float | None]) -> pl.DataFrame:
    """Write ``arg-id`` and ``stance_score``（判定不能は空欄）."""
    frame = pl.DataFrame(
        {"arg-id": list(arg_ids), SCORE_COLUMN: [None if s is None else float(s) for s in scores]},
        schema={"arg-id": pl.Utf8, SCORE_COLUMN: pl.Float64},
    )
    frame.write_csv(path)
    return frame


def build_summary(scores: list[float | None], *, provider: str, model: str, target: str) -> dict[str, Any]:
    """件数・平均・分布（5 区間）をまとめる。分母は分類した意見の件数で、投稿者数ではない。"""
    scored = [s for s in scores if s is not None]
    bins = {"strongly_against": 0, "against": 0, "neutral": 0, "for": 0, "strongly_for": 0}
    for s in scored:
        if s <= -0.6:
            bins["strongly_against"] += 1
        elif s < -0.2:
            bins["against"] += 1
        elif s <= 0.2:
            bins["neutral"] += 1
        elif s < 0.6:
            bins["for"] += 1
        else:
            bins["strongly_for"] += 1
    return {
        "total": len(scores),
        "scored": len(scored),
        "not_applicable": len(scores) - len(scored),
        "mean": (sum(scored) / len(scored)) if scored else None,
        "distribution": bins,
        "provider": provider,
        "model": model,
        "target": target,
        "note": SUMMARY_NOTE,
    }


def resolve_target(config: dict, step_config: dict) -> str:
    """賛否の対象。``opinion_stance.target`` が無ければレポートの ``question`` を使う。"""
    target = step_config.get("target") or config.get("question")
    if not target or not str(target).strip():
        raise RuntimeError("opinion_stance.target か question のどちらかを設定してください（賛否の対象が要ります）")
    return str(target).strip()


def opinion_stance(config: dict) -> None:
    """Score every row of ``args.csv`` and write the CSV and summary files.

    Config should contain:
        - output_dir / _output_base_dir: where ``args.csv`` lives
        - provider, local_llm_address, user_api_key (optional), question
        - opinion_stance: model, prompt, workers, timeout_seconds, target (optional)
    """
    dataset = config["output_dir"]
    output_base_dir = config.get("_output_base_dir", "outputs")
    step_config = config["opinion_stance"]
    model = step_config["model"]
    prompt = step_config["prompt"]
    workers = int(step_config.get("workers") or 1)
    target = resolve_target(config, step_config)
    timeout_seconds = resolve_timeout(step_config.get("timeout_seconds"))
    user_api_key = config.get("user_api_key") or os.getenv("USER_API_KEY")

    if "provider" not in config:
        raise RuntimeError("provider is not set")
    provider = config["provider"]

    # 失敗したときに前回の結果（古い arg-id のスコア）が集計へ混ざらないよう、先に消しておく
    for filename in (STANCES_FILENAME, SUMMARY_FILENAME):
        stale_path = f"{output_base_dir}/{dataset}/{filename}"
        if os.path.exists(stale_path):
            os.remove(stale_path)

    arguments = pl.read_csv(f"{output_base_dir}/{dataset}/args.csv", infer_schema_length=0)
    arg_ids = [str(value) for value in arguments["arg-id"].to_list()]
    texts = [str(value) for value in arguments["argument"].to_list()]
    update_progress(config, total=len(arg_ids))

    scores = score_batch(
        arg_ids,
        texts,
        prompt,
        target,
        model,
        workers,
        provider,
        config.get("local_llm_address"),
        config,
        timeout_seconds,
        user_api_key,
        on_progress=lambda count: update_progress(config, incr=count),
    )

    write_stances(f"{output_base_dir}/{dataset}/{STANCES_FILENAME}", arg_ids, scores)
    summary = build_summary(scores, provider=provider, model=model, target=target)
    with open(f"{output_base_dir}/{dataset}/{SUMMARY_FILENAME}", "w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
