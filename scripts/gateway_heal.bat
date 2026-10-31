@echo off
rem Gateway keeper - Windows scheduled task layer (Hermes_Gateway_Heal, every 5 min)
rem 2026-10-31: health/restart logic fully delegated to gateway_keeper.py (single source of truth).
rem Why this layer exists: Hermes cron runs inside the desktop/gateway process tree;
rem if desktop AND gateway both die, cron dies too. This is the last independent lifeline
rem (clean env, no desktop dependency).
rem Old bug (10-31 incident 2): tasklist name-only check -- desktop backend dashboard
rem shares the same exe name as the gateway, so a dead gateway still reported "OK"
rem and Feishu stayed down 27 minutes with no alert.
rem NOTE: keep this file ASCII-only; cmd runs in GBK codepage and UTF-8 Chinese
rem comments can be mis-parsed as commands.
setlocal
set HERMES_HOME=D:\Hermes Agent CN Desktop\data\hermes-home
set PY=C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe
echo [%DATE% %TIME%] keeper(schtask) >> "%HERMES_HOME%\logs\gateway_auto_heal.log"
cd /d "%HERMES_HOME%\scripts"
"%PY%" gateway_keeper.py >> "%HERMES_HOME%\logs\gateway_auto_heal.log" 2>&1
exit /b 0
