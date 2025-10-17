import { constants } from "node:fs";
import { access, rename } from "node:fs/promises";
import { resolve } from "node:path";

let ignoreFiles = [];

if (process.env.NEXT_PUBLIC_OUTPUT_MODE === "export") {
  // static build 時にビルド対象から除外するファイル
  ignoreFiles = ["app/[slug]/opengraph-image.tsx", "app/[slug]/opengraph-image.png"];
} else {
  // 通常のビルド時にビルド対象から除外するファイル
  ignoreFiles = ["app/[slug]/opengraph-image.png/route.ts"];
}

async function renameFiles() {
  for (const file of ignoreFiles) {
    const filePath = resolve(file);
    const renamedPath = resolve(file.replace(/([^/]+)$/, "_$1"));

    try {
      await access(filePath, constants.F_OK);
      await rename(filePath, renamedPath);
      console.log(`Renamed: ${file} → _${file.split("/").pop()}`);
    } catch (error) {
      console.warn(`Skipping rename for ${file}: ${error.message}`);
    }
  }
}

async function restoreFiles() {
  for (const file of ignoreFiles) {
    const filePath = resolve(file);
    const renamedPath = resolve(file.replace(/([^/]+)$/, "_$1"));

    try {
      await access(renamedPath, constants.F_OK);
      await rename(renamedPath, filePath);
      console.log(`Restored: _${file.split("/").pop()} → ${file}`);
    } catch (error) {
      console.warn(`Skipping restore for ${file}: ${error.message}`);
    }
  }
}

const action = process.argv[2];

if (action !== "rename" && action !== "restore") {
  console.error("Invalid action:", action);
  process.exit(1);
}

if (action === "rename") {
  await renameFiles();
  process.exit(0);
}

if (action === "restore") {
  await restoreFiles();
  process.exit(0);
}
