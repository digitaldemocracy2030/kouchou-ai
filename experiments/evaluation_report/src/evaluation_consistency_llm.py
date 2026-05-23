import sys
from pathlib import Path

# このスクリプトから repo 直下の analysis-core/src を PYTHONPATH に追加
root_path = Path(__file__).resolve().parents[3] / "packages" / "analysis-core" / "src"
sys.path.insert(0, str(root_path))

import argparse
import json
import random
from pathlib import Path
from typing import Literal

import pandas as pd
from analysis_core.services.llm import request_to_chat_ai


def get_criteria_clarity() -> str:
    return """Clarity（明確さ）
評価対象: ラベルおよび説明文

1点: 何を伝えたいのかほとんどわからない。主語・述語があいまいで、意図が不明。
2点: 主旨は掴めるが曖昧な表現や冗長さがあり、推測が必要。
3点: おおむね意図は明確だが、情報の過不足や表現のぶれがある。
4点: 軽微な曖昧さのみで、ほとんどの箇所で明確に伝わる。
5点: 一読で完全に意図が伝わり、誤解の余地がない。
"""

def get_criteria_coherence() -> str:
    return """Coherence（一貫性）
評価対象: ラベルおよび説明文

1点: 論理のつながりが乏しく、要素がバラバラに並んでいる。
2点: 流れはあるが、話題転換や論理の飛躍が目立つ。
3点: 概ねつながっているが、一部あいまいな点や接続不足がある。
4点: 自然な流れで展開されており、小さな接続不足のみ。
5点: 論理的で一貫性があり、構成が明確。
"""

def get_criteria_distinctiveness() -> str:
    return """Distinctiveness（他意見グループとの差異）
評価対象: ラベルおよび説明文（全意見グループまとめて比較）

1点: 内容が他意見グループと大きく重複している。
2点: 一部独自要素はあるが、判別しにくい。
3点: 主要テーマは独自だが、細部に重複がある。
4点: 独自性が高く、他と区別しやすい。
5点: 完全に独自のテーマであり、明確に区別できる。

全体を通じて共通している「背景」や「前提」について勘案し、それらを差異評価の対象から除外してください。そのうえで、主張や論点の違いに注目して意見グループ間の差異を判断してください。
また、最後にdistinctiveness_commentとして全体を通しての「背景」や「前提」、類似点、改善案など総括を行ってください。総括では意見グループIDは使用せず必要があればラベル名を使ってください。
"""

def get_criteria_consistency() -> str:
    return """Consistency（意見の整合度）
評価対象: ラベル・説明文と意見グループ内の意見全体

1点: 説明が意見と全く関係なく、内容が乖離している／論理的に矛盾している。
2点: 意見の要点に触れているが、理由が不適切または論理の飛躍が大きい。
3点: 概ね意見と一致するが、一部に不自然な説明や論理の曖昧さがある。
4点: 意見と説明が整合しており、全体として自然な流れになっている。
5点: 意見と説明が密接に結びついており、論理的に一貫して納得感が高い。
"""

def get_prompt_criteria_text(criteria: list[str]) -> str:
    parts = []
    if "clarity" in criteria:
        parts.append(get_criteria_clarity())
    if "coherence" in criteria:
        parts.append(get_criteria_coherence())
    if "distinctiveness" in criteria:
        parts.append(get_criteria_distinctiveness())
    if "consistency" in criteria:
        parts.append(get_criteria_consistency())
    return "\n".join(parts)

def get_prompt_batch() -> str:
    return """以下の指標について、各意見グループを 1〜5 点で評価します。スコアは下記の基準に沿って判断してください。一見エラーのようなラベルでも全ての意見グループを採点してください。

""" + get_prompt_criteria_text(["distinctiveness"]) + """
出力形式は必ず JSON 形式でお願いします。
出力形式：
{
  "1_1": {
    "distinctiveness": 5
  },
  "1_2": {
    "distinctiveness": 4
  },
  "distinctiveness_comment": "全体を通じて『AI技術への期待』という前提が共通しており、多くの意見グループが社会的課題へのAIの応用可能性を扱っている。その中で、物流・交通や医療、教育といった具体的な応用分野に焦点を当てている意見グループは相対的に差異性が高い。一方、抽象的なAIの利点を繰り返す意見グループ間では内容が重複しているため、今後はラベルにより焦点の違いを明確にする工夫が求められる。"
}
"""

def get_prompt_cluster() -> str:
    return """以下の３指標について、1〜5 点で評価します。スコアは下記の基準に沿って判断してください。
その根拠となる簡潔なコメントを1〜2文で出力してください。
""" + get_prompt_criteria_text(["clarity", "coherence", "consistency"]) + """
出力形式は必ず JSON 形式でお願いします。
出力形式：
{
    "clarity": 5,
    "coherence": 5,
    "consistency": 5,
    "comment": "環境影響評価の透明性と信頼性を強調しており、意見も明確で一貫している。"
}
"""

