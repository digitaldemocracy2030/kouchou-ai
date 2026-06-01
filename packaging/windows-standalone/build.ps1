<#
.SYNOPSIS
  Build a Windows standalone bundle of kouchou-ai using an embeddable Python runtime.

.DESCRIPTION
  Assembles a self-contained folder that runs the FastAPI backend + analysis pipeline
  without requiring a system Python install. Validated approach (see
  tmp-embeddable-poc/FINDINGS.md):
    - embeddable Python 3.12 + pip (site-packages enabled)
    - analysis-core[clustering,gemini] (NO torch — local embeddings are delegated to LM Studio)
    - apps/api dependencies
    - launcher starts uvicorn with UTF-8 mode (-X utf8), mandatory on Japanese Windows

  Frontend bundling:
    - public-viewer: built as a standalone static SPA and served by FastAPI under /viewer.
      Reports are fetched at runtime via /report?slug=..., so reports created locally show
      up without rebuilding (see app/utils/static-build.ts isStandaloneBuild()).
    - admin: being migrated to static export (Server Actions -> FastAPI). Until then it
      needs a Node runtime and is NOT included here.

.PARAMETER PythonVersion
  Embeddable CPython version to download (must be 3.12.x to match analysis-core ABI).

.PARAMETER DistDir
  Output directory for the assembled bundle.

.EXAMPLE
  pwsh -File packaging/windows-standalone/build.ps1
