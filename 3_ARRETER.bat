@echo off
chcp 65001 >nul
title SPENCER-SLOPE | Arret
color 0B
mode con: cols=92 lines=22

echo ==============================================
echo   SPENCER-SLOPE
echo   Arret de l'application
echo ==============================================
echo.
echo Arret des serveurs SPENCER en cours...

taskkill /F /T /FI "WINDOWTITLE eq SPENCER Backend*" >nul 2>&1
taskkill /F /T /FI "WINDOWTITLE eq SPENCER Frontend*" >nul 2>&1

echo Application arretee.
echo.
pause
