import json
import logging
import os
import re
from pathlib import Path

import openai
import polars as pl
from pydantic import BaseModel, Field, ValidationError
from tqdm import tqdm

from analysis_core.core import update_progress
from analysis_core.core.utils import read_input_csv
from analysis_core.services.error_summary import summarize_exception
from analysis_core.services.llm import LLMSafetyBlockError, request_to_chat_ai
from analysis_core.services.parse_json_list import parse_extraction_response
from analysis_core.services.timeouts import DEFAULT_REQUEST_TIMEOUT_SECONDS, resolve_timeout
from analysis_core.steps._pool import iter_pool_completed

COMMA_AND_SPACE_AND_RIGHT_BRACKET = re.compile(r",\s*(\])")
EXTRACTION_WAIT_TIMEOUT_SECONDS = DEFAULT_REQUEST_TIMEOUT_SECONDS
# 形式不正・途中切れの応答を受けたときに、同じ回答を送り直す回数の上限（初回を含む）。
EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS = 3


class ExtractionResponse(BaseModel):
    extractedOpinionList: list[str] = Field(..., description="抽出した意見のリスト")


# 失敗の型名から、管理画面でエラーを読む人向けの説明を引く。理由の詳細（伏せ字済み）は分析ログにある。
FAILURE_EXPLANATIONS = {
    "AuthenticationError": "API キーが無効です",
    "PermissionDeniedError": "API キーにこのモデルを使う権限がありません",
    "NotFoundError": "モデル（Azure ではデプロイ名）が見つかりません",
    "RateLimitError": "API の利用上限に達しました。時間をおくか、並列数を下げて再実行してください",
    "BadRequestError": "API が要求を受け付けませんでした（モデル名や設定の誤りなど）",
    "APITimeoutError": "API の応答が時間内に返りませんでした",
    "APIConnectionError": "API に接続できませんでした",
    "InternalServerError": "API 側でエラーが起きました。時間をおいて再実行してください",
    "LLMRefusalError": "モデルが回答を拒否しました",
    "ValueError": "LLM の応答を解釈できませんでした",
    "ValidationError": "LLM の応答を解釈できませんでした",
    "LengthFinishReasonError": "LLM の応答が途中で切れました",
}


class ExtractionBatchError(RuntimeError):
    """A batch contains failed responses and must not reach downstream analysis."""

    def __init__(self, failures, comment_ids=None):
        self.failures = failures
        identifiers = {comment_ids[i] if comment_ids is not None else i: reason for i, reason in failures.items()}
        reasons = "、".join(
            f"{name}（{FAILURE_EXPLANATIONS[name]}）" if name in FAILURE_EXPLANATIONS else name
            for name in sorted(set(failures.values()))
        )
        super().__init__(
            f"意見抽出に失敗した回答が{len(failures)}件あります。分析を中断しました。理由: {reasons}。"
            f" ({'回答ID' if comment_ids is not None else 'batch index'} / error: {identifiers})"
            " 詳しい理由は分析ログにあります。"
        )


def _validate_property_columns(property_columns: list[str], comments: pl.DataFrame) -> None:
    """Raise ValueError if any required property column is missing from the DataFrame."""
    if not all(property in comments.columns for property in property_columns):
        raise ValueError(f"Properties {property_columns} not found in comments. Columns are {comments.columns}")


def _filter_empty_comments(comments: pl.DataFrame) -> pl.DataFrame:
    """Filter out rows where comment-body is null or contains only whitespace.

    Logs the number of filtered rows and raises RuntimeError if all comments are empty.
    """
    original_count = len(comments)
    normalized_comment_body = pl.col("comment-body").cast(pl.String, strict=False).fill_null("")
    filtered = comments.filter(
        normalized_comment_body.str.strip_chars() != ""
    )
    filtered_count = original_count - len(filtered)
    if filtered_count > 0:
        logging.info("Filtered out %d empty/whitespace-only comments out of %d", filtered_count, original_count)
    if len(filtered) == 0:
        raise RuntimeError("All comments are empty or whitespace-only after filtering")
    return filtered


def filter_empty_comments(comments: pl.DataFrame) -> pl.DataFrame:
    """Public wrapper for filtering empty/whitespace-only comments before LLM processing."""
    return _filter_empty_comments(comments)