def get_prompt_header_all_criteria() -> str:
    return """以下の４指標について、各意見グループを 1〜5 点で評価します。スコアは下記の基準に沿って判断してください。

""" + get_prompt_criteria_text(["clarity", "coherence", "distinctiveness", "consistency"]) + """
また、各意見グループには簡潔なコメント（comment）も必ず記述してください。
スコアの根拠や気づいた改善点・特徴などを1〜2文でわかりやすくまとめてください。

出力形式は必ず JSON 形式でお願いします。
出力形式：
{
  "1_1": {
    "clarity": 5,
    "coherence": 5,
    "distinctiveness": 5,
    "consistency": 5,
    "comment": "環境影響評価の透明性と信頼性を強調しており、意見も明確で一貫している。"
  },
  ...
  "distinctiveness_comment": "全体を通じて『AI技術への期待』という前提が共通しており、多くの意見グループが社会的課題へのAIの応用可能性を扱っている。その中で、物流・交通や医療、教育といった具体的な応用分野に焦点を当てている意見グループは相対的に差異性が高い。一方、抽象的なAIの利点を繰り返す意見グループ間では内容が重複しているため、今後はラベルにより焦点の違いを明確にする工夫が求められる。"
}
"""

def format_prompt_for_all_criteria(cluster_data: dict) -> str:
    prompt = get_prompt_header_all_criteria()
    for cluster_id, data in cluster_data.items():
        prompt += "\n" + "=" * 30 + f"\n【意見グループID】{cluster_id}\n"
        prompt += f"【ラベル】{data['label']}\n"
        prompt += f"【説明】\n{data['description']}\n"
        prompt += "【意見】\n"
        for arg in data["arguments"]:
            prompt += f"- {arg}\n"
    return prompt

def evaluate_all_criteria_prompt_only(cluster_data: dict, output_path: Path = None):
    prompt = format_prompt_for_all_criteria(cluster_data)
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"📄 プロンプトを保存しました: {output_path}")
    else:
        print(prompt)
def load_cluster_data(dataset_path: Path, level: int, max_samples: int) -> dict:
    args_df = pd.read_csv(dataset_path / "args.csv")
    labels_df = pd.read_csv(dataset_path / "hierarchical_merge_labels.csv")
    clusters_df = pd.read_csv(dataset_path / "hierarchical_clusters.csv")

    cluster_col = f"cluster-level-{level}-id"
    cluster_data = {}

    all_args = {}
    for _, row in labels_df[labels_df["level"] == level].iterrows():
        cluster_id = row["id"]
        label = row["label"]
        description = row["description"]
        cluster_args = clusters_df[clusters_df[cluster_col] == cluster_id]["argument"].tolist()
        all_args[cluster_id] = {
            "label": label,
            "description": description,
            "arguments": cluster_args,
        }

    total_clusters = len(all_args)
    total_items = sum(len(v["arguments"]) for v in all_args.values())

    if max_samples < total_clusters:
        raise ValueError(f"max-samples({max_samples}) is less than number of clusters({total_clusters})")

    if total_items > max_samples:
        print(f"⚠️ 入力データ {total_items} 件が max-samples({max_samples}) を超えているため、一部抜粋されます。")

    remaining_budget = max_samples - total_clusters

    for cid, data in all_args.items():
        arg_count = len(data["arguments"])
        ratio = arg_count / total_items if total_items else 0
        extra = int(ratio * remaining_budget)
        count = min(arg_count, 1 + extra)
        cluster_data[cid] = {
            "label": data["label"],
            "description": data["description"],
            "arguments": data["arguments"][:count],
        }

    return cluster_data



def format_batch_prompt_for_ccd(cluster_data: dict) -> str:
    prompt = get_prompt_batch()
    for cluster_id, data in cluster_data.items():
        prompt += "\n" + "=" * 30 + f"\n【意見グループID】{cluster_id}\n"
        prompt += f"【ラベル】{data['label']}\n"
        prompt += f"【説明】\n{data['description']}\n"
    return prompt

def format_prompt_for_consistency(cluster_id: str, data: dict) -> str:
    prompt = get_prompt_cluster()
    prompt += f"\n【意見グループID】{cluster_id}\n"
    prompt += f"【ラベル】{data['label']}\n"
    prompt += f"【説明】\n{data['description']}\n"
    prompt += "【意見】\n"
    for arg in data["arguments"]:
        prompt += f"- {arg}\n"
    return prompt


