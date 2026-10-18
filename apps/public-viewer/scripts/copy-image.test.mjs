import assert from "node:assert/strict";
import { promises as fs } from "node:fs";
import os from "node:os";
import path from "node:path";
import { afterEach, beforeEach, test } from "node:test";

import { copyImages } from "./copy-image.mjs";

let tmp;
let dirs;

async function writeFiles(dir, files) {
  await fs.mkdir(dir, { recursive: true });
  await Promise.all(Object.entries(files).map(([name, body]) => fs.writeFile(path.join(dir, name), body)));
}

async function readDest(file) {
  try {
    return await fs.readFile(path.join(dirs.destDir, file), "utf8");
  } catch {
    return null;
  }
}

function fakeFetch(responses) {
  return async (url) => {
    const file = new URL(url).pathname.replace("/meta/", "");
    const entry = responses[file];
    if (entry === undefined) return new Response("not found", { status: 404 });
    if (entry === null) return new Response(null, { status: 204 });
    return new Response(entry, { status: 200 });
  };
}

beforeEach(async () => {
  tmp = await fs.mkdtemp(path.join(os.tmpdir(), "copy-image-"));
  dirs = {
    defaultDir: path.join(tmp, "default"),
    customDir: path.join(tmp, "custom"),
    destDir: path.join(tmp, "dest"),
  };
  await writeFiles(dirs.defaultDir, {
    "icon.png": "default-icon",
    "ogp.png": "default-ogp",
    "reporter.png": "default-reporter",
  });
  await fs.mkdir(dirs.customDir, { recursive: true });
});

afterEach(async () => {
  await fs.rm(tmp, { recursive: true, force: true });
});

test("API から最新の画像を取得し、イメージ作成時点のローカルコピーより優先する", async () => {
  await copyImages({
    ...dirs,
    apiBaseUrl: "http://api.example:8000",
    fetchImpl: fakeFetch({ "icon.png": "live-icon", "ogp.png": "live-ogp", "reporter.png": "live-reporter" }),
  });

  assert.equal(await readDest("icon.png"), "live-icon");
  assert.equal(await readDest("ogp.png"), "live-ogp");
  assert.equal(await readDest("reporter.png"), "live-reporter");
});

test("API が reporter.png なし (204) を返したら、残っている reporter.png も消す", async () => {
  await writeFiles(dirs.destDir, { "reporter.png": "stale-reporter" });

  await copyImages({
    ...dirs,
    apiBaseUrl: "http://api.example:8000",
    fetchImpl: fakeFetch({ "icon.png": "live-icon", "ogp.png": "live-ogp", "reporter.png": null }),
  });

  assert.equal(await readDest("reporter.png"), null);
  assert.equal(await readDest("icon.png"), "live-icon");
});

test("API に届かない時はローカルにフォールバックし、default のテスト用 reporter.png はコピーしない", async () => {
  await copyImages({
    ...dirs,
    apiBaseUrl: "http://api.example:8000",
    fetchImpl: async () => {
      throw new Error("connection refused");
    },
  });

  assert.equal(await readDest("icon.png"), "default-icon");
  assert.equal(await readDest("ogp.png"), "default-ogp");
  assert.equal(await readDest("reporter.png"), null);
});

test("API がない時は custom の画像が default より優先される", async () => {
  await writeFiles(dirs.customDir, { "icon.png": "custom-icon", "reporter.png": "custom-reporter" });

  await copyImages({ ...dirs, apiBaseUrl: "" });

  assert.equal(await readDest("icon.png"), "custom-icon");
  assert.equal(await readDest("ogp.png"), "default-ogp");
  assert.equal(await readDest("reporter.png"), "custom-reporter");
});
