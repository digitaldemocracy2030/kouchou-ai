# 広聴AI / kouchou-ai

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/digitaldemocracy2030/kouchou-ai)

デジタル民主主義 2030 プロジェクトにおいて、**ブロードリスニング**を実現するためのソフトウェア「広聴 AI」のドキュメントサイトです。

このプロジェクトは、[AI Objectives Institute](https://www.aiobjectivesinstitute.org/) が開発した [Talk to the City](https://github.com/AIObjectives/talk-to-the-city-reports)を参考に、日本の自治体や政治家の実務に合わせた機能改善を進めています。

## 主な機能

- **CSV アップロード**: 開発者以外でも扱いやすいインターフェース
- **濃いクラスタ抽出**: 重要な意見グループの自動識別
- **階層的クラスタリング**: 大量のコメントを構造的に整理
- **パブリックコメント用分析機能**（予定）
- **多数派攻撃に対する防御機能**（予定）

## クイックスタート

### 一般ユーザー向け

お使いの OS に合わせたセットアップガイドをご覧ください：

<div class="grid cards" markdown>

- :fontawesome-brands-windows: **Windows**

    ---
    [Windows セットアップガイド](getting-started/windows-setup.md)

- :fontawesome-brands-apple: **macOS**

    ---
    [Mac セットアップガイド](getting-started/mac-setup.md)

- :fontawesome-brands-linux: **Linux**

    ---
    [Linux セットアップガイド](getting-started/linux-setup.md)

</div>

### 開発者向け

ローカルでコードを触る場合は **[開発者向けスタートガイド](development/developer-quickstart.md)** が canonical な入口です。利用モード（Docker Compose / フロントだけ / native 起動 / CLI）ごとに必要な環境変数・起動コマンド・確認 URL・落とし穴を 1 ページに集約しています。

最短：Docker Compose で全体を起動

```bash
git clone https://github.com/digitaldemocracy2030/kouchou-ai.git
cd kouchou-ai
cp .env.example .env       # OPENAI_API_KEY 等を設定
docker compose up
```

- レポート一覧: <http://localhost:3000>
- 管理画面: <http://localhost:4000>
- API: <http://localhost:8000/docs>

## アーキテクチャ

```text
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  public-viewer  │     │      admin      │     │       api       │
│   (Port 3000)   │     │   (Port 4000)   │     │   (Port 8000)   │
│                 │     │                 │     │                 │
│  レポート閲覧    │     │  レポート作成    │────▶│  バックエンド    │
│  データ可視化    │────▶│  設定管理        │     │  パイプライン    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        └───────────────────────┴───────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │     OpenAI API /      │
                    │     Local LLM         │
                    └───────────────────────┘
```

| サービス | ポート | 役割 |
|---------|-------|------|
| public-viewer | 3000 | レポート表示用フロントエンド |
| admin | 4000 | 管理用フロントエンド |
| api | 8000 | バックエンド API サービス |
| ollama | 11434 | ローカル LLM（オプション） |

## ドキュメント構成

- **[はじめに](getting-started/quickstart.md)**: 一般ユーザー向け Docker クイックスタートと OS 別セットアップ
- **[開発者向けスタートガイド](development/developer-quickstart.md)**: コードを触る開発者のための利用モード別 canonical 入口
- **[ユーザーガイド](user-guide/how-to-use.md)**: 詳細な操作方法
- **[CLI クイックスタート](user-guide/cli-quickstart.md)**: `kouchou-analyze` / `packages/analysis-core` での実行手順
- **[コントリビューション](development/contributing.md)**: 開発参加方法、プラグイン開発
- **[デプロイ](deployment/azure.md)**: Azure、GitHub Pages、静的ホスティング時の CSP 設定
- **[静的ホスティング向け CSP 設定](deployment/static-hosting-csp.md)**: Azure Static Web Apps / Cloudflare Pages / Nginx での CSP 例
- **[技術解説資料](https://www.docswell.com/s/tokoroten/ZL1M88-2025-06-14-014546)**: プロジェクトの技術的背景と設計思想（外部リンク）

## 免責事項

大規模言語モデル（LLM）にはバイアスがあり、信頼性の低い結果を生成することが知られています。私たちはこれらの問題を軽減する方法に積極的に取り組んでいますが、現段階ではいかなる保証も提供することはできません。特に重要な決定を下す際は、本アプリの出力結果のみに依存せず、必ず内容を検証してください。

## クレジット

このプロジェクトは、[AI Objectives Institute](https://www.aiobjectivesinstitute.org/) が開発した [Talk to the City](https://github.com/AIObjectives/talk-to-the-city-reports)を参考に開発されており、ライセンスに基づいてソースコードを一部活用し、機能追加や改善を実施しています。ここに原作者の貢献に感謝の意を表します。