def evaluate_batch_clarity_coherence_distinctiveness(cluster_data: dict, model: str, mode: str) -> dict:
    if mode == "print":
        prompt = format_batch_prompt_for_ccd(cluster_data)
        print(prompt)
        return {}

    messages = [
        {"role": "system", "content": "あなたは評価者です。"},
        {"role": "user", "content": format_batch_prompt_for_ccd(cluster_data)}
    ]
    try:
        response = request_to_chat_ai(messages=messages, model=model, is_json=True)
        results = json.loads(response)
        for cluster_id in cluster_data:
            if cluster_id in results:
                results[cluster_id]["label"] = cluster_data[cluster_id]["label"]
            else:
                print(f"⚠️ 意見グループ {cluster_id} の評価結果がレスポンスに見つかりませんでした。")
        return results
    except Exception as e:
        print(f"❌ バッチ評価に失敗: {e}")
        return {}

def evaluate_consistency_per_cluster(cluster_data: dict, model: str) -> dict:
    results = {}
    for cluster_id, data in cluster_data.items():
        prompt = format_prompt_for_consistency(cluster_id, data)
        messages = [
            {"role": "system", "content": "あなたは評価者です。"},
            {"role": "user", "content": prompt}
        ]
        try:
            response = request_to_chat_ai(messages=messages, model=model, is_json=True)
            result = json.loads(response)
            results[cluster_id] = result
        except Exception as e:
            print(f"❌ 意見グループ {cluster_id} のConsistency評価に失敗: {e}")
    return results


def merge_ccd_and_consistency(ccd: dict, consistency: dict) -> dict:
    merged = {}
    for cluster_id in ccd:
        if isinstance(ccd[cluster_id], dict) and isinstance(consistency.get(cluster_id), dict):
            merged[cluster_id] = {
                **ccd.get(cluster_id, {}),
                **consistency.get(cluster_id, {})
            }
    # distinctiveness_comment のような補足データも残したい場合：
    for key in ccd:
        if key not in merged and not isinstance(ccd[key], dict):
            merged[key] = ccd[key]
    return merged

def save_results(results: dict, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"✓ 結果を保存しました: {output_path}")

def load_cluster_data(dataset_path: Path, level: int, max_samples: int) -> dict:
    args_df = pd.read_csv(dataset_path / "args.csv")
    labels_df = pd.read_csv(dataset_path / "hierarchical_merge_labels.csv")
    clusters_df = pd.read_csv(dataset_path / "hierarchical_clusters.csv")

    cluster_col = f"cluster-level-{level}-id"
    cluster_data = {}

    all_args = {}
    for _, row in labels_df[labels_df["level"] == level].iterrows():
        cluster_id = row["id"]
        label = row["label"]
        description = row["description"]
        cluster_args = clusters_df[clusters_df[cluster_col] == cluster_id]["argument"].tolist()
        all_args[cluster_id] = {
            "label": label,
            "description": description,
            "arguments": cluster_args,
        }

    total_clusters = len(all_args)
    total_items = sum(len(v["arguments"]) for v in all_args.values())

    if max_samples < total_clusters:
        raise ValueError(f"max-samples({max_samples}) is less than number of clusters({total_clusters})")

    if total_items > max_samples:
        print(f"⚠️ 入力データ {total_items} 件が max-samples({max_samples}) を超えているため、一部抜粋されます。")

    remaining_budget = max_samples - total_clusters

    for cid, data in all_args.items():
        arg_count = len(data["arguments"])
        ratio = arg_count / total_items if total_items else 0
        extra = int(ratio * remaining_budget)
        count = min(arg_count, 1 + extra)
        cluster_data[cid] = {
            "label": data["label"],
            "description": data["description"],
            "arguments": data["arguments"][:count],
        }

    return cluster_data


def main():
    parser = argparse.ArgumentParser(description="意見グループ整合性評価（LLM使用）")
    parser.add_argument("--dataset", required=True, help="例: example")
    parser.add_argument("--level", type=int, default=1)
    parser.add_argument("--max-samples", type=int, default=1000)
    parser.add_argument("--mode", choices=["api", "print"], default="api")
    parser.add_argument("--model", default="gpt-4o-mini")
    args = parser.parse_args()

    dataset_path = Path("inputs") / args.dataset
    output_dir = Path("inputs") / args.dataset #他の処理のinputになるのでinputsにした
    cluster_data = load_cluster_data(dataset_path, args.level, args.max_samples)

    if args.mode == "print":
        output_path = Path("outputs") / args.dataset / f"prompt_level{args.level}.txt"
        evaluate_all_criteria_prompt_only(cluster_data, output_path)
        return    
    ccd_result = evaluate_batch_clarity_coherence_distinctiveness(cluster_data, args.model, args.mode)
    consistency_result = evaluate_consistency_per_cluster(cluster_data, args.model)

    if args.mode == "api":
        save_results(ccd_result, output_dir / f"evaluation_consistency_llm_level{args.level}_ccd.json")
        save_results(consistency_result, output_dir / f"evaluation_consistency_llm_level{args.level}_consistency.json")

        # 統合結果の保存
        merged = merge_ccd_and_consistency(ccd_result, consistency_result)
        save_results(merged, output_dir / f"evaluation_consistency_llm_level{args.level}.json")

if __name__ == "__main__":
    main()
