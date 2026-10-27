"""429（rate limit）を受けたときに、送る側が自分で速さを落として送り直すための共通処理。

LLM への要求は工程ごとに workers 本のスレッドで送る。workers がプロバイダの上限（TPM・RPM）を
超える速さになると 429 が返る。以前は SDK と各プロバイダ関数の再試行（数ミリ秒〜20 秒で計 9 回）を
使い切ると、その回答・クラスタが失敗として数えられ、分析全体が止まっていた。利用者に workers を
下げてもらうのではなく、送る側が自分で調整する:

1. 429 は失敗として数えず、待って同じ要求を送り直す。送り直すのはここだけにする（SDK の自動再試行は
   chat_http_client で止め、プロバイダ関数の再試行は持たない）。Azure の retry-after-ms は数ミリ秒で、
   それに従うと上限いっぱいのときに 429 を重ねるだけなので、最低 1 秒から倍々で待つ。
2. 429 を受けたら、すべての送り手がしばらく（RATE_LIMIT_PAUSE_SECONDS）新しい要求を出さない。
3. 同時に送る数を自動で増減する（AIMD）。429 を受けたら今の同時実行数の半分に下げ、成功が続いたら
   1 ずつ戻す。元の workers を超えたら制限を外す。
"""

from __future__ import annotations

import logging
import random
import threading
import time
from collections.abc import Callable
from typing import TypeVar

import httpx
import openai

T = TypeVar("T")

# 1 要求あたり、429 で待ち続ける時間の上限（秒）。これを超えたら 429 をそのまま送出する
RATE_LIMIT_MAX_WAIT_SECONDS = 900
# 送り直すまでの待ち時間（秒）。最低 RATE_LIMIT_MIN_BACKOFF_SECONDS から倍々にし、上限で頭打ちにする
RATE_LIMIT_MIN_BACKOFF_SECONDS = 1.0
RATE_LIMIT_MAX_BACKOFF_SECONDS = 60
# 429 を受けたあと、すべての送り手が新しい要求を出さない時間（秒）
RATE_LIMIT_PAUSE_SECONDS = 1.0
# 一度に返ってきた 429 で同時実行数を何段も下げないよう、下げる間隔をあける（秒）
RATE_LIMIT_DECREASE_INTERVAL_SECONDS = 5

# 待っても直らない 429（課金枠の不足など）。送り直さずに送出する
_NON_TRANSIENT_RATE_LIMIT_CODES = frozenset({"insufficient_quota"})


