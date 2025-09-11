#!/usr/bin/env python3
"""
GitHub Issues fetcher for kouchou-ai problem awareness analysis
Fetches issues from digitaldemocracy2030/kouchou-ai and outputs CSV for pipeline processing
"""

import os
import csv
import argparse
from github import Github
from dotenv import load_dotenv

if not os.getenv('GITHUB_ACTIONS'):
    load_dotenv()

def fetch_github_issues(repo_name="digitaldemocracy2030/kouchou-ai", output_file="github_issues.csv"):
    """
    Fetch GitHub issues and save to CSV format compatible with kouchou-ai pipeline
    
    Args:
        repo_name: GitHub repository in format "owner/repo"
        output_file: Output CSV file path
    """
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("Warning: GITHUB_TOKEN environment variable not found.")
        print("Creating sample data for testing purposes.")
        create_sample_issues_csv(output_file)
        return
    
    try:
        github = Github(github_token)
        repo = github.get_repo(repo_name)
        
        issues = repo.get_issues(state='open', sort='created', direction='desc')
        
        csv_data = []
        for i, issue in enumerate(issues):
            if issue.pull_request:  # Skip pull requests
                continue
                
            csv_data.append({
                'comment-id': issue.number,
                'comment-body': f"{issue.title}\n\n{issue.body or ''}".strip(),
                'source': 'GitHub Issues',
                'url': issue.html_url,
                'created_at': issue.created_at.isoformat(),
                'state': issue.state,
                'labels': ','.join([label.name for label in issue.labels])
            })
        
        if csv_data:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['comment-id', 'comment-body', 'source', 'url', 'created_at', 'state', 'labels']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)
            
            print(f"Fetched {len(csv_data)} issues and saved to {output_file}")
        else:
            print("No issues found")
    except Exception as e:
        print(f"Error fetching GitHub issues: {e}")
        print("Creating sample data for testing purposes.")
        create_sample_issues_csv(output_file)

def create_sample_issues_csv(output_file):
    """Create sample GitHub issues CSV for testing when API is not available"""
    sample_data = [
        {
            'comment-id': 1,
            'comment-body': '機能追加: ユーザーが意見を投稿する際の入力フォームが使いにくい\n\n現在の意見投稿フォームは以下の問題があります：\n- 文字数制限が不明確\n- リアルタイムプレビューがない\n- 投稿前の確認画面がない',
            'source': 'GitHub Issues',
            'url': 'https://github.com/digitaldemocracy2030/kouchou-ai/issues/1',
            'created_at': '2024-01-15T10:30:00Z',
            'state': 'open',
            'labels': 'enhancement,ui'
        },
        {
            'comment-id': 2,
            'comment-body': 'バグ報告: レポート生成時にメモリ不足エラーが発生する\n\n大量のコメントデータ（10,000件以上）でレポート生成を実行すると、メモリ不足でプロセスが停止する。',
            'source': 'GitHub Issues',
            'url': 'https://github.com/digitaldemocracy2030/kouchou-ai/issues/2',
            'created_at': '2024-01-16T14:20:00Z',
            'state': 'open',
            'labels': 'bug,performance'
        },
        {
            'comment-id': 3,
            'comment-body': 'ドキュメント改善: APIの使用方法が不明確\n\n開発者向けドキュメントにAPIの詳細な使用例が不足している。特に認証方法とエラーハンドリングについて。',
            'source': 'GitHub Issues',
            'url': 'https://github.com/digitaldemocracy2030/kouchou-ai/issues/3',
            'created_at': '2024-01-17T09:15:00Z',
            'state': 'open',
            'labels': 'documentation'
        },
        {
            'comment-id': 4,
            'comment-body': 'パフォーマンス改善: 大量データ処理の最適化が必要\n\nクラスタリング処理において、データ量が増加すると処理時間が指数的に増加する問題がある。',
            'source': 'GitHub Issues',
            'url': 'https://github.com/digitaldemocracy2030/kouchou-ai/issues/4',
            'created_at': '2024-01-18T16:45:00Z',
            'state': 'open',
            'labels': 'performance,enhancement'
        },
        {
            'comment-id': 5,
            'comment-body': 'セキュリティ: 認証機能の強化が必要\n\n現在の認証システムでは、APIキーの管理が不十分で、セキュリティリスクが存在する。',
            'source': 'GitHub Issues',
            'url': 'https://github.com/digitaldemocracy2030/kouchou-ai/issues/5',
            'created_at': '2024-01-19T11:30:00Z',
            'state': 'open',
            'labels': 'security,enhancement'
        }
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['comment-id', 'comment-body', 'source', 'url', 'created_at', 'state', 'labels']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample_data)
    
    print(f"Created sample GitHub issues CSV with {len(sample_data)} entries: {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub issues for kouchou-ai analysis")
    parser.add_argument("--repo", default="digitaldemocracy2030/kouchou-ai", 
                       help="GitHub repository (default: digitaldemocracy2030/kouchou-ai)")
    parser.add_argument("--output", default="github_issues.csv",
                       help="Output CSV file (default: github_issues.csv)")
    
    args = parser.parse_args()
    fetch_github_issues(args.repo, args.output)

if __name__ == "__main__":
    main()
