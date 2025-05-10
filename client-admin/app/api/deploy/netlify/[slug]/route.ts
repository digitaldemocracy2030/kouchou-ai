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
    
    const formData = new FormData();
    formData.append('file', new Blob([zipData], { type: 'application/zip' }), `kouchou-ai-${slug}.zip`);
    formData.append('site_name', `kouchou-ai-${slug}`);
    
    const deployRes = await fetch("https://api.netlify.com/api/v1/sites", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.NETLIFY_AUTH_TOKEN}`,
      },
      body: formData,
    });
    
    if (!deployRes.ok) {
      throw new Error("Netlifyへのデプロイに失敗しました");
    }
    
    const deployData = await deployRes.json();
    
    return new Response(JSON.stringify({
      success: true,
      url: deployData.url,
      deployUrl: deployData.deploy_url,
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
