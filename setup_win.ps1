param(
  [Alias("non-interactive")]
  [switch] $NonInteractive,
  [Alias("skip-docker-start")]
  [switch] $SkipDockerStart,
  [Alias("skip-api-key-validation")]
  [switch] $SkipApiKeyValidation,
  [Alias("openai-api-key")]
  [AllowEmptyString()]
  [string] $OpenAiApiKey = "",
  [Alias("gemini-api-key")]
  [AllowEmptyString()]
  [string] $GeminiApiKey = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

$messages = ConvertFrom-Json @'
{
  "dialogTitle": "\u5e83\u8074AI \u30bb\u30c3\u30c8\u30a2\u30c3\u30d7",
  "dockerNotRunning": "Docker Desktop \u304c\u8d77\u52d5\u3057\u3066\u3044\u307e\u305b\u3093\u3002Docker Desktop \u3092\u8d77\u52d5\u3057\u3066\u304b\u3089\u3001\u3082\u3046\u4e00\u5ea6\u5b9f\u884c\u3057\u3066\u304f\u3060\u3055\u3044\u3002\\n\\nDocker \u3092\u30a4\u30f3\u30b9\u30c8\u30fc\u30eb\u3057\u305f\u76f4\u5f8c\u306f\u3001Windows \u306e\u518d\u8d77\u52d5\u304c\u5fc5\u8981\u306a\u5834\u5408\u304c\u3042\u308a\u307e\u3059\u3002",
  "openAiPrompt": "OpenAI API \u30ad\u30fc\u3092\u5165\u529b\u3057\u3066\u304f\u3060\u3055\u3044\u3002\\n\u7a7a\u6b04\u306e\u307e\u307e\u3067\u3082\u9032\u3081\u307e\u3059\u3002\\n\\nCtrl+V \u3067\u8cbc\u308a\u4ed8\u3051\u3067\u304d\u306a\u3044\u5834\u5408\u306f\u3001\u53f3\u30af\u30ea\u30c3\u30af\u3057\u3066\u8cbc\u308a\u4ed8\u3051\u3066\u304f\u3060\u3055\u3044\u3002",
  "geminiPrompt": "Gemini API \u30ad\u30fc\u3092\u5165\u529b\u3057\u3066\u304f\u3060\u3055\u3044\u3002\\n\u7a7a\u6b04\u306e\u307e\u307e\u3067\u3082\u9032\u3081\u307e\u3059\u3002\\n\\nCtrl+V \u3067\u8CBC\u308a\u4ed8\u3051\u3067\u304d\u306a\u3044\u5834\u5408\u306f\u3001\u53f3\u30af\u30ea\u30c3\u30af\u3057\u3066\u8cbc\u308a\u4ed8\u3051\u3066\u304f\u3060\u3055\u3044\u3002",
  "checkingKeys": "API \u30ad\u30fc\u306e\u5f62\u5f0f\u3092\u78ba\u8a8d\u3057\u3066\u3044\u307e\u3059...",
  "invalidOpenAi": "\u5165\u529b\u3055\u308c\u305f OpenAI API \u30ad\u30fc\u306e\u5f62\u5f0f\u304c\u6b63\u3057\u304f\u306a\u3044\u53ef\u80fd\u6027\u304c\u3042\u308a\u307e\u3059\u3002\u901a\u5e38\u306f \"sk-\" \u3067\u59cb\u307e\u308a\u307e\u3059\u3002",
  "invalidGemini": "\u5165\u529b\u3055\u308c\u305f Gemini API \u30ad\u30fc\u306e\u5f62\u5f0f\u304c\u6b63\u3057\u304f\u306a\u3044\u53ef\u80fd\u6027\u304c\u3042\u308a\u307e\u3059\u3002\u901a\u5e38\u306f \"AIza\" \u3067\u59cb\u307e\u308a\u307e\u3059\u3002",
  "continueInvalid": "\u5165\u529b\u5024\u306e\u5f62\u5f0f\u306b\u6c17\u306b\u306a\u308b\u70b9\u304c\u3042\u308a\u307e\u3059\u3002\u3053\u306e\u307e\u307e\u7d9a\u884c\u3057\u307e\u3059\u304b\uff1f",
  "setupCanceled": "\u30bb\u30c3\u30c8\u30a2\u30c3\u30d7\u3092\u4e2d\u6b62\u3057\u307e\u3057\u305f\u3002\u6b63\u3057\u3044 API \u30ad\u30fc\u3092\u7528\u610f\u3057\u3066\u304b\u3089\u3001\u3082\u3046\u4e00\u5ea6\u5b9f\u884c\u3057\u3066\u304f\u3060\u3055\u3044\u3002",
  "startingDocker": "Docker \u30b3\u30f3\u30c6\u30ca\u3092\u8d77\u52d5\u3057\u3066\u3044\u307e\u3059\u3002\u5b8c\u4e86\u307e\u3067\u6570\u5206\u304b\u304b\u308b\u5834\u5408\u304c\u3042\u308a\u307e\u3059\u3002",
  "dockerComposeFailed": "Docker \u30b3\u30f3\u30c6\u30ca\u306e\u8d77\u52d5\u306b\u5931\u6557\u3057\u307e\u3057\u305f\u3002\u8868\u793a\u3055\u308c\u3066\u3044\u308b\u30a8\u30e9\u30fc\u30ed\u30b0\u3092\u78ba\u8a8d\u3057\u3066\u304f\u3060\u3055\u3044\u3002",
  "setupCompleted": "\u30bb\u30c3\u30c8\u30a2\u30c3\u30d7\u304c\u5b8c\u4e86\u3057\u307e\u3057\u305f\u3002\\n\\n\u30ec\u30dd\u30fc\u30c8\u95b2\u89a7\u753b\u9762: http://localhost:3000\\n\u7ba1\u7406\u753b\u9762: http://localhost:4000"
}
'@

function Show-Message {
  param(
    [Parameter(Mandatory = $true)]
    [string] $Text,
    [Parameter(Mandatory = $true)]
    [System.Windows.Forms.MessageBoxIcon] $Icon
  )

  [void][System.Windows.Forms.MessageBox]::Show(
    $Text,
    $messages.dialogTitle,
    [System.Windows.Forms.MessageBoxButtons]::OK,
    $Icon
  )
}

function Confirm-Message {
  param(
    [Parameter(Mandatory = $true)]
    [string] $Text
  )

  $result = [System.Windows.Forms.MessageBox]::Show(
    $Text,
    $messages.dialogTitle,
    [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Warning
  )

  return $result -eq [System.Windows.Forms.DialogResult]::Yes
}

function Prompt-Value {
  param(
    [Parameter(Mandatory = $true)]
    [string] $Prompt,
    [Parameter(Mandatory = $true)]
    [string] $Title
  )

  return [Microsoft.VisualBasic.Interaction]::InputBox($Prompt, $Title, "")
}

function Test-Prefix {
  param(
    [AllowEmptyString()]
    [string] $Value,
    [Parameter(Mandatory = $true)]
    [string] $Prefix
  )

  if ([string]::IsNullOrEmpty($Value)) {
    return $true
  }

  return $Value.StartsWith($Prefix, [System.StringComparison]::OrdinalIgnoreCase)
}

try {
  [Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
} catch {
  # GUI dialogs are the primary UX, so console encoding failures are non-fatal.
}

if (-not $SkipDockerStart) {
  try {
    docker info *> $null
    $dockerInfoExitCode = $LASTEXITCODE
  } catch {
    $dockerInfoExitCode = 1
  }

  if ($dockerInfoExitCode -ne 0) {
    if ($NonInteractive) {
      Write-Error "Docker Desktop is not running. Please start Docker Desktop and try again."
    } else {
      Show-Message -Text $messages.dockerNotRunning -Icon Error
    }
    exit 1
  }
}

$openAiKey = $OpenAiApiKey
$geminiKey = $GeminiApiKey

if ([string]::IsNullOrEmpty($openAiKey) -and -not $NonInteractive) {
  $openAiKey = Prompt-Value -Prompt $messages.openAiPrompt -Title $messages.dialogTitle
}

if ([string]::IsNullOrEmpty($geminiKey) -and -not $NonInteractive) {
  $geminiKey = Prompt-Value -Prompt $messages.geminiPrompt -Title $messages.dialogTitle
}

if (-not $SkipApiKeyValidation) {
  Write-Host $messages.checkingKeys

  $warnings = [System.Collections.Generic.List[string]]::new()

  if (-not (Test-Prefix -Value $openAiKey -Prefix "sk-")) {
    $warnings.Add($messages.invalidOpenAi)
  }

  if (-not (Test-Prefix -Value $geminiKey -Prefix "AIza")) {
    $warnings.Add($messages.invalidGemini)
  }

  if ($warnings.Count -gt 0) {
    if ($NonInteractive) {
      Write-Error "Setup canceled because an API key format looked invalid."
      exit 1
    }

    $warningText = ($warnings -join "`r`n`r`n") + "`r`n`r`n" + $messages.continueInvalid
    if (-not (Confirm-Message -Text $warningText)) {
      Show-Message -Text $messages.setupCanceled -Icon Information
      exit 1
    }
  }
}

$envLines = @(
  "# Auto-generated .env file",
  "OPENAI_API_KEY=$openAiKey",
  "GEMINI_API_KEY=$geminiKey",
  "PUBLIC_API_KEY=public",
  "ADMIN_API_KEY=admin",
  "ENVIRONMENT=development",
  "STORAGE_TYPE=local",
  "NEXT_PUBLIC_PUBLIC_API_KEY=public",
  "NEXT_PUBLIC_ADMIN_API_KEY=admin",
  "NEXT_PUBLIC_CLIENT_BASEPATH=http://localhost:3000",
  "NEXT_PUBLIC_API_BASEPATH=http://localhost:8000",
  "API_BASEPATH=http://api:8000",
  "NEXT_PUBLIC_SITE_URL=http://localhost:3000"
)

Set-Content -Path (Join-Path $PSScriptRoot ".env") -Value $envLines -Encoding ascii

if ($SkipDockerStart) {
  Write-Host "Docker startup skipped."
  exit 0
}

if ($NonInteractive) {
  Write-Host $messages.startingDocker
} else {
  Show-Message -Text $messages.startingDocker -Icon Information
}

& docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
  if ($NonInteractive) {
    Write-Error "Docker environment failed to start."
  } else {
    Show-Message -Text $messages.dockerComposeFailed -Icon Error
  }
  exit $LASTEXITCODE
}

if ($NonInteractive) {
  Write-Host $messages.setupCompleted
} else {
  Show-Message -Text $messages.setupCompleted -Icon Information
}
