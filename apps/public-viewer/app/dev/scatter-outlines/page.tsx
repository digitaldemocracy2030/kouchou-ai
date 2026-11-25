import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { ScatterOutlinePreview } from "@/components/dev/ScatterOutlinePreview";
import type { Result } from "@/type";
import { notFound } from "next/navigation";

const datasets = {
  example: "utils/dummy-server/app/reports/example/hierarchical_result.json",
  polis: "apps/api/broadlistening/pipeline/outputs/example-hierarchical-polis/hierarchical_result.json",
};

export default async function Page({
  searchParams,
}: { searchParams: Promise<{ data?: string; measure?: string; view?: string; pair?: string }> }) {
  if (process.env.NODE_ENV !== "development") notFound();
  const { data, measure, view, pair } = await searchParams;
  const dataset = data === "polis" ? "polis" : "example";
  const file = resolve(process.cwd(), "../..", datasets[dataset]);
  const { arguments: arguments_, clusters, config } = JSON.parse(await readFile(file, "utf8")) as Result;
  return (
    <ScatterOutlinePreview
      arguments={arguments_}
      clusters={clusters}
      config={config}
      dataset={dataset}
      measure={measure === "1"}
      compare={measure !== "1" && view !== "overview"}
      initialPair={pair}
    />
  );
}
