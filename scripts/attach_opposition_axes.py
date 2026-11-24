"""同じレポートから事前計算した可視化カタログの DivCon 結果を添付する。"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def discussion_points(consensus: dict, key: str) -> list[str]:
    return [item["point"] for item in consensus.get(key, [])]


def attach_axes(report: dict, divcon: dict) -> dict:
    clusters = {
        cluster["id"]: cluster for cluster in report["clusters"] if cluster["level"] > 0
    }
    members: dict[str, set[str]] = defaultdict(set)
    for argument in report["arguments"]:
        for cluster_id in argument["cluster_ids"]:
            members[cluster_id].add(argument["arg_id"])

    topic_ids = set()
    for topic in divcon["topics"]:
        cluster_id = topic["cluster_id"]
        if cluster_id in topic_ids or cluster_id not in clusters:
            raise ValueError(
                f"クラスタが重複しているか、レポートにありません: {cluster_id}"
            )
        if topic["label"] != clusters[cluster_id]["label"] or topic["n"] != len(
            members[cluster_id]
        ):
            raise ValueError(
                f"クラスタのラベルまたは所属件数が一致しません: {cluster_id}"
            )
        topic_ids.add(cluster_id)

    axes = []
    used = set()
    for item in divcon["axes"]:
        axis_id = item["id"]
        cluster_id = item["cluster_id"]
        if axis_id in used or cluster_id not in topic_ids:
            raise ValueError(f"対立軸が重複しているか、クラスタが不明です: {axis_id}")
        used.add(axis_id)
        scores: dict[str, int | None] = {}
        for arg_id, score, _reason in divcon["scores"][axis_id]:
            if arg_id not in members[cluster_id] or arg_id in scores:
                raise ValueError(
                    f"意見がクラスタ外にあるか、採点が重複しています: {axis_id} / {arg_id}"
                )
            if type(score) is not int or not 1 <= score <= 6:
                raise ValueError(
                    f"採点が 1～6 の整数ではありません: {axis_id} / {arg_id}"
                )
            scores[arg_id] = score
        n_na, n_missing = item["n_na"], item["n_missing"]
        if (
            len(scores) != item["n_scored"]
            or n_na < 0
            or n_missing < 0
            or len(scores) + n_na + n_missing != len(members[cluster_id])
        ):
            raise ValueError(f"採点・該当なし・未採点の件数が合いません: {axis_id}")

        # カタログの JSON は該当なしの ID を保存しない。応答漏れが 0 の軸だけ補える。
        if n_missing == 0:
            scores.update(dict.fromkeys(sorted(members[cluster_id] - scores.keys())))
        axis = {
            key: item[key]
            for key in ("id", "cluster_id", "name", "left_pole", "right_pole")
        }
        axis["scores"] = scores
        if consensus := item.get("consensus"):
            axis["agreements"] = discussion_points(consensus, "consensus_points")
            axis["conflicts"] = discussion_points(consensus, "conflict_points")
        axes.append(axis)

    return {**report, "opposition_axes": axes}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("divcon", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="新しい出力ファイル")
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        divcon = json.loads(args.divcon.read_text(encoding="utf-8"))
        result = attach_axes(report, divcon)
        with args.out.open("x", encoding="utf-8") as output:
            json.dump(result, output, ensure_ascii=False, separators=(",", ":"))
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
