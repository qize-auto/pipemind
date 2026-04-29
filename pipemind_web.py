"""PipeMind Web 控制台 — 本地管理界面

用法:
  python pipemind_web.py           # 启动 (localhost:9090)
  python pipemind_web.py --port 8080  # 自定义端口
"""

import json, os, datetime, threading, sys, webbrowser

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 守护进程集成 ──────────────────────────────
# pipemind_daemon.py 会设置这两个变量，让 Web 路由使用持久化实例
_daemon_agent = None      # 持久化 PipeMind 实例
_daemon_port = 9090        # 守护进程端口

# ── 尝试加载 Flask ────────────────────────────

try:
    from flask import Flask, request, jsonify, render_template_string, send_from_directory
    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

# ── HTML 模板 ─────────────────────────────────

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PipeMind Console</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,'Segoe UI',sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}
nav{display:flex;gap:10px;margin-bottom:30px;border-bottom:1px solid #30363d;padding-bottom:10px}
nav a{color:#58a6ff;text-decoration:none;padding:8px 16px;border-radius:6px}
nav a:hover{background:#1f2937}
nav a.active{background:#1f6feb;color:#fff}
h1{color:#f0f6fc;margin-bottom:20px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px}
.card h2{color:#f0f6fc;font-size:16px;margin-bottom:10px}
.stat-row{display:flex;gap:20px;flex-wrap:wrap}
.stat{background:#0d1117;border:1px solid #21262d;border-radius:6px;padding:15px;min-width:120px;text-align:center}
.stat .num{font-size:28px;color:#58a6ff;font-weight:bold}
.stat .label{font-size:12px;color:#8b949e;margin-top:4px}
pre{background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:15px;overflow:auto;max-height:400px;font-size:13px}
.chat-box{background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:15px;height:300px;overflow-y:auto;margin-bottom:10px;font-size:14px}
.chat-msg{margin-bottom:8px;line-height:1.5}
.chat-user{color:#58a6ff}
.chat-pm{color:#7ee787}
.chat-input{display:flex;gap:10px}
.chat-input input{flex:1;padding:10px;background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;font-size:14px}
.chat-input button{padding:10px 20px;background:#238636;border:none;border-radius:6px;color:#fff;cursor:pointer}
.chat-input button:hover{background:#2ea043}
.log-line{padding:2px 0;font-size:13px;color:#8b949e}
.log-line .time{color:#484f58}
.log-line .from{color:#58a6ff}
</style>
</head>
<body>

<nav>
  <a href="/" class="active">🏠 Dashboard</a>
  <a href="/chat">💬 Chat</a>
  <a href="/memory">🧠 Memory</a>
  <a href="/skills">📚 Skills</a>
  <a href="/home">🏡 Home</a>
  <a href="/providers">📡 Providers</a>
</nav>

<div id="root">
<h1>🏠 PipeMind Console</h1>
<div class="stat-row">
  <div class="stat"><div class="num">{{stats.modules}}</div><div class="label">Modules</div></div>
  <div class="stat"><div class="num">{{stats.tools}}</div><div class="label">Tools</div></div>
  <div class="stat"><div class="num">{{stats.skills}}</div><div class="label">Skills</div></div>
  <div class="stat"><div class="num">{{stats.home_open}}</div><div class="label">Home Open</div></div>
</div>

<div class="card">
  <h2>📡 Providers</h2>
  <pre>{{providers}}</pre>
</div>

<div class="card">
  <h2>🧠 Active Nudges</h2>
  <pre>{{nudges}}</pre>
</div>
</div>

<script>
setInterval(() => {
  fetch('/api/stats').then(r=>r.json()).then(d=>{
    document.querySelector('.stat:nth-child(1) .num').textContent = d.modules;
    document.querySelector('.stat:nth-child(2) .num').textContent = d.tools;
    document.querySelector('.stat:nth-child(3) .num').textContent = d.skills;
  }).catch(()=>{});
}, 5000);
</script>
</body>
</html>"""

# ── Flask App ──────────────────────────────────

app = Flask(__name__)

def _get_stats():
    """获取系统统计"""
    try:
        import pipemind_evolution as evo
        v = evo.vital_signs()
        tools = v.get("tools", 0)
        skills = v.get("skills", "?")
    except:
        tools = "?"
        skills = "?"
    
    modules = len([f for f in os.listdir(PIPEMIND_DIR) if f.startswith("pipemind_") and f.endswith(".py")])
    
    home_state = {"open": False}
    home_file = os.path.join(PIPEMIND_DIR, "memory", "_home_state.json")
    if os.path.exists(home_file):
        try:
            home_state = json.load(open(home_file))
        except:
            pass
    
    # providers
    cfg_file = os.path.join(PIPEMIND_DIR, "config.json")
    providers = []
    if os.path.exists(cfg_file):
        try:
            cfg = json.load(open(cfg_file))
            providers = cfg.get("providers", [])
        except:
            pass
    
    # nudges
    nudge_file = os.path.join(PIPEMIND_DIR, "pipemind_nudge.json")
    nudges = []
    if os.path.exists(nudge_file):
        try:
            nudges = json.load(open(nudge_file)).get("nudges", [])
        except:
            pass
    
    return {
        "modules": modules,
        "tools": tools,
        "skills": skills,
        "providers": len(providers),
        "home_open": "✅ Open" if home_state.get("open") else "❌ Closed",
        "home_id": home_state.get("home_id", "?"),
    }, providers, nudges

@app.route("/")
def dashboard():
    stats, providers, nudges = _get_stats()
    prov_text = "\n".join(f"  [{i}] {p.get('name','?')} ({p.get('model','?')}) {'✅' if p.get('api_key') else '❌'}" 
                          for i, p in enumerate(providers)) or "  (none)"
    nudge_text = "\n".join(f"  · {n.get('lesson','?')[:60]} (expires {n.get('expires','?')[:10]})" 
                           for n in nudges) or "  (none)"
    return render_template_string(INDEX_HTML, stats=stats, providers=prov_text, nudges=nudge_text)

@app.route("/api/stats")
def api_stats():
    stats, _, _ = _get_stats()
    return jsonify(stats)

@app.route("/chat")
def chat_page():
    return """
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>PipeMind Chat</title>
<style>body{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;max-width:800px;margin:0 auto}
nav{margin-bottom:20px;border-bottom:1px solid #30363d;padding-bottom:10px}
nav a{color:#58a6ff;text-decoration:none;padding:8px 16px}
nav a:hover{background:#1f2937}
h1{color:#f0f6fc}
.chat-box{background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:15px;height:400px;overflow-y:auto;margin-bottom:10px}
.msg{margin-bottom:10px;line-height:1.5}
.user{color:#58a6ff}
.pm{color:#7ee787}
.input-row{display:flex;gap:10px}
.input-row input{flex:1;padding:10px;background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#c9d1d9}
.input-row button{padding:10px 20px;background:#238636;border:none;border-radius:6px;color:#fff;cursor:pointer}
</style></head>
<body>
<nav><a href="/">🏠 Dashboard</a><a href="/chat">💬 Chat</a></nav>
<h1>💬 Chat with PipeMind</h1>
<div id="chat" class="chat-box"></div>
<div class="input-row">
  <input id="input" placeholder="Type a message..." onkeydown="if(event.key==='Enter')send()">
  <button onclick="send()">Send</button>
</div>
<script>
const chat = document.getElementById('chat');
function addMsg(role, text) {
  const d = document.createElement('div'); d.className = 'msg';
  d.innerHTML = `<strong class="${role}">${role === 'user' ? '🧑' : '🤖'}</strong> ${text}`;
  chat.appendChild(d); chat.scrollTop = chat.scrollHeight;
}
function send() {
  const input = document.getElementById('input');
  const text = input.value.trim(); if(!text) return;
  addMsg('user', text); input.value = '';
  fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text})})
  .then(r=>r.json()).then(d => {
    if(d.response) addMsg('pm', d.response);
    if(d.error) addMsg('pm', '❌ ' + d.error);
  }).catch(e => addMsg('pm', '❌ ' + e));
}
</script>
</body>
</html>"""

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    msg = data.get("message", "")
    if not msg:
        return jsonify({"error": "empty"})
    try:
        sys.path.insert(0, PIPEMIND_DIR)

        # 使用持久化 Agent（守护进程模式）
        if _daemon_agent is not None:
            response = _daemon_agent.chat(msg, verbose=False)
            return jsonify({"response": response[:2000]})

        # 非守护进程模式：每次创建新实例（旧行为）
        import pipemind as pm
        agent = pm.PipeMind()
        response = agent.chat(msg, verbose=False)
        return jsonify({"response": response[:2000]})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/skills")
def skills_page():
    import pipemind_skills as pmsk
    skills = pmsk.list_skills()
    rows = "\n".join(f"<tr><td>{s['name']}</td><td>{s.get('desc','')[:60]}</td><td>{len(s.get('commands',[]))}</td></tr>" 
                     for s in skills)
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>PipeMind Skills</title>
<style>body{{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}}
nav{{margin-bottom:20px;border-bottom:1px solid #30363d;padding-bottom:10px}}
nav a{{color:#58a6ff;text-decoration:none;padding:8px 16px}}
h1{{color:#f0f6fc}}
table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:10px;border-bottom:1px solid #30363d}}
th{{color:#8b949e;font-size:12px;text-transform:uppercase}}
td{{font-size:14px}}
</style></head><body>
<nav><a href="/">🏠 Dashboard</a><a href="/skills">📚 Skills</a></nav>
<h1>📚 Skills ({len(skills)})</h1>
<table><tr><th>Name</th><th>Description</th><th>Commands</th></tr>{rows}</table>
</body></html>"""

@app.route("/home")
def home_page():
    home_file = os.path.join(PIPEMIND_DIR, "memory", "_home_state.json")
    known_file = os.path.join(PIPEMIND_DIR, "memory", "_home_known.json")
    state = {"home_id": "?", "open": False, "total_visits": 0, "public": False}
    if os.path.exists(home_file):
        try:
            state = json.load(open(home_file))
        except: pass
    
    known = []
    if os.path.exists(known_file):
        try:
            known = json.load(open(known_file)).get("homes", [])
        except: pass
    
    log = ""
    log_file = os.path.join(PIPEMIND_DIR, "memory", "_home_log.txt")
    if os.path.exists(log_file):
        log = "<br>".join(open(log_file, encoding="utf-8").read().split("\n")[-30:])
    
    known_rows = "\n".join(
        f"<tr><td>{'🟢' if h.get('online') else '🔴'}</td><td>{h.get('name','?')}</td><td>{h.get('host','?')}</td><td>{h.get('tags','general')}</td><td>{h.get('last_seen','?')[:10]}</td></tr>"
        for h in known[-20:]
    ) if known else "<tr><td colspan='5' style='text-align:center;color:#484f58'>No homes discovered yet</td></tr>"
    
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>PipeMind Home</title>
<style>
body{{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;max-width:1000px;margin:0 auto}}
nav{{margin-bottom:20px;border-bottom:1px solid #30363d;padding-bottom:10px}}
nav a{{color:#58a6ff;text-decoration:none;padding:8px 16px;border-radius:6px}}
nav a:hover{{background:#1f2937}}
h1{{color:#f0f6fc}}
h2{{color:#f0f6fc;font-size:16px;margin-bottom:15px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px}}
pre{{background:#0d1117;padding:15px;border-radius:6px;font-size:13px;max-height:300px;overflow:auto}}
table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:10px;border-bottom:1px solid #30363d;font-size:14px}}
th{{color:#8b949e;font-size:12px;text-transform:uppercase}}
.status{{display:inline-block;padding:4px 12px;border-radius:12px;font-size:14px}}
.open{{background:#238636;color:#fff}}
.closed{{background:#484f58;color:#fff}}
.btn{{padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-size:14px}}
.btn-primary{{background:#238636;color:#fff}}
.btn-primary:hover{{background:#2ea043}}
.btn-secondary{{background:#21262d;color:#c9d1d9}}
.btn-secondary:hover{{background:#30363d}}
input[type=text]{{background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:8px 12px;color:#c9d1d9;width:300px;font-size:14px}}
.row{{display:flex;gap:10px;align-items:center;margin-top:10px}}
.online{{color:#7ee787}}
.offline{{color:#484f58}}
</style></head><body>
<nav><a href="/">🏠 Dashboard</a><a href="/chat">💬 Chat</a><a href="/skills">📚 Skills</a><a href="/home">🏡 Home</a><a href="/providers">📡 Providers</a></nav>

<h1>🏡 Home Network</h1>

<div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:20px">
  <div class="card" style="flex:1;min-width:200px">
    <h2>Your Home</h2>
    <p>ID: <code>{state['home_id']}</code></p>
    <p>Door: <span class="status {'open' if state['open'] else 'closed'}">{'🚪 Open' if state['open'] else '🚪 Closed'}</span></p>
    <p>Mode: {'🌐 Public' if state.get('public') else '🔒 Local'}</p>
    <p>Visits: {state.get('total_visits', 0)}</p>
  </div>
  <div class="card" style="flex:1;min-width:200px">
    <h2>Discovery</h2>
    <p>Known homes: {len(known)}</p>
    <p>Online: {sum(1 for h in known if h.get('online'))}</p>
    <p>Harvest: {len([f for f in os.listdir(os.path.join(PIPEMIND_DIR,'memory')) if f.endswith('.json')])} files</p>
  </div>
</div>

<div class="card">
  <h2>🔍 Discover Homes</h2>
  <div class="row">
    <button class="btn btn-primary" onclick="scanLAN()">📡 Scan LAN</button>
    <span style="color:#8b949e;margin:0 10px">or</span>
    <input type="text" id="connStr" placeholder="PM-XXXX@ip:port" style="width:250px">
    <button class="btn btn-secondary" onclick="addHome()">➕ Add Manually</button>
  </div>
  <div id="scanResult" style="margin-top:10px;font-size:13px;color:#8b949e"></div>
</div>

<div class="card">
  <h2>🌐 Known Homes ({len(known)})</h2>
  <table>
    <tr><th>Status</th><th>Name</th><th>Host</th><th>Tags</th><th>Last Seen</th></tr>
    {known_rows}
  </table>
</div>

<div class="card">
  <h2>📜 Live Log</h2>
  <pre>{log}</pre>
</div>

<script>
function scanLAN() {{
  const r = document.getElementById('scanResult');
  r.textContent = '🔍 Scanning LAN for open homes...';
  fetch('/api/home/scan').then(r=>r.json()).then(d => {{
    if(d.homes && d.homes.length) {{
      r.innerHTML = '✅ Found ' + d.homes.length + ' homes: ' + d.homes.map(h=>h.name+':'+h.host).join(', ');
      location.reload();
    }} else {{
      r.textContent = '⛔ No homes found on LAN. Try adding manually.';
    }}
  }}).catch(() => r.textContent = '❌ Scan failed');
}}

function addHome() {{
  const input = document.getElementById('connStr');
  const r = document.getElementById('scanResult');
  if(!input.value.trim()) return;
  r.textContent = '🔗 Connecting...';
  fetch('/api/home/add', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{conn:input.value}})}})
  .then(r=>r.json()).then(d => {{
    if(d.ok) {{ r.innerHTML = '✅ Added: ' + d.name; location.reload(); }}
    else {{ r.textContent = '❌ ' + d.error; }}
  }}).catch(() => r.textContent = '❌ Failed');
}}

setTimeout(() => location.reload(), 30000);
</script>
</body></html>"""

@app.route("/api/home/scan")
def api_home_scan():
    """扫描局域网内的家园"""
    import socket as sock
    found = []
    known_file = os.path.join(PIPEMIND_DIR, "memory", "_home_known.json")
    
    # 扫描常见内网段
    for subnet in ["192.168.1.", "192.168.0.", "10.0.0."]:
        for i in range(1, 255):
            ip = f"{subnet}{i}"
            try:
                s = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
                s.settimeout(0.3)
                if s.connect_ex((ip, 9788)) == 0:
                    found.append({"name": f"PM@{ip}", "host": ip, "online": True})
                s.close()
            except:
                pass
    
    # 保存到已知列表
    known = {"homes": []}
    if os.path.exists(known_file):
        try: known = json.load(open(known_file))
        except: pass
    
    for f in found:
        if not any(h["host"] == f["host"] for h in known["homes"]):
            f["tags"] = "general"
            f["last_seen"] = datetime.datetime.now().isoformat()
            known["homes"].append(f)
    
    with open(known_file, "w") as f:
        json.dump(known, f, indent=2)
    
    return jsonify({"homes": found})

@app.route("/api/home/add", methods=["POST"])
def api_home_add():
    """手动添加家园"""
    data = request.get_json()
    conn = data.get("conn", "").strip()
    
    import re
    m = re.match(r'PM:(\S+)@(\S+):(\d+)', conn)
    if not m:
        m = re.match(r'(\S+)@(\S+):(\d+)', conn)
    
    if not m:
        return jsonify({"ok": False, "error": "Invalid format. Use: PM:ID@host:port"})
    
    home_id, host, port = m.group(1), m.group(2), m.group(3)
    
    known_file = os.path.join(PIPEMIND_DIR, "memory", "_home_known.json")
    known = {"homes": []}
    if os.path.exists(known_file):
        try: known = json.load(open(known_file))
        except: pass
    
    entry = {"name": home_id, "host": host, "port": int(port), "online": True, "tags": "manual", "last_seen": datetime.datetime.now().isoformat()}
    
    existing = [h for h in known["homes"] if h.get("name") == home_id or (h.get("host") == host and h.get("port") == int(port))]
    if existing:
        existing[0].update(entry)
    else:
        known["homes"].append(entry)
    
    with open(known_file, "w") as f:
        json.dump(known, f, indent=2)
    
    return jsonify({"ok": True, "name": home_id})

@app.route("/providers")
def providers_page():
    cfg_file = os.path.join(PIPEMIND_DIR, "config.json")
    providers = []
    if os.path.exists(cfg_file):
        try:
            cfg = json.load(open(cfg_file))
            providers = cfg.get("providers", [])
        except: pass
    rows = "\n".join(
        f"<tr><td>{'🟢' if p.get('api_key') else '🔴'}</td><td>{p.get('name','?')}</td><td>{p.get('model','?')}</td><td>{p.get('base_url','?')[:40]}</td><td>{p.get('priority','?')}</td></tr>"
        for p in providers
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>PipeMind Providers</title>
<style>body{{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}}
nav{{margin-bottom:20px;border-bottom:1px solid #30363d;padding-bottom:10px}}
nav a{{color:#58a6ff;text-decoration:none;padding:8px 16px}}
h1{{color:#f0f6fc}}
table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:10px;border-bottom:1px solid #30363d;font-size:14px}}
th{{color:#8b949e;font-size:12px}}
</style></head><body>
<nav><a href="/">🏠 Dashboard</a><a href="/providers">📡 Providers</a></nav>
<h1>📡 Providers ({len(providers)})</h1>
<table><tr><th></th><th>Name</th><th>Model</th><th>Base URL</th><th>Priority</th></tr>{rows}</table>
</body></html>"""

# ── 守护进程 API ────────────────────────────────

@app.errorhandler(500)
def handle_500(e):
    """捕获 500 错误并返回详细信息"""
    import traceback
    return jsonify({
        "error": str(e),
        "traceback": traceback.format_exc()
    }), 500

@app.route("/api/daemon/status")
def api_daemon_status():
    """守护进程状态"""
    import pipemind_daemon as daemon
    running = daemon.is_running()
    info = {"running": running, "port": _daemon_port}
    if running and _daemon_agent is not None:
        info["messages"] = len(_daemon_agent.messages)
        info["session_id"] = _daemon_agent.session_id
        info["uptime"] = f"PID: {os.getpid()}"
    return jsonify(info)


@app.route("/api/daemon/stop", methods=["POST"])
def api_daemon_stop():
    """优雅关闭守护进程"""
    shutdown = request.environ.get("werkzeug.server.shutdown")
    if shutdown:
        shutdown()
    else:
        import os, signal
        os.kill(os.getpid(), signal.SIGTERM)
    return jsonify({"ok": True})


@app.route("/api/daemon/restart", methods=["POST"])
def api_daemon_restart():
    """重启守护进程（重置 agent + 热重启）"""
    import pipemind_daemon as daemon
    daemon.reset_agent()
    return jsonify({"ok": True, "message": "Agent 已重置"})


# ── 记忆进化 API ──────────────────────────────

@app.route("/memory")
def memory_page():
    """记忆进化控制台页面"""
    try:
        import pipemind_memory_evolution as evo
        stats = evo.get_stats()
        logs = evo.get_consolidation_log(days=7)
    except:
        stats = {"total": 0, "by_type": {}, "top": []}
        logs = []

    log_rows = "\n".join(
        f"<tr><td>{l.get('time','?')[:10]}</td><td>{l.get('sessions',0)}</td>"
        f"<td>{l.get('knowledge',0)}</td><td>{l.get('archived',0)}</td></tr>"
        for l in logs[-7:]
    ) or "<tr><td colspan='4' style='text-align:center;color:#484f58'>No consolidations yet</td></tr>"

    top_items = "\n".join(
        f"<tr><td>{t.get('type','?')}</td><td>{t['content']}</td><td>{t.get('score',0)}</td></tr>"
        for t in stats.get("top", [])
    ) or "<tr><td colspan='3' style='text-align:center;color:#484f58'>No knowledge yet</td></tr>"

    types = "".join(
        f'<span style="display:inline-block;background:#1f2937;padding:4px 12px;border-radius:12px;margin:4px;font-size:13px">'
        f'{t}: {c}</span>'
        for t, c in stats.get("by_type", {}).items()
    ) or '<span style="color:#484f58">(empty)</span>'

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>PipeMind Memory</title>
<style>
body{{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;max-width:1000px;margin:0 auto}}
nav{{margin-bottom:20px;border-bottom:1px solid #30363d;padding-bottom:10px}}
nav a{{color:#58a6ff;text-decoration:none;padding:8px 16px;border-radius:6px}}
nav a:hover{{background:#1f2937}}
h1{{color:#f0f6fc}}
h2{{color:#f0f6fc;font-size:16px;margin-bottom:15px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px}}
.stat-row{{display:flex;gap:15px;flex-wrap:wrap}}
.stat{{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:15px;min-width:100px;text-align:center}}
.stat .num{{font-size:28px;color:#58a6ff;font-weight:bold}}
.stat .label{{font-size:12px;color:#8b949e;margin-top:4px}}
table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:8px;border-bottom:1px solid #30363d;font-size:14px}}
th{{color:#8b949e;font-size:12px}}
.btn{{padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-size:14px;background:#238636;color:#fff}}
.btn:hover{{background:#2ea043}}
</style></head><body>
<nav>
  <a href="/">🏠 Dashboard</a><a href="/chat">💬 Chat</a><a href="/memory">🧠 Memory</a>
  <a href="/skills">📚 Skills</a><a href="/home">🏡 Home</a><a href="/providers">📡 Providers</a>
</nav>

<h1>🧠 Memory Evolution</h1>

<div class="stat-row">
  <div class="stat"><div class="num">{stats['total']}</div><div class="label">Knowledge</div></div>
  <div class="stat"><div class="num">{stats.get('avg_importance',0)}</div><div class="label">Avg Importance</div></div>
  <div class="stat"><div class="num">{stats.get('forget_days',30)}d</div><div class="label">Auto-forget</div></div>
</div>

<div class="card">
  <h2>📊 Type Distribution</h2>
  <div style="margin-top:10px">{types}</div>
</div>

<div class="card">
  <h2>🏆 Top Knowledge</h2>
  <table><tr><th>Type</th><th>Content</th><th>Score</th></tr>{top_items}</table>
</div>

<div class="card">
  <h2>📜 Consolidation History</h2>
  <div style="margin-bottom:10px">
    <button class="btn" onclick="consolidate()">🔄 Run Consolidation Now</button>
    <span id="result" style="margin-left:10px;color:#8b949e"></span>
  </div>
  <table><tr><th>Date</th><th>Sessions</th><th>Knowledge</th><th>Archived</th></tr>{log_rows}</table>
</div>

<script>
function consolidate() {{
  const r = document.getElementById('result');
  r.textContent = '⏳ Running...';
  fetch('/api/memory/consolidate', {{method:'POST'}})
    .then(r=>r.json()).then(d => {{
      r.textContent = '✅ ' + d.sessions + ' sessions, ' + d.knowledge + ' knowledge';
      setTimeout(() => location.reload(), 1500);
    }}).catch(e => r.textContent = '❌ ' + e);
}}
</script>
</body></html>"""


@app.route("/api/memory/consolidate", methods=["POST"])
def api_memory_consolidate():
    """手动触发记忆聚合"""
    try:
        import pipemind_memory_evolution as evo
        result = evo.daily_consolidate()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


# ── 弈辛守护 API ──────────────────────────────

@app.route("/yixin")
def yixin_page():
    """弈辛守护面板"""
    try:
        import pipemind_wsl_bridge as wsl
        mon = wsl.get_monitor()
        s = mon.status
        presets = wsl.get_presets()
        events = wsl.get_events(limit=30)
    except:
        s = {"running": False, "model": "?", "connected": False}
        presets = []
        events = []

    status_badge = "🟢 Running" if s.get("running") else "🔴 Stopped"
    api_badge = "✅ Connected" if s.get("connected") else "❌ Disconnected"

    preset_btns = "\n".join(
        f'<button class="btn {"btn-primary" if p.get("has_key") else "btn-disabled"}" '
        f'onclick="switchPreset({p["index"]})" id="preset-{p["index"]}">'
        f'{p["name"]} ({"🔑" if p.get("has_key") else "❌"})</button>'
        for p in presets
    ) or "<p style='color:#484f58'>No presets configured</p>"

    event_rows = "\n".join(
        f'<tr><td>{e.get("time","?")[11:19]}</td>'
        f'<td><span class="tag tag-{e.get("kind","info")}">{e.get("kind","?")}</span></td>'
        f'<td>{e.get("message","")[:60]}</td></tr>'
        for e in events[-15:]
    ) or "<tr><td colspan='3' style='text-align:center;color:#484f58'>No events yet</td></tr>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>PipeMind - Yixin</title>
<style>
body{{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;max-width:1000px;margin:0 auto}}
nav{{margin-bottom:20px;border-bottom:1px solid #30363d;padding-bottom:10px}}
nav a{{color:#58a6ff;text-decoration:none;padding:8px 16px;border-radius:6px}}
nav a:hover{{background:#1f2937}}
h1{{color:#f0f6fc}}
h2{{color:#f0f6fc;font-size:16px;margin-bottom:15px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px}}
.stat-row{{display:flex;gap:15px;flex-wrap:wrap}}
.stat{{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:15px;min-width:100px;text-align:center}}
.stat .num{{font-size:24px;font-weight:bold}}
.stat .label{{font-size:12px;color:#8b949e;margin-top:4px}}
.green .num{{color:#7ee787}}
.red .num{{color:#f85149}}
.yellow .num{{color:#d29922}}
table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:8px;border-bottom:1px solid #30363d;font-size:14px}}
th{{color:#8b949e;font-size:12px}}
.btn{{padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-size:13px;margin:4px}}
.btn-primary{{background:#238636;color:#fff}}
.btn-danger{{background:#da3633;color:#fff}}
.btn-secondary{{background:#21262d;color:#c9d1d9}}
.btn-disabled{{background:#21262d;color:#484f58;cursor:not-allowed}}
.tag{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px}}
.tag-ok{{background:#238636;color:#fff}}
.tag-fail{{background:#da3633;color:#fff}}
.tag-auto_fixed{{background:#d29922;color:#000}}
.tag-auto_fix_start{{background:#1f6feb;color:#fff}}
.tag-auto_fix_fail{{background:#da3633;color:#fff}}
pre{{background:#0d1117;padding:10px;border-radius:6px;font-size:12px;max-height:200px;overflow:auto}}
</style></head><body>
<nav>
  <a href="/">🏠 Dashboard</a><a href="/chat">💬 Chat</a><a href="/memory">🧠 Memory</a>
  <a href="/yixin">🌉 Yixin</a>
  <a href="/skills">📚 Skills</a><a href="/home">🏡 Home</a><a href="/providers">📡 Providers</a>
</nav>

<h1>🌉 Yixin Guardian</h1>

<div class="stat-row">
  <div class="stat {'green' if s.get('running') else 'red'}"><div class="num">{status_badge}</div><div class="label">Process</div></div>
  <div class="stat {'green' if s.get('connected') else 'red'}"><div class="num">{api_badge}</div><div class="label">API</div></div>
  <div class="stat"><div class="num" style="color:#58a6ff">{s.get('model','?')}</div><div class="label">Model</div></div>
  <div class="stat"><div class="num">{s.get('auto_fixes',0)}</div><div class="label">Auto Fixes</div></div>
  <div class="stat"><div class="num">{s.get('fail_count',0)}</div><div class="label">Fail Streak</div></div>
</div>

<div class="card">
  <h2>🎮 Controls</h2>
  <div style="display:flex;gap:10px;flex-wrap:wrap">
    <button class="btn btn-secondary" onclick="checkNow()">🔍 Check Now</button>
    <button class="btn btn-primary" onclick="restartYixin()">🔄 Restart Yixin</button>
    <button class="btn btn-danger" onclick="stopYixin()">⏹ Stop Yixin</button>
    <button class="btn btn-secondary" onclick="fixNow()">🔧 Auto-Fix Now</button>
  </div>
  <div id="actionResult" style="margin-top:10px;font-size:14px;color:#8b949e"></div>
</div>

<div class="card">
  <h2>📡 Preset Models</h2>
  <div style="display:flex;gap:8px;flex-wrap:wrap">{preset_btns}</div>
  <div id="presetResult" style="margin-top:10px;font-size:13px;color:#8b949e"></div>
</div>

<div class="card">
  <h2>📜 Event Log</h2>
  <table><tr><th>Time</th><th>Type</th><th>Message</th></tr>{event_rows}</table>
</div>

<div class="card">
  <h2>📄 Config (raw)</h2>
  <pre id="configView">Loading...</pre>
</div>

<script>
function act(url, msg, el) {{
  const r = document.getElementById(el||'actionResult');
  r.textContent = '⏳ ' + msg + '...';
  fetch(url, {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:'{{}}'}})
    .then(r=>r.json()).then(d => {{ r.textContent = '✅ ' + JSON.stringify(d).slice(0,80); setTimeout(()=>location.reload(),2000); }})
    .catch(e => r.textContent = '❌ ' + e);
}}
function checkNow() {{ act('/api/yixin/check', 'Checking'); }}
function restartYixin() {{ act('/api/yixin/restart', 'Restarting'); }}
function stopYixin() {{ act('/api/yixin/stop', 'Stopping'); }}
function fixNow() {{ act('/api/yixin/auto-fix', 'Auto-fixing'); }}
function switchPreset(idx) {{
  const r = document.getElementById('presetResult');
  r.textContent = '⏳ Switching...';
  fetch('/api/yixin/switch', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{preset:idx}})}})
    .then(r=>r.json()).then(d => {{ r.textContent = '✅ ' + (d.ok ? 'Switched to ' + d.name : d.error); setTimeout(()=>location.reload(),2000); }})
    .catch(e => r.textContent = '❌ ' + e);
}}
fetch('/api/yixin/config').then(r=>r.json()).then(d => {{
  document.getElementById('configView').textContent = JSON.stringify(d, null, 2);
}}).catch(()=>{{}});
setInterval(() => location.reload(), 15000);
</script>
</body></html>"""


@app.route("/api/yixin/status")
def api_yixin_status():
    """弈辛守护状态"""
    try:
        import pipemind_wsl_bridge as wsl
        return jsonify(wsl.get_monitor().status)
    except Exception as e:
        return jsonify({"error": str(e), "running": False})


@app.route("/api/yixin/config")
def api_yixin_config():
    """弈辛当前配置"""
    try:
        import pipemind_wsl_bridge as wsl
        cfg = wsl.YixinConfig.read()
        # 脱敏
        if "api_key" in cfg:
            cfg["api_key"] = cfg["api_key"][:8] + "..." + cfg["api_key"][-4:]
        return jsonify(cfg)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/yixin/events")
def api_yixin_events():
    """事件日志"""
    try:
        import pipemind_wsl_bridge as wsl
        return jsonify(wsl.get_events(limit=50))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/yixin/presets")
def api_yixin_presets():
    """预设列表"""
    try:
        import pipemind_wsl_bridge as wsl
        return jsonify(wsl.get_presets())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/yixin/switch", methods=["POST"])
def api_yixin_switch():
    """切换模型预设"""
    data = request.get_json() or {}
    idx = data.get("preset", 0)
    key = data.get("api_key", "")
    try:
        import pipemind_wsl_bridge as wsl
        result = wsl.YixinConfig.switch_preset(idx, key)
        if result.get("ok"):
            # 自动重启
            wsl.YixinControl.restart()
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/yixin/restart", methods=["POST"])
def api_yixin_restart():
    """重启弈辛"""
    try:
        import pipemind_wsl_bridge as wsl
        ok = wsl.YixinControl.restart()
        return jsonify({"ok": ok})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/yixin/stop", methods=["POST"])
def api_yixin_stop():
    """停止弈辛"""
    try:
        import pipemind_wsl_bridge as wsl
        ok = wsl.YixinControl.stop()
        return jsonify({"ok": ok})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/yixin/check", methods=["POST"])
def api_yixin_check():
    """手动触发健康检查"""
    try:
        import pipemind_wsl_bridge as wsl
        wsl.get_monitor().trigger_check()
        return jsonify(wsl.get_monitor().status)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/yixin/auto-fix", methods=["POST"])
def api_yixin_autofix():
    """手动触发自动修复"""
    try:
        import pipemind_wsl_bridge as wsl
        wsl.get_monitor().trigger_auto_fix()
        return jsonify({"ok": True, "status": wsl.get_monitor().status})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


# ── 本体进化 API ──────────────────────────────

@app.route("/evolution")
def evolution_page():
    """进化状态面板"""
    try:
        import pipemind_self_evolution as se
        summary = se.format_evolution_summary()
        perf = se.PerformanceTracker.stats(days=7)
        tuning = se.SelfTuner.get_config()
        lessons = se.AutoLearner._load()
        reports = se.get_recent_reports(days=7)
    except:
        summary = "系统初始化中"
        perf = {"total": 0, "avg_duration": 0, "trend": "unknown"}
        tuning = {}
        lessons = []
        reports = []

    high_conf = [l for l in lessons if l.get("confidence", 0) > 0.6]

    report_rows = "\n".join(
        f"<tr><td>{r.get('date','?')}</td>"
        f"<td>{r['performance'].get('total',0)}</td>"
        f"<td>{r['performance'].get('avg_duration',0)}s</td>"
        f"<td>{r['performance'].get('trend','?')}</td>"
        f"<td>{'; '.join(r['tuning'].get('changes',[]))[:40] or '—'}</td></tr>"
        for r in reports[-7:]
    ) or "<tr><td colspan='5' style='text-align:center;color:#484f58'>No reports yet</td></tr>"

    lesson_rows = "\n".join(
        f"<tr><td><span class='conf-{'high' if l.get('confidence',0)>0.7 else 'med' if l.get('confidence',0)>0.4 else 'low'}'>"
        f"{l.get('confidence',0):.0%}</span></td>"
        f"<td>{l.get('trigger','?')}</td>"
        f"<td>{l.get('lesson','')[:50]}</td>"
        f"<td>{l.get('count',0)}</td></tr>"
        for l in sorted(lessons, key=lambda x: -x.get('confidence',0))[:10]
    ) or "<tr><td colspan='4' style='text-align:center;color:#484f58'>No lessons yet</td></tr>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>PipeMind Evolution</title>
<style>
body{{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;max-width:1000px;margin:0 auto}}
nav{{margin-bottom:20px;border-bottom:1px solid #30363d;padding-bottom:10px}}
nav a{{color:#58a6ff;text-decoration:none;padding:8px 16px;border-radius:6px}}
nav a:hover{{background:#1f2937}}
h1{{color:#f0f6fc}} h2{{color:#f0f6fc;font-size:16px;margin-bottom:15px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px}}
.stat-row{{display:flex;gap:15px;flex-wrap:wrap}}
.stat{{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:15px;min-width:100px;text-align:center}}
.stat .num{{font-size:24px;font-weight:bold;color:#58a6ff}}
.stat .label{{font-size:12px;color:#8b949e;margin-top:4px}}
table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:8px;border-bottom:1px solid #30363d;font-size:14px}}
th{{color:#8b949e;font-size:12px}}
.conf-high{{color:#7ee787}} .conf-med{{color:#d29922}} .conf-low{{color:#484f58}}
.btn{{padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-size:13px;margin:4px;background:#238636;color:#fff}}
.btn:hover{{background:#2ea043}}
.btn-secondary{{background:#21262d;color:#c9d1d9}}
pre{{background:#0d1117;padding:10px;border-radius:6px;font-size:12px;max-height:150px;overflow:auto}}
</style></head><body>
<nav>
  <a href="/">🏠 Dashboard</a><a href="/chat">💬 Chat</a><a href="/memory">🧠 Memory</a>
  <a href="/evolution">🧬 Evolution</a>
  <a href="/yixin">🌉 Yixin</a>
  <a href="/skills">📚 Skills</a><a href="/home">🏡 Home</a>
</nav>

<h1>🧬 Self-Evolution</h1>

<div class="stat-row">
  <div class="stat"><div class="num">{perf['total']}</div><div class="label">Conversations (7d)</div></div>
  <div class="stat"><div class="num">{perf['avg_duration']}s</div><div class="label">Avg Response</div></div>
  <div class="stat"><div class="num" style="color:{'#7ee787' if perf.get('trend')=='improving' else '#d29922' if perf.get('trend')=='stable' else '#f85149'}">{perf.get('trend','?')}</div><div class="label">Trend</div></div>
  <div class="stat"><div class="num">{len(high_conf)}</div><div class="label">Learned Lessons</div></div>
</div>

<div class="card">
  <h2>🎛 Current Parameters</h2>
  <div style="display:flex;gap:20px;flex-wrap:wrap">
    <span>🌡 temp: <strong>{tuning.get('temperature','?')}</strong></span>
    <span>📏 max_tokens: <strong>{tuning.get('max_tokens','?')}</strong></span>
    <span>🔧 retry: <strong>{tuning.get('retry_attempts','?')}</strong></span>
    <span>🛠 tool_limit: <strong>{tuning.get('max_tool_calls_per_turn','?')}</strong></span>
  </div>
  <div style="margin-top:12px">
    <button class="btn btn-secondary" onclick="tuneNow()">🔧 Auto-Tune Now</button>
    <button class="btn btn-secondary" onclick="resetTune()">↺ Reset</button>
    <span id="tuneResult" style="margin-left:10px;color:#8b949e"></span>
  </div>
</div>

<div class="card">
  <h2>📜 Evolution Reports</h2>
  <table><tr><th>Date</th><th>Conversations</th><th>Avg Time</th><th>Trend</th><th>Changes</th></tr>{report_rows}</table>
</div>

<div class="card">
  <h2>📖 Auto-Learned Lessons</h2>
  <table><tr><th>Confidence</th><th>Trigger</th><th>Lesson</th><th>Count</th></tr>{lesson_rows}</table>
  <div style="margin-top:10px">
    <button class="btn btn-secondary" onclick="learnNow()">🧠 Learn from Recent</button>
    <span id="learnResult" style="margin-left:10px;color:#8b949e"></span>
  </div>
</div>

<script>
function tuneNow() {{
  const r = document.getElementById('tuneResult');
  r.textContent = '⏳ Tuning...';
  fetch('/api/evolution/tune', {{method:'POST'}})
    .then(r=>r.json()).then(d => {{ r.textContent = '✅ ' + (d.changes.join('; ') || 'No changes'); setTimeout(()=>location.reload(),1500); }})
    .catch(e => r.textContent = '❌ ' + e);
}}
function resetTune() {{
  const r = document.getElementById('tuneResult');
  r.textContent = '⏳ Resetting...';
  fetch('/api/evolution/reset', {{method:'POST'}})
    .then(r=>r.json()).then(d => {{ r.textContent = '✅ Reset'; setTimeout(()=>location.reload(),1500); }})
    .catch(e => r.textContent = '❌ ' + e);
}}
function learnNow() {{
  const r = document.getElementById('learnResult');
  r.textContent = '⏳ Learning...';
  fetch('/api/evolution/learn', {{method:'POST'}})
    .then(r=>r.json()).then(d => {{ r.textContent = '✅ Done'; setTimeout(()=>location.reload(),1500); }})
    .catch(e => r.textContent = '❌ ' + e);
}}
</script>
</body></html>"""


@app.route("/api/evolution/tune", methods=["POST"])
def api_evolution_tune():
    """手动触发自调优"""
    try:
        import pipemind_self_evolution as se
        perf = se.PerformanceTracker.stats(days=3)
        result = se.SelfTuner.auto_tune(perf)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/evolution/reset", methods=["POST"])
def api_evolution_reset():
    """重置调优参数"""
    try:
        import pipemind_self_evolution as se
        state = se.SelfTuner.reset()
        return jsonify({"ok": True, "state": state})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/evolution/learn", methods=["POST"])
def api_evolution_learn():
    """手动触发学习"""
    try:
        import pipemind_self_evolution as se
        stats = se.PerformanceTracker.stats(days=1)
        if stats.get("error_rate", 0) > 0.1:
            se.AutoLearner.learn_from_error("high_error_rate",
                f"Error rate: {stats['error_rate']}", confidence=0.4)
        if stats.get("avg_duration", 0) > 20:
            se.AutoLearner.learn_from_error("slow_response",
                f"Avg duration: {stats['avg_duration']}s", confidence=0.3)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)})


# ── 每日学习 API ─────────────────────────────

@app.route("/learn")
def learn_page():
    """每日学习日志页面"""
    try:
        import pipemind_daily_learn as dl
        logs = dl.get_learn_log(days=7)
        skills = dl.get_learned_skills()
    except:
        logs = []
        skills = []

    log_rows = "\n".join(
        f"<tr><td>{l.get('date','?')}</td>"
        f"<td>{l.get('total_learned',0)}</td>"
        f"<td>{'、'.join(s.get('source','') for s in l.get('sources',[]) if s.get('new_skills')) or '—'}</td>"
        f"<td>{l.get('summary','')[:80]}...</td></tr>"
        for l in logs
    ) or "<tr><td colspan='4' style='text-align:center;color:#484f58'>No learn logs yet</td></tr>"

    skill_rows = "\n".join(
        f"<tr><td>{s.get('name','?')}</td><td>{s.get('desc','')[:50]}</td></tr>"
        for s in skills
    ) or "<tr><td colspan='2' style='text-align:center;color:#484f58'>No absorbed skills yet</td></tr>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>PipeMind Learn</title>
<style>
body{{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;max-width:1000px;margin:0 auto}}
nav{{margin-bottom:20px;border-bottom:1px solid #30363d;padding-bottom:10px}}
nav a{{color:#58a6ff;text-decoration:none;padding:8px 16px;border-radius:6px}}
nav a:hover{{background:#1f2937}}
h1{{color:#f0f6fc}} h2{{color:#f0f6fc;font-size:16px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px}}
.btn{{padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-size:13px;background:#238636;color:#fff}}
.btn:hover{{background:#2ea043}} .btn-secondary{{background:#21262d;color:#c9d1d9}}
table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:8px;border-bottom:1px solid #30363d;font-size:14px}}
th{{color:#8b949e;font-size:12px}}
</style></head><body>
<nav>
  <a href="/">🏠 Dashboard</a><a href="/chat">💬 Chat</a><a href="/memory">🧠 Memory</a>
  <a href="/evolution">🧬 Evolution</a><a href="/learn">📚 Learn</a>
  <a href="/yixin">🌉 Yixin</a><a href="/skills">📚 Skills</a><a href="/home">🏡 Home</a>
</nav>
<h1>📚 Daily Learning</h1>
<div style="margin-bottom:20px">
  <button class="btn" onclick="learnNow()">🧠 Learn Now</button>
  <span id="result" style="margin-left:10px;color:#8b949e"></span>
</div>
<div class="card">
  <h2>📜 Learn History</h2>
  <table><tr><th>Date</th><th>Learned</th><th>Sources</th><th>Summary</th></tr>{log_rows}</table>
</div>
<div class="card">
  <h2>📦 Absorbed Skills (from Yixin)</h2>
  <table><tr><th>Name</th><th>Description</th></tr>{skill_rows}</table>
</div>
<script>
function learnNow() {{
  const r = document.getElementById('result');
  r.textContent = '⏳ Learning...';
  fetch('/api/learn/run', {{method:'POST'}})
    .then(r=>r.json()).then(d => {{
      r.textContent = '✅ ' + (d.summary || 'Done');
      setTimeout(()=>location.reload(),1500);
    }}).catch(e => r.textContent = '❌ ' + e);
}}
</script>
</body></html>"""


@app.route("/api/learn/run", methods=["POST"])
def api_learn_run():
    """手动触发每日学习"""
    try:
        import pipemind_daily_learn as dl
        result = dl.daily_learn()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


# ── 决策引擎 API ────────────────────────────

@app.route("/decisions")
def decisions_page():
    """决策引擎面板"""
    try:
        import pipemind_decision as dec
        state = dec.get_current_state()
        logs = dec.get_decision_log(limit=20)
    except:
        state = {}
        logs = []

    # 状态摘要
    mem = state.get("memory", {})
    perf = state.get("performance", {})
    yixin = state.get("yixin", {})

    state_cards = f"""
    <div class="stat"><div class="num">{mem.get('total',0)}</div><div class="label">Knowledge</div></div>
    <div class="stat"><div class="num">{perf.get('today_conversations',0)}</div><div class="label">Conv Today</div></div>
    <div class="stat"><div class="num" style="color:{'#7ee787' if perf.get('error_rate',0)<0.1 else '#f85149'}">{perf.get('error_rate',0):.0%}</div><div class="label">Error Rate</div></div>
    <div class="stat"><div class="num" style="color:{'#7ee787' if yixin.get('running') else '#f85149'}">{'🟢' if yixin.get('running') else '🔴'}</div><div class="label">Yixin</div></div>
    <div class="stat"><div class="num">{perf.get('trend','?')}</div><div class="label">Trend</div></div>"""

    # 决策历史
    log_rows = "\n".join(
        f"<tr><td>{l.get('time','?')[11:19]}</td>"
        f"<td>{'、'.join(l.get('decisions',[])) or '—'}</td>"
        f"<td>{'; '.join(a.get('result','')[:40] for a in l.get('actions',[])) or '—'}</td></tr>"
        for l in logs[-10:]
    ) or "<tr><td colspan='3' style='text-align:center;color:#484f58'>No decisions yet</td></tr>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>PipeMind Decisions</title>
<style>
body{{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;max-width:1000px;margin:0 auto}}
nav{{margin-bottom:20px;border-bottom:1px solid #30363d;padding-bottom:10px}}
nav a{{color:#58a6ff;text-decoration:none;padding:8px 16px;border-radius:6px}}
nav a:hover{{background:#1f2937}}
h1{{color:#f0f6fc}} h2{{color:#f0f6fc;font-size:16px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px}}
.stat-row{{display:flex;gap:15px;flex-wrap:wrap}}
.stat{{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:15px;min-width:100px;text-align:center}}
.stat .num{{font-size:24px;font-weight:bold;color:#58a6ff}}
.stat .label{{font-size:12px;color:#8b949e;margin-top:4px}}
table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:8px;border-bottom:1px solid #30363d;font-size:14px}}
th{{color:#8b949e;font-size:12px}}
.btn{{padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-size:13px;background:#238636;color:#fff}}
.btn:hover{{background:#2ea043}}
pre{{background:#0d1117;padding:10px;border-radius:6px;font-size:12px;max-height:200px;overflow:auto}}
</style></head><body>
<nav>
  <a href="/">🏠 Dashboard</a><a href="/chat">💬 Chat</a><a href="/memory">🧠 Memory</a>
  <a href="/evolution">🧬 Evolution</a><a href="/learn">📚 Learn</a>
  <a href="/decisions">🤖 Decisions</a>
  <a href="/yixin">🌉 Yixin</a><a href="/home">🏡 Home</a>
</nav>
<h1>🤖 Decision Engine</h1>
<p style="color:#8b949e;margin-bottom:20px">每30分钟自动评估系统状态，决定下一步行动。</p>

<div class="stat-row">{state_cards}</div>

<div class="card">
  <h2>🎮 Control</h2>
  <button class="btn" onclick="cycleNow()">🔄 Run Decision Cycle Now</button>
  <span id="result" style="margin-left:10px;color:#8b949e"></span>
</div>

<div class="card">
  <h2>📜 Decision History</h2>
  <table><tr><th>Time</th><th>Decisions</th><th>Actions Taken</th></tr>{log_rows}</table>
</div>

<div class="card">
  <h2>📄 Current State (raw)</h2>
  <pre>{json.dumps(state, ensure_ascii=False, indent=2)[:500]}</pre>
</div>

<script>
function cycleNow() {{
  const r = document.getElementById('result');
  r.textContent = '⏳ Running...';
  fetch('/api/decisions/cycle', {{method:'POST'}})
    .then(r=>r.json()).then(d => {{
      r.textContent = '✅ ' + (d.actions?.length || 0) + ' actions taken';
      setTimeout(()=>location.reload(),1500);
    }}).catch(e => r.textContent = '❌ ' + e);
}}
</script>
</body></html>"""


@app.route("/api/decisions/state")
def api_decisions_state():
    """当前系统状态"""
    try:
        import pipemind_decision as dec
        return jsonify(dec.get_current_state())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/decisions/log")
def api_decisions_log():
    """决策历史"""
    try:
        import pipemind_decision as dec
        return jsonify(dec.get_decision_log(limit=30))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/decisions/cycle", methods=["POST"])
def api_decisions_cycle():
    """手动触发决策周期"""
    try:
        import pipemind_decision as dec
        result = dec.decision_cycle()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


# ── 系统状态 / 日志 API ─────────────────────

@app.route("/status")
def status_page():
    """系统状态面板 — 所有子系统一览"""
    try:
        from pipemind_core import list_modules, module_stats, get_recent_logs, PIPEMIND_DIR
        modules = list_modules()
        stats = module_stats()
        logs = get_recent_logs(limit=30)
    except:
        modules = []
        stats = {"total": 0, "running": 0, "errored": 0}
        logs = []

    mod_rows = "\n".join(
        f"<tr><td>{m.get('name','?')}</td>"
        f"<td><span class='status-{m['status']}'>{'🟢' if m['status']=='running' else '🔴' if m['status']=='error' else '⚪'}</span></td>"
        f"<td>{m.get('started_at','—')[:19] if m.get('started_at') else '—'}</td>"
        f"<td>{m.get('errors',0)}</td></tr>"
        for m in modules
    ) or "<tr><td colspan='4' style='text-align:center;color:#484f58'>No modules registered</td></tr>"

    log_rows = "\n".join(
        f"<tr><td>{l.get('time','?')[11:19]}</td>"
        f"<td><span class='level-{l.get('level','info')}'>{l.get('level','?')}</span></td>"
        f"<td>{l.get('module','?')}</td>"
        f"<td>{l.get('message','')[:60]}</td></tr>"
        for l in logs
    ) or "<tr><td colspan='4' style='text-align:center;color:#484f58'>No logs yet</td></tr>"

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>PipeMind Status</title>
<style>
body{{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px;max-width:1000px;margin:0 auto}}
nav{{margin-bottom:20px;border-bottom:1px solid #30363d;padding-bottom:10px}}
nav a{{color:#58a6ff;text-decoration:none;padding:8px 16px;border-radius:6px}}
nav a:hover{{background:#1f2937}}
h1{{color:#f0f6fc}} h2{{color:#f0f6fc;font-size:16px}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px}}
.stat-row{{display:flex;gap:15px;flex-wrap:wrap}}
.stat{{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:15px;min-width:80px;text-align:center}}
.stat .num{{font-size:24px;font-weight:bold;color:#58a6ff}}
.stat .label{{font-size:12px;color:#8b949e;margin-top:4px}}
table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:8px;border-bottom:1px solid #30363d;font-size:13px}}
th{{color:#8b949e;font-size:11px}}
.status-running{{color:#7ee787}} .status-error{{color:#f85149}} .status-stopped{{color:#484f58}}
.level-error{{color:#f85149;font-weight:bold}} .level-warn{{color:#d29922}} .level-info{{color:#8b949e}}
</style></head><body>
<nav>
  <a href="/">🏠 Dashboard</a><a href="/chat">💬 Chat</a><a href="/status">📊 Status</a>
  <a href="/memory">🧠 Memory</a><a href="/evolution">🧬 Evolution</a>
  <a href="/decisions">🤖 Decisions</a><a href="/learn">📚 Learn</a>
  <a href="/yixin">🌉 Yixin</a>
</nav>
<h1>📊 System Status</h1>

<div class="stat-row">
  <div class="stat"><div class="num">{stats.get('total',0)}</div><div class="label">Modules</div></div>
  <div class="stat"><div class="num" style="color:#7ee787">{stats.get('running',0)}</div><div class="label">Running</div></div>
  <div class="stat"><div class="num" style="color:#f85149">{stats.get('errored',0)}</div><div class="label">Errored</div></div>
</div>

<div class="card">
  <h2>🧩 Module Registry</h2>
  <table><tr><th>Module</th><th>Status</th><th>Started</th><th>Errors</th></tr>{mod_rows}</table>
</div>

<div class="card">
  <h2>📋 Live Logs</h2>
  <table><tr><th>Time</th><th>Level</th><th>Module</th><th>Message</th></tr>{log_rows}</table>
</div>
</body></html>"""


@app.route("/api/status/modules")
def api_status_modules():
    """模块注册表"""
    try:
        from pipemind_core import list_modules
        return jsonify(list_modules())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/status/logs")
def api_status_logs():
    """最近日志"""
    try:
        from pipemind_core import get_recent_logs
        level = request.args.get("level")
        module = request.args.get("module")
        return jsonify(get_recent_logs(limit=50, level=level, module=module))
    except Exception as e:
        return jsonify({"error": str(e)})


# ── 系统诊断 API ─────────────────────────────

@app.route("/api/doctor/run")
def api_doctor_run():
    """运行系统诊断"""
    try:
        import pipemind_doctor as doc
        report = doc.run_diagnostics()
        return jsonify({"report": report})
    except Exception as e:
        return jsonify({"error": str(e)})


# ── 启动 ──────────────────────────────────────

def run(port=9090, daemon_mode=False):
    """启动 Web 服务器

    Args:
        port: 监听端口
        daemon_mode: 守护进程模式（由 daemon 调用，不打开浏览器）
    """
    if not HAS_FLASK:
        print("❌ 需要 Flask: pip install flask")
        return

    if not daemon_mode:
        print(f"\n  🌐 PipeMind Web Console")
        print(f"     http://localhost:{port}")
        print(f"     📋 Dashboard  |  💬 Chat  |  📚 Skills  |  🏡 Home  |  📡 Providers")
        print(f"     Ctrl+C 停止\n")

    try:
        if not daemon_mode:
            webbrowser.open(f"http://localhost:{port}")
    except:
        pass

    app.run(host="0.0.0.0", port=port, debug=False)


def main():
    """CLI 入口（兼容旧用法）"""
    port = 9090
    if "--port" in sys.argv:
        idx = sys.argv.index("--port") + 1
        if idx < len(sys.argv):
            try:
                port = int(sys.argv[idx])
            except:
                pass
    run(port=port)


if __name__ == "__main__":
    main()
