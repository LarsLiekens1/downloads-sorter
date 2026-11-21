@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONUTF8=1

set PY=
where py >nul 2>nul && set PY=py
if "%PY%"=="" where python >nul 2>nul && set PY=python
if "%PY%"=="" goto nopython

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 goto error
)

if not exist ".venv\.deps_ok" (
    echo Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
    if errorlevel 1 goto error
    echo ok> ".venv\.deps_ok"
)

:menu
cls
echo ==============================
echo        DOWNLOADS SORTER
echo ==============================
echo.
echo   [1] Preview (nothing is moved)
echo   [2] Sort my Downloads folder
echo   [3] Undo the last sort
echo   [4] Quit
echo.
set /p CHOICE=Choose 1-4: 

if "%CHOICE%"=="1" ".venv\Scripts\python.exe" downloads_sorter.py --dry-run & goto again
if "%CHOICE%"=="2" ".venv\Scripts\python.exe" downloads_sorter.py & goto again
if "%CHOICE%"=="3" ".venv\Scripts\python.exe" downloads_sorter.py --undo & goto again
if "%CHOICE%"=="4" exit /b 0
goto menu

:again
echo.
pause
goto menu

:nopython
echo Python was not found. Install Python 3.10+ from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" during installation.
pause
exit /b 1

:error
echo Something went wrong during setup.
pause
exit /b 1