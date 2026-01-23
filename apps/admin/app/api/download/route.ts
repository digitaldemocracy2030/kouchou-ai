import type { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  const buildRes = await fetch(`${process.env.CLIENT_STATIC_BUILD_BASEPATH}/build`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ slugs: (await req.json()).slugs }),
  });

  if (!buildRes.ok || !buildRes.body) {
    return new Response(JSON.stringify({ message: "Build failed" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
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
