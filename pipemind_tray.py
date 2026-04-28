"""PipeMind 系统托盘 — 后台进程管理

用法:
  python pipemind.py --tray        # 从主入口启动
  python pipemind_tray.py          # 直接启动

功能:
  - 系统托盘图标（蓝色 PM 标志）
  - 右键菜单：打开控制台 / 状态 / 重启 / 退出
  - 自动启动守护进程（如未运行）
  - 气泡通知
"""

import os, sys, time, json, subprocess, threading
import urllib.request, urllib.error

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))
DAEMON_PORT = 9090

# ── 尝试加载 pystray ──────────────────────────

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False


# ── 图标生成 ──────────────────────────────────

def _create_icon():
    """创建系统托盘图标（32x32 蓝色 PM 标志）"""
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 蓝色圆角背景
    draw.rounded_rectangle([(1, 1), (31, 31)], radius=7, fill=(30, 30, 140))

    # PM 文字（白色，居中）
    try:
        font = ImageFont.truetype("segoeui.ttf", 14)
    except:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), "PM", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((32 - tw) // 2, (32 - th) // 2 - 1), "PM", fill=(255, 255, 255), font=font)

    return img


# ── 守护进程通信 ──────────────────────────────

def _api_url(path):
    return f"http://localhost:{DAEMON_PORT}{path}"


def _api_get(path):
    try:
        req = urllib.request.Request(_api_url(path))
        resp = urllib.request.urlopen(req, timeout=3)
        return json.loads(resp.read().decode())
    except:
        return None


def _api_post(path):
    try:
        req = urllib.request.Request(
            _api_url(path),
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read().decode())
    except:
        return None


def _check_daemon():
    """检查守护进程状态"""
    data = _api_get("/api/daemon/status")
    if data and data.get("running"):
        return True, data
    return False, None


def _ensure_daemon():
    """确保守护进程在运行"""
    running, info = _check_daemon()
    if running:
        return True, info

    # 启动守护进程
    script = os.path.join(PIPEMIND_DIR, "pipemind.py")
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    proc = subprocess.Popen(
        [sys.executable, script, "--daemon", "--port", str(DAEMON_PORT)],
        startupinfo=startupinfo,
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
    )

    # 等待就绪
    for i in range(30):
        time.sleep(0.5)
        running, info = _check_daemon()
        if running:
            return True, info
    return False, None


# ── 菜单操作 ──────────────────────────────────

def _open_console(icon):
    """打开 Web 控制台"""
    import webbrowser
    webbrowser.open(f"http://localhost:{DAEMON_PORT}")


def _show_status(icon):
    """显示状态气泡"""
    running, info = _check_daemon()
    if running:
        msgs = info.get("messages", 0)
        sid = info.get("session_id", "?")
        icon.notify(
            f"PipeMind 运行中\n"
            f"会话: {sid}\n"
            f"消息: {msgs} 条",
            "PipeMind Status"
        )
    else:
        icon.notify("PipeMind 未运行", "PipeMind Status")


def _restart_agent(icon):
    """重置 Agent（热重启）"""
    result = _api_post("/api/daemon/restart")
    if result and result.get("ok"):
        icon.notify("Agent 已重置", "PipeMind")
    else:
        icon.notify("重置失败", "PipeMind")


def _quit_all(icon):
    """退出托盘 + 停止守护进程"""
    icon.stop()
    _api_post("/api/daemon/stop")
    time.sleep(0.5)
    os._exit(0)


# ── 托盘主循环 ──────────────────────────────

def run_tray(port=9090):
    """显示系统托盘（阻塞直到退出）"""
    global DAEMON_PORT
    DAEMON_PORT = port

    if not HAS_TRAY:
        print("❌ 需要 pystray: pip install pystray")
        return

    # 确保守护进程在运行
    print("  ⏳ 检查守护进程状态...")
    ok, info = _ensure_daemon()
    if ok:
        print(f"  ✅ 守护进程已就绪 (端口 {DAEMON_PORT})")
    else:
        print(f"  ⚠ 守护进程未运行，托盘仅提供手动启动")

    # 创建系统托盘
    icon = pystray.Icon(
        "pipemind",
        _create_icon(),
        "PipeMind — Windows AI Agent",
        pystray.Menu(
            pystray.MenuItem("🖥 打开控制台", _open_console, default=True),
            pystray.MenuItem("📊 状态", _show_status),
            pystray.MenuItem("🔄 重置 Agent", _restart_agent),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("⏹ 退出", _quit_all),
        )
    )

    icon.run()


# ── 独立入口 ──────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PipeMind 系统托盘")
    parser.add_argument("--port", type=int, default=9090)
    args = parser.parse_args()
    run_tray(args.port)
