# GitHub Issues Analysis Scripts

このディレクトリには、GitHub IssuesからkouchouAIパイプラインで問題意識を抽出・分析するためのスクリプトが含まれています。

## スクリプト一覧

### fetch_github_issues.py
GitHub Issuesを取得してCSV形式で出力するスクリプト

**使用方法:**
```bash
# GitHub APIトークンが設定されている場合
export GITHUB_TOKEN=your_token_here
python fetch_github_issues.py --repo digitaldemocracy2030/kouchou-ai --output github_issues.csv

# APIトークンがない場合（サンプルデータを生成）
python fetch_github_issues.py --output github_issues.csv
```

**出力CSV形式:**
- comment-id: Issue番号
- comment-body: Issueタイトルと本文
- source: "GitHub Issues"
- url: GitHub IssueのURL（散布図からのジャンプ用）
- created_at: 作成日時
- state: Issue状態
- labels: ラベル一覧

### analyze_github_issues.py
GitHub Issues取得からパイプライン実行までの完全なワークフロー

**使用方法:**
```bash
python analyze_github_issues.py
```

**実行内容:**
1. GitHub Issuesの取得（fetch_github_issues.py）
2. kouchou-aiパイプラインの実行（問題意識抽出・クラスタリング）
3. 結果の出力（CSV、JSON）

## 設定ファイル

### ../broadlistening/pipeline/configs/github-issues-analysis.json
GitHub Issues分析用のパイプライン設定

**主要設定:**
- extraction.prompt: 問題意識抽出用プロンプト
- enable_source_link: true（URLフィールドを有効化）
- categories: 問題カテゴリ分類設定

## 出力ファイル

### ../broadlistening/pipeline/outputs/github-issues/
- hierarchical_result.json: 分析結果（可視化用）
- final_result_with_comments.csv: コメント付きCSV（URLフィールド含む）

## 注意事項

- GitHub APIトークンが必要（GITHUB_TOKEN環境変数）
- OpenAI APIキーが必要（パイプライン実行時）
- APIキーがない場合はサンプルデータで動作確認可能
