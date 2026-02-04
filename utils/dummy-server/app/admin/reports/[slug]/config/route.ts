import { NextResponse } from "next/server";

const SAMPLE_CONFIG = {
  name: "test-report",
  input: "test-report",
  question: "E2E Test Report",
  intro: "E2Eテスト用レポート",
  model: "gpt-4o-mini",
  provider: "openai",
  is_pubcom: false,
  is_embedded_at_local: false,
  local_llm_address: null,
  extraction: {
    prompt: "extraction prompt",
    workers: 30,
  },
  hierarchical_clustering: {
    cluster_nums: [5, 50],
  },
  hierarchical_initial_labelling: {
    prompt: "initial labelling prompt",
  },
  hierarchical_merge_labelling: {
    prompt: "merge labelling prompt",
  },
  hierarchical_overview: {
    prompt: "overview prompt",
  },
  hierarchical_aggregation: {},
};

export async function GET(request: Request, context: { params: Promise<{ slug: string }> }) {
  const requestApiKey = request.headers.get("x-api-key");
  const validApiKey = process.env.ADMIN_API_KEY;
  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, x-api-key",
  };

  if (!requestApiKey || requestApiKey !== validApiKey) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401, headers: corsHeaders });
  }

  const { slug } = await context.params;
  if (!slug.startsWith("test-report")) {
    return NextResponse.json({ error: "Not Found" }, { status: 404, headers: corsHeaders });
  }

  const config = {
    ...SAMPLE_CONFIG,
    name: slug,
    input: slug,
  };

  return NextResponse.json({ config }, { headers: corsHeaders });
}

export async function OPTIONS() {
  return new Response(null, {
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, x-api-key",
    },
  });
}
