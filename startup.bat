@echo off
cd C:\webapp
call venv\Scripts\activate.bat
start "" venv\Scripts\pythonw.exe app.py
timeout /t 3
start "" "C:\Program Files\Mozilla Firefox\firefox.exe" http://localhost:39765