@echo off
chcp 65001 >nul

echo Kouchou-AI Setup Tool
echo =====================

REM Check if Docker Desktop is running
set "DOCKER_INFO_EXIT=0"
if defined KOUCHOU_AI_FORCE_DOCKER_INFO_FAIL (
  set "DOCKER_INFO_EXIT=1"
) else (
  docker info > nul 2>&1
  set "DOCKER_INFO_EXIT=%errorlevel%"
)
if not "%DOCKER_INFO_EXIT%"=="0" (
  echo Docker Desktop is not running.
  echo Please start Docker Desktop and try again.
  echo 注意: Dockerのインストール直後は再起動が必要な場合があります。
  call :maybe_pause
  exit /b 1
)

REM Enter OpenAI API key
echo OpenAI APIキーを入力してください。（省略可）
echo(
echo 注意: Ctrl+Vが機能しない場合は、右クリックして「貼り付け」を選択してください。
echo(
set /p OPENAI_API_KEY=Enter your OpenAI API key:

REM Enter Gemini API key
echo(
echo Gemini APIキーを入力してください。（省略可）
echo(
echo 注意: Ctrl+Vが機能しない場合は、右クリックして「貼り付け」を選択してください。
echo(
set /p GEMINI_API_KEY=Enter your Gemini API key:

REM Validate OpenAI API key format
echo(
echo APIキーの形式を確認しています...
set "HAS_ERROR="

REM OpenAI: 入力があるときだけチェック
echo(
if defined OPENAI_API_KEY (
  echo %OPENAI_API_KEY% | findstr /R /C:"^sk-" >nul
  if errorlevel 1 (
    echo 警告: 入力されたOpenAI APIキーの形式が正しくない可能性があります。通常は「sk-」で始まります。
    set "HAS_ERROR=1"
  )
)

REM Gemini: 入力があるときだけチェック
echo(
if defined GEMINI_API_KEY (
  echo %GEMINI_API_KEY% | findstr /R /C:"^AIza" >nul
  if errorlevel 1 (
    echo 警告: 入力されたGemini APIキーの形式が正しくない可能性があります。通常は「AIza」で始まります。
    set "HAS_ERROR=1"
  )
)

REM どちらか不正なら継続確認
if defined HAS_ERROR (
  set "CHOICE_EXIT=0"
  if /I "%KOUCHOU_AI_CHOICE_RESPONSE%"=="N" (
    set "CHOICE_EXIT=2"
    echo 続行しますか？ (Y/N): N
  ) else if /I "%KOUCHOU_AI_CHOICE_RESPONSE%"=="Y" (
    set "CHOICE_EXIT=1"
    echo 続行しますか？ (Y/N): Y
  ) else (
    choice /c YN /n /m "続行しますか？ (Y/N): "
    set "CHOICE_EXIT=%errorlevel%"
  )
  if "%CHOICE_EXIT%"=="2" (
    echo セットアップを中止します。正しいAPIキーを用意してから再度実行してください。
    call :maybe_pause
    exit /b 1
  )
)

REM Validate Gemini API key format
if not "%GEMINI_API_KEY%"=="" (
  echo %GEMINI_API_KEY% | findstr /r "^AIza" > nul
  if %errorlevel% neq 0 (
    echo 警告: 入力されたGemini APIキーの形式が正しくない可能性があります。（通常は「AIza」で始まります）
  )
)

REM Generate .env file
echo # Auto-generated .env file > .env
echo OPENAI_API_KEY=%OPENAI_API_KEY% >> .env
echo GEMINI_API_KEY=%GEMINI_API_KEY% >> .env
echo PUBLIC_API_KEY=public >> .env
echo ADMIN_API_KEY=admin >> .env
echo ENVIRONMENT=development >> .env
echo STORAGE_TYPE=local >> .env
echo NEXT_PUBLIC_PUBLIC_API_KEY=public >> .env
echo NEXT_PUBLIC_ADMIN_API_KEY=admin >> .env
echo NEXT_PUBLIC_CLIENT_BASEPATH=http://localhost:3000 >> .env
echo NEXT_PUBLIC_API_BASEPATH=http://localhost:8000 >> .env
echo API_BASEPATH=http://api:8000 >> .env
echo NEXT_PUBLIC_SITE_URL=http://localhost:3000 >> .env

REM Start the environment
echo Starting Docker environment...
if defined KOUCHOU_AI_SKIP_DOCKER_COMPOSE (
  echo [test] Skipping docker compose up -d --build
) else (
  docker compose up -d --build
)

echo.
echo Setup completed!
echo You can now access the following URLs in your browser:
echo   http://localhost:3000 - Report Viewer
echo   http://localhost:4000 - Admin Panel
echo.
call :maybe_pause
exit /b 0

:maybe_pause
if defined KOUCHOU_AI_SETUP_NONINTERACTIVE exit /b 0
pause
exit /b 0
