@echo off
setlocal

REM Keep this launcher ASCII-only so cmd.exe codepage differences do not
REM break parsing before PowerShell starts.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_win.ps1" %*
exit /b %errorlevel%
