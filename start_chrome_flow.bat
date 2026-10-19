@echo off
set "SESSION_DIR=D:\chrome_flow_session"
if not exist "D:\" set "SESSION_DIR=%LOCALAPPDATA%\chrome_flow_session"
if not exist "%SESSION_DIR%" mkdir "%SESSION_DIR%"
echo Membuka Google Chrome dengan Remote Debugging Port 9222...
echo Sesi disimpan di: %SESSION_DIR%
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%SESSION_DIR%" "https://labs.google/fx/tools/flow"
exit
