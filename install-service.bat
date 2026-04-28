@echo off
chcp 65001 >nul
title 安装 PipeMind 系统服务
mode con cols=70 lines=18

cls
echo ╔═══════════════════════════════════════╗
echo ║   PipeMind — 开机自启安装工具         ║
echo ╚═══════════════════════════════════════╝
echo.
echo  本工具会将 PipeMind 安装为 Windows 计划任务
echo  每次登录时自动启动后台守护进程。
echo.
echo  安装内容：
echo    任务名: PipeMind Daemon
echo    触发:  用户登录时
echo    运行:  pipemind.py --daemon (隐藏窗口)
echo    端口:  9090
echo.

set /p confirm="确定安装? (y/N): "
if /i not "%confirm%"=="y" goto :end

echo.
echo  [..] 正在创建计划任务...
echo.

set SCRIPT_DIR=%~dp0
set PYTHON_CMD=python
set DAEMON_SCRIPT="%SCRIPT_DIR%pipemind.py"

schtasks /create /tn "PipeMind Daemon" /sc onlogon /delay 0000:30 ^
  /tr "%PYTHON_CMD% %DAEMON_SCRIPT% --daemon --port 9090" ^
  /rl highest /f 2>&1

if %ERRORLEVEL% equ 0 (
  echo  [OK] 计划任务创建成功
  echo.
  echo  ✅ PipeMind 将在下次登录时自动启动
  echo     后台运行于 http://localhost:9090
  echo.
  echo  你也可以手动启动：
  echo     双击 pipemind.bat
  echo     或运行: python pipemind.py --tray
) else (
  echo  [ERR] 计划任务创建失败
  echo.
  echo  请以管理员身份运行本脚本。
  echo  或手动添加计划任务：
  echo    1. 打开 taskschd.msc
  echo    2. 创建任务 → 用户登录时触发
  echo    3. 操作: 启动 python pipemind.py --daemon
)

:end
echo.
pause
