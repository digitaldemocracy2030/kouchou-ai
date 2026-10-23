"""抽出・意見分類を workers 本のプールで回すことのテスト。

以前は workers 件ずつのバッチの全件完了を待ってから次のバッチを投入していたため、
1 件の遅い応答が他の worker を止めていた。空いた worker にはすぐ次を渡す。
結果の順序（args.csv / relations.csv / 分類 CSV の行順）と、失敗時の挙動
（新しい要求は出さず、実行中の要求の完了を待ってから中断し、成果物を書かない）は変えない。
"""

import importlib
import json
import threading
import time

import polars as pl
import pytest

extraction = importlib.import_module("analysis_core.steps.extraction")
classification = importlib.import_module("analysis_core.steps.opinion_classification")


def _setup_extraction(tmp_path, bodies, workers):
    inputs = tmp_path / "inputs"
    outputs = tmp_path / "outputs"
    inputs.mkdir()
    (outputs / "report").mkdir(parents=True)
    pl.DataFrame({"comment-id": [f"c{i}" for i in range(len(bodies))], "comment-body": bodies}).write_csv(
        str(inputs / "input.csv")
    )
    return {
        "input": "input",
        "output_dir": "report",
        "provider": "openai",
        "_input_base_dir": str(inputs),
        "_output_base_dir": str(outputs),
        "extraction": {"model": "m", "prompt": "p", "workers": workers, "limit": len(bodies), "properties": []},
    }


@pytest.fixture
def progress_calls(monkeypatch):
    calls = []
    monkeypatch.setattr(extraction, "update_progress", lambda config, **kw: calls.append(kw))
    monkeypatch.setattr(classification, "update_progress", lambda config, **kw: calls.append(kw))
    return calls


class _Concurrency:
    def __init__(self):
        self.lock = threading.Lock()
        self.current = 0
        self.max = 0

    def __enter__(self):
        with self.lock:
            self.current += 1
            self.max = max(self.max, self.current)

    def __exit__(self, *exc):
        with self.lock:
            self.current -= 1


class TestExtractionPool:
    def test_free_worker_takes_next_comment_while_slow_one_is_running(self, tmp_path, monkeypatch, progress_calls):
        """workers=2 で c0 が遅いとき、c1 が終わった worker が c2 を始める（c0 の完了を待たない）。"""
        c2_started = threading.Event()
        observed = {}

        def extract(text, *args):
            if text == "slow":
                observed["c2_started_while_slow_running"] = c2_started.wait(timeout=3)
            if text == "third":
                c2_started.set()
            return [f"意見 {text}"], 2, 1, 3

        monkeypatch.setattr(extraction, "extract_arguments", extract)
        config = _setup_extraction(tmp_path, ["slow", "fast", "third", "fourth"], workers=2)
        extraction.extraction(config)

        assert observed["c2_started_while_slow_running"] is True

    def test_output_order_matches_input_order_regardless_of_completion_order(
        self, tmp_path, monkeypatch, progress_calls
    ):
        n = 9

        def extract(text, *args):
            index = int(text.split("-")[1])
            time.sleep(0.01 * (n - index))  # 後ろの回答ほど先に終わる
            return [f"{text} の意見 A", f"{text} の意見 B"], 2, 1, 3

        monkeypatch.setattr(extraction, "extract_arguments", extract)
        config = _setup_extraction(tmp_path, [f"body-{i}" for i in range(n)], workers=3)
        extraction.extraction(config)

        out = tmp_path / "outputs" / "report"
        args = pl.read_csv(str(out / "args.csv"))
        relations = pl.read_csv(str(out / "relations.csv"))
        expected_ids = [f"Ac{i}_{j}" for i in range(n) for j in range(2)]
        assert args["arg-id"].to_list() == expected_ids
        assert args["argument"].to_list() == [f"body-{i} の意見 {x}" for i in range(n) for x in "AB"]
        assert relations["arg-id"].to_list() == expected_ids
        assert relations["comment-id"].to_list() == [f"c{i}" for i in range(n) for _ in range(2)]
        assert config["total_token_usage"] == 3 * n
        # 進捗は全件分だけ進み、更新は workers 件ごとにまとめる（1 件ごとに状態ファイルを書かない）
        increments = [call["incr"] for call in progress_calls if "incr" in call]
        assert sum(increments) == n
        assert len(increments) <= n // 3 + 1

    def test_in_flight_requests_never_exceed_workers(self, tmp_path, monkeypatch, progress_calls):
        concurrency = _Concurrency()

        def extract(text, *args):
            with concurrency:
                time.sleep(0.005)
            return [text], 0, 0, 0

        monkeypatch.setattr(extraction, "extract_arguments", extract)
        extraction.extraction(_setup_extraction(tmp_path, [f"b{i}" for i in range(40)], workers=4))
        assert 1 < concurrency.max <= 4

    def test_failure_stops_new_requests_and_waits_for_in_flight(self, tmp_path, monkeypatch, progress_calls):
        """失敗を検知したら新しい要求は出さない。実行中の要求は完了を待ってトークンを集計し、中断する。"""
        called = []
        lock = threading.Lock()

        def extract(text, *args):
            with lock:
                called.append(text)
            if text == "bad":
                raise RuntimeError("private error")
            time.sleep(0.2)
            return [text], 2, 1, 3

        monkeypatch.setattr(extraction, "extract_arguments", extract)
        config = _setup_extraction(tmp_path, ["bad", "in-flight", "never-1", "never-2", "never-3"], workers=2)
        with pytest.raises(extraction.ExtractionBatchError) as error:
            extraction.extraction(config)

        assert sorted(called) == ["bad", "in-flight"]
        assert error.value.failures == {0: "RuntimeError"}
        assert "c0" in str(error.value)
        assert "private" not in str(error.value)
        assert config["total_token_usage"] == 3
        out = tmp_path / "outputs" / "report"
        assert not (out / "args.csv").exists()
        assert not (out / "relations.csv").exists()
        diagnostics = tmp_path / "diagnostics" / "report-extraction.jsonl"
        records = [json.loads(line) for line in diagnostics.read_text(encoding="utf-8").splitlines()]
        assert records == [{"comment_id": "c0", "comment": "bad", "status": "error", "error_type": "RuntimeError"}]


