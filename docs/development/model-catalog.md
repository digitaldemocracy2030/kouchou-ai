# モデル一覧・検証状態・料金の更新

正本は `apps/api/src/services/model_catalog.json`。新規作成・複製画面は
`GET /admin/models?provider=...` を同じhookで読み、料金APIと計算処理も同じデータを使う。
フロントエンドにモデル一覧や説明のコピーを追加しない。

## モデルの追加

1. provider / value（APIモデルID）の組を一意に追加する。label、description、available、deprecatedを記載する。
2. verifiedは実API検証の証拠がなければfalse。falseでも選択可能で「動作未検証」と表示する。
   #906 / #907の4モデルは指示に合わせunverified_labelを「動作未確認」とし、検証先を#912 / #913へ記載した。
   trueへの変更にはverification_source（検証結果のURL）が必要。既存モデルも検証記録を移入していないためfalseから始める。
3. priceは不明ならnull。既知ならUSD/100万テキストtokenのinput / output、source、checked_at、conditionsを記載する。
   現行の旧単価は移行値でchecked_at=null。最新確認済みとは扱わない。
4. 提供終了は行を消さずavailable=false、deprecated=trueにする。保存済み設定を表示し、再選択を案内する。
5. APIのcatalog / pricingテストとadminのhook / componentテストを実行する。

新モデルの実API検証と一覧追加は別作業。schema、送信パラメーター、思考token、課金集計の検証は#912 / #913で追跡する。

## 動的一覧

Gemini / OpenRouter / LocalLLMは提供元一覧をカタログに合流する。未登録モデルはverified=false、price=null。
動的一覧に同じIDがあっても、カタログの廃止状態や検証結果は上書きしない。
Gemini / OpenRouterの取得失敗時はサーバーカタログを返し、discovery_warningを画面に表示する。
API自体に接続できない場合は再取得を案内する。新規作成も複製も取得中・失敗中の送信を止める。

## 推定料金

未知モデル・未知単価はnullで返す（無料の0と異なる）。保存済みの過去の推定値は書き換えない。
モデル名は価格検索前に正規化するが、未登録のsnapshotを任意に既知モデルへ推測しない。
valid_untilを過ぎた単価は不明に戻す。Gemini 3.8 Flashの導入価格は2026-12-31まで。
GPT-5.6の長文料金はリクエスト別token数が必要なため、累積入力が272,000を超えた場合は保守的に不明とする。
通常単価の概算であり、キャッシュ割引・追加サービス課金・契約割引は反映しない。

## Azure

実際の接続先は既存の `AZURE_CHATCOMPLETION_DEPLOYMENT_NAME` が決める。
UIのモデル選択は固定で、OpenAIのカタログを流用しない。
表示用実モデル名は任意の `AZURE_CHATCOMPLETION_MODEL_NAME`。
推定に使う単価は `AZURE_CHATCOMPLETION_INPUT_PRICE` / `AZURE_CHATCOMPLETION_OUTPUT_PRICE` に
管理者が契約単価を設定する（USD/100万text token）。モデル名と両単価が揃わない、不正値の場合は料金不明。
これらは接続先を変更しない。OpenAI単価へのfallbackはない。
