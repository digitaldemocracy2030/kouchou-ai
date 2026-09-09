# LLM呼び出しのタイムアウト

ローカルLLMの初回モデル読み込みなどで時間がかかる場合は、`.env` に次を指定します。

```dotenv
LLM_REQUEST_TIMEOUT_SECONDS=600
```

未指定の既定値は300秒です。正の整数を指定してください。0・負数・小数・空文字は設定エラーになります。変更後はAPIを再起動します。Docker Composeでは環境変数を取り込むため `docker compose up -d --force-recreate api` でAPIコンテナを再作成してください。CLIでは同じ環境変数を設定してから再実行します。

OpenAI / Azure / Gemini / OpenRouter / ローカルLLMのチャット呼び出しに適用され、初期ラベル・統合ラベル・概要生成でも使用します。embeddingのタイムアウトは対象外です。SDKのリトライやrate limitの待機時間を含む、レポート全体の実行制限時間ではありません。

抽出工程では既存のバッチ待機期限にも同じ値を適用します。バッチの待機にはキュー内の処理も含まれるため、必要に応じて十分に長く設定してください。抽出工程だけ上書きする場合は分析configの `extraction.timeout_seconds` に正の整数を指定します。優先順位は工程設定、環境変数、既定値300秒です。legacy / workflowどちらにも適用されます。

```json
{
  "extraction": {
    "timeout_seconds": 900
  }
}
```

ローカルLLMで同時リクエストが処理能力を超える場合は、作成画面の並列数も1に下げて確認してください。タイムアウトの延長だけでは処理能力の不足は解消しません。

OpenAIのFlex Processingを使う呼び出しでは、この値と `OPENAI_FLEX_TIMEOUT_SECONDS`（既定900秒）の大きい方を適用します。詳細は [openai-flex-processing.md](openai-flex-processing.md) を参照してください。