class TestOpinionClassificationPool:
    def _config(self, tmp_path, texts, workers):
        out = tmp_path / "report"
        out.mkdir()
        pl.DataFrame({"arg-id": [f"A{i}_0" for i in range(len(texts))], "argument": texts}).write_csv(out / "args.csv")
        return {
            "output_dir": "report",
            "_output_base_dir": str(tmp_path),
            "provider": "local",
            "opinion_classification": {"model": "m", "prompt": "p", "workers": workers, "labels": ["question"]},
        }

    def test_free_worker_takes_next_argument_while_slow_one_is_running(self, tmp_path, monkeypatch, progress_calls):
        third_started = threading.Event()
        observed = {}

        def classify(text, *args):
            if text == "slow":
                observed["third_started_while_slow_running"] = third_started.wait(timeout=3)
            if text == "third":
                third_started.set()
            return {"question": text == "slow"}, 2, 1, 3

        monkeypatch.setattr(classification, "classify_argument", classify)
        config = self._config(tmp_path, ["slow", "fast", "third", "fourth"], workers=2)
        classification.opinion_classification(config)

        assert observed["third_started_while_slow_running"] is True
        frame = pl.read_csv(tmp_path / "report" / "opinion_classifications.csv", infer_schema_length=0)
        assert frame["arg-id"].to_list() == ["A0_0", "A1_0", "A2_0", "A3_0"]
        assert frame["question"].to_list() == ["yes", "no", "no", "no"]
        assert config["total_token_usage"] == 12
        assert sum(call["incr"] for call in progress_calls if "incr" in call) == 4

    def test_failure_stops_new_requests(self, tmp_path, monkeypatch, progress_calls):
        called = []
        lock = threading.Lock()

        def classify(text, *args):
            with lock:
                called.append(text)
            if text == "bad":
                raise RuntimeError("private")
            time.sleep(0.2)
            return {"question": False}, 2, 1, 3

        monkeypatch.setattr(classification, "classify_argument", classify)
        config = self._config(tmp_path, ["bad", "in-flight", "never-1", "never-2"], workers=2)
        with pytest.raises(classification.ClassificationBatchError) as error:
            classification.opinion_classification(config)

        assert sorted(called) == ["bad", "in-flight"]
        assert error.value.failures == {"A0_0": "RuntimeError"}
        assert config["total_token_usage"] == 3
        assert not (tmp_path / "report" / "opinion_classifications.csv").exists()
