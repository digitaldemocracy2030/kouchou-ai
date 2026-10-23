import type { NextRequest } from "next/server";
import { StaticBuildTimeoutError, requestStaticBuild, staticBuildTimeoutMs } from "./requestStaticBuild";

function jsonResponse(status: number, message: string): Response {
  return new Response(JSON.stringify({ message }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function POST(req: NextRequest) {
  const { slugs } = await req.json();
  const timeoutMs = staticBuildTimeoutMs();
  let buildRes: Awaited<ReturnType<typeof requestStaticBuild>>;
  try {
    buildRes = await requestStaticBuild(
      `${process.env.CLIENT_STATIC_BUILD_BASEPATH}/build`,
      JSON.stringify({ slugs }),
      { timeoutMs, signal: req.signal },
    );
  } catch (error) {
    if (error instanceof StaticBuildTimeoutError) {
      console.error(`Static build timed out after ${timeoutMs}ms`);
      return jsonResponse(
        504,
        `静的ビルドが待ち時間の上限（${timeoutMs / 1000} 秒）内に終わりませんでした（CLIENT_STATIC_BUILD_TIMEOUT_SECONDS で変更できます）`,
      );
    }
    console.error("Static build request failed:", error);
    return jsonResponse(502, "Build failed");
  }

  if (buildRes.status < 200 || buildRes.status >= 300) {
    await buildRes.body.cancel().catch(() => {});
    return jsonResponse(500, "Build failed");
  }

  const nowDateTime = new Date()
    .toLocaleString("ja-JP", {
      timeZone: "Asia/Tokyo",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    })
    .replace(/(\/|\s)/g, "-")
    .replace(/:/g, "-");
  const ZIP_FILE_NAME = `kouchou-ai-${nowDateTime}.zip`;

  return new Response(buildRes.body, {
    status: 200,
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": `attachment; filename=${ZIP_FILE_NAME}`,
    },
  });
}
