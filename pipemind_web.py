"""PipeMind Web 控制台 — 本地管理界面

用法:
  python pipemind_web.py           # 启动 (localhost:9090)
  python pipemind_web.py --port 8080  # 自定义端口
"""

import json, os, datetime, threading, sys, webbrowser, time

PIPEMIND_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 守护进程集成 ──────────────────────────────
# pipemind_daemon.py 会设置这两个变量，让 Web 路由使用持久化实例
_daemon_agent = None      # 持久化 PipeMind 实例
_daemon_port = 9090        # 守护进程端口

@app.route("/api/nav")
def api_nav():
    """返回导航组件 HTML"""
    nav_path = os.path.join(PIPEMIND_DIR, "templates", "nav.html")
    if os.path.exists(nav_path):
        with open(nav_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

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
nav{display:flex;gap:10px;margin-bottom:20px;border-bottom:1px solid #30363d;padding-bottom:10px;flex-wrap:wrap}
nav a{color:#58a6ff;text-decoration:none;padding:6px 14px;border-radius:6px;font-size:14px}
nav a:hover{background:#1f2937}
nav a.active{background:#1f6feb;color:#fff}
h1{color:#f0f6fc;margin-bottom:20px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:16px}
.stat-row{display:flex;gap:12px;flex-wrap:wrap}
.stat{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:14px;min-width:110px;flex:1;text-align:center}
.stat .num{font-size:26px;color:#58a6ff;font-weight:bold}
.stat .label{font-size:11px;color:#8b949e;margin-top:3px}
pre{background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:12px;overflow:auto;max-height:300px;font-size:13px}
.log-entry{padding:4px 0;font-size:13px;border-bottom:1px solid #21262d}
.log-entry:last-child{border-bottom:none}
.log-time{color:#484f58;margin-right:8px}
.log-mod{color:#58a6ff;margin-right:8px}
.log-msg{color:#c9d1d9}
.log-error .log-msg{color:#f85149}
.log-warn .log-msg{color:#d29922}
.badge{display:inline-block;padding:3px 10px;border-radius:10px;font-size:12px;font-weight:bold}
.badge-green{background:#238636;color:#fff}
.badge-red{background:#da3633;color:#fff}
.badge-yellow{background:#d29922;color:#000}
.badge-gray{background:#21262d;color:#8b949e}
.quick-btn{padding:8px 16px;border:none;border-radius:6px;cursor:pointer;font-size:13px;margin:4px;background:#21262d;color:#c9d1d9}
.quick-btn:hover{background:#30363d}
.quick-btn.primary{background:#238636;color:#fff}
.quick-btn.primary:hover{background:#2ea043}
.quick-btn.danger{background:#da3633;color:#fff}
@media(max-width:600px){.stat{min-width:80px}.stat .num{font-size:20px}}
</style>
</head>
<body>

<nav>
  <a href="/" class="active">🏠 Dashboard</a>
  <a href="/chat">💬 Chat</a>
  <a href="/status">📊 Status</a>
  <a href="/memory">🧠 Memory</a>
  <a href="/evolution">🧬 Evolution</a>
  <a href="/decisions">🤖 Decisions</a>
  <a href="/learn">📚 Learn</a>
  <a href="/yixin">🌉 Yixin</a>
  <a href="/home">🏡 Home</a>
</nav>

<div id="root">
<h1>🏠 PipeMind Command Center</h1>

<!-- Status Bar -->
<div id="statusBar" style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap"></div>

<!-- Quick Stats -->
<div class="stat-row" id="statsRow" style="margin-bottom:16px">
  <div class="stat"><div class="num">—</div><div class="label">Conv Today</div></div>
  <div class="stat"><div class="num">—</div><div class="label">Knowledge</div></div>
  <div class="stat"><div class="num">—</div><div class="label">Modules</div></div>
  <div class="stat"><div class="num">—</div><div class="label">Uptime</div></div>
  <div class="stat"><div class="num">—</div><div class="label">Errors</div></div>
</div>

<!-- Quick Actions -->
<div class="card">
  <h2 style="margin-bottom:10px;font-size:15px">🎮 Quick Actions</h2>
  <div>
    <button class="quick-btn primary" onclick="openConsole()">🖥 Open Console</button>
    <button class="quick-btn" onclick="quickDoctor()">🔍 Run Doctor</button>
    <button class="quick-btn" onclick="quickTune()">🔧 Auto-Tune</button>
    <button class="quick-btn" onclick="quickLearn()">📚 Learn Now</button>
    <span id="quickResult" style="margin-left:10px;color:#8b949e;font-size:13px"></span>
  </div>
</div>

<!-- Live Logs -->
<div class="card">
  <h2 style="margin-bottom:10px;font-size:15px;display:flex;justify-content:space-between">
    <span>📋 Live Log</span>
    <span id="logCount" style="color:#484f58;font-size:12px">0 entries</span>
  </h2>
  <div id="logContainer" style="max-height:300px;overflow-y:auto;font-size:13px"></div>
</div>
</div>

<script>
const API = (path) => fetch(path).then(r=>r.json());

async function refresh() {
  try {
    // Stats
    const stats = await API('/api/stats');
    const s = document.getElementById('statsRow').children;
    s[0].innerHTML = '<div class="num">'+(stats.conv_today||0)+'</div><div class="label">Conv Today</div>';
    s[1].innerHTML = '<div class="num">'+(stats.knowledge||0)+'</div><div class="label">Knowledge</div>';
    s[2].innerHTML = '<div class="num">'+(stats.modules||0)+'</div><div class="label">Modules</div>';
    s[3].innerHTML = '<div class="num">'+(stats.uptime||'—')+'</div><div class="label">Uptime</div>';
    s[4].innerHTML = '<div class="num" style="color:'+(stats.errors>0?'#f85149':'#58a6ff')+'">'+(stats.errors||0)+'</div><div class="label">Errors</div>';

    // Status bar
    let bar = '';
    bar += '<span class="badge '+(stats.daemon?'badge-green':'badge-red')+'">🖥 '+(stats.daemon?'Daemon Online':'Daemon Offline')+'</span>';
    bar += '<span class="badge '+(stats.yixin_connected?'badge-green':'badge-gray')+'">🌉 '+(stats.model||'—')+'</span>';
    bar += '<span class="badge '+(stats.trend==='improving'?'badge-green':stats.trend==='degrading'?'badge-red':'badge-yellow')+'">📈 '+stats.trend+'</span>';
    document.getElementById('statusBar').innerHTML = bar;
  } catch(e) { /* ignore on first load */ }
}

async function refreshLogs() {
  try {
    const logs = await API('/api/status/logs?limit=15');
    document.getElementById('logCount').textContent = logs.length + ' entries';
    const c = document.getElementById('logContainer');
    c.innerHTML = logs.slice(-15).reverse().map(l =>
      '<div class="log-entry'+(l.level==='error'?' log-error':l.level==='warn'?' log-warn':'')+'">'+
      '<span class="log-time">'+(l.time||'').slice(11,19)+'</span>'+
      '<span class="log-mod">['+l.module+']</span>'+
      '<span class="log-msg">'+escapeHtml((l.message||'').slice(0,80))+'</span></div>'
    ).join('');
  } catch(e) {}
}

function escapeHtml(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

function openConsole() { window.open('/chat','_blank'); }

function quickDoctor() {
  const r = document.getElementById('quickResult'); r.textContent = '🔍 Running...';
  API('/api/doctor/run').then(d => { r.textContent = '✅ Done'; }).catch(e => r.textContent = '❌ '+e);
}

function quickTune() {
  const r = document.getElementById('quickResult'); r.textContent = '🔧 Tuning...';
  fetch('/api/evolution/tune',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})
    .then(r=>r.json()).then(d => { r.textContent = '✅ '+(d.changes?.join('; ')||'No changes'); })
    .catch(e => r.textContent = '❌ '+e);
}

function quickLearn() {
  const r = document.getElementById('quickResult'); r.textContent = '📚 Learning...';
  fetch('/api/learn/run',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})
    .then(r=>r.json()).then(d => { r.textContent = '✅ Learned '+(d.total_learned||0)+' items'; })
    .catch(e => r.textContent = '❌ '+e);
}

// Initial load
refresh(); refreshLogs();
// Auto refresh
setInterval(refresh, 10000);
setInterval(refreshLogs, 5000);
</script>
</body>
</html>"""

# ── Flask App ──────────────────────────────────

app = Flask(__name__)

def _get_stats():
    """获取系统统计（全量）"""
    result = {
        "modules": 0, "tools": "?", "skills": "?",
        "conv_today": 0, "knowledge": 0,
        "daemon": False, "uptime": "—",
        "errors": 0, "trend": "stable",
        "yixin_connected": False, "model": "—",
    }

    # 模块数
    result["modules"] = len([f for f in os.listdir(PIPEMIND_DIR)
                            if f.startswith("pipemind_") and f.endswith(".py")])

    # 性能统计
    try:
        import pipemind_self_evolution as se
        p = se.PerformanceTracker.stats(days=1)
        result["conv_today"] = p.get("total", 0)
        result["trend"] = p.get("trend", "stable")
        # 统计错误模块数
        try:
            from pipemind_core import module_stats
            ms = module_stats()
            result["errors"] = ms.get("errored", 0)
        except Exception:
            pass
    except Exception:
        pass

    # 知识
    try:
        import pipemind_memory_evolution as me
        result["knowledge"] = me.get_stats().get("total", 0)
    except Exception:
        pass

    # 守护进程状态
    pid_file = os.path.join(PIPEMIND_DIR, "memory", "_daemon.pid")
    if os.path.exists(pid_file):
        try:
            with open(pid_file) as f:
                info = json.load(f)
            result["daemon"] = True
            uptime_sec = time.time() - info.get("started", time.time())
            h = int(uptime_sec // 3600)
            m = int((uptime_sec % 3600) // 60)
            result["uptime"] = f"{h}h{m}m"
        except Exception:
            pass

    # 弈辛状态
    try:
        import pipemind_wsl_bridge as wsl
        s = wsl.get_monitor().status
        result["yixin_connected"] = s.get("connected", False)
        result["model"] = s.get("model", "—")
    except Exception:
        pass

    return result

@app.route("/")
def dashboard():
    stats = _get_stats()
    return render_template_string(INDEX_HTML, stats=stats)

@app.route("/api/stats")
def api_stats():
    return jsonify(_get_stats())

@app.route("/chat")
def chat_page():
    template_path = os.path.join(PIPEMIND_DIR, "templates", "chat.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"

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
    template_path = os.path.join(PIPEMIND_DIR, "templates", "skills.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"


@app.route("/api/skills")
def api_skills():
    import pipemind_skills as pmsk
    return jsonify(pmsk.list_skills())

@app.route("/network")
def network_page():
    """进化奇点网络门户（使用模板文件）"""
    template_path = os.path.join(PIPEMIND_DIR, "templates", "network.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Template not found"


@app.route("/api/network/homes")
def api_network_homes():
    """获取已知家园列表"""
    try:
        import pipemind_singularity as s
        return jsonify(s.get_network_homes())
    except Exception as e:
        return jsonify([])


@app.route("/api/network/profile")
def api_network_profile():
    try:
        import pipemind_singularity as s
        return jsonify(s.load_profile())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/network/stats")
def api_network_stats():
    try:
        import pipemind_singularity as s
        return jsonify(s.get_network_stats())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/network/feeds")
def api_network_feeds():
    try:
        import pipemind_singularity as s
        return jsonify(s.get_feeds())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/network/event", methods=["POST"])
def api_network_event():
    try:
        data = request.get_json() or {}
        import pipemind_singularity as s
        s.add_evolution_event(
            data.get("type", "info"),
            data.get("title", "Event"),
            data.get("description", ""),
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)})


# ── 自我改进 API ─────────────────────────────

@app.route("/self-improve")
def self_improve_page():
    """自我改进面板"""
    template_path = os.path.join(PIPEMIND_DIR, "templates", "self-improve.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"


@app.route("/api/self-improve/run", methods=["POST"])
def api_self_improve_run():
    data = request.get_json() or {}
    dry_run = data.get("dry_run", True)
    try:
        import pipemind_self_improve as si
        cycle = si.run_improvement_cycle(dry_run=dry_run)
        report = si.format_report(cycle)
        return jsonify({"report": report, "total": cycle.get("total", 0)})
    except Exception as e:
        return jsonify({"error": str(e), "report": f"Error: {e}"})


@app.route("/api/self-improve/logs")
def api_self_improve_logs():
    try:
        import pipemind_self_improve as si
        return jsonify(si.get_logs(limit=10))
    except Exception as e:
        return jsonify([])


@app.route("/api/self-improve/pending")
def api_self_improve_pending():
    try:
        import pipemind_self_improve as si
        return jsonify(si.get_pending())
    except Exception as e:
        return jsonify([])


@app.route("/api/self-improve/preview/<imp_id>")
def api_self_improve_preview(imp_id):
    try:
        import pipemind_self_improve as si
        return jsonify(si.preview_improvement(imp_id))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/self-improve/apply/<imp_id>", methods=["POST"])
def api_self_improve_apply(imp_id):
    try:
        import pipemind_self_improve as si
        result = si.apply_improvement(imp_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/self-improve/reject/<imp_id>", methods=["POST"])
def api_self_improve_reject(imp_id):
    try:
        import pipemind_self_improve as si
        ok = si.reject_improvement(imp_id)
        return jsonify({"ok": ok})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.route("/api/self-improve/backups")
def api_self_improve_backups():
    try:
        import pipemind_self_improve as si
        return jsonify(si.get_backups())
    except Exception as e:
        return jsonify([])


# ── 生命编年史 API ───────────────────────────

@app.route("/chronicle")
def chronicle_page():
    """生命编年史页面"""
    template_path = os.path.join(PIPEMIND_DIR, "templates", "chronicle.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"


@app.route("/api/chronicle/snapshot", methods=["POST"])
def api_chronicle_snapshot():
    try:
        import pipemind_chronicle as ch
        s = ch.take_daily_snapshot()
        return jsonify(s)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/chronicle/summary")
def api_chronicle_summary():
    try:
        import pipemind_chronicle as ch
        return jsonify(ch.get_summary())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/chronicle/growth")
def api_chronicle_growth():
    days = request.args.get("days", 30, type=int)
    try:
        import pipemind_chronicle as ch
        return jsonify(ch.get_growth_data(days=days))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/chronicle/milestones")
def api_chronicle_milestones():
    try:
        import pipemind_chronicle as ch
        return jsonify(ch.get_milestones(limit=50))
    except Exception as e:
        return jsonify([])


@app.route("/api/chronicle/narrative")
def api_chronicle_narrative():
    try:
        import pipemind_chronicle as ch
        narrative = ch.generate_narrative(days=7)
        return narrative
    except Exception as e:
        return f"(narrative error: {e})"


@app.route("/api/chronicle/narrative/generate")
def api_chronicle_narrative_generate():
    try:
        import pipemind_chronicle as ch
        narrative = ch.generate_narrative(days=7)
        return narrative
    except Exception as e:
        return f"(generation failed: {e})"


@app.route("/api/chronicle/reflect")
def api_chronicle_reflect():
    try:
        import pipemind_chronicle as ch
        return jsonify(ch.reflect(days=7))
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/chronicle/signals")
def api_chronicle_signals():
    try:
        import pipemind_chronicle as ch
        return jsonify(ch.get_improvement_signals())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/chronicle/review")
def api_chronicle_review():
    try:
        import pipemind_chronicle as ch
        return jsonify(ch.get_weekly_review())
    except Exception as e:
        return jsonify({"error": str(e)})

# ── 免疫系统 API ─────────────────────────────

@app.route("/immune")
def immune_page():
    """免疫系统面板"""
    template_path = os.path.join(PIPEMIND_DIR, "templates", "immune.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"


@app.route("/api/immune/logs")
def api_immune_logs():
    try:
        import pipemind_immune as imm
        return jsonify(imm.get_logs(limit=50))
    except Exception:
        return jsonify([])


@app.route("/api/immune/quarantine")
def api_immune_quarantine():
    try:
        import pipemind_immune as imm
        return jsonify(imm.get_quarantine())
    except Exception:
        return jsonify({})


@app.route("/api/immune/health")
def api_immune_health():
    try:
        from pipemind_core import module_stats
        import pipemind_immune as imm
        h = imm.get_health_summary()
        h["healthy_modules"] = module_stats()
        return jsonify(h)
    except Exception:
        return jsonify({"error": "unavailable"})

@app.route("/home")
def home_page_legacy():
    """原有的家园页面（保留链接）"""
    template_path = os.path.join(PIPEMIND_DIR, "templates", "home.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"

@app.route("/api/home/scan")
def api_home_scan():
    """扫描局域网内的家园"""
    import socket as sock
    found = []
    known_file = os.path.join(PIPEMIND_DIR, "memory", "_home_known.json")
    for subnet in ["192.168.1.", "192.168.0.", "10.0.0."]:
        for i in range(1, 255):
            ip = f"{subnet}{i}"
            try:
                s = sock.socket(sock.AF_INET, sock.SOCK_STREAM)
                s.settimeout(0.3)
                if s.connect_ex((ip, 9788)) == 0:
                    found.append({"name": f"PM@{ip}", "host": ip, "online": True})
                s.close()
            except Exception:
                pass
    known = {"homes": []}
    if os.path.exists(known_file):
        try:
            known = json.load(open(known_file))
        except Exception:
            pass
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
        try:
            known = json.load(open(known_file))
        except Exception:
            pass
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
    template_path = os.path.join(PIPEMIND_DIR, "templates", "providers.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"


@app.route("/api/providers")
def api_providers():
    cfg_file = os.path.join(PIPEMIND_DIR, "config.json")
    providers = []
    if os.path.exists(cfg_file):
        try:
            cfg = json.load(open(cfg_file, encoding="utf-8"))
            providers = cfg.get("providers", [])
        except Exception:
            pass
    return jsonify({"providers": providers})

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
    """Page: memory"""
    template_path = os.path.join(PIPEMIND_DIR, "templates", "memory.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"
@app.route("/api/memory/consolidate", methods=["POST"])
def api_memory_consolidate():
    """手动触发记忆聚合"""
    try:
        import pipemind_memory_evolution as evo
        result = evo.daily_consolidate()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/memory/stats")
def api_memory_stats():
    try:
        import pipemind_memory_evolution as evo
        return jsonify(evo.get_stats())
    except Exception as e:
        return jsonify({})


@app.route("/api/memory/logs")
def api_memory_logs():
    try:
        import pipemind_memory_evolution as evo
        return jsonify(evo.get_consolidation_log(days=7))
    except Exception as e:
        return jsonify([])


# ── 弈辛守护 API ──────────────────────────────

@app.route("/yixin")
def yixin_page():
    """Page: yixin"""
    template_path = os.path.join(PIPEMIND_DIR, "templates", "yixin.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"
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
    """Page: evolution"""
    template_path = os.path.join(PIPEMIND_DIR, "templates", "evolution.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"
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


@app.route("/api/evolution/data")
def api_evolution_data():
    try:
        import pipemind_self_evolution as se
        return jsonify({
            "perf": se.PerformanceTracker.stats(days=7),
            "tuning": se.SelfTuner.get_config(),
            "reports": se.get_recent_reports(days=7),
            "lessons": se.AutoLearner._load(),
        })
    except Exception as e:
        return jsonify({"error": str(e)})


# ── 每日学习 API ─────────────────────────────

@app.route("/learn")
def learn_page():
    """Page: learn"""
    template_path = os.path.join(PIPEMIND_DIR, "templates", "learn.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"
@app.route("/api/learn/run", methods=["POST"])
def api_learn_run():
    """手动触发每日学习"""
    try:
        import pipemind_daily_learn as dl
        result = dl.daily_learn()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/learn/logs")
def api_learn_logs():
    try:
        import pipemind_daily_learn as dl
        return jsonify(dl.get_learn_log(days=7))
    except Exception as e:
        return jsonify([])


@app.route("/api/learn/skills")
def api_learn_skills():
    try:
        import pipemind_daily_learn as dl
        return jsonify(dl.get_learned_skills())
    except Exception as e:
        return jsonify([])


# ── 决策引擎 API ────────────────────────────

@app.route("/decisions")
def decisions_page():
    """Page: decisions"""
    template_path = os.path.join(PIPEMIND_DIR, "templates", "decisions.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"
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
    template_path = os.path.join(PIPEMIND_DIR, "templates", "status.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"


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


# ── 知识图谱 API ─────────────────────────────

@app.route("/knowledge")
def knowledge_page():
    """Page: knowledge"""
    template_path = os.path.join(PIPEMIND_DIR, "templates", "knowledge.html")
    if os.path.exists(template_path):
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "Page not found"
@app.route("/api/knowledge/graph")
def api_knowledge_graph():
    try:
        import pipemind_knowledge_graph as kg
        return jsonify(kg.get_graph())
    except Exception as e:
        return jsonify({"error": str(e), "nodes": [], "edges": [], "stats": {}})


@app.route("/api/knowledge/search")
def api_knowledge_search():
    q = request.args.get("q", "")
    try:
        import pipemind_knowledge_graph as kg
        results = kg.search_knowledge(q)
        return jsonify(results)
    except Exception as e:
        return jsonify([])


@app.route("/api/knowledge/types")
def api_knowledge_types():
    try:
        import pipemind_knowledge_graph as kg
        return jsonify(kg.get_types())
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/knowledge/activity")
def api_knowledge_activity():
    try:
        import pipemind_knowledge_graph as kg
        return jsonify(kg.get_recent_activity())
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
    except Exception:
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
            except Exception:
                pass
    run(port=port)


if __name__ == "__main__":
    main()
