@echo on
echo Kouchou-AI Setup Tool
echo =====================

REM Check if Docker Desktop is running
docker info > nul 2>&1
if %errorlevel% neq 0 (
  echo Docker Desktop is not running.
  echo Please start Docker Desktop and try again.
  echo 注意: Dockerのインストール直後は再起動が必要な場合があります。
  pause
  exit /b
)

REM Enter OpenAI API key
echo OpenAI APIキーを入力してください。（省略可）
echo 注意: Ctrl+Vが機能しない場合は、右クリックして「貼り付け」を選択してください。
set /p OPENAI_API_KEY=Enter your OpenAI API key:

REM Enter Gemini API key
echo Gemini APIキーを入力してください。（省略可）
set /p GEMINI_API_KEY=Enter your Gemini API key:

REM Validate OpenAI API key format
echo APIキーの形式を確認しています...
echo %OPENAI_API_KEY% | findstr /r "^sk-" > nul
if %errorlevel% neq 0 (
  echo 警告: 入力されたAPIキーの形式が正しくない可能性があります。
  echo 通常、OpenAI APIキーは「sk-」で始まります。
  echo 続行しますか？ (Y/N)
  set /p CONTINUE=
  if /i "%CONTINUE%" neq "Y" (
    echo セットアップを中止します。正しいAPIキーを用意してから再度実行してください。
    pause
    exit /b
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
docker compose up -d --build

echo.
echo Setup completed!
echo You can now access the following URLs in your browser:
echo   http://localhost:3000 - Report Viewer
echo   http://localhost:4000 - Admin Panel
echo.
pause
