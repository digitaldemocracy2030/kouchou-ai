# Biome Implementation Details

## Background & Rationale

### Problem Statement
The kouchou-ai project uses multiple frontend linting and formatting tools:
- **ESLint** — Code quality checks
- **Prettier** — Code formatting
- **Import sorters** — Inconsistent import organization

This **fragmented toolchain** creates:
- ❌ Slow CI/CD pipelines (multiple separate checks)
- ❌ Conflicting configurations (ESLint vs Prettier clashes)
- ❌ Inconsistent developer experience
- ❌ Maintenance burden (3+ config files)

### Solution: Biome
**Biome** unifies linting, formatting, and import sorting into a **single, Rust-based tool**:
- ✅ **Speed:** Orders of magnitude faster than ESLint + Prettier combined
- ✅ **Consistency:** Single configuration source of truth
- ✅ **Reduced Overhead:** No conflicting rule sets
- ✅ **Easy Adoption:** Works with zero-config defaults

---

## Architecture & Scope

### Included Directories
```
client/              # Next.js main frontend
client-admin/        # Next.js admin dashboard
client-build/        # Static build (same config as client)
```

### Excluded Directories
```
server/              # Python codebase (separate tooling)
node_modules/        # Dependencies (ignore)
.next/               # Build artifacts
dist/, build/        # Compiled output
experimental/        # Experimental code
```

### Configuration Strategy: Single Root `biome.json`
Instead of per-package configs, we use a **single root configuration** with directory-specific rules if needed.

**Advantages:**
- Consistent across all frontends
- Single source of truth
- Easier maintenance and updates

---

## Phase 1: Foundation (Weeks 1–2)

### Goals
✅ Set up Biome configuration with minimal friction  
✅ Document adoption strategy  
✅ Make Biome checks non-blocking (warnings)  

### Implementation Details

#### npm Scripts
```json
{
  "scripts": {
    "lint": "biome check .",
    "lint:check": "biome check .",
    "lint:frontend": "biome check client client-admin client-build --write",
    "format": "biome check . --write"
  }
}
```

**Rationale:**
- `lint` and `lint:check` are synonymous for CI/CD flexibility
- `lint:frontend` targets only web directories (excludes server/Python)
- `format` auto-fixes formatting issues

#### Configuration: biome.json

```json
{
  "vcs": {
    "enabled": true,
    "clientKind": "git",
    "useIgnoreFile": true
  },
  "files": {
    "ignore": [
      "server",
      "node_modules",
      ".next",
      "dist",
      "build",
      "experimental"
    ]
  },
  "linter": {
    "rules": {
      "recommended": true,
      "style": {
        "useFilenamingConvention": "off"
      }
    }
  }
}
```

**Key Settings:**

| Setting | Value | Reason |
|---------|-------|--------|
| `vcs.enabled` | `true` | Use `.gitignore` for automatic exclusion |
| `line_width` | `100` | Balance readability and modern screens |
| `indent_width` | `2` | Consistent with Next.js default |
| `quotes` | `"` | JavaScript convention |
| `semicolons` | `always` | Explicit over implicit |
| `trailing_commas` | `all` | ES5+ convention |

#### Disabled / Warning Rules (Phase 1)

| Rule | Severity | Rationale |
|------|----------|-----------|
| `useFilenamingConvention` | Off | Legacy files use camelCase, kebab-case, and PascalCase |
| `noNonNullAssertion` | Warn | Existing codebase relies on non-null assertions |
| `noExplicitAny` | Warn | Gradual TypeScript migration in progress |
| `noBarrelFile` | Off | Intentionally used in component exports |

**Why Warnings in Phase 1?**
- Allows developers to commit without failing checks
- Surfaces issues for future fixes
- Prevents CI/CD bottlenecks during adoption

#### GitHub Actions Workflow (Phase 1)

```yaml
name: Biome Lint (Report-Only)
on: [push, pull_request]
jobs:
  biome:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci
      - run: npm run lint:check
```

**Phase 1 Behavior:**
- ✅ Runs on all PRs and pushes
- ✅ Reports issues as annotations
- ❌ Does NOT block merge (warning stage)

---

## Phase 2: Gradual Enforcement (Weeks 3–6)

### Goals
🎯 Migrate Biome from warnings to blockers  
🎯 Fix existing code issues  
🎯 Require new code to pass checks  

### Actions

#### Escalate Rules to Errors
```json
{
  "linter": {
    "rules": {
      "style": {
        "useFilenamingConvention": "warn",  // Phase 1: off
        "noNonNullAssertion": "error"       // Phase 1: warn
      }
    }
  }
}
```

#### Create Migration Branch
```bash
git checkout -b chore/biome-phase2-migration
npm run lint:frontend
# Commit fixes
```

Expected fixes:
- ~200–500 files reformatted
- 50–100 code quality issues identified
- 20–30 import organization fixes

