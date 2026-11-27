@echo off
title JobDisha India - FastAPI Server
echo ========================================================
echo       Starting JobDisha India (FastAPI + Turso)
echo ========================================================
echo.
cd /d %~dp0
echo Opening local development server on http://localhost:8000 ...
python main.py
pause

