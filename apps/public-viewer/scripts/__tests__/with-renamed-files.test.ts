/**
 * @jest-environment node
 */
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const script = path.join(__dirname, "..", "with-renamed-files.mjs");

function makeWorkdir() {
  const dir = mkdtempSync(path.join(tmpdir(), "with-renamed-files-"));
  mkdirSync(path.join(dir, "app/[slug]/opengraph-image.png"), { recursive: true });
  writeFileSync(path.join(dir, "app/[slug]/opengraph-image.tsx"), "");
  writeFileSync(path.join(dir, "app/[slug]/opengraph-image.png/route.ts"), "");
  return dir;
}

describe("with-renamed-files", () => {
  let dir: string;

  beforeEach(() => {
    dir = makeWorkdir();
  });

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  it("static ビルドが失敗しても改名したファイルを元に戻し、終了コードを引き継ぐ", () => {
    const check = `process.exit(require("node:fs").existsSync("app/[slug]/_opengraph-image.tsx") ? 3 : 0)`;
    const proc = spawnSync(process.execPath, [script, process.execPath, "-e", check], {
      cwd: dir,
      env: { ...process.env, NEXT_PUBLIC_OUTPUT_MODE: "export" },
      encoding: "utf8",
    });

    // コマンドの実行中は改名されていて（exit 3）、終了後は元の名前に戻っている
    expect(proc.status).toBe(3);
    expect(existsSync(path.join(dir, "app/[slug]/opengraph-image.tsx"))).toBe(true);
    expect(existsSync(path.join(dir, "app/[slug]/opengraph-image.png/route.ts"))).toBe(true);
    expect(existsSync(path.join(dir, "app/[slug]/_opengraph-image.tsx"))).toBe(false);
    expect(existsSync(path.join(dir, "app/[slug]/_opengraph-image.png"))).toBe(false);
  });

  it("通常ビルドでは static 用の route.ts だけを改名し、成功後に戻す", () => {
    const check = `process.exit(require("node:fs").existsSync("app/[slug]/opengraph-image.png/_route.ts") ? 0 : 4)`;
    const proc = spawnSync(process.execPath, [script, process.execPath, "-e", check], {
      cwd: dir,
      env: { ...process.env, NEXT_PUBLIC_OUTPUT_MODE: "" },
      encoding: "utf8",
    });

    expect(proc.status).toBe(0);
    expect(existsSync(path.join(dir, "app/[slug]/opengraph-image.png/route.ts"))).toBe(true);
    expect(existsSync(path.join(dir, "app/[slug]/opengraph-image.png/_route.ts"))).toBe(false);
  });
});
