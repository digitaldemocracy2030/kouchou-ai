#!/usr/bin/env python3
"""
Complete GitHub Issues analysis workflow
Fetches issues, runs kouchou-ai pipeline, and generates analysis report
"""

import subprocess
import sys
from pathlib import Path


def main():
    script_dir = Path(__file__).parent
    server_dir = script_dir.parent
    pipeline_dir = server_dir / "broadlistening" / "pipeline"
    
    print("=== GitHub Issues 問題意識分析 ===")
    
    print("1. GitHub Issuesを取得中...")
    fetch_script = script_dir / "fetch_github_issues.py"
    csv_output = pipeline_dir / "inputs" / "github-issues.csv"
    
    result = subprocess.run([
        sys.executable, str(fetch_script),
        "--output", str(csv_output)
    ], cwd=script_dir)
    
    if result.returncode != 0:
        print("GitHub Issues取得に失敗しました")
        return 1
    
    print("2. パイプライン分析を実行中...")
    config_path = pipeline_dir / "configs" / "github-issues-analysis.json"
    
    result = subprocess.run([
        sys.executable, "hierarchical_main.py",
        str(config_path),
        "--skip-interaction",
        "--without-html"
    ], cwd=pipeline_dir)
    
    if result.returncode != 0:
        print("パイプライン分析に失敗しました")
        return 1
    
    print("3. 分析完了！")
    output_dir = pipeline_dir / "outputs" / "github-issues"
    print(f"結果は {output_dir} に保存されました")
    print("- hierarchical_result.json: 分析結果")
    print("- final_result_with_comments.csv: コメント付きCSV")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
