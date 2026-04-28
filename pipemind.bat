@echo off
chcp 65001 >nul
title PipeMind 启动器
mode con cols=65 lines=16

cls
echo ╔═══════════════════════════════════════╗
echo ║         PipeMind  启动器              ║
echo ║   Windows AI Agent · 系统托盘 · 后台  ║
echo ╚═══════════════════════════════════════╝
echo.
echo  [1] 启动托盘（推荐）
echo  [2] 启动守护进程（后台，无界面）
echo  [3] 打开 Web 控制台
echo  [4] 停止守护进程
echo  [5] 安装开机自启
echo  [Q] 退出
echo.

set /p choice="请选择 (1-5/Q): "

if "%choice%"=="1" goto tray
if "%choice%"=="2" goto daemon
if "%choice%"=="3" goto console
if "%choice%"=="4" goto stop
if "%choice%"=="5" goto service
if /i "%choice%"=="Q" exit /b
goto menu

:tray
cls
echo 启动系统托盘...
start "PipeMind Tray" /min pythonw "%~dp0pipemind.py" --tray
echo 托盘图标已启动（在通知区域查看）
pause
exit /b

:daemon
cls
echo 启动后台守护进程...
start "PipeMind Daemon" /min pythonw "%~dp0pipemind.py" --daemon
echo 守护进程已启动 (http://localhost:9090)
pause
exit /b

:console
cls
echo 打开 Web 控制台...
start http://localhost:9090
pause
exit /b

:stop
cls
python "%~dp0pipemind.py" --stop
pause
exit /b

:service
cls
start "安装开机自启" "%~dp0install-service.bat"
exit /b
