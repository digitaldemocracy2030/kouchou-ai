// Build-time switch for the admin standalone (Windows embeddable) static export.
//
// Run ONLY for the standalone build (NEXT_PUBLIC_STANDALONE=1):
//   node scripts/standalone-prep.mjs prep    # before `next build`
//   node scripts/standalone-prep.mjs restore # after `next build` (always)
//
// The hosted deployment never runs this, so its Server Actions / SSR root page /
// route handlers / middleware are untouched. For the static export we:
//   - strip the `"use server"` directive from action modules so they become plain
//     client-callable fetch helpers (they are thin API wrappers; verified to use no
//     server-only APIs like revalidatePath/redirect/cookies),
//   - point server-only ADMIN_API_KEY at NEXT_PUBLIC_ADMIN_API_KEY,
//   - swap the SSR root page for the client page.standalone.tsx,
//   - move aside pieces that hard-block `output: export`: app/api (route handlers),
//     middleware.ts, and app/reuse/[slug] (dynamic duplicate flow, deferred).
//
// All originals are backed up under scripts/.standalone-bak and restored verbatim.

import { existsSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, statSync, writeFileSync, copyFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ADMIN_ROOT = join(__dirname, "..");
const BAK = join(__dirname, ".standalone-bak");
const FILES_BAK = join(BAK, "files"); // edited-in-place file backups
const MOVED_BAK = join(BAK, "moved"); // moved-aside paths

const MOVE_ASIDE = ["middleware.ts", "app/api", "app/reuse"];
// [target, standaloneSource] — target is backed up then overwritten with the client variant.
const SWAP_FILES = [
  ["app/page.tsx", "app/page.standalone.tsx"],
  ["components/Footer/Footer.tsx", "components/Footer/Footer.standalone.tsx"],
];

function walk(dir, out = []) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) {
      if (name === "node_modules" || name === ".next" || name === ".standalone-bak" || name === "out") continue;
      walk(p, out);
    } else if (/\.(ts|tsx|js|jsx|mjs)$/.test(name)) {
      out.push(p);
    }
  }
  return out;
}

function firstCodeLineIsUseServer(src) {
  // match a leading "use server"/'use server' directive (optionally after comments/blank lines)
  return /^﻿?(?:\s|\/\/[^\n]*\n|\/\*[\s\S]*?\*\/)*["']use server["'];?/.test(src);
}

function backupFile(absPath) {
  const rel = relative(ADMIN_ROOT, absPath);
  const dest = join(FILES_BAK, rel);
  mkdirSync(dirname(dest), { recursive: true });
  copyFileSync(absPath, dest);
}

function prep() {
  if (existsSync(BAK)) {
    console.error("standalone-prep: backup dir already exists — run `restore` first.");
    process.exit(1);
  }
  mkdirSync(FILES_BAK, { recursive: true });
  mkdirSync(MOVED_BAK, { recursive: true });

  // 1) Strip "use server" + fix server-only key in action modules.
  let stripped = 0;
  for (const abs of walk(join(ADMIN_ROOT, "app"))) {
    const src = readFileSync(abs, "utf8");
    if (!firstCodeLineIsUseServer(src)) continue;
    backupFile(abs);
    let out = src.replace(/^﻿?(?:\s|\/\/[^\n]*\n|\/\*[\s\S]*?\*\/)*["']use server["'];?[ \t]*\r?\n?/, "");
    out = out.replaceAll("process.env.ADMIN_API_KEY", "process.env.NEXT_PUBLIC_ADMIN_API_KEY");
    writeFileSync(abs, out);
    stripped++;
    console.log(`  stripped use server: ${relative(ADMIN_ROOT, abs)}`);
  }
  console.log(`standalone-prep: stripped ${stripped} server-action module(s)`);

  // 2) Swap server components for their client standalone variants.
  for (const [target, source] of SWAP_FILES) {
    const targetAbs = join(ADMIN_ROOT, target);
    const sourceAbs = join(ADMIN_ROOT, source);
    if (existsSync(sourceAbs) && existsSync(targetAbs)) {
      backupFile(targetAbs);
      copyFileSync(sourceAbs, targetAbs);
      console.log(`standalone-prep: ${target} <- ${source}`);
    }
  }

  // 3) Move aside export-incompatible pieces.
  for (const rel of MOVE_ASIDE) {
    const abs = join(ADMIN_ROOT, rel);
    if (!existsSync(abs)) continue;
    const dest = join(MOVED_BAK, rel);
    mkdirSync(dirname(dest), { recursive: true });
    renameSync(abs, dest);
    console.log(`standalone-prep: moved aside ${rel}`);
  }
}

function restore() {
  if (!existsSync(BAK)) {
    console.log("standalone-prep: nothing to restore.");
    return;
  }
  // restore edited-in-place files
  if (existsSync(FILES_BAK)) {
    for (const abs of walk(FILES_BAK)) {
      const rel = relative(FILES_BAK, abs);
      const dest = join(ADMIN_ROOT, rel);
      mkdirSync(dirname(dest), { recursive: true });
      copyFileSync(abs, dest);
    }
  }
  // restore moved-aside paths
  for (const rel of MOVE_ASIDE) {
    const src = join(MOVED_BAK, rel);
    const dest = join(ADMIN_ROOT, rel);
    if (existsSync(src)) {
      if (existsSync(dest)) rmSync(dest, { recursive: true, force: true });
      mkdirSync(dirname(dest), { recursive: true });
      renameSync(src, dest);
    }
  }
  rmSync(BAK, { recursive: true, force: true });
  console.log("standalone-prep: restored originals.");
}

const cmd = process.argv[2];
if (cmd === "prep") prep();
else if (cmd === "restore") restore();
else {
  console.error("usage: node scripts/standalone-prep.mjs <prep|restore>");
  process.exit(1);
}
