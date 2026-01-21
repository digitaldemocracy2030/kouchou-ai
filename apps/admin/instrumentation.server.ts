import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

export function checkEnvOverrides() {
  const envPath = resolve(process.cwd(), ".env");

  if (!existsSync(envPath)) {
    console.warn("[env-check] .env file not found");
    return;
  }

  const envFileContent = readFileSync(envPath, "utf-8");
  const envFileVars = parseEnvFile(envFileContent);

  const keysToCheck = ["API_BASEPATH", "NEXT_PUBLIC_API_BASEPATH", "NEXT_PUBLIC_ADMIN_API_KEY"];

  let hasOverride = false;

  for (const key of keysToCheck) {
    const fileValue = envFileVars[key];
    const actualValue = process.env[key];

    if (fileValue !== undefined && actualValue !== undefined && fileValue !== actualValue) {
      if (!hasOverride) {
        console.warn("\n[env-check] WARNING: Shell environment variables are overriding .env file values:");
        hasOverride = true;
      }
      console.warn(`  ${key}:`);
      console.warn(`    .env file:    ${fileValue}`);
      console.warn(`    shell env:    ${actualValue} (this value is used)`);
    }
  }

  if (hasOverride) {
    console.warn("\nTo fix this, either:");
    console.warn("  1. Unset the shell environment variables: unset API_BASEPATH NEXT_PUBLIC_API_BASEPATH");
    console.warn("  2. Or start in a new terminal session");
    console.warn("  3. Or explicitly set correct values when starting: API_BASEPATH=http://localhost:8000 npm run dev\n");
  }
}

function parseEnvFile(content: string): Record<string, string> {
  const result: Record<string, string> = {};

  for (const line of content.split("\n")) {
    const trimmed = line.trim();

    // Skip comments and empty lines
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }

    const eqIndex = trimmed.indexOf("=");
    if (eqIndex === -1) {
      continue;
    }

    const key = trimmed.slice(0, eqIndex).trim();
    let value = trimmed.slice(eqIndex + 1).trim();

    // Remove quotes if present
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }

    result[key] = value;
  }

  return result;
}
