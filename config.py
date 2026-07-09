"""XYZRender-Viewer 常量、QSS 样式、Multiwfn 配置与输出解析。"""

import os
import sys
import configparser
import re

# ── Qt 样式 ─────────────────────────────────────────────────────────

LIGHT_QSS = """/* ── Global ── */
QMainWindow { background-color: #E4EAF2; }
QWidget { font-family: "Segoe UI", "Microsoft YaHei", sans-serif; font-size: 9pt; color: #2C3E50; }
QGroupBox { border: 1px solid #CBD5E1; border-radius: 8px; margin-top: 16px; padding: 18px 12px 12px 12px; background-color: #FFFFFF; font-weight: bold; font-size: 10pt; }
QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 2px 12px; color: #FFFFFF; background-color: #1565C0; border-radius: 4px; }
QPushButton { background-color: #1565C0; color: #FFFFFF; border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold; }
QPushButton:hover { background-color: #1976D2; }
QPushButton:pressed { background-color: #0D47A1; }
QPushButton:disabled { background-color: #B0BEC5; }
QComboBox { border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 8px; background-color: #FFFFFF; }
QComboBox:focus { border-color: #1565C0; }
QCheckBox { spacing: 6px; }
QSlider::groove:horizontal { height: 6px; background: #CBD5E1; border-radius: 3px; }
QSlider::handle:horizontal { width: 14px; height: 14px; margin: -4px 0; background: #1565C0; border-radius: 7px; }
QLineEdit { border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 8px; background-color: #FFFFFF; }
QTabWidget::pane { border: 1px solid #CBD5E1; border-radius: 4px; background: #FFFFFF; }
QTabBar::tab { padding: 6px 16px; margin-right: 2px; background: #E4EAF2; border: 1px solid #CBD5E1; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px; }
QTabBar::tab:selected { background: #FFFFFF; font-weight: bold; }
QProgressBar { border: 1px solid #CBD5E1; border-radius: 4px; text-align: center; background: #FFFFFF; }
QProgressBar::chunk { background: #1565C0; border-radius: 3px; }
QTableWidget { border: 1px solid #CBD5E1; gridline-color: #E4EAF2; background: #FFFFFF; }
QHeaderView::section { background: #1565C0; color: #FFFFFF; padding: 4px 8px; font-weight: bold; }
QPlainTextEdit { border: 1px solid #CBD5E1; border-radius: 4px; background: #FAFBFC; }"""

# ── xyzrender 预设 ───────────────────────────────────────────────────

XYZR_PRESETS = [
    "default", "flat", "paton", "pmol", "skeletal",
    "bubble", "tube", "mtube", "btube", "wire", "graph",
]

# ── Multiwfn 路径配置 ───────────────────────────────────────────────

DEFAULT_MULTIWFN = r"E:\Multiwfn_2026.4.10_bin_Win64\Multiwfn.exe"
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__)),
    "xyzrender_viewer.ini"
)

def _load_mw_config():
    cfg = configparser.ConfigParser()
    result = {"multiwfn": DEFAULT_MULTIWFN}
    if os.path.exists(CONFIG_FILE):
        cfg.read(CONFIG_FILE, encoding="utf-8")
        if "multiwfn" in cfg:
            result["multiwfn"] = cfg["multiwfn"].get("exe", DEFAULT_MULTIWFN)
    return result

def _save_mw_config(exe_path):
    cfg = configparser.ConfigParser()
    cfg["multiwfn"] = {"exe": exe_path}
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        cfg.write(f)

# ── Multiwfn ESP ISO 命令 ────────────────────────────────────────────

CMD_ESPISO = """
5
1
1
2
0
5
12
1
2
0
q
"""

# ── 电荷类型配置 ─────────────────────────────────────────────────────

CHARGE_TYPES = {
    "ADCH": {
        "desc": "Atomic Dipole Moment Corrected Hirshfeld (推荐)",
        "input_seq": "\n7\n11\n1\ny\n0\nq\n",
        "marker": ["Final atomic charges:"],
    },
    "Hirshfeld": {
        "desc": "Hirshfeld 原子电荷 (Stockholder 分配)",
        "input_seq": "\n7\n1\n1\ny\n0\nq\n",
        "marker": ["Final atomic charges:"],
    },
    "Mulliken": {
        "desc": "Mulliken 布居分析 (经典方法)",
        "input_seq": "\n7\n5\n1\ny\n0\nq\n",
        "marker": ["Net charge:"],
    },
    "CM5": {
        "desc": "CM5 电荷 (映射到 Hirshfeld)",
        "input_seq": "\n7\n16\n1\ny\n0\nq\n",
        "marker": ["CM5 charges:", "Charge Model 5 charges:"],
    },
    "SCPA": {
        "desc": "Modified Mulliken (Ros & Schuit, SCPA)",
        "input_seq": "\n7\n7\ny\n0\nq\n",
        "marker": ["Atomic charge:"],
    },
    "VDD": {
        "desc": "Voronoi 形变密度电荷",
        "input_seq": "\n7\n2\n1\ny\n0\nq\n",
        "marker": ["Final atomic charges:"],
    },
}

CMAP_PALETTES = ["viridis", "plasma", "coolwarm", "rainbow", "RdBu", "magma", "inferno", "cividis"]

# ── Multiwfn 输出进度解析 ────────────────────────────────────────────

_SKIP_PATTERNS = [
    "======", "------", "Multiwfn", "http://", "Version", "Cite as",
    "Multiwfn: A Multifunctional Wavefunction Analyzer",
    "Release date", "Parallel", "Project supported",
    "Tian Lu", "Beijing Kein", "sobereva",
    "Please wait", "Loading", "Note:", "Warning:",
]

_GRID_PROGRESS_RE = re.compile(r'Progress\s*:\s*(\d+)\s*/\s*(\d+)')
_PCT_RE = re.compile(r'(\d+(?:\.\d+)?)\s*%')

def _filter_mw_line(line: str) -> str | None:
    """过滤 Multiwfn 输出行，返回感兴趣的内容或 None。"""
    stripped = line.strip()
    if len(stripped) < 3:
        return None
    for sp in _SKIP_PATTERNS:
        if sp.lower() in stripped.lower():
            return None
    if len(stripped) > 80:
        stripped = stripped[:77] + "..."
    return stripped

def _parse_mw_progress(line: str) -> float | None:
    """从 Multiwfn 输出行解析进度 (0.0~1.0)，解析不到返回 None。"""
    m = _GRID_PROGRESS_RE.search(line)
    if m:
        return int(m.group(1)) / int(m.group(2))
    m = _PCT_RE.search(line)
    if m:
        return float(m.group(1)) / 100.0
    return None
