"""PipeMind TUI 增强 — 富文本终端输出

如果安装了 rich 库，使用语法高亮和格式化输出。
否则回退到纯 ANSI。

用法:
  from pipemind_tui import print_code, print_table, print_status
"""

import sys, shutil

# ── 检测 rich ──────────────────────────────────

try:
    from rich.console import Console as _RichConsole
    from rich.syntax import Syntax as _RichSyntax
    from rich.table import Table as _RichTable
    from rich.panel import Panel as _RichPanel
    from rich.progress import Progress as _RichProgress
    from rich import box as _RichBox
    HAS_RICH = True
    _console = _RichConsole()
except Exception:
    HAS_RICH = False

# ── 终端宽度 ──────────────────────────────────

def term_width():
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80

# ── 代码块 ────────────────────────────────────

def print_code(code, language="python", title=None):
    """打印语法高亮的代码块"""
    if HAS_RICH and len(code) < 2000:
        try:
            syntax = _RichSyntax(code, language, theme="monokai", line_numbers=True)
            if title:
                _console.print(_RichPanel(syntax, title=title, border_style="dim"))
            else:
                _console.print(syntax)
            return
        except Exception:
            pass
    
    # 回退：纯文本
    width = min(term_width() - 4, 70)
    print(f"  {'─' * width}")
    if title:
        print(f"  {title}")
    for line in code.split("\n"):
        print(f"  │ {line}")
    print(f"  {'─' * width}")

# ── 表格 ──────────────────────────────────────

def print_table(columns, rows, title=None):
    """打印格式化表格"""
    if HAS_RICH:
        try:
            table = _RichTable(title=title, box=_RichBox.ROUNDED,
                                header_style="bold cyan", border_style="dim")
            for col in columns:
                table.add_column(col)
            for row in rows:
                table.add_row(*[str(c) for c in row])
            _console.print(table)
            return
        except Exception:
            pass
    
    # 回退：简单文本表格
    if title:
        print(f"\n  {title}")
    
    # 计算列宽
    widths = [len(c) for c in columns]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))
    
    # 限制总宽度
    max_w = term_width() - 4
    while sum(widths) + len(widths) * 3 > max_w and max_w > 20:
        max_idx = widths.index(max(widths))
        widths[max_idx] -= 1
    
    sep = "─" * (sum(widths) + len(widths) * 3 - 1)
    print(f"  ┌{sep}┐")
    
    # 表头
    header = " │ ".join(c.ljust(widths[i]) for i, c in enumerate(columns))
    print(f"  │ {header} │")
    print(f"  ├{'─' * (sum(widths) + len(widths) * 3 - 3)}┤")
    
    # 数据行
    for row in rows:
        cells = " │ ".join(str(c).ljust(widths[i]) if i < len(widths) else str(c)
                          for i, c in enumerate(row))
        print(f"  │ {cells} │")
    
    print(f"  └{sep}┘")

# ── 状态面板 ──────────────────────────────────

def print_panel(title, content, style="info"):
    """打印信息面板"""
    colors = {"info": "36", "ok": "32", "warn": "33", "error": "31", "dim": "90"}
    c = colors.get(style, "36")
    
    if HAS_RICH:
        try:
            s = {"info": "bold cyan", "ok": "bold green", "warn": "bold yellow",
                 "error": "bold red", "dim": "dim"}
            panel = _RichPanel(content, title=title, border_style=s.get(style, "cyan"))
            _console.print(panel)
            return
        except Exception:
            pass
    
    # 回退
    width = min(term_width() - 4, 60)
    print(f"  \033[{c}m┌{'─' * width}┐\033[0m")
    for line in f"  {title}\n{content}".split("\n"):
        print(f"  \033[{c}m│\033[0m {line:<{width}} \033[{c}m│\033[0m")
    print(f"  \033[{c}m└{'─' * width}┘\033[0m")

# ── 进度条 ────────────────────────────────────

class Progress:
    """简单的进度条"""
    def __init__(self, total, desc="Progress"):
        self.total = total
        self.desc = desc
        self.current = 0
        self.width = min(term_width() - len(desc) - 10, 30)
    
    def update(self, n=1):
        self.current += n
        pct = self.current / self.total
        filled = int(self.width * pct)
        bar = "█" * filled + "░" * (self.width - filled)
        sys.stdout.write(f"\r  {self.desc} [{bar}] {int(pct * 100)}%")
        sys.stdout.flush()
        if self.current >= self.total:
            sys.stdout.write("\n")

# ── 分隔线 ────────────────────────────────────

def print_separator(char="─"):
    width = term_width() - 4
    print(f"  {char * width}")
