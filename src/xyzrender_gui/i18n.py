"""i18n — 中/英 切换支持"""
from PyQt5.QtCore import QObject, pyqtSignal

_tr_dict: dict[str, str] = {}  # Chinese → English

def _build_dict():
    d = {}
    # ── 通用 ──
    d["xyzrender GUI v1.1.0 — 分子结构 + 等值面可视化"] = "xyzrender GUI v1.1.0 — Molecular Structure & Isosurface"
    d["3D 画布"] = "3D Canvas"
    d["渲染预览"] = "Preview"
    d["文件"] = "File"
    d["浏览"] = "Browse"
    d["设置路径"] = "Set Path"
    d["(未加载)"] = "(not loaded)"
    d["(等待渲染...)"] = "(waiting for render...)"
    d["样式:"] = "Style:"
    d["标签:"] = "Label:"
    d["隐藏"] = "Hide"
    d["编号"] = "Number"
    d["元素"] = "Element"
    d["左键旋转 | 右键平移 | 滚轮缩放"] = "Left-drag: Rotate | Right-drag: Pan | Scroll: Zoom"
    d["结构"] = "Structure"
    d["ESP"] = "ESP"
    d["MO"] = "MO"
    d["IGMH"] = "IGMH"
    d["电荷"] = "Charge"
    d["Cub 文件"] = "Cube File"
    d["运行日志"] = "Log"
    d["Multiwfn:"] = "Multiwfn:"
    d["就绪 — 打开 XYZ / cube / log / fchk 文件 | Tab 1: 结构 | Tab 2: 等值面"] = "Ready — Open XYZ / cube / log / fchk | Tab 1: Structure | Tab 2: Isosurface"
    d["已加载 {} — 左键旋转视角, 调好后点「出图」"] = "Loaded {} — Drag to rotate, click Export when ready"
    d["快速预览渲染中..."] = "Rendering preview..."
    d["预览完成"] = "Preview done"
    d["请先打开文件"] = "Please open a file first"
    d["提示"] = "Info"
    d["渲染失败"] = "Render failed"
    d["错误"] = "Error"
    d["保存 PNG"] = "Save PNG"
    d["保存 SVG"] = "Save SVG"
    d["保存等值面 PNG"] = "Save Isosurface PNG"
    d["保存等值面 SVG"] = "Save Isosurface SVG"
    d["保存等值面 GIF"] = "Save Isosurface GIF"
    d["保存 NCI 表面 PNG"] = "Save NCI Surface PNG"
    d["保存 NCI 表面 GIF"] = "Save NCI Surface GIF"
    d["保存 GIF"] = "Save GIF"
    d["旋转GIF:"] = "Rot. GIF:"
    d["FPS:"] = "FPS:"
    d["帧:"] = "Frames:"
    d["预览 GIF"] = "Preview GIF"
    d["旋转 GIF"] = "Rotate GIF"
    d["打开分子结构文件"] = "Open Molecular Structure File"
    d["选择 Multiwfn.exe"] = "Select Multiwfn.exe"
    d["加载失败"] = "Load failed"
    d["所有支持格式 (*.xyz *.cube *.cub *.fchk *.fch *.mol *.sdf *.mol2 *.pdb *.log *.out);;XYZ (*.xyz);;Cube (*.cube *.cub);;fchk (*.fchk *.fch);;Gaussian Log (*.log *.out);;所有文件 (*.*)"] = "All Supported (*.xyz *.cube *.cub *.fchk *.fch *.mol *.sdf *.mol2 *.pdb *.log *.out);;XYZ (*.xyz);;Cube (*.cube *.cub);;fchk (*.fchk *.fch);;Gaussian Log (*.log *.out);;All Files (*.*)"
    d["PNG (*.png)"] = "PNG (*.png)"
    d["SVG (*.svg)"] = "SVG (*.svg)"
    d["PNG (*.png);;SVG (*.svg)"] = "PNG (*.png);;SVG (*.svg)"
    d["加载中: {}"] = "Loading: {}"
    d["渲染中..."] = "Rendering..."
    d["已保存: {}"] = "Saved: {}"

    # ── 结构 tab ──
    d["键编辑（点击画布两个原子画虚线或断键，xyzrender 出图同步）"] = "Bond Editor (click two atoms to draw dashed bond or break bond)"
    d["虚线模式"] = "Dashed"
    d["虚线"] = "Dash"
    d["断键模式"] = "Break Bond"
    d["断键"] = "Break"
    d["撤销断键"] = "Undo Break"
    d["清除断键"] = "Clear Breaks"
    d["Dash Len%:"] = "Dash Len%:"
    d["Gap%:"] = "Gap%:"
    d["W%:"] = "W%:"
    d["撤销"] = "Undo"
    d["撤销虚线"] = "Undo Dash"
    d["清除全部"] = "Clear All"
    d["清除"] = "Clear"
    d["清除虚线"] = "Clear Dashes"
    d["xyzrender 预设"] = "xyzrender Preset"
    d["画布:"] = "Canvas:"
    d["隐藏氢原子"] = "Hide H"
    d["显示氢原子"] = "Show H"
    d["指定编号:"] = "Atoms:"
    d["如 7 8 9"] = "e.g. 7 8 9"
    d["片段1:"] = "Fragment 1:"
    d["片段2:"] = "Fragment 2:"
    d["如 1-5,10-12 或画布 Shift+左键"] = "e.g. 1-5,10-12 or Shift+Click"
    d["如 6-9 或 c (补集) 或画布 Alt+左键"] = "e.g. 6-9 or c (complement) or Alt+Click"
    d["选片段1 (蓝)"] = "Sel. Frag1 (Blue)"
    d["选片段2 (红)"] = "Sel. Frag2 (Red)"
    d["清除片段"] = "Clear Fragments"
    d["vdW 片段1"] = "vdW Frag1"
    d["vdW 片段2"] = "vdW Frag2"
    d["vdW 全部"] = "vdW All"
    d["画布: Shift+左键选片段1, Alt+左键选片段2"] = "Canvas: Shift+Click = Frag1, Alt+Click = Frag2"
    d["原子:"] = "Atom:"
    d["键宽:"] = "Bond W:"
    d["vdW透明:"] = "vdW Alpha:"
    d["导出"] = "Export"
    d["快速预览 400px"] = "Quick Peek 400px"
    d["出图 (PNG)"] = "Render (PNG)"
    d["出图 (SVG)"] = "Render (SVG)"
    d["透明背景"] = "Transparent BG"
    d["模式: 选择片段1"] = "Mode: Select Fragment 1"
    d["模式: 选择片段2"] = "Mode: Select Fragment 2"
    d["已清除"] = "Cleared"
    d["片段1: {}个  片段2: {}个"] = "Frag1: {}  Frag2: {}"
    d["模式:"] = "Mode:"
    d["片段 & vdW"] = "Fragments & vdW"
    d["高亮 & 凸包"] = "Highlight & Hull"
    d["样式微调"] = "Style Tuning"
    d["景深模糊"] = "Depth of Field"
    d["深度雾"] = "Depth Fog"
    d["强度:"] = "Strength:"
    d["元素颜色"] = "Element Colors"
    d["双击行修改颜色"] = "Double-click row to change color"
    d["虚线参数"] = "Dash Parameters"
    d["Len%:"] = "Len%:"

    # ── ESP tab ──
    d["Multiwfn 生成 ESP"] = "Multiwfn Generate ESP"
    d["渲染"] = "Render"
    d["生成 ESP Cube"] = "Generate ESP Cube"
    d["检测"] = "Detect"
    d["等值:"] = "Isovalue:"
    d["调色板:"] = "Palette:"
    d["范围:"] = "Range:"
    d["色彩刻度轴"] = "Color Bar"
    d["对称"] = "Symmetrize"
    d["ESP 着色"] = "ESP Coloring"
    d["如 -0.03,0.03"] = "e.g. -0.03,0.03"
    d["ESP cube 生成完毕 — 点「快速预览」查看"] = "ESP cube ready — click Quick Peek to view"
    d["Multiwfn 完成但缺少输出文件"] = "Multiwfn finished but output file missing"
    d["Multiwfn 执行失败"] = "Multiwfn execution failed"
    d["ESP 范围检测失败"] = "ESP range detection failed"
    d["ESP 范围检测: 未识别到范围数据"] = "ESP range detect: no range data found"
    d["请先设置 Multiwfn 路径"] = "Please set Multiwfn path first"
    d["请先选择 fchk 文件"] = "Please select fchk file first"
    d["ESP 生成需要 fchk 文件"] = "ESP generation requires fchk file"
    d["请先设置 Multiwfn 路径并选择 fchk 文件"] = "Please set Multiwfn path and select fchk file first"
    d["ESP 范围: {}"] = "ESP Range: {}"

    # ── MO tab ──
    d["轨道浏览器"] = "Orbital Browser"
    d["双击行预览轨道"] = "Double-click a row to preview orbital"
    d["轨道"] = "Orbital"
    d["能量 (a.u.)"] = "Energy (a.u.)"
    d["能量 (eV)"] = "Energy (eV)"
    d["占据"] = "Occupancy"
    d["标记"] = "Mark"
    d["网格:"] = "Mesh:"
    d["正瓣:"] = "Pos:"
    d["负瓣:"] = "Neg:"
    d["平面"] = "Flat"
    d["描边"] = "Outlined"
    d["描边宽度:"] = "Outline W:"
    d["平滑:"] = "Blur:"
    d["透明:"] = "Opacity:"
    d["精度x"] = "Upsample"
    d["α 轨道"] = "α Orbitals"
    d["β 轨道"] = "β Orbitals"
    d["HOMO"] = "HOMO"
    d["LUMO"] = "LUMO"
    d["β-HOMO"] = "β-HOMO"
    d["β-LUMO"] = "β-LUMO"
    d["正瓣颜色"] = "Positive Lobe Color"
    d["负瓣颜色"] = "Negative Lobe Color"
    d["请先在轨道表格中双击选择轨道"] = "Please double-click an orbital in the table first"
    d["请先打开 fchk 文件"] = "Please open fchk file first"
    d["等值面预览渲染中..."] = "Rendering isosurface preview..."
    d["等值面预览完成"] = "Isosurface preview done"
    d["等值面渲染中..."] = "Rendering isosurface..."
    d["请先加载或生成 cube 文件"] = "Please load or generate a cube file first"

    # ── IGMH tab ──
    d["片段定义 (用于 IGMH 分析)"] = "Fragment Definition (for IGMH)"
    d["NCI 表面渲染"] = "NCI Surface Render"
    d["运行 IGMH 分析"] = "Run IGMH Analysis"
    d["网格质量:"] = "Mesh Quality:"
    d["着色:"] = "Coloring:"
    d["NCI 预览"] = "NCI Peek"
    d["NCI 出图 (PNG)"] = "NCI Render (PNG)"
    d["NCI 出图 (SVG)"] = "NCI Render (SVG)"
    d["画布点选片段:"] = "Canvas select:"
    d["1 (快速)"] = "1 (Fast)"
    d["2 (标准)"] = "2 (Standard)"
    d["3 (精细)"] = "3 (Fine)"
    d["IGMH 分析完成 — 可点击「NCI 预览」或「NCI 出图」"] = "IGMH analysis done — click NCI Peek or NCI Render"
    d["IGMH 分析失败"] = "IGMH analysis failed"
    d["保存 NCI 表面 SVG"] = "Save NCI Surface SVG"
    d["NCI SVG 渲染中..."] = "Rendering NCI SVG..."
    d["NCI 表面预览渲染中..."] = "Rendering NCI preview..."
    d["NCI 表面预览完成"] = "NCI preview done"
    d["NCI 表面渲染中..."] = "Rendering NCI surface..."
    d["NCI 渲染失败"] = "NCI render failed"
    d["请先运行 IGMH 分析"] = "Please run IGMH analysis first"
    d["请先浏览并载入 fchk 文件"] = "Please load fchk file first"
    d["请输入片段1"] = "Please enter Fragment 1"
    d["请输入片段2"] = "Please enter Fragment 2"
    d["IGMH 分析需要 fchk 文件"] = "IGMH analysis requires fchk file"
    d["IGMH 分析中..."] = "Running IGMH..."
    d["IGMH 分析中... {}%"] = "Running IGMH... {}%"

    # ── 电荷 tab ──
    d["电荷计算 (需 fchk 文件)"] = "Charge Calculation (needs fchk)"
    d["计算结果"] = "Results"
    d["原子着色渲染"] = "Atom Color Render"
    d["计算"] = "Calculate"
    d["电荷类型:"] = "Charge Type:"
    d["色板:"] = "Colormap:"
    d["显示颜色条"] = "Show Color Bar"
    d["序号"] = "#"
    d["元素"] = "Elem."
    d["电荷值"] = "Charge"
    d["cmap 预览"] = "cmap Peek"
    d["电荷出图 (PNG)"] = "Charge Render (PNG)"
    d["电荷出图 (SVG)"] = "Charge Render (SVG)"
    d["~"] = "~"

    # ── Cube tab ──
    d["透明度:"] = "Opacity:"
    d["Cube 预览"] = "Cube Peek"
    d["保存 Cube 图 (PNG)"] = "Save Cube (PNG)"
    d["保存 Cube 图 (SVG)"] = "Save Cube (SVG)"

    # ── 线条样式 ──
    d["线段"] = "Dash"
    d["圆点"] = "Dots"
    d["solid"] = "solid"
    d["mesh"] = "mesh"
    d["contour"] = "contour"
    d["dot"] = "dot"
    d["avg"] = "avg"
    d["pixel"] = "pixel"
    d["uniform"] = "uniform"

    # ── Multiwfn 路径相关的用户可见字符串如果在 viewer.py 中，一并处理 ──
    d["Multiwfn.exe (Multiwfn.exe);;所有文件 (*.*)"] = "Multiwfn.exe (Multiwfn.exe);;All Files (*.*)"

    return d


_tr_dict = _build_dict()

# ── 语言变更信号 ──
class LanguageSignal(QObject):
    changed = pyqtSignal()

_lang_signal = LanguageSignal()

_current_lang = "zh"


def tr(text: str) -> str:
    """Return translated string. zh→returns original; en→returns English."""
    if _current_lang == "zh":
        return text
    # Exact match first, then try str.format patterns
    if text in _tr_dict:
        return _tr_dict[text]
    # Try format-string matching: replace {} with placeholder
    import re
    base = re.sub(r'\{.*?\}', '{}', text)
    if base in _tr_dict:
        en_base = _tr_dict[base]
        # Reinsert the original format args
        args = re.findall(r'\{.*?\}', text)
        result = en_base
        for a in args:
            result = result.replace('{}', a, 1)
        return result
    return text


def toggle_language():
    global _current_lang
    _current_lang = "en" if _current_lang == "zh" else "zh"
    _lang_signal.changed.emit()


def current_lang() -> str:
    return _current_lang


def on_language_changed(callback):
    _lang_signal.changed.connect(callback)
