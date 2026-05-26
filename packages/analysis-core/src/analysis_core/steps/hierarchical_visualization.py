"""Self-contained HTML visualization step.

Reads ``hierarchical_result.json`` from the run's output directory and emits a
single-file ``report.html`` that bundles all data inline. The viewer is
written with vanilla JS and Plotly (loaded from a CDN); no Node, npm, or
running API server is required, which makes the analysis viewable from a CLI /
Coding Agent workflow without spinning up the full docker stack.

The visual design intentionally mirrors ``apps/public-viewer``:

* 750-px single column overview header (question / argument count / overview)
* Scatter chart with no axes and the 40-color soft palette borrowed from
  ``components/charts/ScatterChart.tsx`` (`softColors` array)
* Cluster centroid annotations with the same per-character width based
  wrap (``wrapLabelText``)
* Cluster details list rendered like ``components/report/ClusterOverview.tsx``
  with collapsible sub-cluster ``<details>`` for deeper levels

The function ``build_html`` is exported so callers can use it standalone
without the full pipeline orchestration (e.g. to render a HTML report from
an already-generated ``hierarchical_result.json``).
"""

from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"

# 40-color palette copied verbatim from
# apps/public-viewer/components/charts/ScatterChart.tsx (softColors).
SOFT_COLORS: list[str] = [
    "#7ac943", "#3fa9f5", "#ff7997", "#e0dd02", "#d6410f",
    "#b39647", "#7cccc3", "#a147e6", "#ff6b6b", "#4ecdc4",
    "#ffbe0b", "#fb5607", "#8338ec", "#3a86ff", "#ff006e",
    "#8ac926", "#1982c4", "#6a4c93", "#f72585", "#7209b7",
    "#00b4d8", "#e76f51", "#606c38", "#9d4edd", "#457b9d",
    "#bc6c25", "#2a9d8f", "#e07a5f", "#5e548e", "#81b29a",
    "#f4a261", "#9b5de5", "#f15bb5", "#00bbf9", "#98c1d9",
    "#84a59d", "#f28482", "#00afb9", "#cdb4db", "#fcbf49",
]


def hierarchical_visualization(config: dict[str, Any]) -> None:
    """Pipeline step entry point.

    Reads ``outputs/{output_dir}/hierarchical_result.json`` and writes
    ``outputs/{output_dir}/report.html`` next to it.

    Optional ``config`` keys:
        report_html_title: override the HTML <title>. Defaults to ``config["name"]``.
        report_url_pattern: a Python str template like ``"https://example.com/r/{comment_id}"``.
            When set, scatter points become clickable (open in new tab) and a 🔗
            hint appears on hover, matching the public-viewer's
            ``enable_source_link`` behaviour.
    """
    output_dir = config["output_dir"]
    output_base_dir = config.get("_output_base_dir", "outputs")
    result_path = Path(output_base_dir) / output_dir / "hierarchical_result.json"
    html_path = Path(output_base_dir) / output_dir / "report.html"

    if not result_path.exists():
        raise FileNotFoundError(
            f"hierarchical_result.json not found at {result_path}. "
            "Run the hierarchical_aggregation step first."
        )

    data = json.loads(result_path.read_text(encoding="utf-8"))
    html_str = build_html(
        data,
        title=config.get("report_html_title"),
        url_pattern=config.get("report_url_pattern"),
    )
    html_path.write_text(html_str, encoding="utf-8")
    print(f"  report.html: {html_path} ({html_path.stat().st_size / 1024:.1f} KB)")


def build_html(
    data: dict[str, Any],
    title: str | None = None,
    url_pattern: str | None = None,
) -> str:
    """Render a ``hierarchical_result.json`` payload into a single HTML string.

    Args:
        data: parsed contents of ``hierarchical_result.json``.
        title: HTML ``<title>``. Defaults to ``data["config"]["name"]``.
        url_pattern: Python ``str.format``-style template with ``{comment_id}``.
            If provided, each scatter point becomes a clickable link to that URL
            (target=_blank) and a 🔗 hint is added to the hover label.

    Returns:
        Full HTML document as a single string. Embeds the entire ``data`` payload
        inline as ``<script id="report-data" type="application/json">``; Plotly is
        loaded from the public CDN.
    """
    cfg = data.get("config", {}) or {}
    title = title or cfg.get("name") or "kouchou-ai report"
    question = cfg.get("question", "")
    overview = data.get("overview", "") or ""
    args = data.get("arguments", [])
    n_args = len(args)
    n_comments = data.get("comment_num", 0) or len({a.get("comment_id") for a in args})

    levels = sorted({c["level"] for c in data["clusters"] if c["level"] > 0})
    default_level = levels[0] if levels else 1

    if url_pattern:
        # Inject the resolved URL onto each argument so the JS click handler
        # has it at hand. Mutates a shallow copy so the original isn't touched.
        data = dict(data)
        data["arguments"] = [
            {**a, "url": a.get("url") or url_pattern.format(comment_id=a.get("comment_id"))}
            for a in args
        ]
        args = data["arguments"]

    tree_html = _render_tree(data)
    embedded = _safe_inline_json(data)
    level_options = "".join(
        f'<option value="{lvl}"{" selected" if lvl == default_level else ""}>'
        f"level {lvl} ({_count_at(data, lvl)} clusters)</option>"
        for lvl in levels
    )

    return _TEMPLATE.format(
        title=html.escape(title),
        question=html.escape(question),
        overview=_paragraph(overview),
        n_comments=f"{n_comments:,}",
        n_args=f"{n_args:,}",
        plotly_cdn=PLOTLY_CDN,
        level_options=level_options,
        tree=tree_html,
        embedded_json=embedded,
        palette_js=json.dumps(SOFT_COLORS),
        enable_source_link_js="true" if url_pattern else "false",
    )


