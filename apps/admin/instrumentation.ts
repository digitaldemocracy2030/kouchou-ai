export async function register() {
  // サーバーサイドでのみ実行
  if (process.env.NEXT_RUNTIME === "nodejs") {
    const { checkEnvOverrides } = await import("./instrumentation.server");
    checkEnvOverrides();
  }
}
