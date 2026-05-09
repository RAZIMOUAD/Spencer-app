@echo off
chcp 65001 >nul
title SPENCER - Installation

echo ==============================================
echo   SPENCER - Installation de l'application
echo   (a faire UNE SEULE FOIS)
echo ==============================================
echo.

cd /d "%~dp0"

echo [1/4] Verification de Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERREUR : Python n'est pas installe ou n'est pas dans le PATH.
    echo Installez Python 3.11 ou plus recent :
    echo https://www.python.org/downloads/
    echo Pendant l'installation, cochez "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if errorlevel 1 (
    echo.
    for /f "tokens=*" %%v in ('python --version') do echo Version detectee : %%v
    echo ERREUR : Python 3.11 minimum est requis.
    echo Installez Python 3.11 ou 3.12 puis relancez ce fichier.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('python --version') do echo        %%v trouve.

echo.
echo [2/4] Installation des paquets Python (backend)...
pushd backend
python -m venv .venv
if errorlevel 1 goto backend_error
call .venv\Scripts\activate.bat
if errorlevel 1 goto backend_error
python -m pip install --upgrade pip
if errorlevel 1 goto backend_error
python -m pip install -r requirements.txt
if errorlevel 1 goto backend_error
call deactivate
popd
echo        Backend : OK

echo.
echo [3/4] Verification de Node.js et npm...
node --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERREUR : Node.js n'est pas installe ou n'est pas dans le PATH.
    echo Installez Node.js LTS :
    echo https://nodejs.org/
    echo.
    pause
    exit /b 1
)
npm --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERREUR : npm n'est pas disponible. Reinstallez Node.js LTS.
    echo.
    pause
    exit /b 1
)
for /f "tokens=*" %%v in ('node --version') do echo        Node %%v trouve.
for /f "tokens=*" %%v in ('npm --version') do echo        npm %%v trouve.
node -e "const major=Number(process.versions.node.split('.')[0]); process.exit(major >= 18 && major < 23 && major %% 2 === 0 ? 0 : 1)" >nul 2>&1
if errorlevel 1 (
    echo.
    for /f "tokens=*" %%v in ('node --version') do echo Version detectee : Node %%v
    echo ERREUR : utilisez Node.js LTS 20 ou 22.
    echo Les versions trop recentes comme Node 23/24 peuvent casser Next.js en mode dev.
    echo Installez Node.js LTS :
    echo https://nodejs.org/
    echo.
    pause
    exit /b 1
)

echo.
echo [4/4] Installation des paquets JavaScript (frontend)...
pushd frontend
call npm install --no-audit --no-fund
if errorlevel 1 goto frontend_error
popd
echo        Frontend : OK

echo.
echo ==============================================
echo   Installation terminee avec succes !
echo   Lancez l'application avec 2_LANCER.bat
echo ==============================================
echo.
pause
exit /b 0

:backend_error
echo.
echo ERREUR : installation backend echouee.
echo Verifiez votre connexion internet puis relancez 1_INSTALLER.bat.
echo.
pause
exit /b 1

:frontend_error
echo.
echo ERREUR : installation frontend echouee.
echo Verifiez votre connexion internet puis relancez 1_INSTALLER.bat.
echo.
pause
exit /b 1
