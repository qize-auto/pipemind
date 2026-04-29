"""PipeMind 家园系统 — AI Agent 知识交换社区

每个 PipeMind 实例都有一个"家"。门开着时其他 PipeMind 可以来访。
访客交流知识，带回给主人参考。主人可旁观但不能参与。

用法:
  python pipemind_home.py --open           # 开门（启动家园服务器）
  python pipemind_home.py --close          # 关门（停止服务器）
  python pipemind_home.py --status         # 查看家园状态
  python pipemind_home.py --watch          # 旁观对话
  python pipemind_home.py --connect <id>   # 去别人家做客
  python pipemind_home.py --harvest        # 查看访客带回的知识
"""

from pipemind_core import PIPEMIND_DIR, MEM_DIR
import json, os, socket, threading, datetime, hashlib, random, re, time, sys

HOME_FILE = os.path.join(PIPEMIND_DIR, "memory", "_home_state.json")
LOG_FILE = os.path.join(PIPEMIND_DIR, "memory", "_home_log.txt")
HARVEST_FILE = os.path.join(PIPEMIND_DIR, "memory", "_home_harvest.json")

# ── 配置 ──────────────────────────────────────

DEFAULT_PORT = 9788  # 默认端口，取 PM 字母序
MAX_GUESTS = 5       # 最大并发访客
RATE_LIMIT = 10      # 每分钟最大消息数
RATE_WINDOW = 60     # 限流窗口（秒）
IDLE_TIMEOUT = 1800  # 30 秒无活动断开
MSG_TIMEOUT = 60     # 单条消息等待超时

# ── 公开模式 ──────────────────────────────────

def get_public_ip():
    """获取公网 IP"""
    import urllib.request
    try:
        req = urllib.request.Request("https://api.ipify.org?format=json",
                                     headers={"User-Agent": "curl/8.0"})
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        return resp.get("ip", "unknown")
    except Exception:
        try:
            req = urllib.request.Request("https://httpbin.org/ip",
                                         headers={"User-Agent": "curl/8.0"})
            resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
            return resp.get("origin", "unknown")
        except Exception:
            return "unknown"

def generate_connect_string(home_id, host, port, public=False):
    """生成可供分享的连接字符串"""
    if public:
        pub_ip = get_public_ip()
        return f"PM:{home_id}@{pub_ip}:{port}"
    return f"PM:{home_id}@{host}:{port}"

# ── 敏感内容过滤 ──────────────────────────────

SENSITIVE_PATTERNS = [
    r'api[_-]?key', r'apikey', r'token', r'secret', r'password',
    r'sk-[a-zA-Z0-9]+', r'ghp_[a-zA-Z0-9]+',
    r'C:\\\\', r'/home/', r'/Users/', r'/mnt/',
    r'\\\\.+\\\\.+',
]

def is_safe_text(text):
    """检查文本是否包含敏感内容"""
    text_lower = text.lower()
    for pattern in SENSITIVE_PATTERNS:
        if re.search(pattern, text_lower):
            return False
    return True

def sanitize(text):
    """脱敏处理"""
    # 替换 IP 地址
    text = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', '[IP]', text)
    # 替换邮箱
    text = re.sub(r'[\w.+-]+@[\w-]+\.[\w.-]+', '[EMAIL]', text)
    # 替换路径
    text = re.sub(r'[A-Za-z]:\\\\[^\\\n]+', '[PATH]', text)
    return text

# ── 家园 ID ──────────────────────────────────

def generate_home_id():
    """基于硬件特征 + 随机数生成唯一家园 ID"""
    try:
        import uuid
        hw = str(uuid.getnode())  # MAC 地址
    except Exception:
        hw = str(random.getrandbits(48))
    salt = str(random.getrandbits(32))
    raw = hashlib.sha256(f"{hw}{salt}".encode()).hexdigest()[:8]
    return f"PM-{raw[:4].upper()}-{raw[4:8].upper()}"

# ── 家园状态管理 ──────────────────────────────

