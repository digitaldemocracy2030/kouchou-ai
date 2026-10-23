/**
 * @jest-environment node
 */
import http from "node:http";
import type { AddressInfo } from "node:net";
import type { NextRequest } from "next/server";
import { POST } from "./route";

type Handler = (req: http.IncomingMessage, res: http.ServerResponse) => void;

let server: http.Server | undefined;
const pendingResponses: http.ServerResponse[] = [];

async function startBuilder(handler: Handler): Promise<string> {
  server = http.createServer((req, res) => {
    pendingResponses.push(res);
    handler(req, res);
  });
  await new Promise<void>((resolve) => server?.listen(0, "127.0.0.1", resolve));
  return `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
}

function downloadRequest(slugs = "a,b"): NextRequest {
  return new Request("http://admin.test/api/download", {
    method: "POST",
    body: JSON.stringify({ slugs }),
  }) as unknown as NextRequest;
}

const originalEnv = { ...process.env };

afterEach(async () => {
  process.env = { ...originalEnv };
  for (const res of pendingResponses.splice(0)) res.destroy();
  if (server) {
    server.closeAllConnections();
    await new Promise((resolve) => server?.close(resolve));
    server = undefined;
  }
});

it("builder の ZIP をそのまま中継し、slugs を builder に渡す", async () => {
  let received = "";
  process.env.CLIENT_STATIC_BUILD_BASEPATH = await startBuilder((req, res) => {
    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
    });
    req.on("end", () => {
      received = body;
      res.writeHead(200, { "Content-Type": "application/zip" });
      res.end("PK\u0003\u0004zip");
    });
  });

  const res = await POST(downloadRequest("x,y"));

  expect(res.status).toBe(200);
  expect(res.headers.get("Content-Type")).toBe("application/zip");
  expect(res.headers.get("Content-Disposition")).toMatch(/^attachment; filename=kouchou-ai-.+\.zip$/);
  expect(await res.text()).toBe("PK\u0003\u0004zip");
  expect(JSON.parse(received)).toEqual({ slugs: "x,y" });
});

it("builder がビルドの失敗を返したら 500 の JSON を返す", async () => {
  process.env.CLIENT_STATIC_BUILD_BASEPATH = await startBuilder((_req, res) => {
    res.writeHead(500, { "Content-Type": "application/json" });
    res.end('{"status":"error"}');
  });

  const res = await POST(downloadRequest());

  expect(res.status).toBe(500);
  expect(await res.json()).toEqual({ message: "Build failed" });
});

it("静的ビルドが待ち時間の上限を超えたら、例外で落ちずに 504 の JSON を返す（s004）", async () => {
  // 本番の既定は 30 分。テストでは短くする
  process.env.CLIENT_STATIC_BUILD_TIMEOUT_SECONDS = "0.2";
  process.env.CLIENT_STATIC_BUILD_BASEPATH = await startBuilder(() => {
    // builder はビルドが終わるまで応答ヘッダーを返さない
  });

  const started = Date.now();
  const res = await POST(downloadRequest());

  expect(res.status).toBe(504);
  expect((await res.json()).message).toMatch(/待ち時間の上限（0.2 秒）内に終わりませんでした/);
  expect(Date.now() - started).toBeLessThan(5000);
});

it("builder に接続できなければ、例外で落ちずに 502 の JSON を返す", async () => {
  process.env.CLIENT_STATIC_BUILD_BASEPATH = await startBuilder(() => {});
  const url = process.env.CLIENT_STATIC_BUILD_BASEPATH;
  server?.closeAllConnections();
  await new Promise((resolve) => server?.close(resolve));
  server = undefined;
  process.env.CLIENT_STATIC_BUILD_BASEPATH = url;

  const res = await POST(downloadRequest());

  expect(res.status).toBe(502);
  expect(await res.json()).toEqual({ message: "Build failed" });
});

it("undici の既定の headersTimeout（300 秒）に縛られない経路で builder を呼ぶ（s004）", async () => {
  // global fetch（undici）は応答ヘッダーを 300 秒しか待たないので、5 分を超える静的ビルドの ZIP を
  // 受け取れなかった。route は node:http で呼び、待ち時間は CLIENT_STATIC_BUILD_TIMEOUT_SECONDS で決める
  const fetchSpy = jest.spyOn(global, "fetch");
  process.env.CLIENT_STATIC_BUILD_BASEPATH = await startBuilder((_req, res) => {
    res.writeHead(200, { "Content-Type": "application/zip" });
    res.end("PK");
  });

  const res = await POST(downloadRequest());
  await res.text();

  expect(fetchSpy).not.toHaveBeenCalled();
  fetchSpy.mockRestore();
});