class AdaptiveConcurrencyLimiter:
    """同時に送る要求の数を、429 で半分に下げ、成功が続いたら 1 ずつ戻す。

    制限が無い（limit=None）あいだは、呼び出し側の workers がそのまま同時実行数になる。
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._cond = threading.Condition()
        self._clock = clock
        self._limit: int | None = None
        self._in_flight = 0
        self._peak = 0
        self._successes = 0
        self._last_decrease = float("-inf")
        self._pause_until = float("-inf")

    @property
    def limit(self) -> int | None:
        with self._cond:
            return self._limit

    def acquire(self) -> None:
        with self._cond:
            while True:
                pause = self._pause_until - self._clock()
                if pause > 0:
                    self._cond.wait(pause)
                elif self._limit is not None and self._in_flight >= self._limit:
                    self._cond.wait()
                else:
                    break
            self._in_flight += 1
            self._peak = max(self._peak, self._in_flight)

    def release(self, outcome: str) -> None:
        """outcome: "ok"（成功）、"rate_limited"（429）、"error"（その他の失敗。増減しない）"""
        with self._cond:
            concurrent = self._in_flight
            self._in_flight -= 1
            if outcome == "rate_limited":
                now = self._clock()
                self._pause_until = max(self._pause_until, now + RATE_LIMIT_PAUSE_SECONDS)
                if now - self._last_decrease >= RATE_LIMIT_DECREASE_INTERVAL_SECONDS:
                    new_limit = max(1, concurrent // 2)
                    if self._limit is None or new_limit < self._limit:
                        logging.warning(
                            "rate limit (429) を受けたため、同時に送る要求を %d 件に下げます（いま %d 件）",
                            new_limit,
                            concurrent,
                        )
                        self._limit = new_limit
                    self._last_decrease = now
                    self._successes = 0
            elif outcome == "ok" and self._limit is not None:
                self._successes += 1
                if self._successes >= self._limit:
                    self._successes = 0
                    self._limit += 1
                    if self._limit > self._peak:
                        logging.info("rate limit が収まったため、同時に送る要求の制限を外します")
                        self._limit = None
            self._cond.notify_all()


_limiter = AdaptiveConcurrencyLimiter()

_http_client: httpx.Client | None = None
_http_client_lock = threading.Lock()


def _on_chat_response(response: httpx.Response) -> None:
    if response.status_code == 429:
        # 送り直しは call_with_rate_limit だけが行う。SDK の自動再試行は retry-after-ms（Azure では数ミリ秒）
        # だけ待ってすぐ送り直すので、上限いっぱいのときは 429 を重ねるだけになる。SDK はこのヘッダを見て再試行しない
        response.headers["x-should-retry"] = "false"


def chat_http_client() -> httpx.Client:
    """チャットの要求に使う HTTP クライアント（プロセスで 1 つ）。429 の扱いを call_with_rate_limit に寄せる。"""
    global _http_client
    with _http_client_lock:
        if _http_client is None:
            _http_client = openai.DefaultHttpxClient(event_hooks={"response": [_on_chat_response]})
        return _http_client


def reset_rate_limiter() -> None:
    """テスト用。プロセス全体の制限を初期状態に戻す。"""
    global _limiter
    _limiter = AdaptiveConcurrencyLimiter()


def is_transient_rate_limit(error: BaseException) -> bool:
    return isinstance(error, openai.RateLimitError) and getattr(error, "code", None) not in (
        _NON_TRANSIENT_RATE_LIMIT_CODES
    )


def retry_after_seconds(error: BaseException) -> float | None:
    """429 の応答ヘッダが知らせる待ち時間（秒）。無い・読めないときは None。"""
    headers = getattr(getattr(error, "response", None), "headers", None)
    if headers is None:
        return None
    for name, scale in (("retry-after-ms", 0.001), ("retry-after", 1.0)):
        value = headers.get(name)
        if value is None:
            continue
        try:
            seconds = float(value) * scale
        except (TypeError, ValueError):
            continue
        if seconds >= 0:
            return seconds
    return None


def call_with_rate_limit(fn: Callable[[], T]) -> T:
    """``fn`` を同時実行数の制限の下で呼び、429 なら待って送り直す。

    429 以外の例外と、待っても直らない 429（課金枠の不足）、待ち時間の上限を超えた 429 はそのまま送出する。
    """
    limiter = _limiter
    deadline = time.monotonic() + RATE_LIMIT_MAX_WAIT_SECONDS
    attempt = 0
    while True:
        limiter.acquire()
        try:
            result = fn()
        except openai.RateLimitError as error:
            limiter.release("rate_limited")
            remaining = deadline - time.monotonic()
            if not is_transient_rate_limit(error) or remaining <= 0:
                raise
            # ジッターつきの指数バックオフ（同時に待った要求が一斉に送り直さないように）。
            # retry-after がそれより長ければ従う
            backoff = min(RATE_LIMIT_MAX_BACKOFF_SECONDS, RATE_LIMIT_MIN_BACKOFF_SECONDS * 2**attempt)
            wait = max(retry_after_seconds(error) or 0.0, backoff * (0.5 + random.random()))
            wait = max(0.0, min(wait, RATE_LIMIT_MAX_BACKOFF_SECONDS, remaining))
            attempt += 1
            logging.warning(
                "rate limit (429) のため %.1f 秒待って送り直します（%d 回目、同時に送る要求の上限: %s）",
                wait,
                attempt,
                limiter.limit or "制限なし",
            )
            time.sleep(wait)
            continue
        except BaseException:
            limiter.release("error")
            raise
        limiter.release("ok")
        return result
