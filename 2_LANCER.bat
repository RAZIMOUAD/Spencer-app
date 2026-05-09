@echo off
chcp 65001 >nul
title SPENCER-SLOPE - Controle de demo
color 0B

cd /d "%~dp0"

echo ==============================================
echo   SPENCER-SLOPE
echo   Demarrage et controle de demo
echo ==============================================
echo.
echo   [Diagnostic] Appuyez sur une touche pour continuer.
echo   La fenetre restera ouverte si une erreur apparait ensuite.
echo.
pause

echo Verification de l'installation locale...
echo        Repertoire de travail : %CD%
if not exist "backend\.venv\Scripts\python.exe" (
    echo ERREUR : l'installation backend n'a pas ete faite.
    echo Lancez d'abord 1_INSTALLER.bat
    echo.
    pause
    exit /b 1
)

if not exist "frontend\node_modules" (
    echo.
    echo ERREUR : l'installation n'a pas ete faite ou a echoue.
    echo.
    echo   ==================================================
    echo   ETAPE OBLIGATOIRE AVANT LA PREMIERE UTILISATION :
    echo   Double-cliquez sur 1_INSTALLER.bat et attendez
    echo   que la fenetre affiche "Installation reussie".
    echo   ==================================================
    echo.
    pause
    exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo ERREUR : Python n'est pas accessible dans ce terminal.
    echo Relancez 1_INSTALLER.bat apres installation correcte de Python.
    echo.
    pause
    exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
    echo ERREUR : npm n'est pas accessible dans ce terminal.
    echo Relancez 1_INSTALLER.bat apres installation correcte de Node.js.
    echo.
    pause
    exit /b 1
)

echo Nettoyage d'anciens serveurs SPENCER eventuels...
taskkill /F /T /FI "WINDOWTITLE eq SPENCER Backend" >nul 2>&1
taskkill /F /T /FI "WINDOWTITLE eq SPENCER Frontend" >nul 2>&1

echo Nettoyage du cache Next.js...
if exist "frontend\.next" rmdir /S /Q "frontend\.next"

echo.
echo Demarrage du serveur backend (API)...
start "SPENCER Backend" /D "%~dp0backend" cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000"

echo Attente 4 secondes pour le demarrage du backend...
timeout /t 4 /nobreak >nul

echo Demarrage du serveur frontend (interface)...
start "SPENCER Frontend" /D "%~dp0frontend" cmd /k "npm run dev"

echo Attente 30 secondes pour la compilation Next.js (premiere ouverture)...
timeout /t 30 /nobreak >nul

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
echo   Si la page ne charge pas encore, attendez 10-20 secondes
echo   et actualisez avec F5.
echo.

start "" "http://localhost:3000"

echo.
echo   [Action requise] Appuyez sur une touche pour stopper la demo.
pause >nul

echo.
echo ==============================================
echo   Arret des serveurs SPENCER-SLOPE...
echo ==============================================
taskkill /F /T /FI "WINDOWTITLE eq SPENCER Backend" >nul 2>&1
taskkill /F /T /FI "WINDOWTITLE eq SPENCER Frontend" >nul 2>&1

echo.
echo ==============================================
echo   BILAN DE LA SESSION
echo ==============================================
echo.
echo   Dossier  : %~dp0
echo   Backend  : arrete
echo   Frontend : arrete
echo.
echo   La demo est terminee. Vous pouvez fermer cette fenetre.
echo.
echo ==============================================
echo.
pause
