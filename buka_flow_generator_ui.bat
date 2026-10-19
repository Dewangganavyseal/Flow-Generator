@echo off
title Flow Generator UI
cd /d "%~dp0"
echo Membuka Google Flow Generator UI...
python flow_generator_ui.py
if errorlevel 1 pause
