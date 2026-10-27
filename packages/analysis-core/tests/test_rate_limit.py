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
def fresh_limiter(monkeypatch):
    # 試験では一時停止を短くする（一時停止そのものを確かめるテストは自分で上書きする）
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_PAUSE_SECONDS", 0.01)
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
    now["t"] += rate_limit.RATE_LIMIT_PAUSE_SECONDS  # 429 のあとの一時停止が明けてから送る
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
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_MIN_BACKOFF_SECONDS", 0.01)
    comments = [f"c{i}" for i in range(200)]
    results = extraction.extract_batch(comments, "p", "m", 30, provider="azure", config={})
    assert results == [[c] for c in comments]
    assert state["rejected"] > 0  # 429 は実際に起きた
    assert state["peak"] <= capacity


def test_429_pauses_all_senders(monkeypatch):
    """1 本が 429 を受けたら、ほかの送り手も一時停止が明けるまで新しい要求を出さない。"""
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_PAUSE_SECONDS", 0.3)
    limiter = AdaptiveConcurrencyLimiter()
    limiter.acquire()
    limiter.release("rate_limited")
    t = time.monotonic()
    limiter.acquire()
    assert time.monotonic() - t >= 0.25


def test_backoff_ignores_millisecond_retry_after(monkeypatch):
    """Azure の retry-after-ms は数ミリ秒。それに従うと 429 を重ねるので、最低 1 秒は待つ。"""
    sleeps = []
    monkeypatch.setattr(rate_limit.time, "sleep", sleeps.append)
    monkeypatch.setattr(rate_limit.random, "random", lambda: 0.5)  # ジッターを 1 倍に固定
    calls = {"count": 0}

    def fn():
        calls["count"] += 1
        if calls["count"] <= 3:
            raise _rate_limit_error({"retry-after-ms": "6", "retry-after": "30"})
        return "ok"

    assert rate_limit.call_with_rate_limit(fn) == "ok"
    assert sleeps == [1.0, 2.0, 4.0]


def test_sdk_does_not_retry_429_itself(monkeypatch):
    """送り直しは call_with_rate_limit だけが行う。SDK の自動再試行（数ミリ秒で送り直す）を止める。"""
    from openai import AzureOpenAI

    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(429, headers={"retry-after-ms": "5"}, json={"error": {"code": "429", "message": "x"}})

    client = openai.DefaultHttpxClient(
        transport=httpx.MockTransport(handler), event_hooks={"response": [rate_limit._on_chat_response]}
    )
    azure = AzureOpenAI(
        api_key="k", azure_endpoint="https://example.invalid", api_version="2024-10-21", http_client=client
    )
    with pytest.raises(openai.RateLimitError):
        azure.chat.completions.create(model="d", messages=[{"role": "user", "content": "hi"}])
    assert len(requests) == 1


def test_provider_functions_do_not_retry_429_themselves(monkeypatch):
    """プロバイダ関数（Azure）は 429 をそのまま上げ、送り直しを call_with_rate_limit に任せる。"""
    from unittest.mock import MagicMock, patch

    monkeypatch.setenv("AZURE_CHATCOMPLETION_ENDPOINT", "https://example.invalid")
    monkeypatch.setenv("AZURE_CHATCOMPLETION_DEPLOYMENT_NAME", "dep")
    monkeypatch.setenv("AZURE_CHATCOMPLETION_API_KEY", "k")
    monkeypatch.setenv("AZURE_CHATCOMPLETION_VERSION", "2024-10-21")
    client = MagicMock()
    client.chat.completions.create.side_effect = _rate_limit_error()
    with patch.object(llm, "AzureOpenAI", return_value=client):
        with pytest.raises(openai.RateLimitError):
            llm.request_to_azure_chatcompletion([{"role": "user", "content": "hi"}])
    assert client.chat.completions.create.call_count == 1


def test_gemini_bypasses_shared_limiter(monkeypatch):
    """Gemini は 429 を独自に送り直すので、共通の枠と一時停止を通さない。"""
    monkeypatch.setattr(llm, "call_with_rate_limit", lambda fn: pytest.fail("Gemini must not use the shared limiter"))
    monkeypatch.setattr(llm, "request_to_gemini_chatcompletion", lambda *args, **kwargs: ("ok", 1, 1, 2))
    assert llm.request_to_chat_ai([{"role": "user", "content": "hi"}], provider="gemini")[0] == "ok"
