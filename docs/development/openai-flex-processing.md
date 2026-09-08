# OpenAI Flex Processing

OpenAIを直接利用する場合、対応モデルでは [Flex Processing](https://developers.openai.com/api/docs/guides/flex-processing) を自動で使います。
レイテンシが大きくなる代わりに、標準処理より低い単価で課金されます。Azure / OpenRouter / Gemini / ローカルLLMには適用しません。

## 対象モデル

判定は `packages/analysis-core/src/analysis_core/services/llm.py` の `_should_use_openai_flex` で行います。

- 対象: `gpt-5*` / `gpt-6*` 系（例: `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5-mini`）、`o3`、`o4-mini`
- 除外: モデル名に `pro` / `chat` / `codex` / `realtime` / `audio` / `search` / `transcribe` / `tts` / `image` を含む派生（例: `gpt-5-pro`, `gpt-5-chat-latest`）と、それ以外の世代（`gpt-4o*`, `o3-mini` など）

対応モデルが増減した場合は上記の判定と `apps/api/tests/services/test_llm.py` を更新してください。

## 環境変数

```dotenv
# 未設定: モデルごとに自動判定。false で常に標準処理、true で常に Flex。
OPENAI_USE_FLEX=
# Flex 利用時のタイムアウト（秒）。LLM_REQUEST_TIMEOUT_SECONDS との大きい方を使う。未設定・空欄なら 900。
OPENAI_FLEX_TIMEOUT_SECONDS=900
```

`OPENAI_USE_FLEX=true` は非対応モデルでは 400 エラーになるため、検証目的以外では設定しないでください。

## 挙動

- OpenAIはFlexに15分程度のタイムアウトを推奨しているため、Flex利用時は `OPENAI_FLEX_TIMEOUT_SECONDS` まで待ちます。
- Flexのリソース不足時、OpenAIは 429（エラーコード `resource_unavailable`）を返し課金しません。この場合のみ同じリクエストを `service_tier=default`（標準処理を明示。`auto` は自動選択で再び Flex になり得る）に切り替えて再送します。
  切り替え後は標準処理のみを最大3回リトライし、Flexを叩き直しません（1回の呼び出しで最大4リクエスト）。
- `resource_unavailable` 以外の 429（通常のrate limit・quota超過）は標準処理へ切り替えず、従来どおり同じtierで最大3回リトライします。
- GPT-5/6系および o 系モデルは `temperature` の指定を受け付けないため、これらのモデルでは `temperature` を送信しません（`seed` は送信します）。
