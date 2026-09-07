@echo off
rem Start the local viewer: videos play inline (web page), phone can join over WiFi.
cd /d "%~dp0"
python tools\serve.py
pause
