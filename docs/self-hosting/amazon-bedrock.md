# Amazon Bedrock（東京リージョン）で動かす

このページは、広聴AIの分析で使う AI（LLM）を **Amazon Bedrock の東京リージョン** に置きたい方（自治体に広聴AIを提案・構築する事業者など）向けの構成例です。

!!! warning "DD2030 では動作確認していません"
    この構成は、AWS の公式ドキュメントと広聴AIのコードを読んで組み立てたものです。DD2030 は AWS の実環境で動かしていません。広聴AIがサポートしているほかの接続先と同じく、動作の保証もありません。
    試した結果（動いた・動かなかった・設定で詰まったところ）は、Issue [#1169](https://github.com/digitaldemocracy2030/kouchou-ai/issues/1169) にぜひ書き込んでください。このページを直す材料になります。

## この構成で国内に収まるもの

| 処理・データ | この構成での置き場所 |
| --- | --- |
| LLM の推論（意見の抽出・ラベル付け・要約） | Bedrock 東京リージョン（リージョン内で処理するモデルを選んだ場合） |
| 埋め込み（意見の文章を数値に変える処理） | 広聴AIのサーバの中 |
| 広聴AI本体・入力データ・結果の保存・ログ | 広聴AIを置く場所しだい（構成する側で決める） |

広聴AI本体を国外のサーバに置けば、データは国外に出ます。本体・保存先・ログの置き場所は、構成する側で決めてください。このほか、サーバ内の埋め込みモデルの重みは、初回に外部からダウンロードされることがあります（意見データは送りません）。

「国内」の意味（処理の場所だけか、事業者も国内に限るか、庁内のネットワークから出さないか）によっては、クラウドでは要件を満たせません。選択肢の整理は Issue [#1190](https://github.com/digitaldemocracy2030/kouchou-ai/issues/1190) にあります。

## 仕組み：コードの変更は要りません

Bedrock は OpenAI と同じ形の API（OpenAI 互換の Chat Completions）を東京リージョンで提供しています。広聴AIのプロバイダ **LocalLLM**（`local`）は、OpenAI 互換の HTTPS の接続先と鍵をそのまま扱えるので、ここに Bedrock の接続先と Bedrock の API キーを入れます。

- LocalLLM を選ぶと、埋め込みは自動でサーバの中で行います（管理画面では「埋め込み処理をサーバ内で行う」が強制的に ON になります）。埋め込みを Bedrock や国外の API に送ることはありません。
- 鍵の扱いは [ローカルLLMの認証付きゲートウェイ](../development/local-llm-gateway.md) と同じです。

この方法で使えるのは、Bedrock の OpenAI 互換 API に対応したモデル（gpt-oss など）です。Claude を Bedrock の Converse API で使う構成には、別の実装が要ります（Issue [#1169](https://github.com/digitaldemocracy2030/kouchou-ai/issues/1169) で検討中）。

## 1. Bedrock 側の準備

### モデルを選ぶ

[Bedrock のモデル一覧（Models at a glance）](https://docs.aws.amazon.com/bedrock/latest/userguide/model-cards.html) で、モデルごとのページ（モデルカード）の **Regional Availability** を開き、`ap-northeast-1 (Tokyo)` の **In-Region** が対応になっているモデルを選びます。In-Region は、リクエストを東京リージョンの中だけで処理する方式です。

例として、OpenAI の `gpt-oss-120b` は東京の In-Region に対応しています（2026-11-10 時点の[モデルカード](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-oss-120b.html)）。

!!! note "Geo・Global の推論プロファイルは国外を通ることがあります"
    モデル ID の前に `global.` や `apac.` が付く「推論プロファイル」は、リクエストを複数のリージョンに振り分けます。`global.` は世界中のリージョン、`apac.` はアジア太平洋の複数の国のリージョンに送られえます。国内で処理したい場合は、モデルカードで In-Region の ID を確かめて使ってください。

### API キーを作る

Bedrock のコンソールで API キーを作ります。手順は [Amazon Bedrock API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html) を参照してください。キーには 2 種類あります。

- **期限の短いキー（short-term）**：最長 12 時間で切れます。**作ったリージョンでしか使えない** ので、コンソールで東京リージョン（ap-northeast-1）に切り替えてから作ってください。AWS は本番にはこちらを勧めています。広聴AIはキーを環境変数で読むので、期限が来るたびに差し替えて API を再起動する必要があります
- **期限の長いキー（long-term）**：設定した期限まで使えます。AWS は「試すとき用」としています

キーに紐づく権限には、使う接続先に応じて次が要ります（[Responses API のページの Prerequisites](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-mantle.html)、[API キーの権限](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html#api-keys-control)、[bedrock-mantle の IAM アクション](https://docs.aws.amazon.com/service-authorization/latest/reference/list_bedrock-mantle.html)）。

- `bedrock-mantle` を使う場合：`bedrock-mantle:CreateInference`（推論）、`bedrock-mantle:CallWithBearerToken`（API キーでの呼び出し）、`bedrock-mantle:ListModels`（管理画面のモデル一覧の取得）
- `bedrock-runtime` を使う場合：`bedrock:InvokeModel`（推論）、`bedrock:CallWithBearerToken`（API キーでの呼び出し）

## 2. 接続先を選ぶ

Bedrock の OpenAI 互換 API には、接続先が 2 つあります。どちらも東京リージョンで使えます。

| 接続先 | URL（東京） | モデル ID の例 | モデル一覧の取得 |
| --- | --- | --- | --- |
| `bedrock-mantle` | `https://bedrock-mantle.ap-northeast-1.api.aws/v1` | `openai.gpt-oss-120b` | できる |
| `bedrock-runtime` | `https://bedrock-runtime.ap-northeast-1.amazonaws.com/openai/v1` | `openai.gpt-oss-120b-1:0` | できない |

- **管理画面から使う場合は `bedrock-mantle`** を選んでください。管理画面は、接続先からモデル一覧を取得してプルダウンに出します。`bedrock-runtime` はモデル一覧の API を持たないので、プルダウンが空になり、モデルを選べません。
- **CLI から使う場合**は、設定ファイルにモデル ID を直接書くので、どちらでも使えます。AWS は新しいアプリには `bedrock-runtime` を勧めています。
- 同じモデルでも、接続先によって ID が違います（上の表）。
- `bedrock-mantle` のモデル一覧には、東京から呼べるほかのモデルも並びます。一覧に出ることは、そのモデルが国内で処理されることを意味しません。モデルカードで In-Region を確かめてから選んでください。

## 3. 広聴AIの設定

### API のサーバ（`.env`）

広聴AIの `.env` に、Bedrock の API キーと、そのキーを送ってよい接続先を書きます。

```dotenv
LOCAL_LLM_API_KEY=<Bedrock の API キー>
LOCAL_LLM_ALLOWED_BASE_URLS=https://bedrock-mantle.ap-northeast-1.api.aws/v1
```

`LOCAL_LLM_ALLOWED_BASE_URLS` は必ず書いてください。空のままだと、管理画面で入力途中のアドレスにも鍵を送ります。書いた後は API を再起動します（Docker Compose なら `docker compose up -d --force-recreate api`）。

### 管理画面

レポート作成画面の AI 設定で、次のように選びます。

1. **プロバイダ**：`LocalLLM`
2. **LocalLLM接続設定**：`https://bedrock-mantle.ap-northeast-1.api.aws/v1`（入力すると、モデル一覧の取得を試みます。失敗したら「モデル取得」を押します）
3. **AIモデル**：プルダウンから、In-Region を確かめたモデル（例：`openai.gpt-oss-120b`）
4. **埋め込み処理をサーバ内で行う**：自動で ON になります

本番の前に、作成画面の接続確認と、数十件の小さなデータでの試行をおすすめします。

### CLI

設定ファイルの例です（`gpt-oss-120b` を `bedrock-runtime` で使う場合）。

```json
{
  "name": "市民意見分析",
  "question": "市民からどのような意見が寄せられていますか？",
  "input": "my-comments",
  "provider": "local",
  "local_llm_address": "https://bedrock-runtime.ap-northeast-1.amazonaws.com/openai/v1",
  "model": "openai.gpt-oss-120b-1:0",
  "is_embedded_at_local": true
}
```

鍵は API のサーバと同じ環境変数で渡します。

```bash
export LOCAL_LLM_API_KEY="<Bedrock の API キー>"
export LOCAL_LLM_ALLOWED_BASE_URLS="https://bedrock-runtime.ap-northeast-1.amazonaws.com/openai/v1"
```

CLI の使い方そのものは [CLIクイックスタート](../user-guide/cli-quickstart.md) を参照してください。

## 4. 確かめていないこと

次の点は、AWS の実環境で動かすまで分かりません。動いたかどうかを Issue [#1169](https://github.com/digitaldemocracy2030/kouchou-ai/issues/1169) で教えてください。

- **構造化出力**：広聴AIは、抽出やラベル付けの結果を JSON の形（JSON スキーマ）を指定して受け取ります（`response_format` の `json_schema`、`strict: true`）。Bedrock の[構造化出力](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html)が受け付けるスキーマの範囲（すべての object に `additionalProperties: false`、数値や文字数の制約なし、省略できる項目は 12 個まで）には、広聴AIが送るスキーマ（抽出・ラベル・要約・LLM 直接グルーピング・意見の分類・賛否）が収まることを、コード上では確かめました。モデルが Chat Completions 経由でこれを守るかは未確認です。
- **送っているほかの値**：広聴AIは LocalLLM へのリクエストに `temperature: 0`、`n: 1`、`seed: 0` を付けます。Bedrock がこれらを受け付けるかは未確認です。
- **初回の待ち時間**：Bedrock は新しいスキーマを初めて受け取ったとき、準備に最大 90 秒ほどかかることがあります。広聴AIの既定のタイムアウト（300 秒）には収まりますが、短くしている場合は [LLMタイムアウト設定](../development/llm-timeout.md) で延ばしてください。
- **思考（reasoning）の分の費用**：gpt-oss は既定で思考してから答えるので、思考の分も出力トークンとして課金されます。広聴AIから思考の強さを指定する手段は、今はありません。
- **レート制限**：Bedrock にはアカウントとモデルごとの上限があります。`429` が返ると広聴AIは待って送り直しますが、続く場合は並列実行数を下げてください（[APIの課金と429エラー](api-billing-and-rate-limits.md)）。

## 困ったとき

| 症状 | 考えられる原因 |
| --- | --- |
| 管理画面のモデル一覧が空になる | 接続先が `bedrock-runtime`。管理画面では `bedrock-mantle` を使う |
| `401` / `403` が返る | `LOCAL_LLM_ALLOWED_BASE_URLS` と接続設定の URL が一致せず、鍵が送られていない。または API キーの権限が足りない |
| ``model `<model-id>` isn't supported on this route`` | 接続先とモデル ID の組み合わせが違う（同じモデルでも接続先で ID が違う） |
| `ValidationException` やパラメータのエラーで `400` が返る | 上の「確かめていないこと」に当たった可能性がある。エラー文を添えて #1169 に報告してください |

## 参考

- [Chat Completions API（Amazon Bedrock User Guide）](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-chat-completions.html)
- [Regional availability by endpoints](https://docs.aws.amazon.com/bedrock/latest/userguide/endpoints-region-availability.html)
- [gpt-oss-120b のモデルカード](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-oss-120b.html)
- [Structured outputs](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html)
- [Amazon Bedrock API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html)
