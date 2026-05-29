# 広聴 AI / kouchou-ai

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/digitaldemocracy2030/kouchou-ai)

デジタル民主主義 2030 プロジェクトにおいて、ブロードリスニングを実現するためのソフトウェア「広聴 AI」のリポジトリです。

このプロジェクトは、[AI Objectives Institute](https://www.aiobjectivesinstitute.org/) が開発した [Talk to the City](https://github.com/AIObjectives/talk-to-the-city-reports) を参考に、日本の自治体や政治家の実務に合わせた機能改善を進めています。

- 機能例
  - 開発者以外でも扱いやすいような機能（CSV Upload）
  - 濃いクラスタ抽出機能
  - パブリックコメント用分析機能（予定）
  - 多数派攻撃に対する防御機能（予定）

## ドキュメントサイト

詳細な手順・設計情報はドキュメントサイトを正本としています。

➡ **<https://digitaldemocracy2030.github.io/kouchou-ai/>**

## はじめに

### 一般ユーザーの方（アプリを「使う」だけ）

お使いの OS のセットアップガイドを参照してください。

- [Windows セットアップガイド](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/windows-setup)
- [Mac セットアップガイド](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/mac-setup)
- [Linux セットアップガイド](https://digitaldemocracy2030.github.io/kouchou-ai/getting-started/linux-setup)

### 開発者の方（コードを触る）

利用モード別（Docker Compose / フロントだけ / native / CLI）の入口は **[開発者向けスタートガイド](https://digitaldemocracy2030.github.io/kouchou-ai/development/developer-quickstart)** に集約しました。

最短：Docker Compose で全体を起動

```bash
git clone https://github.com/digitaldemocracy2030/kouchou-ai.git
cd kouchou-ai
cp .env.example .env       # OPENAI_API_KEY 等を設定
docker compose up
```

- public-viewer: <http://localhost:3000>
- admin: <http://localhost:4000>
- api: <http://localhost:8000/docs>

> **Note**: `.env` を編集したら再ビルドが必要なことがある
>
> 一部の環境変数はビルド時に埋め込まれるため、変更後は `docker compose down && docker compose up --build` が必要です。詳細は [開発者向けスタートガイド](https://digitaldemocracy2030.github.io/kouchou-ai/development/developer-quickstart) を参照。

その他のモード（フロントだけ触る / native 起動 / CLI 利用）と、環境変数の置き場所・よくある落とし穴は [開発者向けスタートガイド](https://digitaldemocracy2030.github.io/kouchou-ai/development/developer-quickstart) にまとめています。

## アーキテクチャ概要

| サービス | ポート | 役割 |
|---------|-------|------|
| public-viewer | 3000 | レポート閲覧用フロントエンド（Next.js） |
| admin | 4000 | レポート作成・管理用フロントエンド（Next.js） |
| api | 8000 | バックエンド API、レポート生成パイプライン（FastAPI） |
| ollama（オプション） | 11434 | ローカル LLM 推論 |

詳細：[ドキュメントサイト](https://digitaldemocracy2030.github.io/kouchou-ai/)

## デプロイ / 静的出力 / カスタマイズ

- [Azure 環境へのセットアップ](https://digitaldemocracy2030.github.io/kouchou-ai/deployment/azure)
- [GitHub Pages で静的ホスティング](https://digitaldemocracy2030.github.io/kouchou-ai/deployment/github-pages)
- [静的ホスティング向け CSP 設定](https://digitaldemocracy2030.github.io/kouchou-ai/deployment/static-hosting-csp)
- レポート作成者情報（ロゴ・リンク）のカスタマイズ → [ドキュメントサイト](https://digitaldemocracy2030.github.io/kouchou-ai/)

## 免責事項

大規模言語モデル（LLM）にはバイアスがあり、信頼性の低い結果を生成することが知られています。私たちはこれらの問題を軽減する方法に積極的に取り組んでいますが、現段階ではいかなる保証も提供することはできません。特に重要な決定を下す際は、本アプリの出力結果のみに依存せず、必ず内容を検証してください。

## 注意事項

本アプリは開発の初期段階であり、今後開発を進めていく過程で前バージョンと互換性のない変更が行われる可能性があります。アプリをアップデートする際には、重要なデータ（レポート）がある場合はアプリ・データのバックアップを保存した上でアップデートすることを推奨します。

## 開発者向けガイドライン

広聴 AI は OSS として開発されており、開発者の方からのコントリビュートを募集しています。詳しくは [コントリビューションガイド](https://digitaldemocracy2030.github.io/kouchou-ai/development/contributing) を参照ください。

AI エンジニア（Claude Code / Codex / Devin）との協働方針は [Claude Code / Codex スキル](https://digitaldemocracy2030.github.io/kouchou-ai/development/ai-assistants) と [Devin とのコラボレーション](https://digitaldemocracy2030.github.io/kouchou-ai/development/devin-collaboration) を参照してください。

## 機能要望・バグ報告について

- github アカウントをお持ちの方は [Issue](https://github.com/digitaldemocracy2030/kouchou-ai/issues) にバグ・改善要望を投稿してください
- github アカウントをお持ちでない方は [バグ報告・改善要望フォーム](https://docs.google.com/forms/d/e/1FAIpQLSf43rpi8N1hGQmECDOBOmiV3c-Buwf4gWSj2sYc2KbZL9NOBA/viewform?usp=dialog) より投稿してください

## クレジット

このプロジェクトは、[AI Objectives Institute](https://www.aiobjectivesinstitute.org/) が開発した [Talk to the City](https://github.com/AIObjectives/talk-to-the-city-reports) を参考に開発されており、ライセンスに基づいてソースコードを一部活用し、機能追加や改善を実施しています。ここに原作者の貢献に感謝の意を表します。
