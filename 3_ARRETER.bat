@echo off
chcp 65001 >nul
title SPENCER-SLOPE - Arret
color 0B

cd /d "%~dp0"

echo ==============================================
echo   SPENCER-SLOPE
echo   Arret de l'application
echo ==============================================
echo.
echo   [Diagnostic] Appuyez sur une touche pour continuer.
echo   La fenetre restera ouverte si une erreur apparait ensuite.
echo.
pause

echo Arret des serveurs SPENCER en cours...

taskkill /F /T /FI "WINDOWTITLE eq SPENCER Backend" >nul 2>&1
taskkill /F /T /FI "WINDOWTITLE eq SPENCER Frontend" >nul 2>&1

echo.
echo ==============================================
echo   BILAN
echo ==============================================
echo.
echo   Dossier  : %~dp0
echo   Backend  : arrete
echo   Frontend : arrete
echo.
echo   Vous pouvez fermer cette fenetre.
echo.
echo ==============================================
echo.
pause
