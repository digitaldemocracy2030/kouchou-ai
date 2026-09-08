# AIエージェントを使ったコントリビュート

このページは、Claude Code / CodexでIssueに着手してからPRを提出するまでの入口です。コマンドやテストの詳細は、担当する領域のガイドを参照してください。

## 最初に読む順番

1. [コントリビューション](contributing.md)：担当の割り当て、実装計画、CLA、PRのルール。
2. このページ：作業の流れとタスク別の参照先。
3. [CLAUDE.md](https://github.com/digitaldemocracy2030/kouchou-ai/blob/main/CLAUDE.md)：リポジトリ内のskillsの索引。
4. 下表の必要なskill。E2Eを変更・実行する場合は[E2E開発ガイド](https://github.com/digitaldemocracy2030/kouchou-ai/blob/main/test/e2e/CLAUDE.md)も読む。

`CONTRIBUTING.md`を貢献ルールの正本、このページを作業導線、`CLAUDE.md`を短い索引、各skillを領域別手順として扱います。同じ手順を複数の場所に書き足すより、正本を更新してリンクしてください。

## タスクごとに追加で読むもの

| 作業 | 参照先 | 確認すること |
|---|---|---|
| 構造を把握する | [architecture skill](https://github.com/digitaldemocracy2030/kouchou-ai/blob/main/skills/kouchou-ai-architecture/SKILL.md) | サービス境界、コードの所在、パイプライン |
| ローカル起動・設定・ビルド | [development skill](https://github.com/digitaldemocracy2030/kouchou-ai/blob/main/skills/kouchou-ai-development/SKILL.md) | 起動方法、環境変数、pnpm、lint |
| 管理画面・公開viewer | development skill + [testing skill](https://github.com/digitaldemocracy2030/kouchou-ai/blob/main/skills/kouchou-ai-testing/SKILL.md) | 対象appのテスト、型検査、表示と操作 |
| API・analysis-core | architecture skill + development skill + testing skill | 変更した層のテスト、呼出元への影響 |
| Playwright E2E | testing skill + E2E開発ガイド | dummy-server、事前検証、本番に近いfixture、画面遷移後の待機 |

文書で構造を掴んだ後は、作業対象ブランチのソースコードと既存テストで現在の挙動を確かめます。

## エージェントの準備

リポジトリをcloneし、そのディレクトリをClaude Code / Codexの作業対象として開きます。最小構成では、skillsのインストールをせず、必要なファイルをパスで指定して読むよう依頼できます。

```text
CONTRIBUTING.md、CLAUDE.md、docs/development/ai-assistants.mdを読んでください。
Issueの本文・コメント・担当とopen PRを確認してください。
今回は管理画面の修正なので、skills/kouchou-ai-development/SKILL.mdと
skills/kouchou-ai-testing/SKILL.mdを読んでから実装・検証してください。
```

Claude Codeでは`CLAUDE.md`が入口です。Codexにも上記のように明示しておけば、自動読込の設定に依存せず参照先を伝えられます。

### Codexのスキル一覧から使いたい場合（任意）

現在の[公式スキル案内](https://learn.chatgpt.com/docs/build-skills)では、リポジトリ内の`.agents/skills`が探索対象です。本repoの正本は`skills/`なので、macOS / Linuxではrepoルートで次のようにリンクできます。既存の同名リンク・ディレクトリがある場合は、先に内容を確認してください。

```bash
mkdir -p .agents/skills
ln -s ../../skills/kouchou-ai-architecture .agents/skills/kouchou-ai-architecture
ln -s ../../skills/kouchou-ai-development .agents/skills/kouchou-ai-development
ln -s ../../skills/kouchou-ai-testing .agents/skills/kouchou-ai-testing
```

これは任意のローカル設定です。設定をPRに含める必要はありません。Windowsなどでリンクが難しい場合は、上のファイルパス指定で始められます。古いコピーを作っている場合は更新漏れに注意し、読み込まれたskillのパスと内容を確認してください。

## IssueからPRまで

1. Issueの本文・コメント・assigneeと関連するopen PRを確認する。他の担当者がいる場合は重複実装を始めない。未担当なら自分にassignする（権限がなければ貢献ガイドの`/assign`手順）。
2. 最新mainからtopic branchまたはworktreeを作る。既存の未コミット変更を混ぜない。新機能や広い変更は貢献ガイドに沿って計画を共有する。
3. 不具合の再現条件と変更後の期待動作を定め、必要なガイドを読んで実装する。
4. 変更した領域のテスト・lint・型検査を行う。E2Eでは事前検証を先に実行する。UIは実際の表示と操作も確認する。
5. [PRテンプレート](https://github.com/digitaldemocracy2030/kouchou-ai/blob/main/.github/PULL_REQUEST_TEMPLATE.md)に問題・変更後の動作・関連Issue・検証結果を書く。未検証の項目、既存の失敗、実API確認の有無は区別する。
6. CI結果と差分を確認し、失敗があれば原因を調べる。テストが通ったことと人間によるレビュー・マージは別の状態として報告する。

### serverlessにも関係する変更

[kouchou-ai-serverless](https://github.com/tokoroten/kouchou-ai-serverless)は別repoです。そちらの作業ルールとopen PRも読み、同じ入力・結果表示に影響する変更では対応するPRを相互リンクしてください。同じ入力例で挙動を確認し、差がある場合は理由をPRに残します。片方のテスト成功だけで両版の互換性や実動を確認済みとしません。

## 人間の判断・attentionを使う操作

Issueの調査・実装・テスト・PR準備と、他者への通知や承認は分けて扱います。AIエージェントは、reviewer request、承認の催促、Slack等への連絡、対人escalation、admin mergeを人間の明示指示なしに行いません。

CLAへの同意や人間の動作確認をAIが代わりに済ませたことにしないでください。必要な判断を相談する場合は、先に差分・検証結果・未確認点を揃え、何を判断すればよいかが分かる形にします。
