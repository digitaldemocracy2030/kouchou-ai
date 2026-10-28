# APIの課金と429エラー（残高不足・レート制限）

このページは、広聴AIで **OpenAI などの AI（LLM）の API を自分のキーで使う方** 向けに、API の課金の仕組みと、`429` エラーが出たときの見分け方・対処をまとめたものです。セットアップガイドの「APIキーの準備」や、管理画面・CLI でエラーが出たときに参照してください。

## ChatGPT Plus と OpenAI API は別の契約です

**ChatGPT Plus（ChatGPT の月額プラン）に加入していても、OpenAI API は使えません。** 両者は別の契約で、支払いも別です。

| | ChatGPT Plus | OpenAI API |
| --- | --- | --- |
| 何に使うか | ブラウザやアプリで ChatGPT と会話する | 広聴AIのようなプログラムから AI を呼び出す |
| 料金の形 | 月額の定額 | **従量課金**（処理したテキスト量に応じて課金） |
| 契約・支払いの場所 | ChatGPT の画面 | [OpenAI Platform](https://platform.openai.com/)（開発者向けの管理画面） |

広聴AIで OpenAI のモデルを使うには、ChatGPT Plus の有無にかかわらず、OpenAI Platform で次の準備が必要です。

1. [OpenAI Platform](https://platform.openai.com/) にログインします（ChatGPT と同じ OpenAI アカウントで入れます）。
2. 設定の **Billing**（請求）で支払い方法を登録し、**クレジットを購入**します（前払い方式です）。残高が 0 のままだと、キーが正しくても API は使えません。
3. [API keys](https://platform.openai.com/api-keys) で API キーを作成し、広聴AIに設定します。

!!! tip "キーを作っただけでは使えません"
    API キーは「誰が呼び出しているか」を示すだけで、支払いの手段ではありません。残高が無い状態で広聴AIを動かすと、後述の **残高不足（`insufficient_quota`）** の 429 エラーになります。セットアップの前に、Billing でクレジットを購入しておいてください。

**Gemini を使う場合**: [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key) で取得したキーは、無料枠（free tier）のまま使い始められますが、1 分あたり・1 日あたりの呼び出し回数の上限が低く、件数の多い分析では上限に達しやすくなります。上限と有料プランへの切り替えは、[Gemini API のレート制限](https://ai.google.dev/gemini-api/docs/rate-limits)と[料金](https://ai.google.dev/gemini-api/docs/pricing)の公式ページを参照してください。

**Azure OpenAI・OpenRouter・ローカル LLM を使う場合**: 課金と上限は各サービス側の契約で決まります。このページの OpenAI Platform に関する説明はそのままは当てはまりませんが、429 エラーの見分け方と自動調整の説明（次節以降）は OpenAI 互換の経路に共通です。

## 429 エラーには 2 種類あります

AI の API が返す HTTP ステータス `429` には、原因がまったく違う 2 種類があります。エラー文の中身で見分けてください。

| 種類 | エラー文の例 | 原因 | 対処 |
| --- | --- | --- | --- |
| **残高不足**（`insufficient_quota`） | `You exceeded your current quota, please check your plan and billing details.` | クレジットの残高が無い、または Billing で設定した利用上限（usage limit）に達している | OpenAI Platform の Billing で**クレジットを購入**する（上限に達している場合は上限を見直す）。購入後に分析をやり直す |
| **レート制限**（rate limit） | `Rate limit reached for <モデル名> ... on tokens per min (TPM) ...` / `... requests per min (RPM) ...` | 短時間に送った要求の数（RPM）やトークン量（TPM）が、自分の **Tier** の上限を超えた | 基本は**自動で待って送り直される**ので何もしなくてよい（次節）。頻発する場合は並列実行数を下げるか、Tier を上げる |

広聴AIの画面では、次のように表示されます。

- **作成画面の作成前確認**（キーとモデルを選んで短いチャットを送る確認）: 残高不足は「残高不足 / quota不足：プロバイダーの課金設定・利用上限を確認してください。」、レート制限は「rate limit：時間をおいて再度お試しください。」
- **再利用画面の接続確認**: 残高不足は「デポジット残高が不足しています。チャージしてください。」、レート制限は「APIのレート制限に達しました。時間をおいて再度お試しください。」
- **CLI**: ログに `RateLimitError` と、上の表のエラー文が出ます。`insufficient_quota` の文字が含まれていれば残高不足です。

!!! warning "残高不足は自動では直りません"
    残高不足（`insufficient_quota`）は待っても解消しないため、広聴AIは送り直さずにその場で分析を止めます。クレジットを購入してから、分析をやり直してください。

## レート制限は自動で調整されます

広聴AIは、意見の抽出・ラベル生成・意見分類・要約のすべての工程で、`workers`（並列実行数）本の要求を同時に AI に送ります。この速さがプロバイダの上限を超えるとレート制限の 429 が返りますが、広聴AIは次のように**送る側で自動調整**するので、多くの場合は何もしなくても完走します。

- 429 を受けた要求は、失敗にせず**待ってから同じ内容を送り直します**。待ち時間は 1 秒から倍々に延び（最長 60 秒）、プロバイダが待ち時間を指定していればそれに従います。1 つの要求で 15 分待っても通らない場合だけ失敗になります。
- どれか 1 つが 429 を受けたら、**すべての送り手が 1 秒間新しい要求を止めます**。
- **同時に送る数を自動で増減します**。429 を受けると今の同時実行数を半分に下げ、成功が続けば 1 ずつ戻します。設定した並列実行数は「上限」の意味になり、上限いっぱいに送れるときだけそのまま使われます。

この仕組みは OpenAI・Azure OpenAI・OpenRouter・ローカル LLM（OpenAI 互換の経路）で動きます。Gemini は独自に待って送り直しますが、回数に上限があるため、無料枠では上限に達して失敗することがあります。

!!! note "v4.2.0 以前のリリースをお使いの場合"
    この自動調整は 2026-10-27 以降の `main` に入ったもので、**v4.2.0 以前の安定版リリースには含まれていません**。古い版では、レート制限の 429 が続くと分析が途中で失敗することがあります。その場合は、次の「それでも 429 が続くとき」の手順で並列実行数を下げてください。

### それでも 429 が続くとき

自動調整が入っていても、Tier の上限が並列実行数に対して低すぎると、待ち時間が長くなったり、まれに失敗したりします。次の順に試してください。

1. **時間をおいて再実行する**: 上限は 1 分（または 1 日）あたりの値なので、しばらく待つと回復します。CLI は完了済みのステップを再利用して続きから実行できます（[CLIクイックスタート](../user-guide/cli-quickstart.md)の `Job already running` の項を参照）。
2. **並列実行数を下げる**: 管理画面では作成画面の AI 設定にある **「並列実行数」**、CLI では設定ファイルの **`extraction.workers`** です。半分程度から試して、安定する値を探してください。
3. **Tier を上げる**: 下の「Tier と上限の確認」を参照してください。

## Tier と上限の確認（OpenAI）

OpenAI API では、アカウントごとに **usage tier** が決まっていて、Tier ごとにモデル別の RPM（1 分あたりの要求数）・TPM（1 分あたりのトークン数）の上限が設けられています。新しいアカウントほど Tier が低く、上限も小さいため、件数の多い分析でレート制限に当たりやすくなります。

- **自分の Tier と上限を確認する**: OpenAI Platform の [Limits](https://platform.openai.com/settings/organization/limits) ページ（Settings → Organization → Limits）に、現在の Tier と、モデルごとの RPM / TPM の上限が表示されます。
- **Tier を上げる条件**: これまでの支払額と、初回の支払いからの経過日数で自動的に上がります。条件の具体的な金額・日数と、Tier ごとの上限値は変わることがあるため、ここには書きません。公式の [Rate limits](https://platform.openai.com/docs/guides/rate-limits) のドキュメント（Usage tiers の節）を参照してください。
- **Gemini の無料枠**: Gemini API の無料枠にも、モデルごとに 1 分あたり・1 日あたりの上限があります。値は [Gemini API のレート制限](https://ai.google.dev/gemini-api/docs/rate-limits)を参照してください。

## 関連ページ

- [Windows セットアップ](windows-setup.md) / [Mac セットアップ](mac-setup.md) / [Linux セットアップ](linux-setup.md) — 「APIキーの準備」の手順
- [CLIクイックスタート](../user-guide/cli-quickstart.md) — `extraction.workers` の設定とトラブルシューティング
- [よくあるご質問](../user-guide/faq.md) — 費用の考え方
- [モデル一覧・料金](../development/model-catalog.md) — モデルごとの単価の考え方