def _safe_inline_json(data: Any) -> str:
    """Serialize JSON safely for embedding inside a ``<script>`` tag."""
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _count_at(data: dict[str, Any], level: int) -> int:
    return sum(1 for c in data["clusters"] if c["level"] == level)


def _paragraph(text: str) -> str:
    if not text:
        return ""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return "\n".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)


def _render_tree(data: dict[str, Any]) -> str:
    """Render the cluster hierarchy as nested ``<details>`` blocks.

    Level 1 clusters are rendered as flat ``ClusterOverview``-style sections;
    deeper levels live inside collapsible ``<details>``.
    """
    children_of: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for c in data["clusters"]:
        if c["level"] > 0 and c.get("parent"):
            children_of[c["parent"]].append(c)

    args_in: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for a in data["arguments"]:
        for cid in a.get("cluster_ids", []):
            args_in[cid].append(a)

    def render_children(parent_id: str) -> str:
        kids = sorted(children_of.get(parent_id, []), key=lambda c: -c.get("value", 0))
        if not kids:
            return ""
        items: list[str] = []
        for k in kids:
            cid = k["id"]
            label = k.get("label", "")
            value = k.get("value", 0)
            inner: list[str] = [
                f'<details class="sub-cluster" id="cluster-{html.escape(cid)}">',
                "<summary>",
                f'<span class="sub-label">{html.escape(label)}</span> ',
                f'<span class="count-badge">{value:,} args</span>',
                "</summary>",
            ]
            if k.get("takeaway"):
                inner.append(f'<p class="sub-takeaway">{html.escape(k["takeaway"])}</p>')
            grand = render_children(cid)
            if grand:
                inner.append(grand)
            else:
                members = args_in.get(cid, [])
                if members:
                    inner.append('<ul class="args">')
                    for a in members:
                        comment_id = html.escape(str(a.get("comment_id", "")))
                        argument = html.escape(a.get("argument", ""))
                        url = a.get("url")
                        link = (
                            f' <a href="{html.escape(url)}" target="_blank" rel="noopener" class="src-link">↗</a>'
                            if url
                            else ""
                        )
                        inner.append(
                            f'<li><span class="comment-id">#{comment_id}</span> {argument}{link}</li>'
                        )
                    inner.append("</ul>")
            inner.append("</details>")
            items.append("\n".join(inner))
        return '<div class="sub-clusters">\n' + "\n".join(items) + "\n</div>"

    def render_level1(cluster: dict[str, Any]) -> str:
        cid = cluster["id"]
        parts: list[str] = [
            f'<section class="cluster-overview" id="cluster-{html.escape(cid)}">',
            f'<h3 class="cluster-heading">'
            f'<a href="#cluster-{html.escape(cid)}" class="anchor">#</a> '
            f'{html.escape(cluster.get("label", ""))}'
            "</h3>",
            f'<p class="cluster-count">💬 {cluster.get("value", 0):,} args</p>',
        ]
        if cluster.get("takeaway"):
            parts.append(f'<p class="cluster-takeaway">{html.escape(cluster["takeaway"])}</p>')
        parts.append(render_children(cid))
        parts.append("</section>")
        return "\n".join(parts)

    level1 = sorted(
        [c for c in data["clusters"] if c["level"] == 1],
        key=lambda c: -c.get("value", 0),
    )
    return "\n".join(render_level1(c) for c in level1)


