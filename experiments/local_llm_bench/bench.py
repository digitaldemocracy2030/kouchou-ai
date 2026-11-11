"""ローカル LLM で、レポート全体を作る時間とメモリを測る（#471 / #1195）

本物のローカル LLM（Ollama・llama.cpp など OpenAI 互換の接続先）につないで、広聴AIの CLI
（`python -m analysis_core`）でレポートを最後まで作り、次を CSV に 1 行ずつ足す。

- PC の情報（OS・CPU・コア数・メモリ）
- 完走したか、全体の時間、段ごとの時間（出力の hierarchical_status.json の completed_jobs）
- 分析のプロセス（子プロセスを含む）のメモリの最大値。LLM のサーバ（Ollama など）は別のプロセスなので含まない

使い方は README.md を参照。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = HERE.parents[1] / "apps" / "admin" / "public" / "sample_comments.csv"

try:  # 任意。あれば Windows でもメモリを測れ、メモリの総量も取れる
    import psutil
except ModuleNotFoundError:  # pragma: no cover - 環境による
    psutil = None


def read_comments(path: Path, column: str) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if column not in (reader.fieldnames or []):
            sys.exit(
                f"{path} に列 {column!r} がありません（列: {reader.fieldnames}）。--text-column で指定してください"
            )
        return [row[column].strip() for row in reader if (row.get(column) or "").strip()]


def cpu_name() -> str:
    name = platform.processor()
    if sys.platform.startswith("linux"):
        try:
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.lower().startswith(("model name", "hardware")):
                    return line.split(":", 1)[1].strip()
        except OSError:
            pass  # 読めない環境では次の lscpu で探す
        try:  # ARM などで /proc/cpuinfo に名前が無いとき
            out = subprocess.run(["lscpu"], capture_output=True, text=True).stdout
            for line in out.splitlines():
                if line.startswith("Model name:"):
                    return line.split(":", 1)[1].strip()
        except OSError:
            pass  # lscpu が無い環境では platform.processor() の値を使う
    elif sys.platform == "darwin":
        try:
            return subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True
            ).stdout.strip()
        except OSError:
            pass
    return name


def total_memory_gb() -> float | None:
    if psutil:
        return round(psutil.virtual_memory().total / 1e9, 1)
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return round(int(line.split()[1]) * 1024 / 1e9, 1)
    except OSError:
        pass  # 読めない環境ではメモリ量を記録しない（None）
    return None


def machine_info() -> dict:
    return {
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "cpu": cpu_name(),
        "logical_cpus": os.cpu_count(),
        "memory_gb": total_memory_gb(),
        "python": platform.python_version(),
    }


def run_and_watch(cmd: list[str], env: dict, log_path: Path) -> tuple[int, float, float | None]:
    """cmd を実行し、終了コード・経過秒・メモリの最大値（MB、子プロセスを含む）を返す"""
    peak = [0.0]
    start = time.monotonic()
    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(cmd, env=env, stdout=log, stderr=subprocess.STDOUT)
        stop = threading.Event()

        def sample():  # psutil があれば 0.5 秒ごとに、プロセスと子プロセスの RSS の合計を見る
            p = psutil.Process(proc.pid)
            while not stop.is_set():
                try:
                    rss = p.memory_info().rss + sum(c.memory_info().rss for c in p.children(recursive=True))
                    peak[0] = max(peak[0], rss / 1e6)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass  # 子プロセスが終わった直後などは次の回で測り直す
                stop.wait(0.5)

        watcher = threading.Thread(target=sample, daemon=True) if psutil else None
        if watcher:
            watcher.start()
        if hasattr(os, "wait4"):  # POSIX: 子プロセスの最大 RSS を OS から受け取る（Linux は KB、macOS は B）
            _, status, usage = os.wait4(proc.pid, 0)
            proc.returncode = os.waitstatus_to_exitcode(status)
            unit = 1e6 if sys.platform == "darwin" else 1e3
            peak[0] = max(peak[0], usage.ru_maxrss / unit)
        else:
            proc.wait()
        stop.set()
        if watcher:
            watcher.join()
    elapsed = time.monotonic() - start
    return proc.returncode, elapsed, (round(peak[0]) if peak[0] else None)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", required=True, help="接続先のモデル名（例: gemma4:e4b）")
    ap.add_argument(
        "--address", default="127.0.0.1:11434", help="ローカル LLM の接続先（既定: Ollama の 127.0.0.1:11434）"
    )
    ap.add_argument(
        "--n", type=int, action="append", required=True, help="件数。複数回指定すると順に測る（例: --n 100 --n 400）"
    )
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="意見の CSV（既定: 管理画面のサンプル 400 件）")
    ap.add_argument("--text-column", default="comment", help="意見の本文の列名（既定: comment）")
    ap.add_argument(
        "--reasoning-effort", default="", help="LOCAL_LLM_REASONING_EFFORT に渡す値（例: none）。空なら送らない"
    )
    ap.add_argument(
        "--workers", type=int, default=1, help="抽出の並列数（既定: 1。Ollama の既定の同時処理数に合わせる）"
    )
    ap.add_argument("--workdir", type=Path, default=Path("bench-work"), help="入力・設定・出力を置く場所")
    ap.add_argument("--out", type=Path, default=Path("bench-results.csv"), help="結果を足していく CSV")
    ap.add_argument("--note", default="", help="結果に残すメモ（GPU を切った方法など）")
    args = ap.parse_args()

    comments = read_comments(args.input, args.text_column)
    for n in args.n:
        if n > len(comments):
            sys.exit(
                f"{args.input} の意見は {len(comments)} 件で、--n {n} に足りません。もっと多い CSV を --input で渡してください"
            )

    info = machine_info()
    print("PC:", json.dumps(info, ensure_ascii=False))
    if not psutil and not hasattr(os, "wait4"):
        print("注意: psutil が無いのでメモリは測りません（pip install psutil）")

    env = dict(os.environ)
    env["LOCAL_LLM_REASONING_EFFORT"] = args.reasoning_effort
    if args.reasoning_effort:
        try:
            from analysis_core.services import llm
        except ImportError:
            sys.exit(
                "kouchou-ai-analysis-core が入っていません（pip install 'kouchou-ai-analysis-core[embeddings,clustering]'）"
            )
        if not hasattr(llm, "local_llm_reasoning_effort"):
            # 効いていない設定を結果の CSV に「適用した」として残さないよう、ここで止める
            sys.exit(
                "この analysis-core は LOCAL_LLM_REASONING_EFFORT に対応していません（#1193 より前）。"
                "--reasoning-effort を外すか、analysis-core を更新してください"
            )

    for sub in ("inputs", "configs", "outputs", "logs"):
        (args.workdir / sub).mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    for n in args.n:
        name = f"bench-{n}-{stamp}"
        with (args.workdir / "inputs" / f"{name}.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["comment-id", "comment-body"])
            for i, text in enumerate(comments[:n], 1):
                w.writerow([i, text])
        config = {
            "name": name,
            "question": "寄せられた意見にはどのようなものがありますか？",
            "input": name,
            "model": args.model,
            "provider": "local",
            "local_llm_address": args.address,
            "is_embedded_at_local": True,
            "extraction": {"workers": args.workers, "limit": n},
        }
        config_path = args.workdir / "configs" / f"{name}.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        cmd = [
            sys.executable, "-m", "analysis_core",
            "--config", str(config_path),
            "--input-dir", str(args.workdir / "inputs"),
            "--output-dir", str(args.workdir / "outputs"),
            "--skip-interaction", "--without-html",
        ]  # fmt: skip
        print(f"\n== {n} 件: {args.model}（reasoning_effort={args.reasoning_effort or '送らない'}）")
        code, elapsed, peak_mb = run_and_watch(cmd, env, args.workdir / "logs" / f"{name}.log")

        status_path = args.workdir / "outputs" / name / "hierarchical_status.json"
        status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
        steps = {j.get("step"): round(j.get("duration") or 0, 1) for j in status.get("completed_jobs", [])}
        ok = code == 0 and status.get("status") == "completed"
        print(f"   {'完走' if ok else '失敗'}  {elapsed / 60:.1f} 分  メモリ最大 {peak_mb} MB")
        for step, sec in steps.items():
            print(f"   - {step}: {sec} 秒")
        if not ok:
            print(f"   ログ: {args.workdir / 'logs' / f'{name}.log'}")

        row = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            **info,
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "workers": args.workers,
            "n": n,
            "ok": ok,
            "total_sec": round(elapsed, 1),
            "peak_rss_mb": peak_mb,
            "steps_sec": json.dumps(steps, ensure_ascii=False),
            "note": args.note,
        }
        new = not args.out.exists()
        with args.out.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(row))
            if new:
                w.writeheader()
            w.writerow(row)
    print(f"\n結果: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
