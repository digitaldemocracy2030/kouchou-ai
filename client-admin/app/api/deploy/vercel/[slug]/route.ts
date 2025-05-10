import type { NextRequest } from "next/server";

export async function POST(
  req: NextRequest,
  { params }: { params: { slug: string } }
) {
  const { slug } = params;
  
  try {
    const buildRes = await fetch(
      `${process.env.CLIENT_STATIC_BUILD_BASEPATH}/build/${slug}`,
      { method: "POST" }
    );
    
    if (!buildRes.ok) {
      throw new Error("静的ファイルの生成に失敗しました");
    }
    
    const zipData = await buildRes.arrayBuffer();
    
    const deployRes = await fetch("https://api.vercel.com/v13/deployments", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${process.env.VERCEL_AUTH_TOKEN}`,
      },
      body: JSON.stringify({
        name: `kouchou-ai-${slug}`,
        target: "production",
        files: [
          {
            file: "index.html",
            data: "base64_encoded_content", // 実際の実装では、ZIPファイルを解凍して各ファイルをbase64エンコードする
          }
        ],
        projectSettings: {
          framework: null,
          outputDirectory: ".",
        },
      }),
    });
    
    if (!deployRes.ok) {
      throw new Error("Vercelへのデプロイに失敗しました");
    }
    
    const deployData = await deployRes.json();
    
    return new Response(JSON.stringify({
      success: true,
      url: deployData.url,
    }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    return new Response(JSON.stringify({
      success: false,
      message: error instanceof Error ? error.message : String(error),
    }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
