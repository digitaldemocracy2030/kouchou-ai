import colorsys
import json
import sys
from pathlib import Path

from evaluate_silhouette_score import UMAP_THRESHOLDS
from jinja2 import Environment, FileSystemLoader


def load_json(path: Path):
    """UTF-8優先 → SJISフォールバックで読み込む"""
    if not path.exists():
        print(f"⚠️ Missing: {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except UnicodeDecodeError:
        with open(path, "r", encoding="shift_jis") as f:
            return json.load(f)


def mean(values):
    valid = [v for v in values if isinstance(v, (int, float))]
    return round(sum(valid) / len(valid), 3) if valid else None


def safe_int(v):
    try:
        return int(v)
    except:
        return None


def generate_html(slug: str, input_dir: Path, output_dir: Path, template_dir: Path):
    base_input = input_dir / slug
    base_output = output_dir / slug
    base_output.mkdir(parents=True, exist_ok=True)

    result_data = load_json(base_input / "hierarchical_result.json")

    llm_scores_l1 = load_json(base_input / "evaluation_consistency_llm_level1.json")
    llm_scores_l2 = load_json(base_input / "evaluation_consistency_llm_level2.json")
    llm_scores = {**llm_scores_l1, **llm_scores_l2}
    distinctiveness_comment1 = llm_scores_l1.pop("distinctiveness_comment", None)
    distinctiveness_comment2 = llm_scores_l2.pop("distinctiveness_comment", None)

    silhouette_umap = load_json(base_input / "silhouette_umap_level1_clusters.json").get("clusters", {})
    silhouette_umap_lv2 = load_json(base_input / "silhouette_umap_level2_clusters.json").get("clusters", {})

    umap_points = load_json(base_input / "silhouette_umap_level2_points.json")
    if not umap_points:
        umap_points = load_json(base_input / "silhouette_umap_level1_points.json")

    for arg in result_data.get("arguments", []):
        arg_id = arg.get("arg-id") or arg.get("arg_id")
        ump = umap_points.get(arg_id, {})
        arg["silhouette"] = {
            "umap": {
                "raw": ump.get("silhouette"),
                "scaled": ump.get("silhouette_score"),
                "centroid": ump.get("centroid_dist"),
                "centroid_score": ump.get("centroid_score"),
                "nearest": ump.get("nearest_dist"),
                "nearest_score": ump.get("nearest_score")
            }
        }
    cluster_by_id = {c["id"]: c for c in result_data["clusters"]}
    cluster_children = {}
    for c in result_data["clusters"]:
        parent = c.get("parent")
        if parent:
            cluster_children.setdefault(parent, []).append(c)

    def build_cluster_tree(cluster):
        cid = cluster["id"]
        level = cluster.get("level")

        llm_entry = llm_scores.get(cid)
        if isinstance(llm_entry, dict) and cid in llm_entry:
            llm = llm_entry[cid]
        elif isinstance(llm_entry, dict):
            llm = llm_entry
        else:
            llm = {}
        llm.pop("label", None)
        cluster["llm"] = llm

        umap = silhouette_umap.get(cid) if level == 1 else silhouette_umap_lv2.get(cid)

        cluster["scores"] = {
            "clarity": {"raw": llm.get("clarity"), "scaled": safe_int(llm.get("clarity"))},
            "coherence": {"raw": llm.get("coherence"), "scaled": safe_int(llm.get("coherence"))},
            "consistency": {"raw": llm.get("consistency"), "scaled": safe_int(llm.get("consistency"))},
            "distinctiveness": {"raw": llm.get("distinctiveness"), "scaled": safe_int(llm.get("distinctiveness"))},
            "umap": {
                "raw": umap.get("silhouette") if umap else None,
                "scaled": umap.get("silhouette_score") if umap else None,
                "centroid": umap.get("centroid_dist") if umap else None,
                "centroid_score": umap.get("centroid_score") if umap else None,
                "nearest": umap.get("nearest_dist") if umap else None,
                "nearest_score": umap.get("nearest_score") if umap else None
            }
        }

        cluster["silhouette_umap"] = umap
        cluster["children"] = [build_cluster_tree(child) for child in cluster_children.get(cid, [])]
        return cluster

    level1_clusters = [c for c in result_data["clusters"] if c.get("level") == 1]
    cluster_tree = [build_cluster_tree(c) for c in level1_clusters]

    result_data["llm_avg"] = {
        "clarity": mean([safe_int(c["llm"].get("clarity")) for c in cluster_tree]),
        "coherence": mean([safe_int(c["llm"].get("coherence")) for c in cluster_tree]),
        "consistency": mean([safe_int(c["llm"].get("consistency")) for c in cluster_tree]),
        "distinctiveness": mean([safe_int(c["llm"].get("distinctiveness")) for c in cluster_tree]),
    }

    result_data["llm_avg_scaled"] = {
        "clarity": round(result_data["llm_avg"]["clarity"]),
        "coherence": round(result_data["llm_avg"]["coherence"]),
        "consistency": round(result_data["llm_avg"]["consistency"]),
        "distinctiveness": round(result_data["llm_avg"]["distinctiveness"]),
    }

    result_data["silhouette_umap_avg"] = {
        "silhouette": mean([v.get("silhouette") for v in silhouette_umap.values() if isinstance(v, dict)]),
        "silhouette_score": mean([v.get("silhouette_score") for v in silhouette_umap.values() if isinstance(v, dict)]),
        "centroid_dist": mean([v.get("centroid_dist") for v in silhouette_umap.values() if isinstance(v, dict)]),
        "centroid_score": mean([v.get("centroid_score") for v in silhouette_umap.values() if isinstance(v, dict)]),
        "nearest_dist": mean([v.get("nearest_dist") for v in silhouette_umap.values() if isinstance(v, dict)]),
        "nearest_score": mean([v.get("nearest_score") for v in silhouette_umap.values() if isinstance(v, dict)]),
    }

    result_data["silhouette_umap_avg_scaled"] = {
        "silhouette_score": round(result_data["silhouette_umap_avg"].get("silhouette_score")),
        "centroid_score": round(result_data["silhouette_umap_avg"].get("centroid_score")),
        "nearest_score": round(result_data["silhouette_umap_avg"].get("nearest_score")),
    }

    color_map = {}
    for i, c in enumerate(level1_clusters):
        hue = (i * 0.14) % 1.0
        rgb = colorsys.hsv_to_rgb(hue, 0.6, 0.7)
        hex_color = '#{:02x}{:02x}{:02x}'.format(int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
        color_map[c["id"]] = hex_color

    env = Environment(loader=FileSystemLoader(str(template_dir)))
    env.tests['search'] = lambda value, sub: sub in value
    template = env.get_template("report_template.html")
    html = template.render(
        result=result_data,
        cluster_tree=cluster_tree,
        umap_thresholds=UMAP_THRESHOLDS,
        color_map=color_map,
        distinctiveness_comment1=distinctiveness_comment1, 
        distinctiveness_comment2=distinctiveness_comment2,  
    )

    out_path = base_output / "report.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_html.py [slug]")
        sys.exit(1)

    slug = sys.argv[1]
    generate_html(
        slug=slug,
        input_dir=Path("inputs"),
        output_dir=Path("outputs"),
        template_dir=Path("templates")
    )


if __name__ == "__main__":
    main()
