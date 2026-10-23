import http from "node:http";
import https from "node:https";
import { Readable } from "node:stream";

// static-site-builder はビルド（next build による export）が終わるまで応答ヘッダーを返さない。
// 全レポートのビルドは件数・大きさ・CPU によって 5 分を超えることがある。
export const DEFAULT_STATIC_BUILD_TIMEOUT_SECONDS = 30 * 60;

export class StaticBuildTimeoutError extends Error {
  constructor(timeoutMs: number) {
    super(`static build did not respond within ${timeoutMs}ms`);
    this.name = "StaticBuildTimeoutError";
  }
}

export function staticBuildTimeoutMs(): number {
  const seconds = Number(process.env.CLIENT_STATIC_BUILD_TIMEOUT_SECONDS);
  return (Number.isFinite(seconds) && seconds > 0 ? seconds : DEFAULT_STATIC_BUILD_TIMEOUT_SECONDS) * 1000;
}

/**
 * builder の POST /build を呼び、応答のステータスと本文（Web の ReadableStream）を返す。
 *
 * global fetch（undici）は応答ヘッダーを既定で 300 秒（headersTimeout）しか待たず、5 分を超えるビルドの
 * ZIP を受け取れなかった。undici の Agent を差し込むには依存を足す必要があるので、node:http(s) で呼び、
 * 無通信の待ち時間の上限を timeoutMs（ヘッダー待ち・本文の途中の両方）で決める。
 * 上限を超えたら StaticBuildTimeoutError、接続できなければ通信エラーを reject する。
 * signal が abort されたら（利用者が画面を閉じたなど）builder への接続も切る。
 */
export function requestStaticBuild(
  url: string,
  body: string,
  { timeoutMs, signal }: { timeoutMs: number; signal?: AbortSignal },
): Promise<{ status: number; body: ReadableStream<Uint8Array> }> {
  return new Promise((resolve, reject) => {
    const target = new URL(url);
    const client = target.protocol === "https:" ? https : http;
    const req = client.request(target, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) },
      signal,
    });
    req.setTimeout(timeoutMs, () => {
      req.destroy(new StaticBuildTimeoutError(timeoutMs));
    });
    req.on("response", (res) => {
      resolve({
        status: res.statusCode ?? 500,
        body: Readable.toWeb(res) as ReadableStream<Uint8Array>,
      });
    });
    req.on("error", reject);
    req.end(body);
  });
}
