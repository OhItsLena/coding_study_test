@echo off
cd C:\webapp
git pull origin main
call venv\Scripts\activate.bat
start "" venv\Scripts\pythonw.exe app.py
timeout /t 5
start "" "C:\Program Files\Mozilla Firefox\firefox.exe" http://localhost:39765