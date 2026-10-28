import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import type { Argument, Cluster, Comments, Config } from "@/type";
import { render } from "@testing-library/react";
import { ScatterChart, truncateText } from "../ScatterChart";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// Plotly を実描画せず、ScatterChart が渡した trace の hover text だけを捕まえる
const captured: { data: unknown[] } = { data: [] };
jest.mock("../ChartCore", () => ({
  ChartCore: ({ data }: { data: unknown[] }) => {
    captured.data = data;
    return null;
  },
}));

// lucide-react は ESM のみ配布のため空コンポーネントに差し替える
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

const clusters: Cluster[] = [
  { id: "c1", level: 1, label: "cluster-c1", takeaway: "", value: 1, parent: "", density_rank_percentile: 0.1 },
];
const args: Argument[] = [
  { arg_id: "a1", argument: "抽出された意見", comment_id: 7, x: 0, y: 0, p: 0, cluster_ids: ["c1"] },
];
const comments: Comments = { "7": { comment: "元のコメント本文です" } };

function hoverTexts(): string[] {
  return captured.data.flatMap((trace) => {
    const text = (trace as { text?: unknown }).text;
    return Array.isArray(text) ? (text as string[]) : [];
  });
}

function renderChart(config: Config | undefined, publishedComments: Comments | undefined) {
  return render(
    <Provider>
      <ScatterChart
        clusterList={clusters}
        argumentList={args}
        targetLevel={1}
        config={config}
        comments={publishedComments}
      />
    </Provider>,
  );
}

describe("ScatterChart original comment hover", () => {
  it("config.enable_original_comments が true なら、ホバーに元コメント本文を添える", () => {
    renderChart({ enable_original_comments: true } as Config, comments);
    const text = hoverTexts().join("\n");
    expect(text).toContain("抽出された意見");
    expect(text).toContain("元コメント");
    expect(text).toContain("元のコメント本文です");
  });

  it("config で公開していないレポートでは、comments があっても本文を出さない", () => {
    renderChart({ enable_source_link: false } as Config, comments);
    expect(hoverTexts().join("\n")).not.toContain("元のコメント本文です");
  });

  it("元コメントが無い意見（既存レポート）はこれまで通り意見だけを出す", () => {
    renderChart({ enable_original_comments: true } as Config, {});
    const text = hoverTexts().join("\n");
    expect(text).toContain("抽出された意見");
    expect(text).not.toContain("元コメント");
  });

  it("長い元コメントは先頭だけに切り詰める", () => {
    expect(truncateText("あ".repeat(10), 4)).toBe("ああああ…");
    expect(truncateText("short", 10)).toBe("short");
  });
});
