@echo off
REM kouchou-ai standalone launcher.
REM -X utf8 is REQUIRED: Japanese Windows defaults to cp932 and would crash on
REM UTF-8 report files (see tmp-embeddable-poc/FINDINGS.md).
setlocal
cd /d "%~dp0"
"%~dp0runtime\python.exe" -X utf8 "%~dp0run-server.py"
endlocal
