@echo off

:: Launch mitmdump hidden via PowerShell
powershell -ExecutionPolicy Bypass -File "C:\launch_proxy.ps1"

timeout /t 5 >nul

cd C:\webapp
git config --global http.sslCAInfo "%USERPROFILE%\.mitmproxy\mitmproxy-ca-cert.cer"
git pull origin main --quiet
call venv\Scripts\activate.bat

:: Start web app without console window
start "" venv\Scripts\pythonw.exe app.py
timeout /t 5 >nul

:: Open browser
start "" "C:\Program Files\Mozilla Firefox\firefox.exe" http://localhost:39765
