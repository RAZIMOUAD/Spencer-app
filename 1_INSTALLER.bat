@echo off
chcp 65001 >nul
title SPENCER - Installation

echo ==============================================
echo   SPENCER - Installation de l'application
echo   (reinitialise toute installation precedente)
echo ==============================================
echo.
echo   Appuyez sur une touche pour commencer.
echo   La fenetre restera ouverte en cas d'erreur.
echo.
pause

cd /d "%~dp0"
echo [LOG] debut installation > "%~dp0install_log.txt"

REM ── [0/4] Nettoyage ──────────────────────────────────────────────────────
echo.
echo [0/4] Nettoyage des installations precedentes...

if exist "backend\.venv" (
    echo        Suppression de backend\.venv ...
    rmdir /S /Q "backend\.venv"
    if errorlevel 1 (
        echo ERREUR : impossible de supprimer backend\.venv.
        echo Fermez tout programme qui utilise ce dossier et relancez.
        echo.
        timeout /t 60 /nobreak
        exit /b 1
    )
)

if exist "frontend\node_modules" (
    echo        Suppression de frontend\node_modules ...
    rmdir /S /Q "frontend\node_modules"
    if errorlevel 1 (
        echo ERREUR : impossible de supprimer frontend\node_modules.
        echo Fermez tout programme qui utilise ce dossier et relancez.
        echo.
        timeout /t 60 /nobreak
        exit /b 1
    )
)

if exist "frontend\.next" (
    echo        Suppression de frontend\.next ...
    rmdir /S /Q "frontend\.next"
)

echo        Nettoyage termine.

REM ── [1/4] Python ─────────────────────────────────────────────────────────
echo.
echo [1/4] Verification de Python...

python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ==============================================
    echo   ERREUR - Python introuvable
    echo ==============================================
    echo.
    echo   Python n'est pas installe ou pas dans le PATH.
    echo.
    echo   Installez Python 3.11 ou plus recent :
    echo   https://www.python.org/downloads/
    echo   Cochez "Add Python to PATH" pendant l'installation.
    echo.
    echo ==============================================
    echo   Cette fenetre se ferme dans 60 secondes.
    echo ==============================================
    timeout /t 60 /nobreak
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo.
    echo ==============================================
    echo   ERREUR - Version Python insuffisante
    echo ==============================================
    echo.
    for /f "tokens=*" %%v in ('python --version') do echo   Version detectee : %%v
    echo   Version requise  : 3.11 ou plus recent.
    echo.
    echo   Installez Python 3.11 ou 3.12 :
    echo   https://www.python.org/downloads/
    echo.
    echo ==============================================
    echo   Cette fenetre se ferme dans 60 secondes.
    echo ==============================================
    timeout /t 60 /nobreak
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do set PY_VER=%%v
echo        %PY_VER% trouve.

REM ── [2/4] Backend ────────────────────────────────────────────────────────
echo.
echo [2/4] Installation des paquets Python dans backend\...

if not exist "backend" (
    echo.
    echo ==============================================
    echo   ERREUR - Dossier backend introuvable
    echo ==============================================
    echo.
    echo   Le dossier "backend" est absent.
    echo   Dossier actuel : %CD%
    echo.
    echo   Verifiez que ce fichier .bat est bien dans
    echo   le dossier racine de l'application.
    echo.
    echo ==============================================
    echo   Cette fenetre se ferme dans 60 secondes.
    echo ==============================================
    timeout /t 60 /nobreak
    exit /b 1
)

if not exist "backend\requirements.txt" (
    echo.
    echo ==============================================
    echo   ERREUR - backend\requirements.txt manquant
    echo ==============================================
    echo.
    echo   L'application semble incomplete ou mal copiee.
    echo.
    echo ==============================================
    echo   Cette fenetre se ferme dans 60 secondes.
    echo ==============================================
    timeout /t 60 /nobreak
    exit /b 1
)

cd /d "%~dp0backend"
echo        Repertoire courant : %CD%

echo        Creation de l'environnement virtuel Python...
python -m venv .venv
if errorlevel 1 (
    cd /d "%~dp0"
    goto backend_error
)

echo        Mise a jour de pip...
.venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 (
    cd /d "%~dp0"
    goto backend_error
)

echo        Installation des dependances Python...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    cd /d "%~dp0"
    echo [LOG] pip install ECHEC >> "%~dp0install_log.txt"
    goto backend_error
)

echo [LOG] pip install OK >> "%~dp0install_log.txt"
cd /d "%~dp0"
echo [LOG] cd racine OK >> "%~dp0install_log.txt"
echo        Backend : OK

echo [LOG] debut section Node.js >> "%~dp0install_log.txt"
where node >> "%~dp0install_log.txt" 2>&1
where npm  >> "%~dp0install_log.txt" 2>&1
REM ── [3/4] Node.js ────────────────────────────────────────────────────────
echo.
echo [3/4] Verification de Node.js et npm...

where node >nul 2>&1
if errorlevel 1 (
    echo [LOG] ERREUR node introuvable dans PATH >> "%~dp0install_log.txt"
    echo.
    echo ==============================================
    echo   ERREUR - Node.js introuvable dans le PATH
    echo ==============================================
    echo.
    echo   Installez Node.js LTS : https://nodejs.org/
    echo.
    echo ==============================================
    echo   Cette fenetre se ferme dans 60 secondes.
    echo ==============================================
    timeout /t 60 /nobreak
    exit /b 1
)
echo [LOG] where node OK >> "%~dp0install_log.txt"

