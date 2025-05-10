import type { NextRequest } from "next/server";

export async function GET(
  req: NextRequest,
  { params }: { params: { slug: string } }
) {
  const { slug } = params;
  
  const buildRes = await fetch(
    `${process.env.CLIENT_STATIC_BUILD_BASEPATH}/build/${slug}`,
    {
      method: "POST",
    },
  );

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
  const ZIP_FILE_NAME = `kouchou-ai-${slug}-${nowDateTime}.zip`;

  return new Response(buildRes.body, {
    status: 200,
    headers: {
      "Content-Type": "application/zip",
      "Content-Disposition": `attachment; filename=${ZIP_FILE_NAME}`,
    },
  });
}
