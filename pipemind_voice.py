"""PipeMind — 语音交互：听 + 说（Windows 原生）"""
from pipemind_core import PIPEMIND_DIR, MEM_DIR
import os, subprocess, datetime, tempfile


_has_speech = False
try:
    import speech_recognition as sr
    _has_speech = True
except Exception:
    pass


def speak(text: str) -> str:
    """用 Windows TTS 朗读文本"""
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    try:
        # PowerShell TTS
        ps_code = f'''
Add-Type -AssemblyName System.Speech
$tts = New-Object System.Speech.Synthesis.SpeechSynthesizer
$tts.Speak("{text.Replace('"', '""')}")
'''
        subprocess.run(["powershell", "-Command", ps_code], capture_output=True, timeout=30)
        return f"🔊 [{ts}] 已朗读 ({len(text)} 字)"
    except subprocess.TimeoutExpired:
        return "⏱ TTS 超时"
    except Exception as e:
        # Fallback: 用 edge-tts 如果装了
        try:
            subprocess.run(["edge-tts", "--text", text, "--write-media", 
                           os.path.join(tempfile.gettempdir(), "pipemind_tts.mp3")],
                          capture_output=True, timeout=15)
            return f"🔊 [{ts}] 已生成语音"
        except Exception:
            return f"❌ TTS 不可用: {e}"


def listen(timeout: int = 5) -> str:
    """听麦克风输入，返回文字"""
    if not _has_speech:
        return "❌ 需要安装 SpeechRecognition: pip install SpeechRecognition"
    
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.listen(source, timeout=timeout, phrase_time_limit=10)
        
        text = r.recognize_google(audio, language="zh-CN")
        return f"🎤 {text}"
    except sr.WaitTimeoutError:
        return "⏱ 未检测到语音"
    except sr.UnknownValueError:
        return "❓ 无法识别"
    except Exception as e:
        return f"❌ {e}"


def listen_loop(callback, timeout: int = 5):
    """持续监听模式（返回生成器）"""
    if not _has_speech:
        yield "❌ 需要安装 SpeechRecognition"
        return
    
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            while True:
                try:
                    audio = r.listen(source, timeout=timeout, phrase_time_limit=10)
                    text = r.recognize_google(audio, language="zh-CN")
                    yield text
                except sr.WaitTimeoutError:
                    continue
                except Exception:
                    continue
    except Exception as e:
        yield f"❌ {e}"
