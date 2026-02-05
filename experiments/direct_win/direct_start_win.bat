@echo off
setlocal enabledelayedexpansion

rem === Check if .env exists ===
if not exist ".env" (
    echo [ERROR] .env file not found.
    echo Please create it using the following steps:
    echo   1. Copy .env.example to .env
    echo   2. Edit environment variables - see .env.example for details
    echo.
    pause
    exit /b 1
)

rem --- Initialize target .env files for each service ---
set CLIENT_ENV=apps\public-viewer\.env
set ADMIN_ENV=apps\admin\.env
set SERVER_ENV=apps\api\.env

(del %CLIENT_ENV%) >nul 2>&1
(del %ADMIN_ENV%) >nul 2>&1
(del %SERVER_ENV%) >nul 2>&1

rem --- Parse .env and split to each service ---
echo [STEP 1] Parsing .env and generating service-specific env files...

for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    set KEY=%%A
    set VALUE=%%B

    rem Skip comments and empty lines
    echo !KEY! | findstr /b "#" >nul && (
        rem skip comment
    ) || if not "!KEY!"=="" (
        rem Server
        if /i "!KEY!"=="OPENAI_API_KEY" (
            echo !KEY!=!VALUE!>>%SERVER_ENV%
        ) else if /i "!KEY!"=="PUBLIC_API_KEY" (
            echo !KEY!=!VALUE!>>%SERVER_ENV%
        ) else if /i "!KEY!"=="ADMIN_API_KEY" (
            echo !KEY!=!VALUE!>>%SERVER_ENV%
        ) else if /i "!KEY!"=="ENVIRONMENT" (
            echo !KEY!=!VALUE!>>%SERVER_ENV%
        ) else if /i "!KEY!"=="STORAGE_TYPE" (
            echo !KEY!=!VALUE!>>%SERVER_ENV%
        )

        rem Client
        if /i "!KEY!"=="NEXT_PUBLIC_API_BASEPATH" (
            echo !KEY!=!VALUE!>>%CLIENT_ENV%
        ) else if /i "!KEY!"=="NEXT_PUBLIC_PUBLIC_API_KEY" (
            echo !KEY!=!VALUE!>>%CLIENT_ENV%
        ) else if /i "!KEY!"=="NEXT_PUBLIC_SITE_URL" (
            echo !KEY!=!VALUE!>>%CLIENT_ENV%
        ) else if /i "!KEY!"=="NEXT_PUBLIC_GA_MEASUREMENT_ID" (
            echo !KEY!=!VALUE!>>%CLIENT_ENV%
        )

        rem Client-admin
        if /i "!KEY!"=="NEXT_PUBLIC_CLIENT_BASEPATH" (
            echo !KEY!=!VALUE!>>%ADMIN_ENV%
        ) else if /i "!KEY!"=="NEXT_PUBLIC_API_BASEPATH" (
            echo !KEY!=!VALUE!>>%ADMIN_ENV%
        ) else if /i "!KEY!"=="NEXT_PUBLIC_ADMIN_API_KEY" (
            echo !KEY!=!VALUE!>>%ADMIN_ENV%
        ) else if /i "!KEY!"=="BASIC_AUTH_USERNAME" (
            echo !KEY!=!VALUE!>>%ADMIN_ENV%
        ) else if /i "!KEY!"=="BASIC_AUTH_PASSWORD" (
            echo !KEY!=!VALUE!>>%ADMIN_ENV%
        ) else if /i "!KEY!"=="NEXT_PUBLIC_ADMIN_GA_MEASUREMENT_ID" (
            echo !KEY!=!VALUE!>>%ADMIN_ENV%
        )
    )
)

rem --- Set default Python executable ---
set "PYTHON_EXECUTABLE=.venv\Scripts\python.exe"

rem --- Override from .env if PYTHON_EXECUTABLE is defined ---
for /f "tokens=1,* delims==" %%A in (.env) do (
    if /i "%%A"=="PYTHON_EXECUTABLE" (
        set "PYTHON_EXECUTABLE=%%B"
    )
)

rem --- Save current directory and move to server folder ---
set CURRENT_DIR=%cd%
cd apps\api

rem --- Check if Python executable exists (relative to server) ---
if not exist "%PYTHON_EXECUTABLE%" (
    echo [ERROR] Python executable %PYTHON_EXECUTABLE% not found.
    echo Please check:
    echo.
    cd "%CURRENT_DIR%"
    pause
    exit /b 1
)

echo [INFO] Using Python: %PYTHON_EXECUTABLE%

rem --- Return to original directory ---
cd "%CURRENT_DIR%"

rem --- Start API server ---
echo [STEP 2] Starting FastAPI server in a new window...
start "api" cmd /k "cd apps\api && %PYTHON_EXECUTABLE% -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload --log-level debug"

rem --- Start client (frontend) ---
echo [STEP 3] Starting public-viewer (frontend) in a new window...
start "public-viewer" cmd /k "cd apps\public-viewer && pnpm run dev"

rem --- Start admin (admin panel) ---
echo [STEP 4] Starting admin (admin panel) in a new window...
start "admin" cmd /k "cd apps\admin && pnpm run dev"

echo [DONE] All services launched. Close each window to stop.
pause
