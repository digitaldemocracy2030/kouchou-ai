import argparse
import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    print(f"\n=== {description} ===")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"❌ {description} に失敗しました")
        sys.exit(result.returncode)


def all_exist(paths):
    return all(p.exists() for p in paths)


def script_path(script_name):
    # このスクリプトと同じディレクトリ内にあるスクリプトを呼び出す
    return str((Path(__file__).parent / script_name).resolve())


def main():
    parser = argparse.ArgumentParser(description="クラスタ評価一括実行スクリプト")
    parser.add_argument("dataset", help="データセットID（例: 2）")
    parser.add_argument("--level", choices=["1", "2", "both"], default="both", help="評価レベル（1, 2, both）")
    parser.add_argument("--max-samples", type=int, help="LLMプロンプトに含める最大意見数（省略可）")
    parser.add_argument("--mode", choices=["api", "print"], default="api", help="LLM評価の実行モード（api or print）")
    parser.add_argument("--model", help="使用するOpenAIモデル名（例: gpt-4o）")
    args = parser.parse_args()

    dataset = args.dataset
    level_option = args.level
    input_dir = Path("inputs") / dataset
    output_dir = Path("outputs") / dataset
    # 出力ディレクトリが存在しなければ作成
    output_dir.mkdir(parents=True, exist_ok=True)
    levels = [1, 2] if level_option == "both" else [int(level_option)]

    # mode=print の場合は先にLLMプロンプト出力のみ行い、結果を使うように案内
    if args.mode == "print":
        for level in levels:
            print(f"\n=== ステップ: LLMプロンプト出力（level {level}） ===")

            # prompt_level{level}.txt の出力を前提として評価スクリプトに任せる
            cmd = (
                f"python {script_path('evaluation_consistency_llm.py')} "
                f"--dataset {dataset} --level {level} --mode print"
            )
            if args.max_samples:
                cmd += f" --max-samples {args.max_samples}"
            if args.model:
                cmd += f" --model {args.model}"

            run_command(cmd, f"LLMプロンプト出力（level {level}）")

            print(f"📄 定性評価用プロンプトを output/{dataset}/prompt_level{level}.txt に保存しました。")
            print(f"💾 実行結果を output/{dataset}/evaluation_consistency_llm_level{level}.json に保存すれば、CSVやHTMLで利用できます。")
        return

    for level in levels:
        print(f"\n=== ステップ1: シルエットスコア（level {level}） ===")
        required_files = [
            input_dir / f"silhouette_umap_level{level}_clusters.json",
            input_dir / f"silhouette_umap_level{level}_points.json"
        ]
        if all_exist(required_files):
            for f in required_files:
                print(f"✅ 出力ファイルが存在するためスキップします: {f}")
        else:
            cmd = f"python {script_path('evaluate_silhouette_score.py')} --dataset {dataset} --level {level} --source umap"
            run_command(cmd, f"シルエットスコア計算（level {level}）")

    for level in levels:
        print(f"\n=== ステップ2: LLM評価（level {level}） ===")
        out_path = input_dir / f"evaluation_consistency_llm_level{level}.json"
        if out_path.exists():
            print(f"✅ 出力ファイルが存在するためスキップします: {out_path}")
        else:
            cmd = (
                f"python {script_path('evaluation_consistency_llm.py')} "
                f"--dataset {dataset} --level {level} --mode {args.mode}"
            )
            if args.max_samples:
                cmd += f" --max-samples {args.max_samples}"
            if args.model:
                cmd += f" --model {args.model}"

            run_command(cmd, f"LLM評価（level {level}）")

    print(f"\n=== ステップ3: CSV出力 ===")
    run_command(f"python {script_path('generate_csv.py')} {dataset}", "CSV出力")
    print(f"✓ CSV出力完了:")
    print(f" - クラスタ: {output_dir / 'cluster_evaluation.csv'}")
    print(f" - 意見:     {output_dir / 'comment_evaluation.csv'}")

    print(f"\n=== ステップ4: HTMLレポート生成 ===")
    run_command(f"python {script_path('generate_html.py')} {dataset}", "HTMLレポート生成")
    print(f"✓ HTML出力完了: {output_dir / 'report.html'}")


if __name__ == "__main__":
    main()