def extraction(config):
    """Extract arguments from comments using LLM, skipping empty/whitespace-only entries."""
    dataset = config["output_dir"]
    output_base_dir = config.get("_output_base_dir", "outputs")
    input_base_dir = config.get("_input_base_dir", "inputs")
    path = f"{output_base_dir}/{dataset}/args.csv"
    model = config["extraction"]["model"]
    prompt = config["extraction"]["prompt"]
    workers = config["extraction"]["workers"]
    limit = config["extraction"]["limit"]
    property_columns = config["extraction"]["properties"]
    timeout_seconds = resolve_timeout(config["extraction"].get("timeout_seconds"))
    user_api_key = config.get("user_api_key") or os.getenv("USER_API_KEY")

    if "provider" not in config:
        raise RuntimeError("provider is not set")
    provider = config["provider"]

    # カラム名だけを読み込み、必要なカラムが含まれているか確認する
    input_path = f"{input_base_dir}/{config['input']}.csv"
    comments = read_input_csv(input_path, n_rows=0)
    _validate_property_columns(property_columns, comments)
    # エラーが出なかった場合、すべての行を読み込む
    comments = read_input_csv(input_path, columns=["comment-id", "comment-body"] + config["extraction"]["properties"])

    # 空文字列・空白のみのコメントを除外する (#583)
    comments = _filter_empty_comments(comments)

    comment_ids = comments["comment-id"].to_list()[:limit]
    if len(comments) > len(comment_ids):
        # 切り詰めた残りの回答は分析されない。CLI で limit を省略すると spec の既定値（1000）が使われるので、
        # 黙って落とさずに件数を知らせる（管理画面からの実行は limit=入力件数なので起きない）。
        logging.warning(
            "空でない回答 %d件のうち、先頭の %d件だけを分析します（extraction.limit=%d）。"
            "残りの %d件は分析されません。全件を分析するには extraction.limit を回答数以上に設定してください"
            "（省略時の既定値は 1000）。",
            len(comments),
            len(comment_ids),
            limit,
            len(comments) - len(comment_ids),
        )
    comments_lookup = {row["comment-id"]: row for row in comments.iter_rows(named=True)}
    update_progress(config, total=len(comment_ids))

    # Keep original comments outside the published outputs tree.
    diagnostics_dir = Path(output_base_dir).resolve().parent / "diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_path = diagnostics_dir / f"{Path(dataset).name}-extraction.jsonl"
    fd = os.open(diagnostics_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.close(fd)
    logging.info("抽出診断（原文を含む非公開ファイル）: %s", diagnostics_path)

    argument_map = {}
    relation_rows = []

    # 全回答を 1 つのプール（workers 本）で回す。workers 件ずつのバッチの完了を待つと、
    # バッチ内で最も遅い 1 件の応答が終わるまで他の worker が遊ぶ。
    batch_inputs = [comments_lookup[id]["comment-body"] for id in comment_ids]
    with tqdm(total=len(comment_ids)) as progress_bar:

        def on_progress(count):
            progress_bar.update(count)
            update_progress(config, incr=count)

        all_results = extract_batch(
            batch_inputs,
            prompt,
            model,
            workers,
            provider,
            config.get("local_llm_address"),
            config,
            timeout_seconds,
            user_api_key,
            comment_ids=comment_ids,
            diagnostics_path=diagnostics_path,
            on_progress=on_progress,
        )

    # 結果は入力順に並んでいるので、args.csv / relations.csv の行順は回答の順のまま
    for comment_id, extracted_args in zip(comment_ids, all_results, strict=True):
        for j, arg in enumerate(extracted_args):
            # 同じ文面でも回答ごとに別の意見として扱う。回答をまたいでまとめると、
            # 集計で意見1件に回答1件分の属性・URLしか残らず、他の回答者の帰属が消える。
            # 同じ回答の中で同じ文面が繰り返されたときは 1 件にまとめ、relation も 1 行だけにする。
            # key に comment_id が入っているので、既出なら同じ (arg-id, comment-id) の行は記録済み。
            key = (comment_id, arg)
            if key in argument_map:
                continue
            arg_id = f"A{comment_id}_{j}"
            argument_map[key] = {
                "arg-id": arg_id,
                "argument": arg,
            }
            relation_rows.append(
                {
                    "arg-id": arg_id,
                    "comment-id": comment_id,
                }
            )

    # DataFrame化
    results = pl.DataFrame(list(argument_map.values()))
    relation_df = pl.DataFrame(relation_rows)

    if len(results) == 0:
        blocked_ids = config.get("extraction_blocked_comment_ids") or []
        # 全件が止められたときだけフィルタのせいと言う。止められなかった回答も意見 0 件なら、通常の空の結果として扱う
        if blocked_ids and len(blocked_ids) == len(comment_ids):
            raise RuntimeError(
                f"抽出できた意見がありません。コンテンツフィルタに止められた回答が{len(blocked_ids)}件あります。"
            )
        raise RuntimeError("result is empty, maybe bad prompt")

    results.write_csv(path)
    # comment-idとarg-idの関係を保存
    relation_df.write_csv(f"{output_base_dir}/{dataset}/relations.csv")


def extract_batch(
    batch,
    prompt,
    model,
    workers,
    provider="openai",
    local_llm_address=None,
    config=None,
    timeout_seconds=EXTRACTION_WAIT_TIMEOUT_SECONDS,
    user_api_key=None,
    comment_ids=None,
    diagnostics_path=None,
    on_progress=None,
):
    """Run argument extraction concurrently with a pool of ``workers`` threads.

    空いた worker にはすぐ次の回答を渡し、結果は入力順に返す。
    失敗を検知したら新しい要求は出さず、実行中の要求の完了を待ってから
    ExtractionBatchError を送出する（完了した要求のトークンは集計し、診断ファイルにも書く）。
    ただしプロバイダのコンテンツフィルタに止められた回答（LLMSafetyBlockError）は、送り直しても
    同じ結果になる回答ごとの拒否なので、中断せずにその回答だけを除外する。除外した回答は
    警告ログと診断ファイル（status=blocked）に残し、件数と回答IDを config に書く。
    トークン集計・進捗（on_progress）・診断ファイルへの追記は、workers 件の完了ごとに
    呼び出し元のスレッドでまとめて行う。
    """
    results = [[] for _ in range(len(batch))]
    failures = {}
    blocked = set()
    flush_every = max(1, int(workers))
    pending = {"count": 0, "input": 0, "output": 0, "total": 0, "diagnostics": []}

    def flush():
        if pending["count"] == 0:
            return
        if config is not None:
            config["total_token_usage"] = config.get("total_token_usage", 0) + pending["total"]
            config["token_usage_input"] = config.get("token_usage_input", 0) + pending["input"]
            config["token_usage_output"] = config.get("token_usage_output", 0) + pending["output"]
            print(
                f"Extraction batch: input={pending['input']}, output={pending['output']}, total={pending['total']} tokens"
            )
        if diagnostics_path is not None and pending["diagnostics"]:
            with open(diagnostics_path, "a", encoding="utf-8") as diagnostic_file:
                for index in sorted(pending["diagnostics"]):
                    record = {
                        "comment_id": comment_ids[index] if comment_ids is not None else index,
                        "comment": batch[index],
                        "status": "error" if index in failures else "blocked" if index in blocked else "empty",
                        "error_type": failures.get(index, LLMSafetyBlockError.__name__ if index in blocked else None),
                    }
                    diagnostic_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        if on_progress is not None:
            on_progress(pending["count"])
        pending.update(count=0, input=0, output=0, total=0, diagnostics=[])

    def run(input):
        return extract_arguments(input, prompt, model, provider, local_llm_address, timeout_seconds, user_api_key)

    # 1 リクエストの上限は各プロバイダの SDK に渡す timeout_seconds が担う。
    # プール側で同じ値の待機上限を重ねると、Flex (最大 900 秒) や SDK 内部の再試行で
    # timeout_seconds を超えて成功した応答まで TimeoutError として捨ててしまう。
    for i, future in iter_pool_completed(run, batch, workers, stop=lambda: bool(failures)):
        try:
            result = future.result()
            if isinstance(result, tuple) and len(result) == 4:
                items, token_input, token_output, token_total = result
                results[i] = items
                pending["input"] += token_input
                pending["output"] += token_output
                pending["total"] += token_total
            else:
                results[i] = result
        except LLMSafetyBlockError as e:
            blocked.add(i)
            logging.warning(
                "コンテンツフィルタに止められたため、この回答を分析から除外します。%s %s: %s",
                "回答ID" if comment_ids is not None else "batch index",
                comment_ids[i] if comment_ids is not None else i,
                summarize_exception(e, (user_api_key,)),
            )
        except Exception as e:
            # status と診断には分類名（型名）だけを残し、理由は秘密情報を伏せて通常ログに出す
            failures[i] = type(e).__name__
            logging.error(
                "意見抽出に失敗しました。%s %s: %s",
                "回答ID" if comment_ids is not None else "batch index",
                comment_ids[i] if comment_ids is not None else i,
                summarize_exception(e, (user_api_key,)),
            )
        if i in failures or i in blocked or not results[i]:
            pending["diagnostics"].append(i)
        pending["count"] += 1
        if pending["count"] >= flush_every:
            flush()
    flush()

    # 除外の記録は、ほかの失敗で中断するときも残す（再実行で同じ config を使うときに前回の値も残さない）
    if config is not None:
        config.pop("extraction_blocked_comment_ids", None)
    if blocked:
        blocked_ids = [comment_ids[i] if comment_ids is not None else i for i in sorted(blocked)]
        logging.warning(
            "コンテンツフィルタに止められた %d件の回答を分析から除外しました（%s: %s）",
            len(blocked_ids),
            "回答ID" if comment_ids is not None else "batch index",
            blocked_ids,
        )
        if config is not None:
            config["extraction_blocked_comment_ids"] = blocked_ids
    if failures:
        raise ExtractionBatchError(failures, comment_ids)
    return results


def extract_arguments(
    input,
    prompt,
    model,
    provider="openai",
    local_llm_address=None,
    timeout_seconds=EXTRACTION_WAIT_TIMEOUT_SECONDS,
    user_api_key=None,
):
    """Send a single comment to the LLM and return extracted arguments.

    応答が形式不正・途中切れのとき（JSON の不正・スキーマ違反・finish_reason=length）は、
    この回答だけを EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS 回まで送り直す。200 で返った
    応答の中身の不正は SDK も再試行しないため、1 件の不調で抽出全体が中断していた。
    API エラーと、拒否・コンテンツフィルタは送り直しても変わらないか SDK が扱うので、そのまま送出する。
    拒否・コンテンツフィルタは経路によって返り方が違う。OpenAI・Azure・OpenRouter の構造化出力
    （parse）経路では内容なし（None）か SDK の例外で返り、OpenRouter の JSON fallback 経路と
    ローカル LLM 経路では本文（「I'm sorry...」など）や空文字列で返る。後者は JSON の括弧を
    含まない本文として見分ける（_looks_like_json_attempt）。送り直した分のトークンも課金されて
    いるので合計に含める。
    """
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": input},
    ]
    total_input = total_output = total_tokens = 0
    for attempt in range(1, EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS + 1):
        try:
            response, token_input, token_output, token_total = request_to_chat_ai(
                messages=messages,
                model=model,
                is_json=False,
                json_schema=ExtractionResponse,
                provider=provider,
                local_llm_address=local_llm_address,
                user_api_key=user_api_key or os.getenv("USER_API_KEY"),
                timeout_seconds=timeout_seconds,
            )
        except (ValidationError, openai.LengthFinishReasonError) as error:
            # SDK の構造化出力の parse が、途中で切れた・スキーマに合わない応答を弾いた
            token_input, token_output, token_total = _token_usage_of_failed_completion(error)
            total_input += token_input
            total_output += token_output
            total_tokens += token_total
            if attempt >= EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS:
                raise
            _log_malformed_retry(error, attempt)
            continue

        total_input += token_input
        total_output += token_output
        total_tokens += token_total
        try:
            items = parse_extraction_response(response)
        except ValueError as error:
            # 内容が無い応答や、JSON を書こうとしていない本文（拒否・コンテンツフィルタの空応答）は
            # 送り直しても変わらないので、再試行しない
            if not _looks_like_json_attempt(response) or attempt >= EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS:
                raise
            _log_malformed_retry(error, attempt)
            continue
        items = list(filter(None, items))  # omit empty strings
        return items, total_input, total_output, total_tokens

    raise AssertionError("unreachable")  # pragma: no cover


def _looks_like_json_attempt(response: str | dict | None) -> bool:
    """応答が JSON を書こうとした形か（壊れていても送り直す価値があるか）。

    JSON fallback 経路やローカル LLM 経路の拒否・コンテンツフィルタは、括弧を含まない本文や空文字列で返る。
    これらは決定的に繰り返されるので、形式不正（途中切れ・スキーマ違反）と区別して送り直さない。
    """
    if response is None:
        return False
    if not isinstance(response, str):
        return True
    return "{" in response or "[" in response


def _token_usage_of_failed_completion(error: Exception) -> tuple[int, int, int]:
    """finish_reason=length で弾かれた応答の usage（取れない場合は 0）。"""
    usage = getattr(getattr(error, "completion", None), "usage", None)
    if usage is None:
        return 0, 0, 0
    return usage.prompt_tokens or 0, usage.completion_tokens or 0, usage.total_tokens or 0


def _log_malformed_retry(error: Exception, attempt: int) -> None:
    # 応答本文・原文は公開ログに出さない（例外の種類だけを残す）
    logging.warning(
        "意見抽出の応答を解釈できなかったため、同じ回答を送り直します（%s、%d/%d 回目）",
        type(error).__name__,
        attempt,
        EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS,
    )