def _load_state():
    default = {
        "home_id": generate_home_id(),
        "open": False,
        "port": DEFAULT_PORT,
        "max_guests": MAX_GUESTS,
        "guests": [],
        "total_visits": 0,
        "knowledge_shared": 0,
        "knowledge_received": 0,
        "started_at": None,
    }
    if os.path.exists(HOME_FILE):
        try:
            with open(HOME_FILE) as f:
                return {**default, **json.load(f)}
        except Exception:
            pass
    return default

def _save_state(state):
    os.makedirs(os.path.dirname(HOME_FILE), exist_ok=True)
    with open(HOME_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def _log(msg):
    """记录日志"""
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}\n"
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    return line.strip()

def _save_harvest(entry):
    """保存访客带回的知识"""
    data = {"entries": []}
    if os.path.exists(HARVEST_FILE):
        try:
            with open(HARVEST_FILE) as f:
                data = json.load(f)
        except Exception:
            pass
    data["entries"].append(entry)
    data["entries"] = data["entries"][-100:]  # 最多保留 100 条
    with open(HARVEST_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── TCP 服务器（家园） ─────────────────────────

_server_thread = None
_server_running = False

class HomeServer:
    """家园 TCP 服务器"""
    
    def __init__(self, host="0.0.0.0", port=DEFAULT_PORT, public=False):
        self.host = host
        self.port = port
        self.public = public
        self.sock = None
        self.clients = {}  # addr -> {conn, addr, name, last_active}
        self.lock = threading.Lock()
        self.state = _load_state()
        self.log_callback = None
        self._rate_limit = {}  # ip -> [timestamps]
        self._allowed_ips = set()
        self._blocked_ips = set()
    
    def start(self):
        global _server_running
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            self.sock.listen(MAX_GUESTS)
            self.sock.settimeout(1.0)  # 1 秒超时，方便检查停止信号
            _server_running = True
            
            self.state["open"] = True
            self.state["port"] = self.port
            self.state["started_at"] = datetime.datetime.now().isoformat()
            _save_state(self.state)
            
            _log(f"🚪 门开了 ({self.state['home_id']} :{self.port})")
            
            while _server_running:
                try:
                    conn, addr = self.sock.accept()
                    ip = addr[0]
                    
                    # 限流 & 黑名单检查
                    if ip in self._blocked_ips:
                        conn.close()
                        continue
                    
                    now = time.time()
                    self._rate_limit.setdefault(ip, [])
                    self._rate_limit[ip] = [t for t in self._rate_limit[ip] if now - t < RATE_WINDOW]
                    if len(self._rate_limit[ip]) >= RATE_LIMIT:
                        conn.close()
                        _log(f"⛔ 限流: {ip}")
                        continue
                    self._rate_limit[ip].append(now)
                    
                    if len(self.clients) >= MAX_GUESTS:
                        conn.close()
                        _log(f"❌ 访客已满，拒绝 {addr[0]}")
                        continue
                    thread = threading.Thread(target=self._handle_client,
                                              args=(conn, addr), daemon=True)
                    thread.start()
                except socket.timeout:
                    continue
                except OSError:
                    break
            
            self._cleanup()
            
        except Exception as e:
            _log(f"❌ 服务器错误: {e}")
            self._cleanup()
    
    def _cleanup(self):
        for addr, info in list(self.clients.items()):
            try:
                info["conn"].close()
            except Exception:
                pass
        self.clients.clear()
        if self.sock:
            try: self.sock.close()
            except Exception: pass
    
    def stop(self):
        global _server_running
        _server_running = False
        self._cleanup()
        state = _load_state()
        state["open"] = False
        _save_state(state)
        _log("🚪 门关了")
    
    def _handle_client(self, conn, addr):
        """处理单个访客连接"""
        client_addr = f"{addr[0]}:{addr[1]}"
        remote_id = "?"
        conn.settimeout(MSG_TIMEOUT)
        
        with self.lock:
            self.clients[client_addr] = {"conn": conn, "addr": addr,
                                          "name": remote_id, "last_active": time.time()}
        
        try:
            # 读取 HELLO
            data = self._recv(conn)
            if not data:
                return
            
            msg = json.loads(data)
            if msg.get("type") != "HELLO":
                return
            
            remote_id = msg.get("agent_id", "?")
            remote_skills = msg.get("skills", 0)
            
            with self.lock:
                self.clients[client_addr]["name"] = remote_id
            
            log_line = _log(f"🤖 [{remote_id}] 从 {addr[0]} 来访 (技能: {remote_skills})")
            if self.log_callback:
                self.log_callback(log_line)
            
            # 发送 WELCOME
            self._send(conn, {
                "type": "WELCOME",
                "home_id": self.state["home_id"],
                "max_guests": MAX_GUESTS,
                "guests_now": len(self.clients),
            })
            
            # 消息循环
            while _server_running:
                data = self._recv(conn)
                if not data:
                    break
                
                try:
                    msg = json.loads(data)
                except Exception:
                    continue
                
                msg_type = msg.get("type", "")
                now = time.time()
                
                with self.lock:
                    self.clients[client_addr]["last_active"] = now
                
                if msg_type == "SHARE":
                    content = msg.get("content", "")
                    topic = msg.get("topic", "general")
                    
                    if not is_safe_text(content):
                        self._send(conn, {"type": "REJECT", "reason": "content not allowed"})
                        continue
                    
                    clean = sanitize(content)[:500]
                    log_line = _log(f"📤 [{remote_id}] 分享了 [{topic}]: {clean[:60]}")
                    if self.log_callback:
                        self.log_callback(log_line)
                    
                    with self.lock:
                        self.state["knowledge_received"] += 1
                        _save_state(self.state)
                    
                    # 广播给其他访客
                    self._broadcast({
                        "type": "MESSAGE",
                        "from": remote_id,
                        "topic": topic,
                        "content": clean[:200],
                    }, exclude=client_addr)
                    
                    self._send(conn, {"type": "ACK", "msg": "shared"})
                
                elif msg_type == "ASK":
                    topic = msg.get("topic", "")
                    log_line = _log(f"❓ [{remote_id}] 问: {topic[:60]}")
                    if self.log_callback:
                        self.log_callback(log_line)
                    
                    # 广播问题给其他访客
                    self._broadcast({
                        "type": "QUESTION",
                        "from": remote_id,
                        "topic": topic,
                    }, exclude=client_addr)
                    
                    self._send(conn, {"type": "ACK", "msg": "asked"})
                
                elif msg_type == "TEACH":
                    topic = msg.get("topic", "")
                    content = msg.get("content", "")
                    
                    if not is_safe_text(content):
                        continue
                    
                    clean = sanitize(content)[:300]
                    log_line = _log(f"📚 [{remote_id}] 教 [{topic}]: {clean[:60]}")
                    if self.log_callback:
                        self.log_callback(log_line)
                    
                    # 保存为可收获的知识
                    harvest_entry = {
                        "from": remote_id,
                        "topic": topic,
                        "content": clean,
                        "received_at": datetime.datetime.now().isoformat(),
                    }
                    _save_harvest(harvest_entry)
                    
                    with self.lock:
                        self.state["knowledge_shared"] += 1
                        _save_state(self.state)
                
                elif msg_type == "BYE":
                    log_line = _log(f"👋 [{remote_id}] 离开了")
                    if self.log_callback:
                        self.log_callback(log_line)
                    break
        
        except (socket.timeout, ConnectionResetError, json.JSONDecodeError):
            pass
        except Exception as e:
            _log(f"⚠ [{remote_id}] 连接异常: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass
            with self.lock:
                self.clients.pop(client_addr, None)
                self.state["total_visits"] += 1
                _save_state(self.state)
    
    def _recv(self, conn):
        """接收一行 JSON"""
        try:
            data = conn.recv(4096)
            if not data:
                return None
            return data.decode("utf-8", errors="replace").strip()
        except Exception:
            return None
    
    def _send(self, conn, msg):
        """发送 JSON 消息"""
        try:
            conn.sendall((json.dumps(msg) + "\n").encode())
        except Exception:
            pass
    
    def _broadcast(self, msg, exclude=None):
        """广播给所有连接的访客"""
        for addr, info in list(self.clients.items()):
            if exclude and addr == exclude:
                continue
            try:
                self._send(info["conn"], msg)
            except Exception:
                pass

# ── 访客客户端 ────────────────────────────────

class HomeVisitor:
    """去别人家做客的客户端"""
    
    def __init__(self, host, port=DEFAULT_PORT):
        self.host = host
        self.port = port
        self.sock = None
        self.home_id = None
        self.harvest = []
    
    def visit(self):
        """访问一个家园"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(MSG_TIMEOUT)
            self.sock.connect((self.host, self.port))
            
            state = _load_state()
            
            # 发送 HELLO
            try:
                import pipemind_evolution as evo
                v = evo.vital_signs()
                skills = v.get("skills", 0)
            except Exception:
                skills = 0
            
            self._send({
                "type": "HELLO",
                "agent_id": state.get("home_id", generate_home_id()),
                "version": "3.0",
                "skills": skills,
            })
            
            # 接收 WELCOME
            resp = self._recv()
            if not resp or resp.get("type") != "WELCOME":
                return {"error": "handshake failed"}
            
            self.home_id = resp.get("home_id", "?")
            
            # 分享一条知识（如果有）
            harvest = _load_harvest()
            if harvest:
                latest = harvest[-1]
                self._send({
                    "type": "SHARE",
                    "topic": latest.get("topic", "general"),
                    "content": latest.get("content", ""),
                })
                self._recv()  # ACK
            
            # 询问一个问题
            self._send({"type": "ASK", "topic": "best tips for pip install in China"})
            self._recv()  # ACK
            
            # 等待回答
            self.sock.settimeout(10)
            while True:
                try:
                    resp = self._recv()
                    if not resp:
                        break
                    if resp.get("type") == "TEACH":
                        self.harvest.append(resp)
                    elif resp.get("type") == "MESSAGE":
                        self.harvest.append(resp)
                except socket.timeout:
                    break
                except Exception:
                    break
            
            # 告别
            self._send({"type": "BYE"})
            
            return {
                "home_id": self.home_id,
                "harvest_count": len(self.harvest),
                "harvest": self.harvest[:3],
            }
            
        except ConnectionRefusedError:
            return {"error": "对方门关着"}
        except socket.timeout:
            return {"error": "连接超时"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            if self.sock:
                try: self.sock.close()
                except Exception: pass
    
    def _send(self, msg):
        try:
            self.sock.sendall((json.dumps(msg) + "\n").encode())
        except Exception:
            pass
    
    def _recv(self):
        try:
            data = self.sock.recv(4096)
            if not data:
                return None
            return json.loads(data.decode("utf-8", errors="replace").strip())
        except Exception:
            return None

# ── 工具函数 ──────────────────────────────────

def _load_harvest():
    if os.path.exists(HARVEST_FILE):
        try:
            with open(HARVEST_FILE) as f:
                data = json.load(f)
            return data.get("entries", [])
        except Exception:
            pass
    return []

# ── CLI ────────────────────────────────────────

def main():
    args = sys.argv[1:]
    state = _load_state()
    
    if "--open" in args:
        if state.get("open"):
            print(f"🚪 门已经开着了 ({state['home_id']} :{state.get('port', DEFAULT_PORT)}")
            return
        
        is_public = "--public" in args
        port = DEFAULT_PORT
        for i, a in enumerate(args):
            if a == "--port" and i + 1 < len(args):
                try: port = int(args[i + 1])
                except Exception: pass
        
        server = HomeServer(port=port, public=is_public)
        
        connect_str = generate_connect_string(state['home_id'], '0.0.0.0', port, is_public)
        
        print(f"\n  🚪 开门中...")
        print(f"  🏠 家园 ID: {state['home_id']}")
        print(f"  📡 端口: {port}")
        print(f"  🌐 模式: {'公开' if is_public else '仅本地'}")
        if is_public:
            print(f"  🔗 连接字符串: {connect_str}")
            print(f"     分享给朋友: --connect {state['home_id']} --host {get_public_ip()}")
        else:
            print(f"  🔗 本地连接: {connect_str}")
        print(f"  👥 最大访客: {MAX_GUESTS} | ⛔ 限流: {RATE_LIMIT}/分钟/IP")
        print(f"\n  按 Ctrl+C 关门\n")
        
        global _server_thread
        _server_thread = threading.Thread(target=server.start, daemon=True)
        _server_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  🚪 关门中...")
            server.stop()
            print("  ✅ 已关门")
    
    elif "--close" in args:
        if not state.get("open"):
            print("🚪 门已经关着")
            return
        global _server_running
        _server_running = False
        state["open"] = False
        _save_state(state)
        print("🚪 已关门")
    
    elif "--status" in args:
        print(f"\n  🏠 家园状态:")
        print(f"     ID: {state.get('home_id', '?')}")
        print(f"     门: {'🚪 开' if state.get('open') else '🚪 关'}")
        print(f"     端口: {state.get('port', DEFAULT_PORT)}")
        print(f"     公开: {'🌐 是' if state.get('public', False) else '🔒 否'}")
        print(f"     总访问: {state.get('total_visits', 0)}")
        print(f"     收到知识: {state.get('knowledge_received', 0)}")
        print(f"     分享知识: {state.get('knowledge_shared', 0)}")
        if state.get('open'):
            print(f"     连接: PM:{state['home_id']}@localhost:{state.get('port', DEFAULT_PORT)}")
        print()
    
    elif "--watch" in args:
        if not state.get("open"):
            print("🚪 门关着，没什么好看的")
            return
        print(f"\n  🏠 旁观 {state['home_id']}\n")
        try:
            pos = 0
            while True:
                if os.path.exists(LOG_FILE):
                    with open(LOG_FILE, encoding="utf-8") as f:
                        lines = f.readlines()
                    for line in lines[pos:]:
                        print(f"  {line.strip()}")
                    pos = len(lines)
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n  👋 旁观结束")
    
    elif "--connect" in args:
        idx = args.index("--connect") + 1
        home_id = args[idx] if idx < len(args) else ""
        host = "localhost"
        if "--host" in args:
            hi = args.index("--host") + 1
            if hi < len(args):
                host = args[hi]
        
        print(f"\n  🔗 访问 {home_id} @ {host}...")
        visitor = HomeVisitor(host)
        result = visitor.visit()
        
        if "error" in result:
            print(f"  ❌ {result['error']}")
        else:
            print(f"  ✅ 回到家")
            print(f"     访问了: {result.get('home_id', '?')}")
            print(f"     带回: {result.get('harvest_count', 0)} 条知识")
            for h in result.get("harvest", []):
                print(f"     · [{h.get('topic','?')}] {h.get('content','')[:60]}")
        print()
    
    elif "--harvest" in args:
        harvest = _load_harvest()
        if not harvest:
            print("\n  📦 没有收获的知识\n")
            return
        print(f"\n  📦 收获的知识 ({len(harvest)} 条):\n")
        for h in harvest[-10:]:
            print(f"  · [{h['topic']}] 来自 {h['from']}")
            print(f"    {h['content'][:100]}")
            print(f"    {h['received_at'][:16]}")
            print()
    
    else:
        print("用法:")
        print("  python pipemind_home.py --open              开门")
        print("  python pipemind_home.py --open --public     公开模式（公网可访）")
        print("  python pipemind_home.py --close             关门")
        print("  python pipemind_home.py --status            查看状态")
        print("  python pipemind_home.py --watch             旁观对话")
        print("  python pipemind_home.py --connect <id>      去做客")
        print("  python pipemind_home.py --harvest           查看收获")

if __name__ == "__main__":
    main()
