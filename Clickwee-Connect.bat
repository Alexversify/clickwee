@echo off
title Clickwee
echo.
echo   Clickwee - connecting this PC ...
echo.
set "DIR=%LOCALAPPDATA%\Clickwee"
if not exist "%DIR%" mkdir "%DIR%"
curl -fsSL -o "%DIR%\Clickwee.ps1" https://clickwee.com/Clickwee.ps1
if errorlevel 1 powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest 'https://clickwee.com/Clickwee.ps1' -OutFile \"%DIR%\Clickwee.ps1\" -UseBasicParsing"
if not exist "%DIR%\Clickwee.ps1" (
  echo   Download failed. Check your internet connection and try again.
  pause & exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%DIR%\Clickwee.ps1" -Install
echo.
echo   Done. Go back to clickwee.com and pick a cursor.
echo   This window closes in 5 seconds.
timeout /t 5 >nul
