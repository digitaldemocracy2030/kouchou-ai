#!/usr/bin/env node
/**
 * shell ビルドの出力を「配布物」に組み立てる。
 *
 * shell ビルドはレポートに依存しない HTML を 1 枚（out/__shell__/）だけ出力する。
 * 配布時にはその 1 枚を各レポートの slug へコピーし、レポートの中身は
 * data/*.json として並べる。ページは実行時に URL から slug を求めて JSON を読む。
 *
 * ここでは E2E 用に fixture から組み立てる。実際の配布では同じ処理を
 * 配信側（FastAPI）が DB の内容で行う想定。
 *
 * 使用方法: node package-shell.mjs <outDir> <fixtureDir>
 */
import { cp, mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import { join, resolve } from "node:path";

const SHELL_SLUG = "__shell__";

const [, , outDirArg, fixtureDirArg] = process.argv;

if (!outDirArg || !fixtureDirArg) {
  console.error("使用方法: node package-shell.mjs <outDir> <fixtureDir>");
  process.exit(1);
}

const outDir = resolve(outDirArg);
const fixtureDir = resolve(fixtureDirArg);
const shellDir = join(outDir, SHELL_SLUG);

const readJson = async (path) => JSON.parse(await readFile(path, "utf8"));

const entries = await readdir(outDir).catch(() => {
  throw new Error(`出力ディレクトリがありません: ${outDir}`);
});

if (!entries.includes(SHELL_SLUG)) {
  throw new Error(`shell ルート (${SHELL_SLUG}) が出力にありません。build:shell で生成してください。`);
}

const reports = await readJson(join(fixtureDir, "reports.json"));
const metadata = await readJson(join(fixtureDir, "metadata.json"));
const readyReports = reports.filter((report) => report.status === "ready");

await mkdir(join(outDir, "data", "reports"), { recursive: true });
await writeFile(join(outDir, "data", "metadata.json"), JSON.stringify(metadata));
await writeFile(join(outDir, "data", "reports.json"), JSON.stringify(readyReports));

for (const report of readyReports) {
  // shell HTML を slug ごとに配置する（中身は同一）
  await cp(shellDir, join(outDir, report.slug), { recursive: true });

  const bodyPath = join(fixtureDir, `report-${report.slug}.json`);
  const body = await readJson(bodyPath).catch(() => null);

  if (body) {
    await writeFile(join(outDir, "data", "reports", `${report.slug}.json`), JSON.stringify(body));
    console.log(`packaged: ${report.slug}`);
  } else {
    // 本文の無い slug は「見つかりません」表示の確認に使う
    console.log(`packaged (body なし): ${report.slug}`);
  }
}

console.log(`shell 配布物を組み立てました: ${outDir}`);
