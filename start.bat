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

if not exist ".venv\.deps_v2" (
    echo Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
    if errorlevel 1 goto error
    echo ok> ".venv\.deps_v2"
)

set PYX=.venv\Scripts\python.exe

:menu
cls
echo ==============================
echo        DOWNLOADS SORTER
echo ==============================
echo.
echo   Downloads folder
echo   [1] Preview sort
echo   [2] Sort
echo   [3] Undo the last sort
echo   [4] Trash files older than 30 days
echo.
echo   All personal folders (Downloads, Desktop, Documents, Pictures, Videos, Music)
echo   [5] Preview sort
echo   [6] Sort
echo   [7] Find duplicates (preview)
echo   [8] Remove duplicates
echo   [9] Show the 20 largest files
echo.
echo   [0] Quit
echo.
set /p CHOICE=Choose 0-9: 

if "%CHOICE%"=="1" %PYX% downloads_sorter.py --dry-run & goto again
if "%CHOICE%"=="2" %PYX% downloads_sorter.py & goto again
if "%CHOICE%"=="3" %PYX% downloads_sorter.py --undo & goto again
if "%CHOICE%"=="4" %PYX% downloads_sorter.py --older-than 30 & goto again
if "%CHOICE%"=="5" %PYX% downloads_sorter.py --all --dry-run & goto again
if "%CHOICE%"=="6" %PYX% downloads_sorter.py --all & goto again
if "%CHOICE%"=="7" %PYX% downloads_sorter.py --all --duplicates --dry-run & goto again
if "%CHOICE%"=="8" %PYX% downloads_sorter.py --all --duplicates & goto again
if "%CHOICE%"=="9" %PYX% downloads_sorter.py --all --top 20 & goto again
if "%CHOICE%"=="0" exit /b 0
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