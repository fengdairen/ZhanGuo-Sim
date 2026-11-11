@echo off
setlocal
cd /d "%~dp0..\.."

set "PY="

python -c "import sys" >nul 2>nul
if errorlevel 1 goto try_py
set "PY=python"
goto run

:try_py
py -3 -c "import sys" >nul 2>nul
if errorlevel 1 goto try_bundled
set "PY=py"
goto run

:try_bundled
if exist "%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" set "PY=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if defined PY goto run
goto nopy

:run
echo.
echo   River Editor  -  starting local server
echo   Data file: data\map\rivers\river_segments.json
echo   Keep this window open. Close it to stop the server.
echo.
"%PY%" "tools\serve_river_editor.py" --open
echo.
echo   Server stopped.
pause
exit /b 0

:nopy
echo.
echo   Python not found.
echo   Try running manually:
echo       python tools\serve_river_editor.py --open
echo.
pause
exit /b 1
