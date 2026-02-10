# Claude Code / Codex で skills を使う

このリポジトリでは、`skills/` に Codex 用のスキルを置き、`CLAUDE.md` を案内役として使います。
特に `kouchou-ai-architecture` のようなスキルは、アーキテクチャの説明やディレクトリ把握に役立ちます。

## 前提
- スキル本体は `skills/` 以下にあります。
- `CLAUDE.md` はスキルの索引として使います。
- Playwright E2E の詳細は `test/e2e/CLAUDE.md` を参照します。

## Claude Code で使う
Claude Code は `CLAUDE.md` を自動で読み込みます。必要なスキルの `SKILL.md` を開くよう指示してください。

### 例
```
skills/kouchou-ai-architecture/SKILL.md を参照して、主要サービスとポートを説明して。
```

```
skills/kouchou-ai-development/SKILL.md を読んで、ローカル開発の起動手順をまとめて。
```

## Codex で使う
Codex は `$CODEX_HOME/skills` にあるスキルを読み込むため、`skills/` の各フォルダをリンクまたはコピーします。

### セットアップ例（シンボリックリンク）
```
export CODEX_HOME="$HOME/.codex"
ln -s /path/to/kouchou-ai/skills/kouchou-ai-architecture "$CODEX_HOME/skills/"
ln -s /path/to/kouchou-ai/skills/kouchou-ai-development "$CODEX_HOME/skills/"
ln -s /path/to/kouchou-ai/skills/kouchou-ai-testing "$CODEX_HOME/skills/"
```

### 使い方のポイント
- 依頼文にスキル名を含めると読み込みが確実になります。

#### 例
```
kouchou-ai-architecture を使って、パイプラインの流れと主要ディレクトリを説明して。
```

```
kouchou-ai-testing を使って、E2E テストの注意点をまとめて。
```

## 運用のコツ
- スキルを更新したら `CLAUDE.md` の索引も更新します。
- Codex 側でコピー運用している場合は、更新後に再コピーします。
