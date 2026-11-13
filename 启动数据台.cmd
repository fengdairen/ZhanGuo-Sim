@echo off
rem ============================================================
rem  ZhanGuo data workbench: one local server + one entry page.
rem  Opens http://127.0.0.1:8765/  (dist\index.html)
rem  Content kept pure ASCII: the console codepage is GBK.
rem ============================================================
setlocal
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

set "PY="
where python >nul 2>nul
if errorlevel 1 goto try_py
set "PY=python"
goto have_py

:try_py
where py >nul 2>nul
if errorlevel 1 goto try_bundled
set "PY=py -3"
goto have_py

:try_bundled
set "PY=%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
if not exist "%PY%" goto no_python

:have_py
echo Starting local server on 127.0.0.1:8765 ...
%PY% tools\serve_data_workbench.py --open
if errorlevel 1 goto failed
exit /b 0

:no_python
echo.
echo ERROR: python not found (tried python, py -3, bundled runtime).
pause
exit /b 1

:failed
echo.
echo ERROR: server failed to start.
pause
exit /b 1
