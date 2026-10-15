@echo off
setlocal enabledelayedexpansion

set HERMES_HOME=D:\Hermes Agent CN Desktop\data\hermes-home
set HERMES_EXE=D:\Hermes Agent CN Desktop\data\versions\0.21.0-cn.18\hermes-agent-cn-runtime-win32-x64.exe
set LOG=%HERMES_HOME%\logs\gateway_auto_heal.log

echo [%DATE% %TIME%] Checking gateway... >> "%LOG%"

rem Check if gateway process is alive
tasklist /FI "IMAGENAME eq hermes-agent-cn-runtime-win32-x64.exe" /NH 2>nul | findstr /I "hermes-agent-cn-runtime" >nul
if !ERRORLEVEL! EQU 0 (
    echo [%DATE% %TIME%] Gateway running, OK >> "%LOG%"
    exit /b 0
)

echo [%DATE% %TIME%] Gateway NOT running, starting... >> "%LOG%"
cd /d "%HERMES_HOME%"
"%HERMES_EXE%" gateway start >> "%LOG%" 2>&1

echo [%DATE% %TIME%] Gateway start command executed >> "%LOG%"
exit /b 0
