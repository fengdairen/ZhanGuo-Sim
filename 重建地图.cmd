@echo off
rem ============================================================
rem  Rebuild the vector map from traced river/lake/coast data.
rem  Usage:  重建地图.cmd             just rebuild
rem          重建地图.cmd open        rebuild then open map.html
rem  (Content kept pure ASCII: the console codepage is GBK.)
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
echo.
echo === 1/4  sync traced data ===
%PY% tools\pipeline\sync_river_editor.py
if errorlevel 1 goto failed

echo.
echo === 2/4  traced data to vector layers ===
%PY% tools\pipeline\rivers_from_editor.py
if errorlevel 1 goto failed

echo.
echo === 3/4  coastline to sea polygon ===
%PY% tools\pipeline\build_sea_from_coast.py
if errorlevel 1 goto failed

echo.
echo === 4/4  build map.html ===
rem 3.5 面与归属（node 跑平面划分）
where node >nul 2>nul
if not errorlevel 1 (
  echo [3.5/4] faces: planar arrangement ...
  node tools\pipeline\faces.js
) else (
  echo [3.5/4] SKIP faces.js - node not found, map will use old realms
)

%PY% tools\pipeline\make_vector_map.py
if errorlevel 1 goto failed

echo.
echo ============================================================
echo  OK  dist\map-vector\map.html
echo      dist\map-vector\map.html
for %%F in ("dist\map-vector\map.html") do echo      %%~zF bytes
echo ============================================================
if /i "%~1"=="open" start "" "dist\map-vector\map.html"
pause
exit /b 0

:no_python
echo.
echo ERROR: python not found (tried python, py -3, bundled runtime).
pause
exit /b 1

:failed
echo.
echo ERROR: a step above failed. Map NOT updated.
pause
exit /b 1
