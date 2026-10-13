# レポート作成者情報（メタデータ）の設定

レポートに表示される **作成者情報**（名前・紹介文・ロゴ画像・各種リンク）は、メタデータファイルで設定します。このページは、レポートを作成・公開する方（発行者）向けの設定ガイドです。

公開前の最終確認は [使い方 — レポートを公開する前のリンク確認](how-to-use.md#pre-publish-check) もあわせて参照してください。

## デフォルト環境（未設定の状態）

デフォルト環境（`apps/api/public/meta/default`）では、作成者の画像やリンクは表示されません。これはテスト用の設定であり、本番公開には使用しないでください。設定が未登録のままだと、レポートには「レポーター情報が未設定です」と表示されます。

## カスタマイズ方法

`apps/api/public/meta/custom` ディレクトリに次のファイルを置くと、作成者情報をカスタマイズできます。

| ファイル | 内容 |
| --- | --- |
| `metadata.json` | 作成者の基本情報（名前・紹介文・各種リンク・ブランドカラーなど） |
| `reporter.png` | 作成者のロゴ画像 |
| `icon.png` | レポートのアイコン画像 |
| `ogp.png` | レポートの OGP 画像（SNS 共有時のサムネイル） |

`metadata.json` の設定例（URL は公開者自身のものに置き換えてください）:

```json
{
  "reporter": "レポート発行者名",
  "message": "このレポートの作成目的と問い合わせ先を記載します。",
  "webLink": "https://example.org/",
  "privacyLink": "https://example.org/privacy",
  "termsLink": "https://example.org/terms",
  "brandColor": "#2577b1"
}
```

## 表示の条件

- **画像**: `reporter.png` が `custom` ディレクトリに存在する場合のみ表示されます。
- **リンク**: `metadata.json` の各リンク（`webLink` / `privacyLink` / `termsLink`）に値が設定されている場合のみ表示されます。
- 値が空、またはファイルが存在しない場合、その要素は表示されません。

## 関連ページ

- [使い方 — レポートを公開する前のリンク確認](how-to-use.md#pre-publish-check)
- [結果の信頼性・限界・責任の所在](reliability-and-responsibility.md)
- [ライセンスと結果の公開](license.md)
