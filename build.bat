@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python build.py %*
if errorlevel 1 (
  echo.
  echo 构建失败，按任意键退出...
  pause >nul
)
endlocal
