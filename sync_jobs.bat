@echo off
title JobDisha India - Daily Vacancy Sync
echo ========================================================
echo       JobDisha India - Syncing Latest Vacancies
echo ========================================================
echo.
cd /d %~dp0
python sync_service.py
echo.
pause
