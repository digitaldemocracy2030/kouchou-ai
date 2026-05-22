Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Assert-True {
  param(
    [bool]$Condition,
    [string]$Message
  )

  if (-not $Condition) {
    throw $Message
  }
}

function Invoke-SetupWin {
  param(
    [string]$Workspace,
    [string[]]$InputLines,
    [bool]$DockerInfoFails = $false,
    [string]$ChoiceResponse = ""
  )

  $stdoutPath = Join-Path $Workspace "stdout.txt"
  $stderrPath = Join-Path $Workspace "stderr.txt"
  $commandLogPath = Join-Path $Workspace "setup-command.log"

  $processInfo = New-Object System.Diagnostics.ProcessStartInfo
  $processInfo.FileName = "cmd.exe"
  $processInfo.Arguments = "/c setup_win.bat"
  $processInfo.WorkingDirectory = $Workspace
  $processInfo.UseShellExecute = $false
  $processInfo.RedirectStandardInput = $true
  $processInfo.RedirectStandardOutput = $true
  $processInfo.RedirectStandardError = $true
  $processInfo.Environment["KOUCHOU_AI_SETUP_NONINTERACTIVE"] = "1"
  $processInfo.Environment["KOUCHOU_AI_SKIP_DOCKER_COMPOSE"] = "1"
  $processInfo.Environment["KOUCHOU_AI_FORCE_DOCKER_INFO_FAIL"] = if ($DockerInfoFails) { "1" } else { "" }
  $processInfo.Environment["KOUCHOU_AI_CHOICE_RESPONSE"] = $ChoiceResponse

  $process = [System.Diagnostics.Process]::Start($processInfo)
  $stdout = ""
  $stderr = ""
  $exitCode = 1
  try {
    foreach ($line in $InputLines) {
      $process.StandardInput.WriteLine($line)
    }
    $process.StandardInput.Close()

    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    $exitCode = $process.ExitCode
  } finally {
    $process.Dispose()
  }

  Set-Content -Path $stdoutPath -Value $stdout -Encoding utf8NoBOM
  Set-Content -Path $stderrPath -Value $stderr -Encoding utf8NoBOM

  return @{
    ExitCode = $exitCode
    Stdout = $stdout
    Stderr = $stderr
    CommandLogPath = $commandLogPath
    EnvPath = Join-Path $Workspace ".env"
  }
}

function New-Workspace {
  $workspace = Join-Path ([System.IO.Path]::GetTempPath()) ("kouchou-ai-win-test-" + [guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Path $workspace | Out-Null
  Copy-Item -Path (Join-Path $PSScriptRoot "..\..\setup_win.bat") -Destination (Join-Path $workspace "setup_win.bat")
  return $workspace
}

function Test-Encoding {
  $bytes = [System.IO.File]::ReadAllBytes((Join-Path $PSScriptRoot "..\..\setup_win.bat"))
  Assert-True ($bytes.Length -gt 3) "setup_win.bat is unexpectedly short"
  Assert-True (-not ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF)) "setup_win.bat should not include a UTF-8 BOM"

  $text = [System.Text.Encoding]::UTF8.GetString($bytes)
  Assert-True ($text.Contains("chcp 65001 >nul")) "setup_win.bat should set UTF-8 code page"
  Assert-True ($text.Contains("注意: Dockerのインストール直後は再起動が必要な場合があります。")) "Japanese warning text is missing"
  Assert-True (-not $text.Contains([char]0xFFFD)) "setup_win.bat contains replacement characters"
}

function Test-DockerNotRunning {
  $workspace = New-Workspace
  try {
    $result = Invoke-SetupWin -Workspace $workspace -InputLines @() -DockerInfoFails $true
    Assert-True ($result.ExitCode -ne 0) "setup_win.bat should fail when Docker is unavailable"
    Assert-True ($result.Stdout.Contains("Docker Desktop is not running.")) "Missing Docker not running message"
    Assert-True ($result.Stdout.Contains("Please start Docker Desktop and try again.")) "Missing Docker startup guidance"
    Assert-True (-not (Test-Path $result.EnvPath)) ".env should not be generated when Docker is unavailable"
  } finally {
    Remove-Item -Path $workspace -Recurse -Force
  }
}

function Test-ValidInputGeneratesEnv {
  $workspace = New-Workspace
  try {
    $result = Invoke-SetupWin -Workspace $workspace -InputLines @("sk-test-openai", "AIzaSyGeminiTest")
    Assert-True ($result.ExitCode -eq 0) "setup_win.bat should succeed for valid inputs"
    Assert-True (Test-Path $result.EnvPath) ".env should be generated"

    $envText = Get-Content -Path $result.EnvPath -Raw
    Assert-True ($envText.Contains("OPENAI_API_KEY=sk-test-openai")) "OpenAI API key was not written to .env"
    Assert-True ($envText.Contains("GEMINI_API_KEY=")) "Gemini API key line was not written to .env"
    Assert-True ($envText.Contains("NEXT_PUBLIC_API_BASEPATH=http://localhost:8000")) "Expected API base path missing from .env"
    Assert-True ($result.Stdout.Contains("[test] Skipping docker compose up -d --build")) "Expected docker compose skip message"
  } finally {
    Remove-Item -Path $workspace -Recurse -Force
  }
}

function Test-InvalidInputCanAbort {
  $workspace = New-Workspace
  try {
    $result = Invoke-SetupWin -Workspace $workspace -InputLines @("not-openai", "") -ChoiceResponse "N"
    Assert-True ($result.ExitCode -ne 0) "setup_win.bat should fail when user aborts after invalid key warning"
    Assert-True ($result.Stdout.Contains("警告: 入力されたOpenAI APIキーの形式が正しくない可能性があります。")) "Expected invalid key warning"
    Assert-True ($result.Stdout.Contains("セットアップを中止します。正しいAPIキーを用意してから再度実行してください。")) "Expected abort message"
    Assert-True (-not (Test-Path $result.EnvPath)) ".env should not be generated when setup is aborted"
  } finally {
    Remove-Item -Path $workspace -Recurse -Force
  }
}

Test-Encoding
Test-DockerNotRunning
Test-ValidInputGeneratesEnv
Test-InvalidInputCanAbort

Write-Host "setup_win.bat lightweight Windows checks passed."
