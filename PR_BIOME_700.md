# Unified Biome Linting & Formatting Toolchain – Issue #700

## Summary

This PR introduces **Biome**, a fast, unified linting and formatting toolchain, to replace fragmented ESLint + Prettier + import sorters. We're adopting a **3-phase gradual adoption strategy** to minimize disruption and ensure team buy-in.

**Phase 1 (This PR):** Foundation setup with non-blocking checks  
**Phase 2 (2-4 weeks):** Gradual enforcement with codebase fixes  
**Phase 3 (4-8 weeks):** Strict enforcement in CI/CD  

---

## Why Biome?

### Current Pain Points ❌
- Multiple separate linting/formatting tools (ESLint, Prettier, import sorters)
- Slow CI/CD pipelines with redundant checks
- Conflicting configurations and rule sets
- Inconsistent developer experience

### Biome Benefits ✅
- **Single unified toolchain** — Linting + formatting + import org in one
- **~10x faster** — Rust-based; processes all files instantly
- **Zero conflicts** — One configuration source of truth
- **Easy adoption** — Works with sensible defaults

---

## What's Changed

### Files Modified/Created

#### Configuration
- **`package.json`** — Added npm scripts and `@biomejs/biome@^1.9.4`
- **`biome.json`** — Root Biome configuration with Phase 1 settings
- **`.github/workflows/biome-lint.yml`** — Report-only GitHub Actions workflow

#### Documentation
- **`biome.md`** — Full setup guide with 3-phase adoption strategy
- **`BIOME_SETUP_SUMMARY.md`** — Executive summary for quick reference
- **`BIOME_QUICK_REFERENCE.md`** — Developer command cheatsheet
- **`docs/BIOME_IMPLEMENTATION.md`** — Detailed implementation rationale & roadmap
- **`IMPLEMENTATION_CHECKLIST.md`** — Verification checklist
- **`PR_BIOME_700.md`** — This PR template

### npm Scripts Added
```json
{
  "lint": "biome check .",
  "lint:check": "biome check .",
  "lint:frontend": "biome check client client-admin client-build --write",
  "format": "biome check . --write"
}
```

---

## Configuration Highlights

### Scope
- **Linted:** `client/`, `client-admin/`, `client-build/`
- **Excluded:** `server/` (Python), `node_modules/`, `.next/`, `dist/`, `build/`, `experimental/`

### Phase 1 Rules
- ✅ All recommended rules enabled
- ⚠️ Selected rules as warnings (not blocking):
  - `useFilenamingConvention` — Off (legacy file names)
  - `noNonNullAssertion` — Warn (existing assertions)
  - `noExplicitAny` — Warn (gradual typing)
  - `noBarrelFile` — Off (intentional usage)

### Formatting Standards
- Indent: 2 spaces
- Line width: 100 chars
- Quotes: Double (`"`)
- Semicolons: Always
- Trailing commas: All (JavaScript)

---

## Phase 1: Non-Blocking Foundation

**Status:** ✅ Active

### What This Phase Does
- Runs Biome on all PRs/pushes
- Reports issues as warnings (not blocking)
- Allows team to familiarize themselves
- Builds confidence before Phase 2

### How to Test Locally
```bash
npm install
npm run lint          # Check all files (no changes)
npm run format        # Auto-fix formatting
npm run lint:frontend # Check frontend only with fixes
```

### CI/CD Behavior
- GitHub Actions workflow runs: `.github/workflows/biome-lint.yml`
- Issues reported as annotations
- PRs can merge even with warnings ✅

---

## Adoption Timeline

### Phase 1 (Weeks 1–2) — This PR
- [ ] Setup complete
- [ ] Documentation finalized
- [ ] Non-blocking checks enabled
- [ ] Team onboarding begins

### Phase 2 (Weeks 3–6) — Planned
- Migrate rules to warnings/errors
- Fix codebase systematically
- Enable blocking checks on CI
- Require new code to pass

