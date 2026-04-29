"""PipeMind — 视觉能力：截图 + 图像分析 + OCR"""
from pipemind_core import PIPEMIND_DIR, MEM_DIR
import os, subprocess, base64, json, datetime, sys

SCREENSHOT_DIR = os.path.join(PIPEMIND_DIR, "output")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def screenshot() -> str:
    """截取当前屏幕，返回文件路径"""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCREENSHOT_DIR, f"screenshot_{ts}.png")
    
    try:
        # Windows: 用 PowerShell 截图
        ps_code = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$image = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$graphics = [System.Drawing.Graphics]::FromImage($image)
$graphics.CopyFromScreen($screen.X, $screen.Y, 0, 0, $screen.Size)
$image.Save('{path}', [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$image.Dispose()
"""
        subprocess.run(["powershell", "-Command", ps_code], capture_output=True, timeout=15)
        if os.path.exists(path):
            size = os.path.getsize(path)
            return f"📸 截图已保存 ({size//1024}KB): {path}"
        return "❌ 截图失败"
    except Exception as e:
        return f"❌ {e}"


def analyze_image(image_path: str, question: str = "描述这张图片") -> str:
    """调用多模态模型分析图片"""
    if not os.path.exists(image_path):
        return f"❌ 图片不存在: {image_path}"
    
    # 读取图片为 base64
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    
    cfg = _get_model_config()
    if not cfg:
        return "❌ 未配置 API Key"
    
    url = f"{cfg['base_url'].rstrip('/')}/chat/completions"
    body = {
        "model": cfg.get("vision_model") or "qwen-vl-max",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
            ]
        }],
        "max_tokens": 1024
    }
    
    data = json.dumps(body).encode()
    try:
        req = urllib.request.Request(url, data=data, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}"
        })
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read().decode())
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        # 保存分析结果
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out = os.path.join(SCREENSHOT_DIR, f"vision_{ts}.md")
        with open(out, "w", encoding="utf-8") as f:
            f.write(f"## 图片分析 ({os.path.basename(image_path)})\n\n{content}\n")
        return f"👁 {content}"
    except urllib.error.HTTPError as e:
        return f"❌ API Error: {e.code}"
    except Exception as e:
        return f"❌ {e}"


def _get_model_config() -> dict:
    """读取配置中的视觉模型"""
    try:
        import pipemind_config as cfg
        c = cfg.load()
        m = c.get("model", {})
        if m.get("api_key"):
            return m
        return None
    except Exception:
        return None


# 尝试导入 urllib
import urllib.request
