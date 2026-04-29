"""快速端到端测试"""
import subprocess, time, urllib.request, json, os, sys

d = r"C:\Users\qize\Desktop\弈辛\pipemind"
os.chdir(d)
PORT = 9201

p = subprocess.Popen([sys.executable, "pipemind.py", "--daemon", "--port", str(PORT)],
                     cwd=d, creationflags=subprocess.CREATE_NO_WINDOW)
time.sleep(10)

ok = 0
pages = ["/", "/chat", "/status", "/skills", "/chronicle", "/immune",
         "/self-improve", "/network", "/knowledge", "/memory", "/evolution",
         "/decisions", "/learn", "/home"]
apis = ["/api/stats", "/api/status/modules", "/api/skills", "/api/nav",
        "/api/network/profile", "/api/knowledge/graph"]

for path in pages + apis:
    try:
        r = urllib.request.urlopen(f"http://localhost:{PORT}{path}", timeout=5)
        d = r.read()
        if r.status == 200 and len(d) > 50:
            ok += 1
        print(f"  {'✅' if r.status==200 and len(d)>50 else '⚠'} {path} ({len(d)} bytes)")
    except Exception as e:
        print(f"  ❌ {path}: {str(e)[:40]}")

try:
    urllib.request.urlopen(f"http://localhost:{PORT}/api/daemon/stop", data=b"{}", timeout=3)
except:
    p.kill()

total = len(pages) + len(apis)
print(f"\n{ok}/{total} 响应正常")
