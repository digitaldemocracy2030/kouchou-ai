# Biome Quick Reference

Quick command cheatsheet for developers.

---

## Essential Commands

### Check Code (No Changes)
```bash
npm run lint
# or
npm run lint:check
```

### Format All Files
```bash
npm run format
```

### Format Frontend Only
```bash
npm run lint:frontend
```

---

## Detailed Commands

### Check Specific Directory
```bash
npx biome check client --write
npx biome check client-admin --write
```

### Check Specific File
```bash
npx biome check path/to/file.ts --write
```

### View Issues Without Fixing
```bash
npx biome check client
```

### Get Verbose Output
```bash
npx biome check client --verbose
```

### Format with JSON Output
```bash
npx biome check client --output=json
```

---

## Biome CLI Flags

| Flag | Purpose |
|------|---------|
| `--write` | Apply fixes automatically |
| `--verbose` | Show detailed output |
| `--changed` | Check only changed files (Git) |
| `--output=<format>` | Output format: `text` (default), `json`, `checkstyle` |
| `--exclude=<paths>` | Exclude paths |

---

## Common Scenarios

### Format Before Committing
```bash
npm run format
git add .
git commit -m "chore: format code"
```

### Check a Feature Branch
```bash
npm run lint:check
```

### Fix Imports Only
```bash
npx biome check client --only=organizeImports --write
```

### Dry Run (see what would change)
```bash
npm run lint
```

---

## IDE Integration

### VS Code
Install **Biome** extension (`biomejs.biome`):
- Real-time linting
- On-save formatting
- Quick fixes

### WebStorm
Biome support is built-in. Enable in:
**Settings → Languages & Frameworks → JavaScript → Biome**

---

## Pre-commit Hook

Biome runs automatically via **lefthook**:
```bash
git commit  # Runs linting before commit
```

To skip (not recommended):
```bash
git commit --no-verify
```

---

## Troubleshooting

### "Biome not found"
```bash
npm install
```

### "Permission denied"
```bash
npx biome check .
# or
npm run lint
```

### Files not being checked
Check `biome.json` `ignore` list:
```bash
npx biome check file.ts --verbose
```

### Disable a rule temporarily
Add comment in code:
```javascript
// biome-ignore lint/style/useConst: TODO: refactor
let x = 5;
```

---

## Advanced

### Check All Changed Files Only (Git)
```bash
npx biome check --changed
```

### Initialize Default Config (creates new biome.json)
```bash
npx biome init
```

### Inspect Biome Version
```bash
npx biome --version
```

---

## Useful Links

- **Documentation:** https://biomejs.dev
- **Configuration:** https://biomejs.dev/reference/configuration
- **Rules Reference:** https://biomejs.dev/linter/rules
- **GitHub Issues:** https://github.com/biomejs/biome/issues

---

## Rule Severity Levels

- **Error:** Must fix; blocks commit (Phase 3+)
- **Warn:** Should fix; reported (Phase 1–2)
- **Off:** Not checked

Adjust in `biome.json`:
```json
{
  "linter": {
    "rules": {
      "style": {
        "useConst": "warn"
      }
    }
  }
}
```
