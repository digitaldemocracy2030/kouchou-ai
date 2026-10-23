/**
 * @jest-environment node
 */
import { readFileSync } from "node:fs";
import path from "node:path";

// /api/revalidate は API が送る secret と、実行時の process.env.REVALIDATE_SECRET を比べる。
// API にだけ REVALIDATE_SECRET を渡して public-viewer に渡さないと、正規の要求が毎回 401 になる。
const repoRoot = path.resolve(__dirname, "../../../../../..");
const makefile = readFileSync(path.join(repoRoot, "Makefile"), "utf8");

const azureConfigUpdate = () => {
  const target = makefile.match(/^azure-config-update:\n([\s\S]*?)(?=\n\S)/m);
  expect(target).not.toBeNull();
  return target?.[1] ?? "";
};

const containerUpdate = (recipe: string, name: string) => {
  const update = recipe.match(
    new RegExp(`az containerapp update --name ${name} [\\s\\S]*?(?=&& \\\\\\n\\s*echo|"\\s*$)`),
  );
  expect(update).not.toBeNull();
  return update?.[0] ?? "";
};

describe("make azure-config-update の REVALIDATE_SECRET", () => {
  it("public-viewer の route が実行時の REVALIDATE_SECRET を読んでいる（前提の確認）", () => {
    const route = readFileSync(path.join(repoRoot, "apps/public-viewer/app/api/revalidate/route.ts"), "utf8");
    expect(route).toContain("process.env.REVALIDATE_SECRET");
  });

  it("api と public-viewer の両方に同じ REVALIDATE_SECRET を渡す", () => {
    const recipe = azureConfigUpdate();
    expect(containerUpdate(recipe, "api")).toContain("'REVALIDATE_SECRET=$(REVALIDATE_SECRET)'");
    expect(containerUpdate(recipe, "public-viewer")).toContain("'REVALIDATE_SECRET=$(REVALIDATE_SECRET)'");
  });

  it("REVALIDATE_SECRET が空のまま環境変数を更新しない", () => {
    // azure-setup-all は azure-update-deployment と違い、事前チェックを通らずにこのターゲットを呼ぶ
    expect(azureConfigUpdate()).toMatch(/\$\(MAKE\) azure-check-revalidate-secret/);
  });
});
