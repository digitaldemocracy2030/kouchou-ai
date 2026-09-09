#!/usr/bin/env node
// E2E adapter. Production packaging itself uses only Python's standard library.
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

execFileSync("python3", [fileURLToPath(new URL("./package-shell.py", import.meta.url)), ...process.argv.slice(2)], {
  stdio: "inherit",
});
