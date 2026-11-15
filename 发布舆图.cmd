@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PY=%LOCALAPPDATA%\..\..\..\..
where python >nul 2>nul && set PY=python
echo [1/2] 重建舆图 ...
call "重建地图.cmd" --no-pause
echo.
echo [2/2] 打包可分享站点 ...
"%PY%" tools\pipeline\make_site.py
echo.
echo 产物在 dist\site，整个目录上传到静态托管即可。
pause
