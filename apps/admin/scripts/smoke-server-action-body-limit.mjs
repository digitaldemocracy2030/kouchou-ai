#!/usr/bin/env node
// 管理画面の Server Action（createReport）に大きな本文を送り、全件が API まで届くかを確かめるスモークテスト。
//
// jest や dummy-server の e2e は Next のサーバーと middleware を通らないので、本文サイズの上限
// （serverActions.bodySizeLimit と、middleware が本文を複製するときの proxyClientMaxBodySize）を検出できない。
// このスクリプトは `next build` 済みの standalone（Docker と同じ server.js）を起動し、偽の API を相手に
// ブラウザと同じ形（Next-Action ヘッダー + JSON.stringify([args])）で POST /create を送る。
//
// 使い方（apps/admin で）:
//   npx next build
//   node scripts/smoke-server-action-body-limit.mjs          # 既定は 15 MiB
//   node scripts/smoke-server-action-body-limit.mjs 15 40    # MiB を複数指定できる
//
// 実在の API キー・LLM は使わない（偽の API は受け取った件数を数えるだけ）。成功なら終了コード 0。
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const adminDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const serverJs = path.join(adminDir, ".next/standalone/apps/admin/server.js");
const manifestPath = path.join(adminDir, ".next/server/app/create/page/server-reference-manifest.json");
const sizesMiB = process.argv
  .slice(2)
  .map(Number)
  .filter((n) => n > 0);
if (sizesMiB.length === 0) sizesMiB.push(15);

function findActionId(exportedName) {
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  const entry = Object.entries(manifest.node).find(([, value]) => value.exportedName === exportedName);
  if (!entry) throw new Error(`${exportedName} の Server Action が ${manifestPath} に見つからない`);
  return entry[0];
}

function listen(server) {
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve(server.address().port)));
}

async function freePort() {
  const server = http.createServer();
  const port = await listen(server);
  await new Promise((resolve) => server.close(resolve));
  return port;
}

function startFakeApi(received) {
  const server = http.createServer((req, res) => {
    const chunks = [];
    req.on("data", (chunk) => chunks.push(chunk));
    req.on("end", () => {
      try {
        const body = JSON.parse(Buffer.concat(chunks).toString("utf8"));
        received.push(Array.isArray(body.comments) ? body.comments.length : -1);
      } catch {
        received.push(-1);
      }
      res.writeHead(200, { "content-type": "application/json" });
      res.end('{"status":"ok"}');
    });
  });
  return listen(server).then((port) => ({ server, port }));
}

async function waitForReady(baseUrl, child) {
  const deadline = Date.now() + 60_000;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`admin が起動中に終了した（code=${child.exitCode}）`);
    try {
      const res = await fetch(`${baseUrl}/api/healthcheck`);
      if (res.ok) return;
    } catch {
      // 起動待ち
    }
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  throw new Error("admin が 60 秒以内に起動しなかった");
}

function buildArgs(targetBytes) {
  const row = "これは大きなCSVを模したテスト用の意見本文です。".repeat(12);
  const comments = [];
  let size = 0;
  for (let i = 0; size < targetBytes; i++) {
    const comment = { id: `csv-${i + 1}`, comment: `${i} ${row}`, source: null, url: null };
    comments.push(comment);
    size += Buffer.byteLength(JSON.stringify(comment)) + 1;
  }
  return {
    input: "smoke-body-limit",
    question: "q",
    intro: "",
    comments,
    cluster: [3, 6],
    provider: "local",
    model: "m",
    workers: 1,
    prompt: { extraction: "", initial_labelling: "", merge_labelling: "", overview: "" },
    analysis_mode: "default",
    is_pubcom: true,
    inputType: "file",
    is_embedded_at_local: true,
    enable_source_link: false,
    local_llm_address: "127.0.0.1:1",
  };
}

async function main() {
  const actionId = findActionId("createReport");
  const received = [];
  const api = await startFakeApi(received);
  const port = await freePort();
  const baseUrl = `http://127.0.0.1:${port}`;
  const env = { ...process.env, NODE_ENV: "production", PORT: String(port), HOSTNAME: "127.0.0.1" };
  env.API_BASEPATH = `http://127.0.0.1:${api.port}`;
  env.NEXT_PUBLIC_ADMIN_API_KEY = "smoke-test-not-a-real-key";
  env.BASIC_AUTH_USERNAME = undefined;
  env.BASIC_AUTH_PASSWORD = undefined;
  const child = spawn(process.execPath, [serverJs], { env, stdio: ["ignore", "pipe", "pipe"] });
  let log = "";
  child.stdout.on("data", (chunk) => {
    log += chunk;
  });
  child.stderr.on("data", (chunk) => {
    log += chunk;
  });

  let failed = false;
  try {
    await waitForReady(baseUrl, child);
    for (const mib of sizesMiB) {
      received.length = 0;
      const args = buildArgs(mib * 1024 * 1024);
      const body = JSON.stringify([args]);
      const started = Date.now();
      const res = await fetch(`${baseUrl}/create`, {
        method: "POST",
        headers: { "Next-Action": actionId, "Content-Type": "text/plain;charset=UTF-8", Accept: "text/x-component" },
        body,
      });
      await res.arrayBuffer();
      const ok = res.status === 200 && received.length === 1 && received[0] === args.comments.length;
      failed ||= !ok;
      console.log(
        `${ok ? "OK  " : "FAIL"} body=${(Buffer.byteLength(body) / 1024 ** 2).toFixed(2)}MiB ` +
          `comments=${args.comments.length} status=${res.status} api_received=${JSON.stringify(received)} ` +
          `${((Date.now() - started) / 1000).toFixed(1)}s`,
      );
    }
  } finally {
    child.kill();
    api.server.close();
  }
  if (failed) {
    console.log("--- admin のログ（末尾）---");
    console.log(log.split("\n").slice(-20).join("\n"));
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
