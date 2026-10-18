import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const defaultDir = path.join(__dirname, "../../api/public/meta/default");
const customDir = path.join(__dirname, "../../api/public/meta/custom");
const destDir = path.join(__dirname, "../public/meta");

// API の /meta/*.png から取得する画像。
// static-site-builder のコンテナが持つ apps/api/public はイメージ作成時点のコピーなので、
// ビルドのたびに API から最新の画像を取り直す。
const META_IMAGES = ["icon.png", "ogp.png", "reporter.png"];

// default の reporter.png はテスト用画像なので出力に含めない。
// API の /meta/reporter.png も custom がない時は 204 を返す。
const DEFAULT_EXCLUDED_FILES = ["reporter.png"];

function getApiBaseUrl() {
  return process.env.API_BASEPATH || process.env.NEXT_PUBLIC_API_BASEPATH || "";
}

async function listPngFiles(dir) {
  try {
    return (await fs.readdir(dir)).filter((file) => file.endsWith(".png"));
  } catch {
    return [];
  }
}

/**
 * ローカルの apps/api/public/meta から 1 ファイルを解決する（custom 優先）。
 * default の reporter.png は返さない。
 */
async function resolveLocalFile(file, { defaultDir, customDir }) {
  if ((await listPngFiles(customDir)).includes(file)) {
    return path.join(customDir, file);
  }
  if (!DEFAULT_EXCLUDED_FILES.includes(file) && (await listPngFiles(defaultDir)).includes(file)) {
    return path.join(defaultDir, file);
  }
  return null;
}

/**
 * API から画像を取得する。
 * @returns {Promise<Buffer | null | undefined>} 画像（200）、画像なし（204）なら null、取得できなければ undefined
 */
async function fetchFromApi(file, { apiBaseUrl, fetchImpl }) {
  if (!apiBaseUrl) return undefined;
  try {
    const res = await fetchImpl(new URL(`/meta/${file}`, apiBaseUrl).toString());
    if (res.status === 204) return null;
    if (!res.ok) return undefined;
    return Buffer.from(await res.arrayBuffer());
  } catch {
    return undefined;
  }
}

export async function copyImages({
  apiBaseUrl = getApiBaseUrl(),
  fetchImpl = globalThis.fetch,
  defaultDir: defaultDirOption = defaultDir,
  customDir: customDirOption = customDir,
  destDir: destDirOption = destDir,
} = {}) {
  const dirs = { defaultDir: defaultDirOption, customDir: customDirOption };
  await fs.mkdir(destDirOption, { recursive: true });

  const localFiles = new Set([
    ...META_IMAGES,
    ...(await listPngFiles(dirs.defaultDir)),
    ...(await listPngFiles(dirs.customDir)),
  ]);

  await Promise.all(
    [...localFiles].map(async (file) => {
      const destFile = path.join(destDirOption, file);
      const fromApi = META_IMAGES.includes(file) ? await fetchFromApi(file, { apiBaseUrl, fetchImpl }) : undefined;

      if (fromApi) {
        await fs.writeFile(destFile, fromApi);
        console.log(`Fetched from API: ${file}`);
        return;
      }

      const sourceFile = fromApi === null ? null : await resolveLocalFile(file, dirs);
      if (sourceFile) {
        await fs.copyFile(sourceFile, destFile);
        console.log(`Copied from ${path.basename(path.dirname(sourceFile))}: ${file}`);
        return;
      }

      // 前回のビルドで残った画像（古い custom や default のテスト画像）を出力に混ぜない
      await fs.rm(destFile, { force: true });
    }),
  );

  console.log("✅ All images copied successfully.");
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  copyImages().catch((error) => {
    console.error("❌ Error copying images:", error);
  });
}