#### Update CI/CD
```yaml
# .github/workflows/biome-lint.yml
- run: npm run lint:check
  # Now blocks PRs
```

#### Team Communication
- Send PR with automated fixes (formatting, imports)
- Announce Phase 2 kick-off
- Provide migration guide for teams

---

## Phase 3: Strict Enforcement (Weeks 7–10)

### Goals
🎯 Biome is mandatory  
🎯 All rules enforced as errors  
🎯 Zero technical debt from linting  

### Actions

#### Final Rule Escalation
```json
{
  "linter": {
    "rules": {
      "recommended": true
      // All warnings → errors
    }
  }
}
```

#### Update Pre-commit Hook
```yaml
# lefthook.yml
lint:
  run: npm run lint
  stage: commit
  fail: true  # Fail commit if Biome fails
```

#### Enforce in CI
```yaml
# .github/workflows/biome-lint.yml
- name: Biome Check
  run: npm run lint:check
  # Blocks merge on failure
```

---

## Migration Roadmap

### Week 1: Phase 1 Setup
- [ ] Deploy Biome config
- [ ] Add npm scripts
- [ ] Document adoption strategy
- [ ] Open PR for review

### Week 2: Phase 1 Stabilization
- [ ] Run in CI (non-blocking)
- [ ] Gather team feedback
- [ ] Create Biome champion group
- [ ] Plan Phase 2 kickoff

### Weeks 3–4: Phase 2 Migration
- [ ] Fix auto-fixable issues (formatting, imports)
- [ ] Address code quality issues
- [ ] Update CI to warn on Biome failures
- [ ] Merge Phase 2 updates

### Weeks 5–6: Phase 2 Enforcement
- [ ] Enforce on new code
- [ ] Encourage existing code fixes
- [ ] Monitor CI results

### Weeks 7–10: Phase 3 Rollout
- [ ] Escalate all warnings to errors
- [ ] Update pre-commit hooks
- [ ] Enforce in CI
- [ ] Celebrate! 🎉

---

## Integration Points

### Pre-commit Hook (lefthook)
**File:** `lefthook.yml`

Phase 1:
```yaml
lint:
  run: npm run lint --if-present
  fail: false  # Non-blocking
```

Phase 3:
```yaml
lint:
  run: npm run lint --if-present
  fail: true   # Blocks commit
```

### CI/CD Pipeline
**Phases 1–2:** Report-only  
**Phase 3:** Blocking

### IDE Integration
- **VS Code:** Install `biomejs.biome` extension
- **WebStorm:** Built-in Biome support

---

## Expected Outcomes

### Before Biome
- Separate ESLint, Prettier, import sorter
- 3+ config files to maintain
- Slow CI pipelines
- Inconsistent formatting

### After Biome (Phase 3)
- Single unified toolchain ✅
- One configuration file ✅
- Fast CI pipelines ✅
- Consistent code style ✅

### Metrics
- **Speed:** ~2x faster linting
- **Maintenance:** 1 config file vs. 3
- **Developer Time:** ~5 hrs/week saved (fewer CI failures, manual fixes)

---

## Risk Mitigation

### Risk: Breaking Changes Between Versions
**Mitigation:** Lock to `@biomejs/biome@^1.9.4` in `package.json`  
Use semantic versioning; test minor updates before upgrading

### Risk: Team Resistance
**Mitigation:** 
- Non-blocking phase 1
- Clear communication about benefits
- Biome champion group for questions

### Risk: Slow Migration
**Mitigation:** 
- Prioritize auto-fixable issues (formatting, imports)
- Use `--write` flag liberally
- Create focused migration branches

---

## Rollback Plan

If Biome causes issues:

```bash
# Remove Biome
npm uninstall @biomejs/biome

# Restore ESLint + Prettier
npm install --save-dev eslint prettier

# Update package.json scripts
"lint": "eslint ."
"format": "prettier --write ."
```

**Note:** We're confident Biome will succeed, but this safety net is available.

---

## Resources

- **Official Docs:** https://biomejs.dev
- **Configuration Guide:** https://biomejs.dev/reference/configuration
- **Rules Reference:** https://biomejs.dev/linter/rules
- **GitHub:** https://github.com/biomejs/biome

---

## FAQ

### Q: Will Biome replace ESLint entirely?
**A:** Yes, but gradually (Phase 1–3). All ESLint rules can be configured in Biome.

### Q: What about custom rules?
**A:** Biome focuses on recommended rules. For edge cases, fall back to comments:
```javascript
// biome-ignore lint/rule-name: reason
```

### Q: Can we run Biome alongside ESLint?
**A:** Not recommended; causes conflicts. Migrate fully to Biome (Phase 3).

### Q: Performance impact on CI?
**A:** Positive. Biome is ~10x faster than ESLint + Prettier combined.

### Q: What if we don't want to use Biome?
**A:** You can disable it by removing the npm scripts and CI job. However, we recommend adopting it for consistency and speed.
