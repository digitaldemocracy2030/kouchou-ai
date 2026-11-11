# ローカル LLM でレポート全体を作る時間とメモリを測る（local_llm_bench）

自治体の普通の PC で広聴AIを動かせるか、何件なら実用的かを決めるための測定スクリプトです（[#471](https://github.com/digitaldemocracy2030/kouchou-ai/issues/471)）。測った結果は [#1195](https://github.com/digitaldemocracy2030/kouchou-ai/issues/1195) にコメントしてください。複数の PC の結果が集まったら、推奨スペックの文書にまとめます。

本物のローカル LLM（Ollama・llama.cpp など OpenAI 互換の接続先）につなぎ、広聴AIの CLI でレポートを最後まで作って、次を CSV に記録します。

- PC の情報（OS・CPU・論理コア数・メモリの総量）
- 完走したか、全体の時間、段ごとの時間（抽出・埋め込み・クラスタリング・ラベル付け・概要など）
- 分析のプロセスのメモリの最大値（MB）

LLM のサーバ（Ollama など）は別のプロセスなので、そのメモリは含みません。サーバのメモリは、タスクマネージャーなどで別に見てください。

## 準備

1. Python 3.12 以上で、分析コアと psutil を入れます（psutil は Windows でメモリを測るのに使います）

    ```bash
    python3.12 -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install 'kouchou-ai-analysis-core[embeddings,clustering]' psutil
    ```

    このリポジトリの開発中の版で測るときは、`pip install -e 'packages/analysis-core[embeddings,clustering]' psutil` にします。

2. ローカル LLM を動かします。Ollama なら次のとおりです

    ```bash
    ollama pull gemma4:e4b
    ollama serve
    ```

    GPU を使わずに測るときは、GPU が使われていないことを確かめてください。Ollama は `CUDA_VISIBLE_DEVICES=-1` だけでは Vulkan 経由で GPU を使うことがあります。`OLLAMA_VULKAN=false` と `GGML_VK_VISIBLE_DEVICES=-1` も設定し、起動ログに `library=cpu` と出ることを確かめます（#471 の katsushi2441 さんの測定より）。

3. 初回は、埋め込みのモデル（`paraphrase-multilingual-mpnet-base-v2`、約 1GB）が自動でダウンロードされます。

## 測る

```bash
python experiments/local_llm_bench/bench.py --model gemma4:e4b --reasoning-effort none --n 100 --n 400
```

- `--n` は件数です。複数回指定すると順に測ります。既定の入力は管理画面のサンプル（`apps/admin/public/sample_comments.csv`、400 件）です。それより多く測るときは、`--input <CSV> --text-column <本文の列名>` で別の CSV を渡します
- `--reasoning-effort none` は、gemma4 などの思考型モデルの思考を止めます（`LOCAL_LLM_REASONING_EFFORT` に渡します。分析コアが [#1193](https://github.com/digitaldemocracy2030/kouchou-ai/pull/1193) より前の版だと効きません。そのときはスクリプトが注意を出します）
- `--address` は接続先です（既定は Ollama の `127.0.0.1:11434`）。llama.cpp の `llama-server` なら `127.0.0.1:8080` などにします
- `--workers` は抽出の並列数です（既定 1）。Ollama の同時処理数（`OLLAMA_NUM_PARALLEL`）を増やしたときに合わせます
- `--note` に、GPU を切った方法など結果を読むときに要るメモを残せます

入力・設定・出力・ログは `bench-work/` に、結果は `bench-results.csv` に 1 回 1 行で足されます。失敗したときは、表示されるログのファイルを見てください。

## 結果の例

| PC | モデル | 件数 | 全体 | メモリ最大 |
| --- | --- | ---: | ---: | ---: |
| ARM（Neoverse-N1）8 コア・30GB・GPU なし（llama.cpp、サーバ側で思考を止めた、`--workers 1`） | gemma-4-E4B（Q4_K_M） | 20 | 4.9 分 | 2.0GB |

このときの段ごとの時間は、抽出 85 秒・埋め込み 12 秒・クラスタリング 15 秒・初期ラベル 93 秒・統合ラベル 62 秒・概要 23 秒でした。件数が少ないうちは、ラベル付けの時間（クラスタの数で決まる）が抽出より長くなります。

ARM のサーバの値は、自治体の PC（x86）の目安にはなりません。#1195 に、自治体の PC に近い PC での結果をお願いします。
