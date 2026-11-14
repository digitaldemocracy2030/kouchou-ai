# ローカルLLMで動かす PC の目安（時間とメモリ）

このページは、広聴AIの分析をクラウドの API ではなく、手元の PC で動かす LLM（プロバイダ **LocalLLM**、`docker compose --profile ollama`）で行いたい方向けに、どのくらいの PC で、どのくらいの時間がかかるかをまとめたものです。自治体などで、GPU の無い普通の PC で使うことを想定しています。

どのモデルを選ぶかは [ローカルLLMのモデル選び（品質の測定結果）](local-llm-models.md) にまとめています。このページの数字は、そこで第一候補にしている **gemma4:e4b を、思考を止めて使う**場合のものです。

!!! note "2026-11 時点の測定です"
    1 台の PC で、各 1 回測った結果です。測った PC と、測っていないことは下に書いています。ほかの PC で測った結果は、Issue で教えてください（測り方は下の「自分の PC で測る」）。

## まとめ

| 項目 | 目安 |
| --- | --- |
| CPU | 4 コア 8 スレッドの x86 の PC で、レポートを最後まで作れました。GPU は要りません（下の「GPU の無い PC で起動する」） |
| メモリ | **16GB 以上**。Ollama が約 8GB、分析が約 2GB を使い、ほかに OS と Docker の分が要ります |
| ディスクの空き | モデル（gemma4:e4b）に約 6.6GB。ほかに広聴AIの Docker イメージの分 |
| 時間 | 意見 100 件で約 40 分、400 件で約 1 時間 45 分 |
| 必須の設定 | `.env` に `LOCAL_LLM_REASONING_EFFORT=none`。設定しないと、待ち時間切れでレポートを作れません |

- **数百件までなら、普通の PC で半日のうちに終わります。** 件数がもっと多いときや、何度も作り直したいときは、クラウドの API（[クイックスタート](quickstart.md)）か、GPU のある PC を考えてください。
- **思考を止める設定は必ず入れてください。** gemma4 は思考型のモデルで、止めないと 1 回の呼び出しが数分かかり、ラベル付けで待ち時間（300 秒）を超えて失敗しました。止めると、抽出の 1 回の呼び出しは約 5 分の 1 になりました（[#1194 の検証](https://github.com/digitaldemocracy2030/kouchou-ai/issues/1194#issuecomment-6795596666)）。

## GPU の無い PC で起動する

`compose.yaml` の Ollama は NVIDIA の GPU を予約する設定なので、GPU の無い PC ではそのままでは起動しません。GPU の予約を外す `compose.cpu.yaml` を重ねて起動してください。

```bash
docker compose -f compose.yaml -f compose.cpu.yaml --profile ollama up -d
```

止めるときや作り直すときも、同じ `-f` の指定を付けてください。そのうえで `.env` に `LOCAL_LLM_REASONING_EFFORT=none` を書き、レポート作成画面でプロバイダ LocalLLM・モデル gemma4:e4b を選びます。

## 測った PC

- CPU: AMD Ryzen 7 5700X（デスクトップ向け、DDR4）のうち、**4 コア 8 スレッドだけ**を割り当て
- GPU: 使っていません（Ollama の起動ログが `library=cpu` であることを確認）
- メモリ: Ollama のコンテナに上限 12GB、分析のプロセスに上限 4GB を割り当て
- OS: Ubuntu 22.04（x86_64）、Docker、Ollama 0.33.2
- 広聴AI: `main` の 4f506750、モデル gemma4:e4b、`LOCAL_LLM_REASONING_EFFORT=none`、並列数（`workers`）1

測定は katsushi2441 さんによるものです（[#1195 の検証](https://github.com/digitaldemocracy2030/kouchou-ai/issues/1195#issuecomment-6800727843)、記録は [katsushi2441/kouchou-ai-kit の bench/issue1195](https://github.com/katsushi2441/kouchou-ai-kit/tree/master/bench/issue1195)）。

## 時間

| | 100 件 | 400 件 |
| --- | ---: | ---: |
| 全体 | 37.9 分 | 104.1 分 |
| 意見の抽出（extraction） | 21.9 分 | 76.9 分 |
| 初期ラベル（hierarchical_initial_labelling） | 10.9 分 | 22.1 分 |
| 統合ラベル（hierarchical_merge_labelling） | 3.2 分 | 3.8 分 |
| 埋め込み・クラスタリング・概要ほか | 1.9 分 | 1.2 分 |

- 時間の大部分は意見の抽出で、1 件あたり約 12 秒でした。件数に比例して伸びます。
- 1,000 件は測っていません。400 件と同じ割合で伸びるとすれば 4 時間強です（計算による見込みです）。
- 100 件の埋め込み・クラスタリングが 400 件より長いのは、1 回目に埋め込みのモデルの読み込みなどが入ったためと見られます。

## メモリ

| | 測った値 |
| --- | ---: |
| 分析のプロセス（最大） | 100 件 2.1GB、400 件 1.8GB |
| Ollama のコンテナ（400 件が終わった直後） | 8.2GiB |

Ollama の値は終わった直後のもので、測定中の最大値ではありません。この 2 つに OS・Docker・ブラウザの分を足すと、16GB が下限の目安になります。

## 測っていないこと

- **メモリ 16GB の PC そのもので動かしてはいません。** 測った PC は全体で 67GB あり、コンテナと分析のプロセスに上限を付けて測りました。16GB の PC では、ほかのアプリを閉じて使うのが無難です。
- **事務用のノート PC や省電力の CPU では、これより遅くなるはずです。** 測ったのはデスクトップ向けの CPU を 4 コアに絞ったものです。
- GPU のある PC、Mac（Apple シリコン）、NPU を積んだ PC（Copilot+ PC など）。NPU で速くする件は [#1196](https://github.com/digitaldemocracy2030/kouchou-ai/issues/1196) で扱っています。
- 並列数（`workers`）を 2 以上にしたときの時間とメモリ。
- 出来上がったレポートの中身。品質はモデル選びのページで別に測っています。

## 自分の PC で測る

本体の [`experiments/local_llm_bench`](https://github.com/digitaldemocracy2030/kouchou-ai/tree/main/experiments/local_llm_bench) で、同じ測り方ができます。件数を指定すると、サンプルの意見でレポート全体を作り、段ごとの時間とメモリの最大値を CSV に書きます。

```bash
python experiments/local_llm_bench/bench.py --model gemma4:e4b --reasoning-effort none --n 100 --n 400
```

結果は、PC の型番・CPU・メモリと一緒に Issue で教えてください。
