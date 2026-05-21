# 静的ホスティング向け CSP 設定ガイド

このガイドでは、`public-viewer` を静的エクスポートして配信する環境で、`Content-Security-Policy` (CSP) をどこに設定すべきか、最低限どの許可が必要かを説明します。

対象は次のような構成です。

- `make client-build-static` で `public-viewer` を静的ファイルとして出力する
- 生成物を GitHub Pages / Azure Static Web Apps / Cloudflare Pages / Nginx 配下などで配信する
- 配信先で CSP を付与したい、または既に CSP が付いている

## 背景

`public-viewer` は静的エクスポート時に `output: "export"` を使います。

```ts
const isStaticExport = process.env.NEXT_PUBLIC_OUTPUT_MODE === "export";

const nextConfig: NextConfig = {
  output: isStaticExport ? "export" : undefined,
};
```

このモードでは、Next.js アプリ側で動的にレスポンスヘッダーを配る前提が弱くなるため、**CSP は配信先の CDN / リバースプロキシ / 静的ホスティング設定で付与する**のが基本です。

特に Plotly の PNG ダウンロードでは、ブラウザが `blob:` URL を使って画像を書き出します。CSP の `img-src` に `blob:` が入っていないと、ダウンロード処理がブラウザにブロックされます。

## 最低限必要な考え方

静的エクスポート配信でまず確認すべきなのは次の 3 点です。

1. `img-src` に `blob:` を含める
2. `img-src` に `data:` を含める
3. 静的サイトから外部 API や解析タグへ通信する場合は、必要な origin を `connect-src` や `script-src` に明示する

最小構成の例:

```text
default-src 'self';
script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline';
img-src 'self' data: blob:;
font-src 'self' data:;
connect-src 'self';
frame-ancestors 'none';
```

## 環境ごとに追加で見直す点

- API を別 origin で配信している場合:
  - `connect-src` に API origin を追加
- Google Analytics など外部スクリプトを使う場合:
  - `script-src` と `connect-src` にその origin を追加
- レポート内で外部画像を表示する場合:
  - `img-src` にその画像 origin を追加

例:

```text
connect-src 'self' https://api.example.com https://www.google-analytics.com;
img-src 'self' data: blob: https://images.example.com;
script-src 'self' 'unsafe-inline' https://www.googletagmanager.com;
```

## Azure Static Web Apps

Azure Static Web Apps では、`staticwebapp.config.json` の `globalHeaders` で CSP を付与できます。ファイルはデプロイ対象の app root に置いてください。

例:

```json
{
  "globalHeaders": {
    "content-security-policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' https://api.example.com; frame-ancestors 'none';"
  }
}
```

Azure Application Insights を使う場合は、必要に応じて `connect-src` と `script-src` に監視用 origin を追加してください。

例:

```text
script-src 'self' 'unsafe-inline' https://js.monitor.azure.com;
connect-src 'self' https://api.example.com https://js.monitor.azure.com https://*.applicationinsights.azure.com https://*.azurestaticapps.net;
```

## Cloudflare Pages

Cloudflare Pages では、静的アセット配信に対して `_headers` ファイルで CSP を付与できます。静的エクスポートの成果物ルートに `_headers` を置いてください。

例:

```text
/*
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' https://api.example.com; frame-ancestors 'none';
```

`public/` に `_headers` を置いておくと、ビルド後の出力ディレクトリへ一緒にコピーされる構成では運用しやすいです。ただし、この repo では API origin や analytics origin が環境ごとに違うので、**固定値の `_headers` をそのままコミットするより、デプロイ前に環境に合わせて生成・配置する運用**を推奨します。

## Nginx

Nginx で静的ファイルを配る場合は、server または location ブロックで CSP を追加します。

例:

```nginx
server {
    listen 443 ssl;
    server_name reports.example.com;

    root /var/www/kouchou-ai-public-viewer;
    index index.html;

    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' https://api.example.com; frame-ancestors 'none';" always;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

既に別の `Content-Security-Policy` を返している場合は、重複して送らないように 1 箇所へ寄せてください。

## GitHub Pages について

GitHub Pages は簡単に静的ファイルを公開できますが、このガイドで説明しているような **配信時の CSP ヘッダーを細かく制御したい用途には向きません**。既に適切な CSP を付与できる CDN / リバースプロキシの背後に置くか、Azure Static Web Apps / Cloudflare Pages / Nginx など、レスポンスヘッダーを制御できる配信先を使ってください。

## 確認項目

CSP を変更した後は、少なくとも次を確認してください。

1. レポート画面が通常表示できる
2. Scatter / Treemap / 階層リストが崩れない
3. PNG ダウンロードがブラウザ console の CSP エラーなしで動く
4. 外部 API を使う構成なら、network error ではなく正常応答になる
5. 外部画像や監視タグを使う構成なら、それらが CSP で落ちていない
