# kouchou-ai Windows standalone (embeddable Python)

Build a self-contained Windows bundle that runs the kouchou-ai FastAPI backend
and analysis pipeline **without a system Python install**, using an embeddable
CPython runtime. Designed for "just try it locally" users, pairing with
[LM Studio](https://lmstudio.ai/) for a fully local (no API cost) LLM.

Feasibility was validated end to end — see
[`tmp-embeddable-poc/FINDINGS.md`](../../tmp-embeddable-poc/FINDINGS.md).

## What works today

- ✅ Embeddable Python 3.12 + pip, with `analysis-core[clustering,gemini]`
  (numba/UMAP/scipy/scikit-learn) and the `apps/api` dependencies.
- ✅ **No PyTorch** — local embeddings are delegated to LM Studio's
  OpenAI-compatible `/v1/embeddings` endpoint (`provider="local"`), avoiding a
  ~2.5GB dependency.
- ✅ Real `hierarchical_clustering` step (UMAP → KMeans → ward) runs under the
  embeddable runtime.
- ✅ The real FastAPI app boots and serves `/meta`, `/admin/reports`, etc.
- ✅ **public-viewer bundled** as a standalone static SPA, served by FastAPI under
  `/viewer`. Reports are fetched at runtime (`/report?slug=...`), so reports created
  locally appear without rebuilding. Verified end to end (list → click → report with
  Plotly charts) against the embeddable API.

## Requirements to run a full report

- **LM Studio** running locally (chat + embedding models loaded), or a cloud
  API key in `.env`. The pipeline talks to any OpenAI-compatible endpoint.

## Build

```powershell
# from repo root
powershell -ExecutionPolicy Bypass -File packaging\windows-standalone\build.ps1
```

Output lands in `packaging\windows-standalone\dist\`. Re-running is incremental;
add `-Clean` to rebuild from scratch.

## Run

```text
dist\start.bat
```

`start.bat` launches `runtime\python.exe -X utf8 run-server.py`, which boots
uvicorn on http://127.0.0.1:8000/ and opens the browser at the viewer
(http://127.0.0.1:8000/viewer/ — the API owns `/`).

### `-X utf8` is mandatory

Japanese Windows defaults to the **cp932** text encoding. The codebase has
`open()` / `json.load()` calls without an explicit `encoding=`, so without
UTF-8 mode the server crashes on startup with `UnicodeDecodeError: 'cp932'`.
`start.bat` sets `-X utf8`; do not remove it. (A more robust long-term fix is to
add `encoding="utf-8"` to those file reads in `apps/api`.)

## How the viewer is bundled (SPA, not frozen export)

`public-viewer` is built with a dedicated standalone flag and served statically:

- Build env: `NEXT_PUBLIC_OUTPUT_MODE=export`, `NEXT_PUBLIC_STANDALONE=1`,
  `NEXT_PUBLIC_API_BASEPATH=` (empty → same-origin), `NEXT_PUBLIC_PUBLIC_API_KEY=local-public`,
  `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH=/viewer`.
- `isStandaloneBuild()` (see `app/utils/static-build.ts`) switches the viewer to
  client-side data fetching so it works for reports created at runtime. This is
  **separate** from the static-site-builder's "freeze reports into HTML" export,
  which is left untouched.
- The dev file `apps/public-viewer/.env.local` (if present) points the viewer at a
  dev API port; standalone code ignores it and fetches same-origin.

## Known limitations / TODO

- **admin is NOT bundled.** It uses Next.js **Server Actions** (`output: "standalone"`)
  and needs a Node runtime as-is. Planned: migrate its Server Actions to FastAPI calls
  so it can ship as a static SPA too (the same treatment public-viewer just got).
  Until then the bundle supports viewing reports but not creating them via UI.
- **Installer not built yet.** Wrap `dist\` with Inno Setup / NSIS for a double-click
  installer + Start Menu shortcut and a windowless launcher (current `start.bat` shows
  a console window).
- **Minor (non-fatal):** a React #418 hydration warning is logged on first paint
  (the page still renders fully), and Next emits 404s for RSC prefetch `.txt` payloads
  that don't exist under static serving (client falls back to full navigation, which works).
- Harden reproducibility by installing from the repo lockfiles instead of latest.

## Files

| File | Purpose |
|---|---|
| `build.ps1` | Downloads embeddable Python, installs deps, assembles `dist/` |
| `run-server.py` | Launcher: sets defaults, boots uvicorn, opens browser |
| `start.bat` | Entry point (`python.exe -X utf8 run-server.py`) |
| `env.sample` | Template for `.env` (copied to `dist/.env` by the build) |