### Phase 3 (Weeks 7–10) — Planned
- All rules enforced as errors
- Biome mandatory in pre-commit hooks
- Blocking CI checks
- Official rollout complete

---

## Documentation

New developers should start here:

1. **Quick Summary:** Read `BIOME_SETUP_SUMMARY.md` (2 min read)
2. **Commands:** Use `BIOME_QUICK_REFERENCE.md` for CLI reference
3. **Setup Guide:** Refer to `biome.md` for full context
4. **Deep Dive:** See `docs/BIOME_IMPLEMENTATION.md` for rationale
5. **Verify Setup:** Follow `IMPLEMENTATION_CHECKLIST.md`

---

## Testing Instructions

### Local Setup
```bash
npm install
npm run lint
npm run format
npm run lint:frontend
```

### GitHub Actions
- PR will automatically run `.github/workflows/biome-lint.yml`
- Verify workflow completes (status check appears)
- Note: PRs can merge even if Biome reports warnings (Phase 1)

### IDE Integration
- Install VS Code extension: `biomejs.biome`
- Or use WebStorm built-in Biome support
- Real-time linting and on-save formatting

---

## Breaking Changes

⚠️ **None in Phase 1.** This is a non-breaking setup.

**Later phases (Phase 2–3)** will enforce stricter rules, requiring codebase fixes. We'll schedule those changes with ample notice.

---

## Migration Path

| Phase | Status | When | Action |
|-------|--------|------|--------|
| Phase 1 | 🟢 Active | Now | Merge this PR |
| Phase 2 | 🟡 Planned | +2-4 wks | Enforce checks |
| Phase 3 | 🟡 Planned | +6-10 wks | Mandatory checks |

---

## Rollback Plan

If issues arise, we can revert to ESLint + Prettier:
```bash
npm uninstall @biomejs/biome
npm install --save-dev eslint prettier
# Update package.json scripts
```

**Note:** We're confident in this adoption. This is a safety net.

---

## Benefits Realized After Phase 3

- ✅ Single linting/formatting tool (vs. 3+)
- ✅ ~2x faster CI/CD pipelines
- ✅ Consistent code style across all frontends
- ✅ Reduced maintenance burden
- ✅ Improved developer experience

---

## FAQ

### Q: Will this affect the Python server?
**A:** No. `server/` is excluded. Python tooling remains unchanged.

### Q: What about our existing ESLint/Prettier configs?
**A:** Biome supersedes them. We'll archive the old configs as reference in Phase 2.

### Q: Can we skip Biome?
**A:** Phase 1 is opt-in (non-blocking). Phase 3 will make it mandatory.

### Q: How do I disable Biome for a line?
**A:** Use comment:
```javascript
// biome-ignore lint/rule-name: reason
const x = 5;
```

### Q: When does Phase 2 start?
**A:** 2–4 weeks after Phase 1 merge. We'll post an announcement.

---

## Related Issues

- Closes #700 (Biome integration)
- Related to code quality improvements
- Aligns with ESM/TypeScript modernization efforts

---

## Checklist

- [x] Configuration files added/updated
- [x] Documentation complete
- [x] npm scripts added
- [x] GitHub Actions workflow created
- [x] Phase 1 non-blocking
- [x] Team communication ready
- [x] Rollback plan documented
- [x] IMPLEMENTATION_CHECKLIST provided

---

## Reviewers

- Please test locally (`npm run lint`, `npm run format`)
- Review documentation for clarity
- Provide feedback on Phase 1 approach
- Approve to merge and begin adoption

---

## Next Steps (After Merge)

1. ✅ PR merged
2. ⏳ Team reviews documentation (1 week)
3. ⏳ Gather feedback (1 week)
4. ⏳ Schedule Phase 2 kickoff (2 weeks out)
5. ⏳ Begin Phase 2 migration

---

**Let's make code quality and developer experience better, one phase at a time! 🚀**