where npm >nul 2>&1
if errorlevel 1 (
    echo [LOG] ERREUR npm introuvable dans PATH >> "%~dp0install_log.txt"
    echo.
    echo ==============================================
    echo   ERREUR - npm introuvable dans le PATH
    echo ==============================================
    echo.
    echo   Reinstallez Node.js LTS : https://nodejs.org/
    echo.
    echo ==============================================
    echo   Cette fenetre se ferme dans 60 secondes.
    echo ==============================================
    timeout /t 60 /nobreak
    exit /b 1
)
echo [LOG] where npm OK >> "%~dp0install_log.txt"

echo        Test d'execution de node (message d'erreur visible si echec) :
node --version
if errorlevel 1 (
    echo [LOG] ERREUR node --version plante a l'execution >> "%~dp0install_log.txt"
    echo.
    echo ==============================================
    echo   ERREUR - node.exe plante au demarrage
    echo ==============================================
    echo.
    echo   node.exe est installe mais ne peut pas s'executer.
    echo   Cause probable : Visual C++ Redistributable 2022 manquant.
    echo.
    echo   Telechargez et installez :
    echo   https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo   Puis relancez 1_INSTALLER.bat
    echo.
    echo ==============================================
    echo   Cette fenetre se ferme dans 60 secondes.
    echo ==============================================
    timeout /t 60 /nobreak
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do set NODE_VER=%%v
for /f "tokens=*" %%v in ('npm --version')  do set NPM_VER=%%v
echo        Node %NODE_VER% OK
echo        npm  %NPM_VER% OK
echo [LOG] Node=%NODE_VER% npm=%NPM_VER% OK >> "%~dp0install_log.txt"

echo [LOG] debut section Frontend >> "%~dp0install_log.txt"
REM ── [4/4] Frontend ───────────────────────────────────────────────────────
echo.
echo [4/4] Installation des paquets JavaScript dans frontend\...

if not exist "frontend" (
    echo.
    echo ==============================================
    echo   ERREUR - Dossier frontend introuvable
    echo ==============================================
    echo.
    echo   Le dossier "frontend" est absent.
    echo   Dossier actuel : %CD%
    echo.
    echo   Verifiez que ce fichier .bat est bien dans
    echo   le dossier racine de l'application.
    echo.
    echo ==============================================
    echo   Cette fenetre se ferme dans 60 secondes.
    echo ==============================================
    timeout /t 60 /nobreak
    exit /b 1
)

if not exist "frontend\package.json" (
    echo.
    echo ==============================================
    echo   ERREUR - frontend\package.json manquant
    echo ==============================================
    echo.
    echo   L'application semble incomplete ou mal copiee.
    echo.
    echo ==============================================
    echo   Cette fenetre se ferme dans 60 secondes.
    echo ==============================================
    timeout /t 60 /nobreak
    exit /b 1
)

cd /d "%~dp0frontend"
echo        Repertoire courant : %CD%
echo        Lancement de npm install - NE PAS FERMER CETTE FENETRE
echo        (peut prendre 3 a 10 minutes selon la connexion)
echo.

call npm install --no-audit --no-fund
if errorlevel 1 (
    cd /d "%~dp0"
    echo [LOG] npm install ECHEC >> "%~dp0install_log.txt"
    goto frontend_error
)

if not exist "node_modules" (
    cd /d "%~dp0"
    echo [LOG] node_modules absent >> "%~dp0install_log.txt"
    goto frontend_error
)

echo [LOG] npm install OK >> "%~dp0install_log.txt"
cd /d "%~dp0"

echo [LOG] INSTALLATION COMPLETE - succes >> "%~dp0install_log.txt"
REM ── Succes ───────────────────────────────────────────────────────────────
echo.
echo ==============================================
echo   BILAN DE L'INSTALLATION - SUCCES
echo ==============================================
echo.
echo   Dossier  : %~dp0
echo   Python   : %PY_VER%
echo   Node.js  : %NODE_VER%
echo   npm      : %NPM_VER%
echo.
echo   backend\.venv         : OK
echo   frontend\node_modules : OK
echo.
echo   Lancez maintenant 2_LANCER.bat
echo.
echo ==============================================
echo   Cette fenetre se ferme dans 60 secondes.
echo   Appuyez sur une touche pour la fermer maintenant.
echo ==============================================
timeout /t 60 /nobreak
exit /b 0

:backend_error
cd /d "%~dp0"
echo.
echo ==============================================
echo   BILAN - ECHEC INSTALLATION BACKEND
echo ==============================================
echo.
echo   Dossier  : %~dp0
echo   Python   : %PY_VER%
echo   Backend  : ECHEC
echo.
echo   Verifiez votre connexion internet puis
echo   relancez 1_INSTALLER.bat.
echo.
echo ==============================================
echo   Cette fenetre se ferme dans 60 secondes.
echo   Appuyez sur une touche pour la fermer maintenant.
echo ==============================================
timeout /t 60 /nobreak
exit /b 1

:frontend_error
cd /d "%~dp0"
echo.
echo ==============================================
echo   BILAN - ECHEC INSTALLATION FRONTEND
echo ==============================================
echo.
echo   Dossier  : %~dp0
echo   Python   : %PY_VER%
echo   Node.js  : %NODE_VER%
echo   npm      : %NPM_VER%
echo   Backend  : OK
echo   Frontend : ECHEC
echo.
echo   Verifiez votre connexion internet puis
echo   relancez 1_INSTALLER.bat.
echo.
echo ==============================================
echo   Cette fenetre se ferme dans 60 secondes.
echo   Appuyez sur une touche pour la fermer maintenant.
echo ==============================================
timeout /t 60 /nobreak
exit /b 1
