# Biome Setup Guide

## Overview

Biome is a fast unified toolchain for code linting, formatting, and import organization. This document outlines our three-phase adoption strategy for integrating Biome into the kouchou-ai project.

**Target Directories:**
- `client/` (Next.js frontend)
- `client-admin/` (Next.js admin panel)
- `client-build/` (Static build, same config as client)

**Excluded:**
- `server/` (Python—uses separate tooling)
- `node_modules/`, `.next/`, `dist/`, `build/`, `experimental/`

---

## Three-Phase Adoption Strategy

### Phase 1: Foundation & Gradual Enablement (Current)
**Goal:** Introduce Biome without breaking existing code.

**What's Enabled:**
- ✅ Formatting rules (auto-fixable)
- ✅ Recommended linter rules (with warnings for noisy rules)
- ✅ Import organization

**Disabled / Warnings Only:**
- ⚠️ `useFilenamingConvention` — Not all files follow strict naming
- ⚠️ `noNonNullAssertion` — Legacy code has assertions
- ⚠️ `noExplicitAny` — TypeScript files need gradual typing

**Status:** Non-blocking; developers can commit without Biome passing in CI.

---

### Phase 2: Enforcement
**Goal:** Gradually migrate code to pass Biome checks as warnings → errors.

**Timeline:** 2-4 weeks after Phase 1 (allow time for fixes).

**Actions:**
- Migrate disabled rules to warnings
- Create focused branch for high-impact fixes
- Require new code to pass Biome checks

**Enforcement:** CI will report failures but not block merges (warning stage).

---

### Phase 3: Strict Mode
**Goal:** Biome is a mandatory pre-commit/CI check.

**Timeline:** 4-8 weeks after Phase 2.

**Actions:**
- All rules enforced as errors
- Biome check required to pass before merge
- Update pre-commit hooks and CI pipelines

---

## Quick Start

### Installation

Biome is already in `devDependencies` at version `^1.9.4`. Install locally:

```bash
npm install
```

### Running Biome

**Check all files (no changes):**
```bash
npm run lint
# or
npm run lint:check
```

**Format all files:**
```bash
npm run format
```

**Format frontend only (with write):**
```bash
npm run lint:frontend
```

**Format a specific directory:**
```bash
npx biome check client --write
```

---

## Configuration

**File:** `biome.json` (root directory)

Key settings:
- **Schema:** `https://biomejs.dev/schemas/1.9.4/schema.json`
- **Line Width:** 100 characters
- **Indent:** 2 spaces
- **Quotes:** Double quotes (JavaScript)
- **Semicolons:** Always
- **Trailing Commas:** All (JavaScript)
- **VCS Integration:** Enabled (Git)

---

## Rules & Customization

### Phase 1 Disabled Rules

| Rule | Category | Reason |
|------|----------|--------|
| `useFilenamingConvention` | Style | Legacy file naming patterns |
| `noNonNullAssertion` | Style | Existing non-null assertions in code |
| `noExplicitAny` | Suspicious | Gradual typing migration in progress |
| `noBarrelFile` | Performance | Used intentionally in some dirs |

### Severity Levels

- **Error (default):** Must be fixed; blocks commit/CI
- **Warn:** Should be fixed; reported but non-blocking
- **Off:** Not enforced

To adjust, edit `biome.json`:

```json
{
  "linter": {
    "rules": {
      "style": {
        "useFilenamingConvention": "off"
      }
    }
  }
}
```

---

## Integration Points

### Pre-commit Hook (lefthook)

Already configured in `lefthook.yml`:

```yaml
lint:
  run: npm run lint --if-present
```

Run locally before committing:
```bash
lefthook run lint
```

### GitHub Actions

See `.github/workflows/biome-lint.yml` for the report-only workflow.

Currently, the workflow runs Biome on every push/PR but does not block the build (Phase 1).

---

## Migration Timeline

| Phase | Duration | Status | Key Actions |
|-------|----------|--------|-------------|
| **Phase 1** | Weeks 1–2 | ✅ Active | Set up config, document, non-blocking CI |
| **Phase 2** | Weeks 3–6 | ⏳ Planned | Migrate rules to warnings, fix codebase |
| **Phase 3** | Weeks 7–10 | ⏳ Planned | Strict enforcement, mandatory checks |

---

## Troubleshooting

### "Biome not found"
```bash
npm install
npm run lint
```

### Formatting conflicts with Prettier/ESLint
Biome supersedes both. Remove conflicting configs:
- Delete `.prettierrc`
- Remove `prettier` from `package.json` (if present)
- Merge ESLint rules into `biome.json` as needed

### Specific files not being checked
Check `biome.json` `ignore` list. Example:
```bash
npx biome check file.ts --verbose
```

---

## Resources

- **Biome Docs:** https://biomejs.dev
- **Configuration Docs:** https://biomejs.dev/reference/configuration
- **Rules Docs:** https://biomejs.dev/linter/rules
- **IDE Extensions:** VS Code (biomejs.biome), WebStorm (built-in)

---

## Next Steps

1. ✅ Phase 1 setup complete
2. ⏳ Run `npm run lint:frontend` to review issues
3. ⏳ Schedule Phase 2 migration work
4. ⏳ Plan Phase 3 enforcement
