"""PipeMind Web 控制台 — 本地管理界面

用法:
  python pipemind_web.py           # 启动 (localhost:9090)
  python pipemind_web.py --port 8080  # 自定义端口
"""

import json, os, datetime, threading, sys, webbrowser

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))

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
        import pipemind as pm
        agent = pm.PipeMind()
        response = agent.chat(msg, verbose=False)
        return jsonify({"response": response[:1000]})
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
    state = {"home_id": "?", "open": False, "total_visits": 0}
    if os.path.exists(home_file):
        try:
            state = json.load(open(home_file))
        except: pass
    
    log = ""
    log_file = os.path.join(PIPEMIND_DIR, "memory", "_home_log.txt")
    if os.path.exists(log_file):
        log = "<br>".join(open(log_file).read().split("\n")[-20:])
    
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>PipeMind Home</title>
<style>body{{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}}
nav{{margin-bottom:20px;border-bottom:1px solid #30363d;padding-bottom:10px}}
nav a{{color:#58a6ff;text-decoration:none;padding:8px 16px}}
h1{{color:#f0f6fc}}
.card{{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:20px}}
pre{{background:#0d1117;padding:15px;border-radius:6px;font-size:13px}}
.status{{display:inline-block;padding:4px 12px;border-radius:12px;font-size:14px}}
.open{{background:#238636;color:#fff}}
.closed{{background:#484f58;color:#fff}}
</style></head><body>
<nav><a href="/">🏠 Dashboard</a><a href="/home">🏡 Home</a></nav>
<h1>🏡 Home Network</h1>
<div class="card">
  <h2>Status</h2>
  <p>ID: <code>{state['home_id']}</code></p>
  <p>Door: <span class="status {'open' if state['open'] else 'closed'}">{'🚪 Open' if state['open'] else '🚪 Closed'}</span></p>
  <p>Total visits: {state.get('total_visits', 0)}</p>
</div>
<div class="card">
  <h2>Live Log</h2>
  <pre>{log}</pre>
</div>
</body></html>"""

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

# ── 启动 ──────────────────────────────────────

def main():
    port = 9090
    if "--port" in sys.argv:
        idx = sys.argv.index("--port") + 1
        if idx < len(sys.argv):
            try: port = int(sys.argv[idx])
            except: pass
    
    if not HAS_FLASK:
        print("❌ 需要 Flask: pip install flask")
        return
    
    print(f"\n  🌐 PipeMind Web Console")
    print(f"     http://localhost:{port}")
    print(f"     📋 Dashboard  |  💬 Chat  |  📚 Skills  |  🏡 Home  |  📡 Providers")
    print(f"     Ctrl+C 停止\n")
    
    try:
        webbrowser.open(f"http://localhost:{port}")
    except:
        pass
    
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    main()
