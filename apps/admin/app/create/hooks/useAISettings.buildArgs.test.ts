/**
 * @jest-environment node
 */
import { readFileSync } from "node:fs";
import path from "node:path";

// useAISettings は、作成フォームの初期値（LocalLLM のアドレス・既定のプロバイダー）を
// これらの NEXT_PUBLIC_* から決める。フォームはクライアントで描画されるので、効くのは
// next build の時点の値だけで、実行時の環境変数（compose の env_file など）は効かない。
// したがって、admin のイメージをビルドする経路はすべてビルド引数として渡す必要がある。
const BUILD_TIME_ENVS = ["NEXT_PUBLIC_LOCAL_LLM_ADDRESS", "NEXT_PUBLIC_USE_AZURE"];

const repoRoot = path.resolve(__dirname, "../../../../..");
const read = (relativePath: string) => readFileSync(path.join(repoRoot, relativePath), "utf8");

describe("作成フォームの初期値に使う NEXT_PUBLIC_* が admin のビルドに渡る", () => {
  it.each(BUILD_TIME_ENVS)("useAISettings が %s を読んでいる（前提の確認）", (name) => {
    expect(read("apps/admin/app/create/hooks/useAISettings.ts")).toContain(`process.env.${name}`);
  });

  it.each(BUILD_TIME_ENVS)("apps/admin/Dockerfile の builder ステージが %s を ARG と ENV にする", (name) => {
    const dockerfile = read("apps/admin/Dockerfile");
    const builder = dockerfile.split(/^FROM .* AS runner$/m)[0];
    expect(builder).toMatch(new RegExp(`^ARG ${name}$`, "m"));
    expect(builder).toMatch(new RegExp(`^ENV ${name}=\\$\\{${name}\\}$`, "m"));
  });

  it.each(BUILD_TIME_ENVS)("compose.yaml の admin の build.args に %s がある", (name) => {
    const compose = read("compose.yaml");
    const admin = compose.match(/^ {2}admin:\n([\s\S]*?)(?=^ {2}\S)/m)?.[1] ?? "";
    const args = admin.match(/^ {6}args:\n((?: {8}.*\n)+)/m)?.[1] ?? "";
    expect(args).toMatch(new RegExp(`- ${name}=\\$\\{${name}`));
  });

  it.each(BUILD_TIME_ENVS)("make azure-build の admin ビルド（2 か所）に %s がある", (name) => {
    const makefile = read("Makefile");
    const target = makefile.match(/^azure-build:\n([\s\S]*?)(?=\n\S)/m)?.[1] ?? "";
    const adminBuilds = target.match(/docker build [^;&]*?-f \.\/apps\/admin\/Dockerfile/g) ?? [];
    expect(adminBuilds).toHaveLength(2);
    for (const build of adminBuilds) {
      expect(build).toContain(`--build-arg ${name}="$(${name})"`);
    }
  });
});
