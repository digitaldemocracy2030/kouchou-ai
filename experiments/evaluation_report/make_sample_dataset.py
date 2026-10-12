"""評価ハーネス用の小さな同梱サンプルデータセットを生成するスクリプト。

実際の意見・コメントは一切含まない完全な合成データ（市政アンケートを模した
ダミーテキスト）で、クラスタリング pipeline の出力ファイル形式だけを忠実に
再現する。巨大 JSON・embeddings・秘匿情報は含めない。

生成物は ``inputs/sample/`` に置かれ、これを入力に ``evaluate_silhouette_score.py``
→ ``generate_csv.py`` → ``generate_html.py`` が追加の取得なしで走る。

使い方::

    python make_sample_dataset.py          # inputs/sample/ を生成（既定）
    python make_sample_dataset.py --dataset sample

決定論的（乱数シード固定）なので、第三者が再生成しても同じ結果になる。
"""

import argparse
import csv
import json
import math
from pathlib import Path

import numpy as np

# --- サンプル設計 ------------------------------------------------------------
# 3 つの level-1 クラスタ（大テーマ）、各 2 つの level-2 サブクラスタ = 6 クラスタ。
# 各 level-2 クラスタに 4 件ずつの合成「意見」を割り当て、合計 24 件。
# 2D 座標 (x, y) は umap 出力を模し、クラスタごとに離れた中心の周りへ配置する。

LEVEL1 = {
    "1_0": {
        "label": "公共交通の利便性",
        "description": "バス路線や自転車利用など、移動手段の使いやすさに関する意見のまとまり。",
        "center": (0.0, 0.0),
    },
    "1_1": {
        "label": "公園と緑地の整備",
        "description": "遊具や緑地の管理など、公園空間の質に関する意見のまとまり。",
        "center": (10.0, 0.0),
    },
    "1_2": {
        "label": "図書館サービス",
        "description": "開館時間や蔵書など、図書館の利用環境に関する意見のまとまり。",
        "center": (5.0, 9.0),
    },
}

# level-2: id -> (parent level-1 id, ラベル, 説明, 中心オフセット, 意見リスト)
LEVEL2 = {
    "2_0": {
        "parent": "1_0",
        "label": "バス路線の拡充",
        "description": "運行本数の増加や路線網の見直しを求める意見。",
        "offset": (-1.2, -1.2),
        "arguments": [
            "朝夕のバスの本数を増やしてほしい。",
            "郊外へ向かうバス路線を新設してほしい。",
            "最終バスの時刻をもっと遅くしてほしい。",
            "乗り換えなしで中心部へ行ける路線がほしい。",
        ],
    },
    "2_1": {
        "parent": "1_0",
        "label": "自転車環境の改善",
        "description": "自転車レーンや駐輪場の整備を求める意見。",
        "offset": (1.2, 1.2),
        "arguments": [
            "幹線道路に自転車専用レーンを整備してほしい。",
            "駅前の駐輪場が不足しているので増やしてほしい。",
            "シェアサイクルの拠点を増やしてほしい。",
            "歩行者と自転車の動線を分けて安全にしてほしい。",
        ],
    },
    "2_2": {
        "parent": "1_1",
        "label": "遊具の充実",
        "description": "子ども向け遊具の種類や安全性に関する意見。",
        "offset": (-1.2, -1.2),
        "arguments": [
            "幼児でも遊べる低い遊具を増やしてほしい。",
            "老朽化した遊具を早めに更新してほしい。",
            "雨の日でも遊べる屋根付きの広場がほしい。",
            "バリアフリーで誰でも使える遊具を設置してほしい。",
        ],
    },
    "2_3": {
        "parent": "1_1",
        "label": "緑地の維持管理",
        "description": "芝生や樹木の手入れ、清掃に関する意見。",
        "offset": (1.2, 1.2),
        "arguments": [
            "芝生の手入れの頻度を上げてほしい。",
            "落ち葉や雑草の清掃をこまめに行ってほしい。",
            "花壇の植え替えで季節感を出してほしい。",
            "木陰になる高木をもっと植えてほしい。",
        ],
    },
    "2_4": {
        "parent": "1_2",
        "label": "開館時間の延長",
        "description": "平日夜間や休日の開館時間に関する意見。",
        "offset": (-1.2, -1.2),
        "arguments": [
            "平日の閉館時間を延ばして夜も使えるようにしてほしい。",
            "日曜も開館してほしい。",
            "祝日の開館日を増やしてほしい。",
            "試験期間は自習室の利用時間を延長してほしい。",
        ],
    },
    "2_5": {
        "parent": "1_2",
        "label": "蔵書の拡充",
        "description": "書籍のジャンルや新刊の取り揃えに関する意見。",
        "offset": (1.2, 1.2),
        "arguments": [
            "新刊の入荷を早くしてほしい。",
            "専門書や技術書をもっと増やしてほしい。",
            "子ども向けの絵本の種類を増やしてほしい。",
            "電子書籍の貸出に対応してほしい。",
        ],
    },
}

QUESTION = "サンプル自治体アンケート（合成データ）"
OVERVIEW = (
    "これはクラスタ品質評価ハーネスの動作確認用に生成された完全な合成データセットです。"
    "実在する意見・個人情報は含まれていません。"
)


