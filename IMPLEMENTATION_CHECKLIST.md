# Biome Implementation Checklist

Use this checklist to verify the Biome setup is complete and correct.

---

## Pre-Implementation

- [ ] Read `BIOME_SETUP_SUMMARY.md` (executive overview)
- [ ] Read `biome.md` (full setup guide)
- [ ] Review `BIOME_IMPLEMENTATION.md` (detailed rationale)
- [ ] Team is aligned on three-phase adoption strategy

---

## Phase 1: Foundation Setup

### Configuration Files

- [ ] **`package.json` updated:**
  - [ ] `@biomejs/biome@^1.9.4` in `devDependencies`
  - [ ] `npm run lint` — Check all files
  - [ ] `npm run lint:check` — Alias for `lint`
  - [ ] `npm run lint:frontend` — Format frontend with `--write`
  - [ ] `npm run format` — Format all files with `--write`

- [ ] **`biome.json` configured:**
  - [ ] Schema set to `https://biomejs.dev/schemas/1.9.4/schema.json`
  - [ ] `vcs.enabled: true` (Git integration)
  - [ ] `files.ignore` includes: `server`, `node_modules`, `.next`, `dist`, `build`, `experimental`
  - [ ] `linter.rules.recommended: true`
  - [ ] Phase 1 disabled/warning rules set:
    - [ ] `useFilenamingConvention: "off"`
    - [ ] `noNonNullAssertion: "warn"`
    - [ ] `noExplicitAny: "warn"`
    - [ ] `noBarrelFile: "off"`
  - [ ] `formatter` configured:
    - [ ] `indentStyle: "space"`, `indentWidth: 2`
    - [ ] `lineWidth: 100`
    - [ ] `semicolons: "always"`, `quotes: "\""`, `trailingCommas: "all"`

### Documentation Files

- [ ] **`biome.md` created** in root:
  - [ ] Overview of Biome included
  - [ ] Three-phase adoption strategy documented
  - [ ] Quick start section
  - [ ] Configuration details
  - [ ] Integration points (pre-commit, CI)
  - [ ] Troubleshooting section

- [ ] **`BIOME_SETUP_SUMMARY.md` created** in root:
  - [ ] What is Biome? (1 paragraph)
  - [ ] Why Biome? (benefits listed)
  - [ ] Project scope (included/excluded dirs)
  - [ ] How to use (quick commands)
  - [ ] Current phase explained
  - [ ] Files changed table

- [ ] **`BIOME_QUICK_REFERENCE.md` created** in root:
  - [ ] Essential commands section
  - [ ] Detailed commands reference
  - [ ] CLI flags table
  - [ ] Common scenarios
  - [ ] IDE integration instructions
  - [ ] Pre-commit hook info
  - [ ] Troubleshooting tips

- [ ] **`docs/BIOME_IMPLEMENTATION.md` created**:
  - [ ] Background & rationale
  - [ ] Architecture & scope
  - [ ] Phase 1 details
  - [ ] Phase 2 details
  - [ ] Phase 3 details
  - [ ] Migration roadmap
  - [ ] Risk mitigation
  - [ ] Rollback plan
  - [ ] FAQ section

### Local Testing

- [ ] Run `npm install` successfully
- [ ] Run `npm run lint` — No critical errors (warnings OK in Phase 1)
- [ ] Run `npm run lint:frontend` — Formats frontend code successfully
- [ ] Run `npm run format` — Formats all code successfully
- [ ] IDE extension installed (VS Code: `biomejs.biome`)
- [ ] `lefthook run lint` runs without errors

---

## GitHub Actions Workflow (Optional)

- [ ] **`.github/workflows/biome-lint.yml` created:**
  - [ ] Workflow name: "Biome Lint (Report-Only)"
  - [ ] Triggers on: `push` and `pull_request`
  - [ ] Checks out code
  - [ ] Sets up Node.js (v18+)
  - [ ] Installs dependencies: `npm ci`
  - [ ] Runs: `npm run lint:check`
  - [ ] Does NOT fail the build (Phase 1)

- [ ] Workflow visible in GitHub Actions tab
- [ ] Workflow runs on PRs without blocking merge

---

## Team Communication

- [ ] Issue or discussion posted explaining Biome adoption
- [ ] Link to `biome.md` in README or docs index
- [ ] Team trained on:
  - [ ] How to run Biome locally (`npm run lint`, `npm run format`)
  - [ ] How to interpret warnings (Phase 1)
  - [ ] Where to find help (BIOME_QUICK_REFERENCE.md)

---

## Phase 2 Preparation (Optional)

- [ ] Document prepared for Phase 2 kickoff (1–2 weeks later)
- [ ] Team identified for Phase 2 migration branch
- [ ] Timeline planned for Phase 2 → Phase 3 progression

---

## Verification Steps

### Command-Line Verification

Run these commands and verify output:

```bash
# Should show Biome version
npx biome --version

# Should check files without errors
npm run lint:check

# Should format files
npm run format

# Should check frontend only
npm run lint:frontend

# Should show Biome info
npx biome --help
```

### Configuration Verification

```bash
# Verify biome.json is valid
npx biome --version  # If this works, config is valid

# Check specific file
npx biome check client/app/layout.tsx

# Show what would be fixed (without --write)
npx biome check client --verbose
```

### Git Integration Verification

```bash
# Verify VCS integration
cd /path/to/repo
npx biome check . --changed  # Only changed files

# Verify .gitignore is respected
npx biome check .  # Should exclude .gitignore entries
```

---

## Sign-Off

- [ ] All checklist items completed
- [ ] Team has reviewed and approved
- [ ] Ready to open PR for Issue #700

---

## Notes

- **Phase 1 is non-blocking:** Warnings are expected; developers can commit.
- **Phase 2 timeline:** Plan for 2–4 weeks after Phase 1 merge.
- **Phase 3 timeline:** Plan for 4–8 weeks after Phase 2 merge.
- **Rollback available:** If needed, can revert and restore ESLint + Prettier.

---

## Post-Implementation Monitoring

After Phase 1 merge, monitor:

- [ ] Team feedback on Biome usability
- [ ] CI/CD pipeline performance (should improve)
- [ ] Number of Biome warnings in codebase
- [ ] IDE integration working for all team members
- [ ] Schedule Phase 2 kickoff (1–2 weeks out)
