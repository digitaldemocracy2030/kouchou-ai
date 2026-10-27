"""429 を受けたら送る側が速さを落として送り直し、分析を止めない。

以前は SDK とプロバイダ関数の再試行（数秒〜20 秒で 3 回）を使い切ると、その回答が失敗になり、
workers=30 で 1000 件を流すと Azure の TPM 上限で抽出全体が止まっていた。
"""

import importlib
import threading
import time

import httpx
import openai
import pytest

from analysis_core.services import llm, rate_limit
from analysis_core.services.rate_limit import AdaptiveConcurrencyLimiter

extraction = importlib.import_module("analysis_core.steps.extraction")


@pytest.fixture(autouse=True)
def fresh_limiter():
    rate_limit.reset_rate_limiter()
    yield
    rate_limit.reset_rate_limiter()


def _rate_limit_error(headers=None, code="rate_limit_exceeded"):
    request = httpx.Request("POST", "https://example.invalid/openai/deployments/d/chat/completions")
    response = httpx.Response(429, request=request, headers=headers or {})
    return openai.RateLimitError("Error code: 429", response=response, body={"code": code, "message": "too many"})


def test_waits_retry_after_and_resends(monkeypatch):
    sleeps = []
    monkeypatch.setattr(rate_limit.time, "sleep", sleeps.append)
    calls = {"count": 0}

    def fn():
        calls["count"] += 1
        if calls["count"] == 1:
            raise _rate_limit_error({"retry-after": "3"})
        return "ok"

    assert rate_limit.call_with_rate_limit(fn) == "ok"
    assert calls["count"] == 2
    assert sleeps == [3.0]


def test_retry_after_ms_is_preferred():
    error = _rate_limit_error({"retry-after-ms": "1500", "retry-after": "9"})
    assert rate_limit.retry_after_seconds(error) == 1.5


def test_backoff_without_retry_after_is_bounded(monkeypatch):
    sleeps = []
    monkeypatch.setattr(rate_limit.time, "sleep", sleeps.append)
    calls = {"count": 0}

    def fn():
        calls["count"] += 1
        if calls["count"] <= 8:
            raise _rate_limit_error()
        return "ok"

    assert rate_limit.call_with_rate_limit(fn) == "ok"
    assert len(sleeps) == 8
    assert all(0 < s <= rate_limit.RATE_LIMIT_MAX_BACKOFF_SECONDS * 1.5 for s in sleeps)


def test_insufficient_quota_is_not_retried(monkeypatch):
    monkeypatch.setattr(rate_limit.time, "sleep", lambda s: pytest.fail("must not wait"))

    def fn():
        raise _rate_limit_error(code="insufficient_quota")

    with pytest.raises(openai.RateLimitError):
        rate_limit.call_with_rate_limit(fn)


def test_gives_up_after_max_wait(monkeypatch):
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_MAX_WAIT_SECONDS", 0)
    monkeypatch.setattr(rate_limit.time, "sleep", lambda s: None)

    def fn():
        raise _rate_limit_error({"retry-after": "1"})

    with pytest.raises(openai.RateLimitError):
        rate_limit.call_with_rate_limit(fn)


def test_other_errors_are_raised_without_retry():
    calls = {"count": 0}

    def fn():
        calls["count"] += 1
        raise ValueError("bad response")

    with pytest.raises(ValueError):
        rate_limit.call_with_rate_limit(fn)
    assert calls["count"] == 1


def test_limiter_halves_on_429_and_recovers():
    now = {"t": 0.0}
    limiter = AdaptiveConcurrencyLimiter(clock=lambda: now["t"])
    for _ in range(8):
        limiter.acquire()
    limiter.release("rate_limited")  # 8 件同時のときに 429
    assert limiter.limit == 4
    limiter.release("rate_limited")  # 同じ時刻に続けて返った 429 では下げない
    assert limiter.limit == 4
    now["t"] += rate_limit.RATE_LIMIT_DECREASE_INTERVAL_SECONDS
    limiter.release("rate_limited")  # 6 件同時のときに 429（間隔をあけた後）
    assert limiter.limit == 3
    for _ in range(5):
        limiter.release("ok")
    # 成功が limit 件続くたびに 1 ずつ戻す
    assert limiter.limit == 4
    for _ in range(4 + 5 + 6 + 7 + 8):
        limiter.acquire()
        limiter.release("ok")
    # 最大の同時実行数（8）を超えたら制限を外す
    assert limiter.limit is None


def test_limiter_blocks_beyond_limit():
    limiter = AdaptiveConcurrencyLimiter()
    limiter.acquire()
    limiter.acquire()
    limiter.release("rate_limited")  # 2 件同時で 429 → 上限 1
    assert limiter.limit == 1
    entered = threading.Event()

    def worker():
        limiter.acquire()
        entered.set()

    thread = threading.Thread(target=worker)
    thread.start()
    assert not entered.wait(0.1)  # まだ 1 件実行中なので入れない
    limiter.release("ok")
    assert entered.wait(1)
    thread.join()


def test_request_to_chat_ai_resends_after_429(monkeypatch):
    monkeypatch.setattr(rate_limit.time, "sleep", lambda s: None)
    calls = {"count": 0}

    def azure(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise _rate_limit_error({"retry-after": "1"})
        return '{"ok": true}', 1, 1, 2

    monkeypatch.setattr(llm, "request_to_azure_chatcompletion", azure)
    assert llm.request_to_chat_ai([{"role": "user", "content": "hi"}], provider="azure")[0] == '{"ok": true}'
    assert calls["count"] == 2


def test_extraction_with_many_workers_completes_under_rate_limit(monkeypatch):
    """同時に 5 件を超えると 429 を返すプロバイダに workers=30 で流しても、1 件も失敗せずに完走する。"""
    capacity = 5
    state = {"in_flight": 0, "peak": 0, "rejected": 0}
    lock = threading.Lock()

    def azure(messages, *args, **kwargs):
        with lock:
            state["in_flight"] += 1
            over = state["in_flight"] > capacity
            if over:
                state["rejected"] += 1
            else:
                state["peak"] = max(state["peak"], state["in_flight"])
        try:
            if over:
                raise _rate_limit_error({"retry-after-ms": "5"})
            time.sleep(0.005)
            return '{"extractedOpinionList": ["' + messages[-1]["content"] + '"]}', 1, 1, 2
        finally:
            with lock:
                state["in_flight"] -= 1

    monkeypatch.setattr(llm, "request_to_azure_chatcompletion", azure)
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_DECREASE_INTERVAL_SECONDS", 0)
    comments = [f"c{i}" for i in range(200)]
    results = extraction.extract_batch(comments, "p", "m", 30, provider="azure", config={})
    assert results == [[c] for c in comments]
    assert state["rejected"] > 0  # 429 は実際に起きた
    assert state["peak"] <= capacity