#>
[CmdletBinding()]
param(
  [string]$PythonVersion = "3.12.10",
  [string]$DistDir = "$PSScriptRoot\dist",
  [switch]$Clean,
  [switch]$SkipFrontend
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
$Runtime  = Join-Path $DistDir "runtime"
$AppDir   = Join-Path $DistDir "app"
$Work     = Join-Path $PSScriptRoot ".work"

function Log($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

if ($Clean -and (Test-Path $DistDir)) { Log "Cleaning $DistDir"; Remove-Item -Recurse -Force $DistDir }
New-Item -ItemType Directory -Force -Path $DistDir, $Runtime, $Work | Out-Null

# ----------------------------------------------------------------------------
# 1. Download + extract embeddable Python
# ----------------------------------------------------------------------------
$embedZip = Join-Path $Work "python-embed.zip"
if (-not (Test-Path (Join-Path $Runtime "python.exe"))) {
  $url = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"
  Log "Downloading embeddable Python $PythonVersion"
  Invoke-WebRequest -Uri $url -OutFile $embedZip
  Log "Extracting to $Runtime"
  Expand-Archive -Path $embedZip -DestinationPath $Runtime -Force
} else {
  Log "Embeddable Python already present, skipping download"
}

# ----------------------------------------------------------------------------
# 2. Enable site-packages so pip-installed packages are importable
#    (embeddable ships with site disabled and no Lib\site-packages on path)
# ----------------------------------------------------------------------------
$pthMajorMinor = "python" + ($PythonVersion.Split('.')[0]) + ($PythonVersion.Split('.')[1])
$pth = Join-Path $Runtime "$pthMajorMinor._pth"
Log "Patching $pth (enable site-packages + import site)"
@"
$pthMajorMinor.zip
.
Lib\site-packages

import site
"@ | Set-Content -Path $pth -Encoding ascii

# ----------------------------------------------------------------------------
# 3. Bootstrap pip
# ----------------------------------------------------------------------------
$py = Join-Path $Runtime "python.exe"
if (-not (Test-Path (Join-Path $Runtime "Lib\site-packages\pip"))) {
  $getpip = Join-Path $Work "get-pip.py"
  Log "Bootstrapping pip"
  Invoke-WebRequest -Uri "https://bootstrap.pypa.io/get-pip.py" -OutFile $getpip
  & $py $getpip --no-warn-script-location
} else {
  Log "pip already present, skipping bootstrap"
}

# ----------------------------------------------------------------------------
# 4. Install analysis-core[clustering,gemini] (NO torch) + apps/api deps
#    embeddable build isolation cannot import the build backend, so pre-install
#    hatchling and install the local project with --no-build-isolation.
# ----------------------------------------------------------------------------
Log "Installing hatchling (build backend for the local analysis-core project)"
& $py -m pip install --no-warn-script-location hatchling

Log "Installing analysis-core[clustering,gemini] (torch intentionally excluded)"
& $py -m pip install --no-warn-script-location --no-build-isolation `
  "$RepoRoot\packages\analysis-core[clustering,gemini]"

Log "Installing apps/api runtime dependencies"
& $py -m pip install --no-warn-script-location `
  "fastapi" "uvicorn[standard]" "pydantic-settings" "polars" "openai" "google-genai" `
  "python-dotenv" "structlog" "orjson" "requests" "httpx" `
  "azure-storage-blob" "azure-core" "azure-identity" "tenacity"

# ----------------------------------------------------------------------------
# 5. Copy backend application source into the bundle
# ----------------------------------------------------------------------------
Log "Copying apps/api source into $AppDir"
# Clean first: Copy-Item -Recurse into an EXISTING same-named dir nests it
# (broadlistening/broadlistening/...), silently retaining stale 400MB of report data.
if (Test-Path $AppDir) { Remove-Item -Recurse -Force $AppDir }
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
Copy-Item -Recurse -Force "$RepoRoot\apps\api\src" (Join-Path $AppDir "src")
Copy-Item -Recurse -Force "$RepoRoot\apps\api\broadlistening" (Join-Path $AppDir "broadlistening")
# public/ holds the default reporter metadata + images served by /meta endpoints.
Copy-Item -Recurse -Force "$RepoRoot\apps\api\public" (Join-Path $AppDir "public")

# IMPORTANT: ship an EMPTY data set, not the developer's local reports.
# The repo's broadlistening/pipeline/{configs,inputs,outputs} and data/report_status.json
# contain real reports (incl. large embeddings.pkl) — copying them would both leak
# private data to end users and bloat the bundle (~+800MB). Reset them here.
Log "Resetting bundled report data to empty (privacy + size)"
foreach ($sub in @("pipeline\configs", "pipeline\inputs", "pipeline\outputs")) {
  $p = Join-Path $AppDir "broadlistening\$sub"
  if (Test-Path $p) { Remove-Item -Recurse -Force $p }
  New-Item -ItemType Directory -Force -Path $p | Out-Null
}
New-Item -ItemType Directory -Force -Path (Join-Path $AppDir "data") | Out-Null
# WriteAllText emits UTF-8 without BOM (Set-Content -Encoding utf8 would add a BOM).
[System.IO.File]::WriteAllText((Join-Path $AppDir "data\report_status.json"), "{}")

# Strip __pycache__ to keep the bundle lean
Get-ChildItem -Recurse -Force -Directory $AppDir -Filter "__pycache__" |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# ----------------------------------------------------------------------------
# 6. Copy launcher files
# ----------------------------------------------------------------------------
Log "Copying launcher"
Copy-Item -Force "$PSScriptRoot\run-server.py" (Join-Path $DistDir "run-server.py")
Copy-Item -Force "$PSScriptRoot\start.bat"     (Join-Path $DistDir "start.bat")
if (-not (Test-Path (Join-Path $DistDir ".env"))) {
  Copy-Item -Force "$PSScriptRoot\env.sample" (Join-Path $DistDir ".env")
}

# ----------------------------------------------------------------------------
# 7. Build + bundle the public-viewer as a standalone static SPA
#    Served by FastAPI under /viewer (the API owns "/"). Reports are fetched at
#    runtime via /report?slug=..., so newly created reports show up without a rebuild.
#    NOTE: admin is NOT bundled yet — its Server Actions still need migration to
#    FastAPI calls before it can ship as static files.
# ----------------------------------------------------------------------------
if ($SkipFrontend) {
  Log "Skipping frontend build (-SkipFrontend)."
} elseif (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Log "WARNING: node not found on PATH — skipping public-viewer build. Install Node.js + pnpm to bundle the UI."
} else {
  $viewerSrc = Join-Path $RepoRoot "apps\public-viewer"
  Log "Building public-viewer (standalone static export)"
  Push-Location $viewerSrc
  # next/node write progress + warnings to stderr; under $ErrorActionPreference='Stop'
  # PowerShell would treat those lines as terminating errors. Switch to Continue here
  # and detect real failures via $LASTEXITCODE.
  $prevEAP = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    # Standalone SPA build flags (see app/utils/static-build.ts isStandaloneBuild()).
    # API is same-origin, so NEXT_PUBLIC_API_BASEPATH is empty (root-relative fetches).
    # The key must match the bundle .env PUBLIC_API_KEY.
    $env:NEXT_PUBLIC_OUTPUT_MODE = "export"
    $env:NEXT_PUBLIC_STANDALONE = "1"
    $env:NEXT_PUBLIC_API_BASEPATH = ""
    $env:NEXT_PUBLIC_PUBLIC_API_KEY = "local-public"
    $env:NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH = "/viewer"

    if (Test-Path "out") { Remove-Item -Recurse -Force "out" }
    # Run the static-export steps directly. The package.json build:static script uses
    # POSIX inline env prefixes (VAR=val cmd) that fail under Windows cmd, so we don't use it.
    & node "scripts\copy-image.mjs"
    & node "scripts\rename-file.mjs" rename
    try {
      & npx next build
      if ($LASTEXITCODE -ne 0) { throw "next build failed (exit $LASTEXITCODE)" }
    } finally {
      & node "scripts\rename-file.mjs" restore
    }

    $viewerOut = Join-Path $DistDir "viewer"
    # robocopy /MIR mirrors out -> viewer; it tolerates locked dirs (e.g. an editor
    # file-watcher on dist/) better than Remove-Item + Copy-Item. Exit codes 0-7 = success.
    & robocopy "out" $viewerOut /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed copying viewer (exit $LASTEXITCODE)" }
    $global:LASTEXITCODE = 0
    Log "public-viewer bundled at $viewerOut"
  } finally {
    $ErrorActionPreference = $prevEAP
    Pop-Location
  }
}

Log "Done. Bundle assembled at: $DistDir"
Log "Run it with: $DistDir\start.bat"
