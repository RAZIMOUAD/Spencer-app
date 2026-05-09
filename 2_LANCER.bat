@echo off
chcp 65001 >nul
title SPENCER-SLOPE | Controle de demo
color 0B
mode con: cols=92 lines=30

cd /d "%~dp0"

echo ==============================================
echo   SPENCER-SLOPE
echo   Demarrage et controle de demo
echo ==============================================
echo.

if not exist "backend\.venv\Scripts\python.exe" (
    echo ERREUR : l'installation backend n'a pas ete faite.
    echo Lancez d'abord 1_INSTALLER.bat
    echo.
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo ERREUR : l'installation frontend n'a pas ete faite.
    echo Lancez d'abord 1_INSTALLER.bat
    echo.
    pause
    exit /b 1
)

echo Nettoyage d'anciens serveurs SPENCER eventuels...
taskkill /F /T /FI "WINDOWTITLE eq SPENCER Backend*" >nul 2>&1
taskkill /F /T /FI "WINDOWTITLE eq SPENCER Frontend*" >nul 2>&1

echo Nettoyage du cache Next.js...
if exist "frontend\.next" rmdir /S /Q "frontend\.next"

echo.
echo Demarrage du serveur backend (API)...
start "SPENCER Backend" /D "%~dp0backend" cmd /k "call .venv\Scripts\activate.bat && python -m uvicorn app.main:app --reload --port 8000"

echo Attente 4 secondes pour le demarrage du backend...
timeout /t 4 /nobreak >nul

echo Demarrage du serveur frontend (interface)...
start "SPENCER Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

echo Attente 6 secondes pour le demarrage du frontend...
timeout /t 6 /nobreak >nul

echo.
echo ==============================================
echo   Application lancee !
echo   Ouverture du navigateur...
echo ==============================================
echo.
echo   Adresse : http://localhost:3000
echo.
echo   IMPORTANT :
echo   Gardez cette fenetre ouverte pendant la demo.
echo   Quand la demo est terminee, revenez ici.
echo   Appuyez sur n'importe quelle touche pour tout arreter proprement.
echo.

start "" "http://localhost:3000"

echo.
echo   [Action requise] Appuyez sur une touche pour stopper la demo.
pause >nul

echo.
echo ==============================================
echo   Arret des serveurs SPENCER-SLOPE...
echo ==============================================
taskkill /F /T /FI "WINDOWTITLE eq SPENCER Backend*" >nul 2>&1
taskkill /F /T /FI "WINDOWTITLE eq SPENCER Frontend*" >nul 2>&1

echo Application arretee.
echo.
pause