_TEMPLATE = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
<script src="{plotly_cdn}" defer></script>
<style>
  :root {{
    --fg: #333;
    --muted: #777;
    --border: #e5e7eb;
    --hover: #f3f4f6;
    --accent: #2577b1;
    --accent-soft: #e0eef7;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{
    margin: 0; padding: 0;
    font-family: "Roboto", "Noto Sans JP", -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--fg);
    background: #fff;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }}
  .container {{ padding: 0 1.5rem 3rem; }}
  .overview-section {{ max-width: 750px; margin: 40px auto 32px; }}
  .label-small {{ font-size: 14px; font-weight: 700; margin-bottom: 12px; }}
  h1.question {{
    font-size: 28px; font-weight: 700; line-height: 1.4;
    color: var(--accent); margin: 0 0 8px;
  }}
  .arg-count {{ font-size: 18px; font-weight: 700; margin: 8px 0 16px; display: flex; align-items: center; gap: 8px; }}
  .arg-count .icon {{ font-size: 18px; }}
  .arg-count .breakdown {{ font-size: 13px; color: var(--muted); font-weight: 400; }}
  .overview-text p {{ margin: 8px 0; line-height: 1.7; }}

  .chart-section {{ max-width: 1200px; margin: 32px auto 24px; }}
  .chart-controls {{ display: flex; gap: 16px; align-items: center; margin: 0 auto 8px; max-width: 1200px; font-size: 13px; color: var(--muted); }}
  .chart-controls label {{ display: inline-flex; align-items: center; gap: 6px; }}
  .chart-controls select {{ font: inherit; padding: 4px 8px; border: 1px solid var(--border); border-radius: 4px; background: #fff; }}
  #scatter {{
    width: 100%; height: 600px;
    border: 1px solid #ccc; border-radius: 4px; background: #fff;
  }}

  .clusters-section {{ max-width: 750px; margin: 48px auto 0; }}
  .clusters-section h2 {{
    text-align: center; font-size: 18px; font-weight: 700;
    margin: 0 0 24px; padding-top: 24px; border-top: 1px solid var(--border);
  }}
  section.cluster-overview {{ margin: 0 0 48px; }}
  .cluster-heading {{
    font-size: 22px; font-weight: 700; color: var(--accent);
    margin: 0 0 4px; position: relative;
  }}
  .cluster-heading .anchor {{
    position: absolute; left: -1.4rem; color: var(--muted);
    opacity: 0; transition: opacity 0.1s; text-decoration: none; font-weight: 400;
  }}
  .cluster-heading:hover .anchor {{ opacity: 1; }}
  .cluster-count {{
    font-size: 14px; font-weight: 700; margin: 0 0 12px; display: flex; align-items: center; gap: 6px;
  }}
  .cluster-takeaway {{ margin: 0 0 16px; line-height: 1.7; }}

  .sub-clusters {{ margin: 16px 0 0; padding-left: 16px; border-left: 2px solid var(--border); }}
  details.sub-cluster {{ margin: 10px 0; }}
  details.sub-cluster > summary {{
    cursor: pointer; padding: 6px 8px; border-radius: 4px;
    list-style: none; font-size: 16px;
  }}
  details.sub-cluster > summary::-webkit-details-marker {{ display: none; }}
  details.sub-cluster > summary:hover {{ background: var(--hover); }}
  details.sub-cluster > summary::before {{ content: "▸ "; color: var(--muted); font-size: 12px; margin-right: 4px; }}
  details.sub-cluster[open] > summary::before {{ content: "▾ "; color: var(--accent); }}
  .sub-label {{ font-weight: 500; }}
  .count-badge {{
    display: inline-block; margin-left: 8px; padding: 2px 8px;
    background: var(--accent-soft); color: var(--accent);
    border-radius: 3px; font-size: 13px; font-weight: 500;
  }}
  .sub-takeaway {{ margin: 8px 0 8px 24px; color: var(--muted); font-size: 15px; line-height: 1.7; }}
  ul.args {{ margin: 8px 0 12px 24px; padding-left: 20px; }}
  ul.args li {{ margin: 4px 0; line-height: 1.7; font-size: 15px; }}
  .comment-id {{ color: var(--muted); font-family: ui-monospace, Menlo, monospace; font-size: 12px; }}
  .src-link {{ color: var(--accent); text-decoration: none; font-size: 13px; margin-left: 4px; }}
  .src-link:hover {{ text-decoration: underline; }}

  footer {{
    max-width: 750px; margin: 64px auto 0; padding-top: 24px;
    border-top: 1px solid var(--border); color: var(--muted); font-size: 12px;
    text-align: center;
  }}
</style>
</head>
<body>
<div class="container">

<section class="overview-section">
  <p class="label-small">Report</p>
  <h1 class="question">{question}</h1>
  <p class="arg-count">
    <span class="icon">💬</span>
    {n_args} arguments
    <span class="breakdown">(from {n_comments} comments)</span>
  </p>
  <div class="overview-text">{overview}</div>
</section>

<section class="chart-section">
  <div class="chart-controls">
    <label>Color by level:
      <select id="color-level">{level_options}</select>
    </label>
    <label>
      <input type="checkbox" id="show-labels" checked> Show cluster labels
    </label>
    <label>
      <input type="checkbox" id="show-mst" checked> Show MST skeleton
    </label>
    <label>
      <input type="checkbox" id="use-mst-layout" checked> Use MST layout
    </label>
    <span id="scatter-meta"></span>
  </div>
  <div id="scatter"></div>
</section>

<section class="clusters-section">
  <h2>Clusters</h2>
  {tree}
</section>

<footer>
  Generated by analysis_core.steps.hierarchical_visualization
</footer>

</div>

<script id="report-data" type="application/json">{embedded_json}</script>
<script>
(function() {{
  const SOFT_COLORS = {palette_js};
  const ENABLE_SOURCE_LINK = {enable_source_link_js};

  function alpha(hex, a) {{
    const aa = Math.floor(a * 255).toString(16).padStart(2, "0");
    return hex + aa;
  }}

  // Mirrors apps/public-viewer wrapLabelText: ASCII chars take 0.6 width,
  // full-width chars take 1.0 width relative to the font size.
  function wrap(text, maxPx, fontPx) {{
    let out = "", line = "", w = 0;
    for (const ch of text) {{
      const cw = /[!-~]/.test(ch) ? 0.6 : 1;
      const px = cw * fontPx;
      if (w + px > maxPx) {{
        out += line + "<br>";
        line = ch;
        w = px;
      }} else {{
        line += ch;
        w += px;
      }}
    }}
    return out + line;
  }}

  function escapeHtml(s) {{
    return String(s).replace(/[&<>"']/g, c => ({{
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\\"": "&quot;", "'": "&#39;"
    }}[c]));
  }}

  function sqDist(a, b) {{
    const dx = a.x - b.x;
    const dy = a.y - b.y;
    return dx * dx + dy * dy;
  }}

  function buildMstEdges(points) {{
    if (points.length <= 1) return [];
    const visited = new Set([0]);
    const edges = [];

    while (visited.size < points.length) {{
      let bestFrom = -1;
      let bestTo = -1;
      let bestDist = Infinity;

      visited.forEach(fromIdx => {{
        for (let toIdx = 0; toIdx < points.length; toIdx += 1) {{
          if (visited.has(toIdx)) continue;
          const dist = sqDist(points[fromIdx], points[toIdx]);
          if (dist < bestDist) {{
            bestDist = dist;
            bestFrom = fromIdx;
            bestTo = toIdx;
          }}
        }}
      }});

      if (bestTo === -1) break;
      visited.add(bestTo);
      edges.push([points[bestFrom], points[bestTo]]);
    }}

    return edges;
  }}

  function buildIndexedMst(points) {{
    if (points.length <= 1) return [];
    const visited = new Set([0]);
    const edges = [];

    while (visited.size < points.length) {{
      let bestFrom = -1;
      let bestTo = -1;
      let bestDist = Infinity;

      visited.forEach(fromIdx => {{
        for (let toIdx = 0; toIdx < points.length; toIdx += 1) {{
          if (visited.has(toIdx)) continue;
          const dist = sqDist(points[fromIdx], points[toIdx]);
          if (dist < bestDist) {{
            bestDist = dist;
            bestFrom = fromIdx;
            bestTo = toIdx;
          }}
        }}
      }});

      if (bestTo === -1) break;
      visited.add(bestTo);
      edges.push([bestFrom, bestTo, Math.sqrt(bestDist)]);
    }}

    return edges;
  }}

  function buildAdjacency(count, edges) {{
    const adj = Array.from({{ length: count }}, () => []);
    edges.forEach(([a, b, dist]) => {{
      adj[a].push({{ to: b, dist }});
      adj[b].push({{ to: a, dist }});
    }});
    return adj;
  }}

  function pickRoot(points) {{
    if (points.length <= 1) return 0;
    const cx = points.reduce((s, p) => s + p.x, 0) / points.length;
    const cy = points.reduce((s, p) => s + p.y, 0) / points.length;
    let bestIdx = 0;
    let bestDist = Infinity;
    points.forEach((p, idx) => {{
      const dist = (p.x - cx) * (p.x - cx) + (p.y - cy) * (p.y - cy);
      if (dist < bestDist) {{
        bestDist = dist;
        bestIdx = idx;
      }}
    }});
    return bestIdx;
  }}

  function computeSubtreeSizes(adj, node, parent, sizes) {{
    let size = 1;
    adj[node].forEach(({{ to }}) => {{
      if (to === parent) return;
      size += computeSubtreeSizes(adj, to, node, sizes);
    }});
    sizes[node] = size;
    return size;
  }}

  function layoutTree(points, mstEdges, options = {{}}) {{
    if (points.length === 0) return [];
    if (points.length === 1) return [{{ ...points[0], layoutX: 0, layoutY: 0 }}];

    const adj = buildAdjacency(points.length, mstEdges);
    const root = pickRoot(points);
    const sizes = Array(points.length).fill(1);
    computeSubtreeSizes(adj, root, -1, sizes);

    const avgEdge = mstEdges.length
      ? mstEdges.reduce((s, [, , dist]) => s + dist, 0) / mstEdges.length
      : 1;
    const minEdge = options.minEdgeLength ?? Math.max(avgEdge * 0.9, 0.8);
    const depthScale = options.depthScale ?? 0.9;
    const positions = Array(points.length);

    function place(node, parent, startAngle, endAngle, px, py, depth) {{
      positions[node] = {{ ...points[node], layoutX: px, layoutY: py }};
      const children = adj[node].filter(edge => edge.to !== parent);
      if (children.length === 0) return;

      const total = children.reduce((s, edge) => s + sizes[edge.to], 0);
      let cursor = startAngle;

      children
        .sort((a, b) => sizes[b.to] - sizes[a.to])
        .forEach(edge => {{
          const share = total > 0 ? (endAngle - startAngle) * (sizes[edge.to] / total) : 0;
          const childStart = cursor;
          const childEnd = cursor + share;
          const angle = (childStart + childEnd) / 2;
          const length = Math.max(minEdge, edge.dist * depthScale + depth * 0.12);
          const nx = px + Math.cos(angle) * length;
          const ny = py + Math.sin(angle) * length;
          place(edge.to, node, childStart, childEnd, nx, ny, depth + 1);
          cursor = childEnd;
        }});
    }}

    place(root, -1, -Math.PI, Math.PI, 0, 0, 0);
    return positions;
  }}

  function normalizeClusterLayout(points, targetRadius) {{
    if (points.length === 0) return [];
    let maxRadius = 0;
    points.forEach(p => {{
      const radius = Math.hypot(p.layoutX, p.layoutY);
      if (radius > maxRadius) maxRadius = radius;
    }});
    const scale = maxRadius > 0 ? targetRadius / maxRadius : 1;
    return points.map(p => ({{
      ...p,
      layoutX: p.layoutX * scale,
      layoutY: p.layoutY * scale,
    }}));
  }}

  function buildClusterBridgeCandidates(clusters, groups) {{
    const bridges = [];
    for (let i = 0; i < clusters.length; i += 1) {{
      for (let j = i + 1; j < clusters.length; j += 1) {{
        const left = clusters[i];
        const right = clusters[j];
        const leftPoints = groups[left.id] || [];
        const rightPoints = groups[right.id] || [];
        if (leftPoints.length === 0 || rightPoints.length === 0) continue;

        let best = null;
        for (let a = 0; a < leftPoints.length; a += 1) {{
          for (let b = 0; b < rightPoints.length; b += 1) {{
            const dist2 = sqDist(leftPoints[a], rightPoints[b]);
            if (!best || dist2 < best.dist2) {{
              best = {{
                leftClusterId: left.id,
                rightClusterId: right.id,
                leftPointIndex: a,
                rightPointIndex: b,
                leftPoint: leftPoints[a],
                rightPoint: rightPoints[b],
                leftArgId: leftPoints[a].arg_id,
                rightArgId: rightPoints[b].arg_id,
                dist2,
              }};
            }}
          }}
        }}
        if (best) bridges.push(best);
      }}
    }}
    return bridges;
  }}

  function selectClusterBridgeMst(clusters, bridgeCandidates) {{
    if (clusters.length <= 1) return [];
    const clusterIndex = Object.fromEntries(clusters.map((c, idx) => [c.id, idx]));
    const visited = new Set([0]);
    const chosen = [];

    while (visited.size < clusters.length) {{
      let best = null;
      bridgeCandidates.forEach(candidate => {{
        const leftIdx = clusterIndex[candidate.leftClusterId];
        const rightIdx = clusterIndex[candidate.rightClusterId];
        const leftVisited = visited.has(leftIdx);
        const rightVisited = visited.has(rightIdx);
        if (leftVisited === rightVisited) return;
        if (!best || candidate.dist2 < best.dist2) best = candidate;
      }});

      if (!best) break;
      chosen.push(best);
      visited.add(clusterIndex[best.leftClusterId]);
      visited.add(clusterIndex[best.rightClusterId]);
    }}

    return chosen;
  }}

  function rotateLocalPoint(point, rotation) {{
    const cos = Math.cos(rotation);
    const sin = Math.sin(rotation);
    return {{
      x: point.layoutX * cos - point.layoutY * sin,
      y: point.layoutX * sin + point.layoutY * cos,
    }};
  }}

  function clampMagnitude(x, y, limit) {{
    const length = Math.hypot(x, y);
    if (length <= limit || length === 0) return {{ x, y }};
    const scale = limit / length;
    return {{ x: x * scale, y: y * scale }};
  }}

  function endpointWorld(body, localPoint) {{
    const rotated = rotateLocalPoint(localPoint, body.rotation);
    return {{
      x: body.x + rotated.x,
      y: body.y + rotated.y,
      localX: rotated.x,
      localY: rotated.y,
    }};
  }}

  function layoutRigidBridgeClusters(clusters, clusterLayouts, initialCenters, bridgeEdges) {{
    const centerById = Object.fromEntries(initialCenters.map(center => [center.id, center]));
    const bodies = {{}};
    clusters.forEach(cluster => {{
      const points = clusterLayouts[cluster.id] || [];
      const radius = Math.max(
        cluster.radius || 0,
        ...points.map(point => Math.hypot(point.layoutX, point.layoutY)),
      ) + 0.65;
      const center = centerById[cluster.id] || {{ layoutX: 0, layoutY: 0 }};
      bodies[cluster.id] = {{
        id: cluster.id,
        x: center.layoutX,
        y: center.layoutY,
        radius,
        rotation: 0,
      }};
    }});

    const localByClusterAndArg = Object.fromEntries(
      clusters.map(cluster => [
        cluster.id,
        Object.fromEntries((clusterLayouts[cluster.id] || []).map(point => [point.arg_id, point])),
      ]),
    );

    const resolvedBridgeEdges = bridgeEdges
      .map(edge => {{
        const leftBody = bodies[edge.leftClusterId];
        const rightBody = bodies[edge.rightClusterId];
        const leftLocal = localByClusterAndArg[edge.leftClusterId]?.[edge.leftArgId];
        const rightLocal = localByClusterAndArg[edge.rightClusterId]?.[edge.rightArgId];
        if (!leftBody || !rightBody || !leftLocal || !rightLocal) return null;
        return {{
          ...edge,
          leftBody,
          rightBody,
          leftLocal,
          rightLocal,
          target: 0.8,
        }};
      }})
      .filter(Boolean);

    for (let iter = 0; iter < 180; iter += 1) {{
      const forces = Object.fromEntries(Object.keys(bodies).map(id => [id, {{ x: 0, y: 0, torque: 0 }}]));
      const ids = Object.keys(bodies);

      for (let i = 0; i < ids.length; i += 1) {{
        for (let j = i + 1; j < ids.length; j += 1) {{
          const a = bodies[ids[i]];
          const b = bodies[ids[j]];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.hypot(dx, dy) || 0.001;
          const minDist = a.radius + b.radius + 1.6;
          if (dist < minDist) {{
            const push = (minDist - dist) * 0.12;
            const ux = dx / dist;
            const uy = dy / dist;
            forces[a.id].x -= ux * push;
            forces[a.id].y -= uy * push;
            forces[b.id].x += ux * push;
            forces[b.id].y += uy * push;
          }}
        }}
      }}

      resolvedBridgeEdges.forEach(edge => {{
        const leftEndpoint = endpointWorld(edge.leftBody, edge.leftLocal);
        const rightEndpoint = endpointWorld(edge.rightBody, edge.rightLocal);
        const dx = rightEndpoint.x - leftEndpoint.x;
        const dy = rightEndpoint.y - leftEndpoint.y;
        const dist = Math.hypot(dx, dy) || 0.001;
        const pull = (dist - edge.target) * 0.045;
        const ux = dx / dist;
        const uy = dy / dist;
        const fx = ux * pull;
        const fy = uy * pull;

        forces[edge.leftClusterId].x += fx;
        forces[edge.leftClusterId].y += fy;
        forces[edge.rightClusterId].x -= fx;
        forces[edge.rightClusterId].y -= fy;
        forces[edge.leftClusterId].torque += leftEndpoint.localX * fy - leftEndpoint.localY * fx;
        forces[edge.rightClusterId].torque += rightEndpoint.localX * (-fy) - rightEndpoint.localY * (-fx);
      }});

      ids.forEach(id => {{
        const body = bodies[id];
        const force = clampMagnitude(forces[id].x, forces[id].y, 0.24);
        body.x += force.x;
        body.y += force.y;
        const inertia = Math.max(body.radius * body.radius, 1);
        const rotationStep = Math.max(-0.045, Math.min(0.045, (forces[id].torque / inertia) * 0.25));
        body.rotation += rotationStep;
      }});

      const cx = ids.reduce((sum, id) => sum + bodies[id].x, 0) / Math.max(ids.length, 1);
      const cy = ids.reduce((sum, id) => sum + bodies[id].y, 0) / Math.max(ids.length, 1);
      ids.forEach(id => {{
        bodies[id].x -= cx;
        bodies[id].y -= cy;
      }});
    }}

    const finalLayouts = {{}};
    clusters.forEach(cluster => {{
      const body = bodies[cluster.id];
      finalLayouts[cluster.id] = (clusterLayouts[cluster.id] || []).map(point => {{
        const rotated = rotateLocalPoint(point, body.rotation);
        return {{
          ...point,
          clusterId: cluster.id,
          finalX: body.x + rotated.x,
          finalY: body.y + rotated.y,
        }};
      }});
    }});

    const finalByClusterAndArg = Object.fromEntries(
      clusters.map(cluster => [
        cluster.id,
        Object.fromEntries((finalLayouts[cluster.id] || []).map(point => [point.arg_id, point])),
      ]),
    );
    const bridgeSegments = resolvedBridgeEdges
      .map(edge => {{
        const left = finalByClusterAndArg[edge.leftClusterId]?.[edge.leftArgId];
        const right = finalByClusterAndArg[edge.rightClusterId]?.[edge.rightArgId];
        if (!left || !right) return null;
        return [
          {{ x: left.finalX, y: left.finalY }},
          {{ x: right.finalX, y: right.finalY }},
        ];
      }})
      .filter(Boolean);

    return {{ clusterLayouts: finalLayouts, bridgeSegments }};
  }}

  function edgesToSegments(edges) {{
    const xs = [];
    const ys = [];
    edges.forEach(([a, b]) => {{
      xs.push(a.x, b.x, null);
      ys.push(a.y, b.y, null);
    }});
    return {{ x: xs, y: ys }};
  }}

  function init() {{
    if (typeof Plotly === "undefined") {{ setTimeout(init, 50); return; }}
    const data = JSON.parse(document.getElementById("report-data").textContent);
    const byId = Object.fromEntries(data.clusters.map(c => [c.id, c]));
    const layoutCatalog = data.layouts || {{}};
    const selectedLayoutId = data.default_layout_id || "embedding_umap";
    const selectedLayout = layoutCatalog[selectedLayoutId] || null;
    const layoutPoints = selectedLayout && selectedLayout.points ? selectedLayout.points : {{}};

    const select = document.getElementById("color-level");
    const labelToggle = document.getElementById("show-labels");
    const mstToggle = document.getElementById("show-mst");
    const mstLayoutToggle = document.getElementById("use-mst-layout");
    const meta = document.getElementById("scatter-meta");

    const ANNOTATION_WIDTH = 228, ANNOTATION_FONT = 14;

    function build(level) {{
      const clusters = data.clusters.filter(c => c.level === level);
      const colorOf = {{}};
      const colorOfA = {{}};
      clusters.forEach((c, i) => {{
        const base = SOFT_COLORS[i % SOFT_COLORS.length];
        colorOf[c.id] = base;
        colorOfA[c.id] = alpha(base, 0.8);
      }});

      const groups = {{}};
      data.arguments.forEach(a => {{
        const cid = a.cluster_ids.find(id => byId[id] && byId[id].level === level);
        if (!cid) return;
        if (!groups[cid]) groups[cid] = [];
        const layoutPoint = layoutPoints[a.arg_id] || null;
        groups[cid].push({{
          ...a,
          x: Number(layoutPoint ? layoutPoint.x : a.x),
          y: Number(layoutPoint ? layoutPoint.y : a.y),
        }});
      }});

      const clusterEdgeTraces = [];
      const centroidPoints = [];
      const clusterLayouts = {{}};
      const clusterLocalMst = {{}};
      const clusterRadii = {{}};
      let mstEdgeCount = 0;

      clusters.forEach(c => {{
        const pts = groups[c.id] || [];
        if (pts.length === 0) return;
        const mstIndexed = buildIndexedMst(pts);
        const mstEdges = mstIndexed.map(([a, b]) => [pts[a], pts[b]]);
        mstEdgeCount += mstEdges.length;
        const baseRadius = 1.4 + Math.sqrt(pts.length) * 0.55;
        const localLayout = normalizeClusterLayout(layoutTree(pts, mstIndexed), baseRadius);
        clusterLayouts[c.id] = localLayout;
        clusterLocalMst[c.id] = mstIndexed;
        clusterRadii[c.id] = baseRadius;
        centroidPoints.push({{
          id: c.id,
          x: pts.reduce((s, a) => s + a.x, 0) / pts.length,
          y: pts.reduce((s, a) => s + a.y, 0) / pts.length,
          radius: baseRadius,
        }});
      }});

      const clusterBridgeCandidates = buildClusterBridgeCandidates(clusters, groups);
      const clusterBridgeMst = selectClusterBridgeMst(clusters, clusterBridgeCandidates);
      const bridgeTreeEdges = clusterBridgeMst.map(edge => ([
        clusters.findIndex(c => c.id === edge.leftClusterId),
        clusters.findIndex(c => c.id === edge.rightClusterId),
        Math.sqrt(edge.dist2),
      ]));
      const centroidLayout = normalizeClusterLayout(
        layoutTree(
          centroidPoints,
          bridgeTreeEdges,
          {{
            minEdgeLength: 6.5,
            depthScale: 1.15,
          }},
        ),
        Math.max(10, clusters.length * 2.4),
      );

      let bridgeEdges = [];
      if (mstLayoutToggle.checked) {{
        const rigidLayout = layoutRigidBridgeClusters(
          centroidPoints,
          clusterLayouts,
          centroidLayout,
          clusterBridgeMst,
        );
        Object.entries(rigidLayout.clusterLayouts).forEach(([clusterId, nodes]) => {{
          clusterLayouts[clusterId] = nodes;
        }});
        bridgeEdges = rigidLayout.bridgeSegments;
      }} else {{
        bridgeEdges = clusterBridgeMst.map(edge => [
          {{ x: edge.leftPoint.x, y: edge.leftPoint.y }},
          {{ x: edge.rightPoint.x, y: edge.rightPoint.y }},
        ]);
      }}
      const bridgeSegments = edgesToSegments(
        bridgeEdges,
      );
      const bridgeTrace = centroidPoints.length > 1 ? {{
        type: "scatter",
        mode: "lines",
        x: bridgeSegments.x,
        y: bridgeSegments.y,
        hoverinfo: "skip",
        line: {{
          color: "rgba(55, 65, 81, 0.55)",
          width: 1.6,
          dash: "dot",
        }},
        showlegend: false,
      }} : null;

      const pointTraces = clusters
        .map(c => {{
          const pts = (mstLayoutToggle.checked ? clusterLayouts[c.id] : groups[c.id]) || [];
          if (pts.length === 0) return null;
          return {{
            type: "scattergl",
            mode: "markers",
            name: c.label,
            x: pts.map(a => mstLayoutToggle.checked ? a.finalX : a.x),
            y: pts.map(a => mstLayoutToggle.checked ? a.finalY : a.y),
            text: pts.map(a => {{
              const body = "<b>" + escapeHtml(c.label) + "</b><br>" +
                escapeHtml(a.argument).replace(/(.{{30}})/g, "$1<br>");
              return ENABLE_SOURCE_LINK && a.url
                ? body + "<br><b>🔗 Click to open source</b>"
                : body;
            }}),
            customdata: pts.map(a => ({{ url: a.url || null, comment_id: a.comment_id }})),
            hovertemplate: "%{{text}}<extra></extra>",
            hoverlabel: {{
              align: "left",
              bgcolor: "white",
              bordercolor: colorOf[c.id],
              font: {{ size: 12, color: "#333" }},
            }},
            marker: ENABLE_SOURCE_LINK
              ? {{ size: 10, color: colorOf[c.id], line: {{ width: 2, color: "#ffffff" }} }}
              : {{ size: 7, color: colorOf[c.id] }},
            showlegend: false,
          }};
        }})
        .filter(Boolean);

      if (mstToggle.checked) {{
        clusters.forEach(c => {{
          const pts = (mstLayoutToggle.checked ? clusterLayouts[c.id] : groups[c.id]) || [];
          if (pts.length <= 1) return;
          const mstIndexed = buildIndexedMst(groups[c.id] || []);
          const lineSegments = mstIndexed.map(([a, b]) => {{
            const from = pts[a];
            const to = pts[b];
            return [
              {{ x: mstLayoutToggle.checked ? from.finalX : from.x, y: mstLayoutToggle.checked ? from.finalY : from.y }},
              {{ x: mstLayoutToggle.checked ? to.finalX : to.x, y: mstLayoutToggle.checked ? to.finalY : to.y }},
            ];
          }});
          const segments = edgesToSegments(lineSegments);
          clusterEdgeTraces.push({{
            type: "scatter",
            mode: "lines",
            x: segments.x,
            y: segments.y,
            hoverinfo: "skip",
            line: {{
              color: alpha(colorOf[c.id], 0.35),
              width: 1.4,
            }},
            showlegend: false,
          }});
        }});
      }}

      const traces = mstToggle.checked
        ? [
            ...clusterEdgeTraces,
            ...(bridgeTrace ? [bridgeTrace] : []),
            ...pointTraces,
          ]
        : pointTraces;

      const annotations = labelToggle.checked
        ? clusters.map(c => {{
            const pts = (mstLayoutToggle.checked ? clusterLayouts[c.id] : groups[c.id]) || [];
            if (pts.length === 0) return null;
            const cx = pts.reduce((s, a) => s + (mstLayoutToggle.checked ? a.finalX : a.x), 0) / pts.length;
            const cy = pts.reduce((s, a) => s + (mstLayoutToggle.checked ? a.finalY : a.y), 0) / pts.length;
            return {{
              x: cx, y: cy,
              text: wrap(c.label, ANNOTATION_WIDTH, ANNOTATION_FONT),
              showarrow: false,
              font: {{ color: "white", size: ANNOTATION_FONT, weight: 700 }},
              bgcolor: colorOfA[c.id],
              borderpad: 10,
              width: ANNOTATION_WIDTH,
              align: "left",
            }};
          }}).filter(Boolean)
        : [];

      return {{ traces, annotations, clusters, mstEdgeCount, bridgeEdgeCount: clusterBridgeMst.length }};
    }}

    function redraw() {{
      const lvl = parseInt(select.value, 10);
      const {{ traces, annotations, clusters, mstEdgeCount, bridgeEdgeCount }} = build(lvl);
      const layout = {{
        uirevision: "scatter",
        margin: {{ l: 0, r: 0, b: 0, t: 0 }},
        xaxis: {{ zeroline: false, showticklabels: false, showgrid: false }},
        yaxis: {{ zeroline: false, showticklabels: false, showgrid: false }},
        hovermode: "closest",
        dragmode: "pan",
        annotations,
        showlegend: false,
      }};
      const scatterEl = document.getElementById("scatter");
      Plotly.react(scatterEl, traces, layout, {{
        responsive: true,
        displayModeBar: "hover",
        scrollZoom: true,
      }});
      scatterEl.style.cursor = ENABLE_SOURCE_LINK ? "pointer" : "default";
      if (ENABLE_SOURCE_LINK && !scatterEl._clickBound) {{
        scatterEl.on("plotly_click", ev => {{
          const pt = ev.points && ev.points[0];
          const cd = pt && pt.customdata;
          if (cd && cd.url) window.open(cd.url, "_blank", "noopener,noreferrer");
        }});
        scatterEl._clickBound = true;
      }}
      meta.textContent = clusters.length + " clusters / " + data.arguments.length + " args" +
        (mstLayoutToggle.checked ? " / layout=MST (" + selectedLayoutId + " base)" : " / layout=" + selectedLayoutId) +
        (mstToggle.checked ? " / " + mstEdgeCount + " intra-cluster MST edges / " + bridgeEdgeCount + " bridge edges" : "") +
        (ENABLE_SOURCE_LINK ? " (click a point to open source)" : "");
    }}

    select.addEventListener("change", redraw);
    labelToggle.addEventListener("change", redraw);
    mstToggle.addEventListener("change", redraw);
    mstLayoutToggle.addEventListener("change", redraw);

    redraw();
  }}
  init();
}})();
</script>
</body>
</html>
"""


def _cli_main(argv: list[str] | None = None) -> int:
    """Standalone CLI: render a hierarchical_result.json into a HTML file.

    Useful when you already have a result JSON and only want the HTML view
    (skips the orchestration / pipeline). For end-to-end CLI usage, prefer
    ``kouchou-analyze --config X.json`` which now invokes this step.
    """
    parser = argparse.ArgumentParser(
        prog="python -m analysis_core.steps.hierarchical_visualization",
        description="Render hierarchical_result.json to a single-file HTML report.",
    )
    parser.add_argument("input", type=Path, help="path to hierarchical_result.json")
    parser.add_argument("-o", "--output", type=Path, required=True, help="output HTML path")
    parser.add_argument("--title", default=None, help="HTML <title> (defaults to config.name)")
    parser.add_argument(
        "--url-pattern",
        default=None,
        help='Python str.format template with {comment_id} (e.g. "https://example.com/r/{comment_id}"). '
        "When set, scatter points become clickable and a 🔗 hint appears on hover.",
    )
    args = parser.parse_args(argv)

    data = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.write_text(build_html(data, title=args.title, url_pattern=args.url_pattern), encoding="utf-8")
    print(f"wrote {args.output} ({args.output.stat().st_size / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli_main())
