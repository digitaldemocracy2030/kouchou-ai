@echo off
chcp 65001 >nul
setlocal EnableExtensions DisableDelayedExpansion

set "NON_INTERACTIVE="
set "SKIP_DOCKER_START="
set "SKIP_API_KEY_VALIDATION="

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--non-interactive" (
  set "NON_INTERACTIVE=1"
  shift
  goto parse_args
)
if /I "%~1"=="--skip-docker-start" (
  set "SKIP_DOCKER_START=1"
  shift
  goto parse_args
)
if /I "%~1"=="--skip-api-key-validation" (
  set "SKIP_API_KEY_VALIDATION=1"
  shift
  goto parse_args
)
if /I "%~1"=="--openai-api-key" (
  if "%~2"=="" (
    echo Missing value for --openai-api-key
    exit /b 1
  )
  set "OPENAI_API_KEY=%~2"
  shift
  shift
  goto parse_args
)
if /I "%~1"=="--gemini-api-key" (
  if "%~2"=="" (
    echo Missing value for --gemini-api-key
    exit /b 1
  )
  set "GEMINI_API_KEY=%~2"
  shift
  shift
  goto parse_args
)
echo Unknown option: %~1
exit /b 1

:args_done
echo Kouchou-AI Setup Tool
echo =====================

REM Check if Docker Desktop is running unless this run only verifies script behavior.
if not defined SKIP_DOCKER_START (
  call docker info >nul 2>&1
  if errorlevel 1 (
    echo Docker Desktop is not running.
    echo Please start Docker Desktop and try again.
    echo Note: You may need to restart Windows after installing Docker Desktop.
    if not defined NON_INTERACTIVE pause
    exit /b 1
  )
)

REM Enter API keys. They are optional because users may use either provider.
if not defined OPENAI_API_KEY if not defined NON_INTERACTIVE (
  echo Enter your OpenAI API key. This is optional.
  echo(
  echo If Ctrl+V does not paste, right-click this window and choose Paste.
  echo(
  set /p OPENAI_API_KEY=Enter your OpenAI API key:
)

if not defined GEMINI_API_KEY if not defined NON_INTERACTIVE (
  echo(
  echo Enter your Gemini API key. This is optional.
  echo(
  echo If Ctrl+V does not paste, right-click this window and choose Paste.
  echo(
  set /p GEMINI_API_KEY=Enter your Gemini API key:
)

REM Validate API key formats.
if not defined SKIP_API_KEY_VALIDATION (
  echo(
  echo Checking API key formats...
  set "HAS_ERROR="

  if defined OPENAI_API_KEY (
    if /I not "%OPENAI_API_KEY:~0,3%"=="sk-" (
      echo Warning: The OpenAI API key may be invalid. It usually starts with "sk-".
      set "HAS_ERROR=1"
    )
  )

  if defined GEMINI_API_KEY (
    if /I not "%GEMINI_API_KEY:~0,4%"=="AIza" (
      echo Warning: The Gemini API key may be invalid. It usually starts with "AIza".
      set "HAS_ERROR=1"
    )
  )

  if defined HAS_ERROR (
    if defined NON_INTERACTIVE (
      echo Setup canceled because an API key format looked invalid.
      exit /b 1
    )
    choice /c YN /n /m "Continue? (Y/N): "
    if errorlevel 2 (
      echo Setup canceled. Please prepare the correct API keys and run this file again.
      pause
      exit /b 1
    )
  )
)

REM Generate .env file.
> .env echo # Auto-generated .env file
>> .env echo OPENAI_API_KEY=%OPENAI_API_KEY%
>> .env echo GEMINI_API_KEY=%GEMINI_API_KEY%
>> .env echo PUBLIC_API_KEY=public
>> .env echo ADMIN_API_KEY=admin
>> .env echo ENVIRONMENT=development
>> .env echo STORAGE_TYPE=local
>> .env echo NEXT_PUBLIC_PUBLIC_API_KEY=public
>> .env echo NEXT_PUBLIC_ADMIN_API_KEY=admin
>> .env echo NEXT_PUBLIC_CLIENT_BASEPATH=http://localhost:3000
>> .env echo NEXT_PUBLIC_API_BASEPATH=http://localhost:8000
>> .env echo API_BASEPATH=http://api:8000
>> .env echo NEXT_PUBLIC_SITE_URL=http://localhost:3000

if defined SKIP_DOCKER_START (
  echo Docker startup skipped.
  exit /b 0
)

REM Start the environment.
echo Starting Docker environment...
call docker compose up -d --build
if errorlevel 1 (
  echo Docker environment failed to start.
  if not defined NON_INTERACTIVE pause
  exit /b 1
)

echo.
echo Setup completed!
echo You can now access the following URLs in your browser:
echo   http://localhost:3000 - Report Viewer
echo   http://localhost:4000 - Admin Panel
echo.
if not defined NON_INTERACTIVE pause