def build() -> dict:
    rng = np.random.default_rng(143)  # issue #143 にちなんだ固定シード
    rows = []  # 各 arg の dict
    arg_counter = 0
    for l2_id, l2 in LEVEL2.items():
        parent = l2["parent"]
        cx = LEVEL1[parent]["center"][0] + l2["offset"][0]
        cy = LEVEL1[parent]["center"][1] + l2["offset"][1]
        for text in l2["arguments"]:
            arg_counter += 1
            arg_id = f"A{arg_counter}"
            x = float(cx + rng.normal(scale=0.25))
            y = float(cy + rng.normal(scale=0.25))
            rows.append(
                {
                    "arg-id": arg_id,
                    "comment-id": f"C{arg_counter}",
                    "argument": text,
                    "x": round(x, 6),
                    "y": round(y, 6),
                    "cluster-level-1-id": parent,
                    "cluster-level-2-id": l2_id,
                }
            )
    return {"rows": rows}


def write_args_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["arg-id", "comment-id", "argument"])
        for r in rows:
            w.writerow([r["arg-id"], r["comment-id"], r["argument"]])


def write_clusters_csv(path: Path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["arg-id", "argument", "x", "y", "cluster-level-1-id", "cluster-level-2-id"])
        for r in rows:
            w.writerow(
                [r["arg-id"], r["argument"], r["x"], r["y"], r["cluster-level-1-id"], r["cluster-level-2-id"]]
            )


def _density(rows, level_col, cid):
    """クラスタ内 2D 点の平均ペア距離に基づく簡易 density（pipeline を模した値）。"""
    pts = [(r["x"], r["y"]) for r in rows if r[level_col] == cid]
    if len(pts) < 2:
        return 0.0
    dists = []
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            dists.append(math.dist(pts[i], pts[j]))
    mean_d = sum(dists) / len(dists)
    return 1.0 / (1.0 + mean_d)


def write_merge_labels_csv(path: Path, rows):
    records = []
    # level 1
    for cid, meta in LEVEL1.items():
        value = sum(1 for r in rows if r["cluster-level-1-id"] == cid)
        records.append(
            {
                "level": 1,
                "id": cid,
                "label": meta["label"],
                "description": meta["description"],
                "value": value,
                "parent": "0",
                "density": _density(rows, "cluster-level-1-id", cid),
            }
        )
    # level 2
    for cid, meta in LEVEL2.items():
        value = sum(1 for r in rows if r["cluster-level-2-id"] == cid)
        records.append(
            {
                "level": 2,
                "id": cid,
                "label": meta["label"],
                "description": meta["description"],
                "value": value,
                "parent": meta["parent"],
                "density": _density(rows, "cluster-level-2-id", cid),
            }
        )
    # density_rank / percentile を level ごとに付与
    for level in (1, 2):
        subset = [rec for rec in records if rec["level"] == level]
        ordered = sorted(subset, key=lambda r: r["density"], reverse=True)
        n = len(ordered)
        for rank, rec in enumerate(ordered, start=1):
            rec["density_rank"] = rank
            rec["density_rank_percentile"] = round(rank / n, 6)

    cols = ["level", "id", "label", "description", "value", "parent", "density", "density_rank", "density_rank_percentile"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for rec in records:
            w.writerow({c: rec[c] for c in cols})


def write_result_json(path: Path, rows):
    label_lookup = {cid: m["label"] for cid, m in LEVEL1.items()}
    label_lookup.update({cid: m["label"] for cid, m in LEVEL2.items()})
    desc_lookup = {cid: m["description"] for cid, m in LEVEL1.items()}
    desc_lookup.update({cid: m["description"] for cid, m in LEVEL2.items()})

    arguments = []
    for r in rows:
        arguments.append(
            {
                "arg_id": r["arg-id"],
                "argument": r["argument"],
                "comment_id": r["comment-id"],
                "x": r["x"],
                "y": r["y"],
                "p": 0,
                "cluster_ids": ["0", r["cluster-level-1-id"], r["cluster-level-2-id"]],
                "attributes": None,
                "url": None,
            }
        )

    clusters = [
        {"level": 0, "id": "0", "label": "全体", "takeaway": "", "value": len(rows), "parent": "", "density_rank_percentile": 0}
    ]
    for cid, meta in LEVEL1.items():
        value = sum(1 for r in rows if r["cluster-level-1-id"] == cid)
        clusters.append(
            {
                "level": 1,
                "id": cid,
                "label": meta["label"],
                "takeaway": meta["description"],
                "value": value,
                "parent": "0",
                "density_rank_percentile": None,
            }
        )
    for cid, meta in LEVEL2.items():
        value = sum(1 for r in rows if r["cluster-level-2-id"] == cid)
        clusters.append(
            {
                "level": 2,
                "id": cid,
                "label": meta["label"],
                "takeaway": meta["description"],
                "value": value,
                "parent": meta["parent"],
                "density_rank_percentile": None,
            }
        )

    result = {
        "arguments": arguments,
        "clusters": clusters,
        "comments": {},
        "propertyMap": {},
        "translations": {},
        "overview": OVERVIEW,
        "comment_num": len(rows),
        "config": {"question": QUESTION, "intro": OVERVIEW},
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="評価ハーネス用サンプルデータ生成")
    parser.add_argument("--dataset", default="sample", help="データセットID（既定: sample）")
    args = parser.parse_args()

    out_dir = Path(__file__).parent / "inputs" / args.dataset
    out_dir.mkdir(parents=True, exist_ok=True)

    data = build()
    rows = data["rows"]

    write_args_csv(out_dir / "args.csv", rows)
    write_clusters_csv(out_dir / "hierarchical_clusters.csv", rows)
    write_merge_labels_csv(out_dir / "hierarchical_merge_labels.csv", rows)
    write_result_json(out_dir / "hierarchical_result.json", rows)

    print(f"✓ サンプルデータを生成しました: {out_dir}")
    for p in sorted(out_dir.iterdir()):
        print(f"  - {p.name}")


if __name__ == "__main__":
    main()
