@echo off
chcp 65001 >nul
title PipeMind

rem ── 子命令模式 ──
if /i "%1"=="doctor" goto doctor
if /i "%1"=="ps" goto ps
if /i "%1"=="log" goto log
if /i "%1"=="status" goto status
if /i "%1"=="--help" goto help

rem ── 无参数 → 显示菜单 ──
mode con cols=70 lines=18
cls
echo ╔═══════════════════════════════════════╗
echo ║         PipeMind  启动器              ║
echo ║   Windows AI Agent · CLI 子命令支持   ║
echo ╚═══════════════════════════════════════╝
echo.
echo  [1] 启动托盘（推荐）
echo  [2] 启动守护进程（后台，无界面）
echo  [3] 打开 Web 控制台
echo  [4] 停止守护进程
echo  [5] 安装开机自启
echo  [6] 系统诊断 (doctor)
echo  [Q] 退出
echo.
echo  子命令: pipemind doctor / ps / log / status
echo.
set /p choice="请选择 (1-6/Q): "

if "%choice%"=="1" goto tray
if "%choice%"=="2" goto daemon
if "%choice%"=="3" goto console
if "%choice%"=="4" goto stop
if "%choice%"=="5" goto service
if "%choice%"=="6" goto doctor
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

:doctor
cls
python "%~dp0pipemind.py" doctor
pause
exit /b

:ps
cls
python "%~dp0pipemind.py" ps
pause
exit /b

:log
cls
if "%2"=="" (
    python "%~dp0pipemind.py" log
) else (
    python "%~dp0pipemind.py" log %2
)
pause
exit /b

:status
cls
python "%~dp0pipemind.py" --status
pause
exit /b

:help
cls
python "%~dp0pipemind.py" --help
pause
exit /b
