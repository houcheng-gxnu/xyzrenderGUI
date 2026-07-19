"""xyzrender GUI 主窗口 — 布局编排 + 文件加载 + 渲染出口。"""

import os
import sys
import shutil
import tempfile
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QPushButton, QComboBox, QLabel,
    QFileDialog, QMessageBox, QSplitter, QTabWidget,
    QPlainTextEdit, QLineEdit, QApplication, QColorDialog,
    QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QColor, QMovie, QIcon

from molcanvas.canvas import MolCanvas
from molcanvas.styles import STYLE_PRESETS
from molcanvas.atoms import ATOM_RADII, REVERSE_SYMBOLS, ELEMENT_SYMBOLS

from xyzrender import load, render, render_gif, build_config
from xyzrender.config import apply_hydrogen_flags
from xyz_render_bridge import rotate_copy, rotate_copy_from_quat

from .config import LIGHT_QSS, _load_mw_config, _save_mw_config, DEFAULT_MULTIWFN
from .parsing import (
    parse_fchk_mo_info, parse_charge_output, parse_esp_range,
    _parse_xyz_local, _parse_fchk_local, _write_atoms_to_xyz, _indices_to_text,
)
from .workers import MultiwfnWorker, MOCubeWorker, IgmhWorker, ChargeWorker, DetectRangeWorker
from .tabs import StructureTab, ESPTab, MOTab, IGMHTab, ChargeTab, CubeTab
from .i18n import tr, on_language_changed, toggle_language, current_lang


class XYZRenderViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(tr("xyzrender GUI v1.1.0 — 分子结构 + 等值面可视化"))
        # 窗口图标
        _icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if not os.path.exists(_icon_path):
            _icon_path = r"C:\Users\Administrator\Pictures\xyzrenderGUI.png"
        if os.path.exists(_icon_path):
            self.setWindowIcon(QIcon(_icon_path))
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.80), int(screen.height() * 0.80))
        self.setAcceptDrops(True)

        on_language_changed(self._retranslate_ui)

        self.molecule = None
        self.file_path = None
        self._xyzr_temp_dir = None
        self._esp_color_cube = None
        self._esp_density_path = None
        self._esp_path = None
        self._mw_worker = None

        self._iso_cube_paths = [None, None, None]  # [ESP, MO, Cub]
        self._mo_selected = None

        # IGMH 状态
        self._igmh_work_dir = None
        self._igmh_sl2r = None
        self._igmh_dg = None
        self._igmh_worker = None
        self._igmh_atoms = []

        # 电荷
        self._charge_cache = {}
        self._charge_worker = None
        self._charge_cmap_path = None
        self._detect_range_worker = None

        self._mw_config = _load_mw_config()
        self._current_fchk_path = None

        self._build_ui()
        self._apply_style()
        self._status(tr("就绪 — 打开 XYZ / cube / log / fchk 文件 | Tab 1: 结构 | Tab 2: 等值面"))

    def _apply_style(self):
        self.setStyleSheet(LIGHT_QSS)

    _DND_EXTS = {".xyz", ".cube", ".cub", ".fchk", ".fch", ".mol",
                 ".sdf", ".mol2", ".pdb", ".log", ".out"}

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if os.path.splitext(url.toLocalFile())[1].lower() in self._DND_EXTS:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.splitext(path)[1].lower() in self._DND_EXTS:
                try:
                    self._load_file(path)
                except Exception as e:
                    QMessageBox.critical(self, tr("加载失败"), str(e))
                break

    def _retranslate_ui(self):
        """Update all UI strings when language changes."""
        self.setWindowTitle(tr("xyzrender GUI v1.1.0 — 分子结构 + 等值面可视化"))
        self.gb_canvas.setTitle(tr("3D 画布"))
        self.gb_preview.setTitle(tr("渲染预览"))
        self.gb_file.setTitle(tr("文件"))
        self._file_edit.setPlaceholderText(tr("(未加载)"))
        self._btn_open.setText(tr("浏览"))
        self._mw_label.setText(tr("Multiwfn:"))
        self._mw_btn.setText(tr("设置路径"))
        self._style_label.setText(tr("样式:"))
        self._label_label.setText(tr(" 标签:"))
        self._canvas_hint_label.setText(tr("左键旋转 | 右键平移 | 滚轮缩放"))
        self._btn_lang.setText("中" if current_lang() == "en" else "EN")
        # preview label text (only update if no pixmap showing)
        if self._preview_label.pixmap() is None:
            self._preview_label.setText(tr("(等待渲染...)"))
        # label combo items
        self._label_combo.clear()
        self._label_combo.addItems([tr("隐藏"), tr("编号"), tr("元素")])
        # tab texts
        self._tabs.setTabText(0, tr("结构"))
        self._tabs.setTabText(1, tr("ESP"))
        self._tabs.setTabText(2, tr("MO"))
        self._tabs.setTabText(3, tr("IGMH"))
        self._tabs.setTabText(4, tr("电荷"))
        self._tabs.setTabText(5, tr("Cub 文件"))
        self._tabs.setTabText(6, tr("运行日志"))

    def _on_toggle_lang(self):
        toggle_language()

    # ══════════════════════════════════════════════════════════════════
    #  UI 构建
    # ══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        # ── 左侧: MolCanvas + 预览 ──
        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.setContentsMargins(8, 8, 4, 8)

        left_splitter = QSplitter(Qt.Vertical)

        self.gb_canvas = QGroupBox(tr("3D 画布"))
        cv = QVBoxLayout(self.gb_canvas); cv.setContentsMargins(4, 4, 4, 4)
        self.canvas = MolCanvas()
        self.canvas.setMinimumSize(200, 150)
        self.canvas.box_selected.connect(self._on_canvas_box_select)
        cv.addWidget(self.canvas)
        left_splitter.addWidget(self.gb_canvas)

        self.gb_preview = QGroupBox(tr("渲染预览"))
        pv = QVBoxLayout(self.gb_preview); pv.setContentsMargins(4, 4, 4, 4)
        self._preview_label = QLabel()
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setMinimumHeight(60)
        self._preview_label.setStyleSheet("background:#ffffff; border:1px solid #ccc;")
        self._preview_label.setText(tr("(等待渲染...)"))
        pv.addWidget(self._preview_label)
        left_splitter.addWidget(self.gb_preview)
        left_splitter.setSizes([400, 250])
        left_splitter.setChildrenCollapsible(False)
        left.addWidget(left_splitter, stretch=1)

        style_bar = QHBoxLayout()
        self._style_label = QLabel(tr("样式:"))
        style_bar.addWidget(self._style_label)
        self._style_combo = QComboBox()
        self._style_combo.addItems(STYLE_PRESETS.keys())
        self._style_combo.currentTextChanged.connect(lambda k: self.canvas.set_style(k))
        self._style_combo.setCurrentText("HoukMol")
        style_bar.addWidget(self._style_combo)
        self._label_label = QLabel(tr(" 标签:"))
        style_bar.addWidget(self._label_label)
        self._label_combo = QComboBox()
        self._label_combo.addItems([tr("隐藏"), tr("编号"), tr("元素")])
        self._label_combo.setCurrentIndex(0)
        self._label_combo.currentIndexChanged.connect(
            lambda idx: (setattr(self.canvas, 'label_mode', [2, 1, 0][idx]), self.canvas.update()))
        style_bar.addWidget(self._label_combo)
        style_bar.addStretch()
        self._canvas_hint_label = QLabel(tr("左键旋转 | 右键平移 | 滚轮缩放"))
        style_bar.addWidget(self._canvas_hint_label)
        left.addLayout(style_bar)

        splitter.addWidget(left_widget)

        # ── 右侧: 共用文件区 + Tab 面板 ──
        right_widget = QWidget()
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(4, 8, 8, 8)
        right.setSpacing(4)

        # 文件加载
        self.gb_file = QGroupBox(tr("文件"))
        fl = QVBoxLayout(self.gb_file)
        fh = QHBoxLayout()
        self._file_edit = QLineEdit(); self._file_edit.setReadOnly(True); self._file_edit.setPlaceholderText(tr("(未加载)"))
        self._btn_open = QPushButton(tr("浏览")); self._btn_open.setFixedWidth(120); self._btn_open.clicked.connect(self._open_file)
        self._btn_lang = QPushButton("EN"); self._btn_lang.setFixedWidth(70); self._btn_lang.clicked.connect(self._on_toggle_lang)
        self._file_label = QLabel(tr("文件:"))
        self._file_label.setFixedWidth(80)
        fh.addWidget(self._file_label); fh.addWidget(self._file_edit); fh.addWidget(self._btn_open); fh.addWidget(self._btn_lang)
        fl.addLayout(fh)
        mwh = QHBoxLayout()
        self._mw_label = QLabel(tr("Multiwfn:"))
        self._mw_label.setFixedWidth(80)
        mwh.addWidget(self._mw_label)
        self._mw_edit = QLineEdit(self._mw_config["multiwfn"])
        self._mw_btn = QPushButton(tr("设置路径")); self._mw_btn.setFixedWidth(120); self._mw_btn.clicked.connect(self._browse_mw)
        self._mw_spacer = QWidget(); self._mw_spacer.setFixedWidth(70)
        mwh.addWidget(self._mw_edit); mwh.addWidget(self._mw_btn); mwh.addWidget(self._mw_spacer)
        fl.addLayout(mwh)
        right.addWidget(self.gb_file)

        # ── 创建各 Tab ──
        self._tabs = QTabWidget()
        right.addWidget(self._tabs)

        self._structure_tab = StructureTab()
        self._esp_tab = ESPTab()
        self._mo_tab = MOTab()
        self._igmh_tab = IGMHTab()
        self._charge_tab = ChargeTab()
        self._cube_tab = CubeTab()

        self._tabs.addTab(self._structure_tab, tr("结构"))
        self._tabs.addTab(self._esp_tab, tr("ESP"))
        self._tabs.addTab(self._mo_tab, tr("MO"))
        self._tabs.addTab(self._igmh_tab, tr("IGMH"))
        self._tabs.addTab(self._charge_tab, tr("电荷"))
        self._tabs.addTab(self._cube_tab, tr("Cub 文件"))

        # 运行日志
        tab_log = QWidget()
        logl = QVBoxLayout(tab_log); logl.setContentsMargins(0, 0, 0, 0)
        self._log_view = QPlainTextEdit(); self._log_view.setReadOnly(True); self._log_view.setMaximumBlockCount(500)
        logl.addWidget(self._log_view)
        self._tabs.addTab(tab_log, tr("运行日志"))

        # 状态栏
        self._status_label = QLabel(""); self._status_label.setObjectName("ProgressLabel")
        right.addWidget(self._status_label)

        splitter.addWidget(right_widget)
        splitter.setSizes([750, 350])
        splitter.setChildrenCollapsible(False)

        # ── 信号连接 ──
        self._wire_signals()

    def _wire_signals(self):
        """连接各 Tab 信号到主窗口处理函数。"""
        # 结构 Tab
        st = self._structure_tab
        st.render_requested.connect(self._on_structure_render)
        st.export_png_requested.connect(self._on_structure_export_png)
        st.export_svg_requested.connect(self._on_structure_export_svg)
        st.export_gif_requested.connect(self._on_structure_export_gif)
        st.preview_gif_requested.connect(self._on_structure_preview_gif)
        # 片段选择：同步 structure tab ↔ canvas
        st._btn_frag1.clicked.connect(lambda: self._on_frag_mode_changed(1))
        st._btn_frag2.clicked.connect(lambda: self._on_frag_mode_changed(2))
        st._btn_frag_clear.clicked.connect(self._on_clear_structure_frags)
        # 画布原子点击 → 结构 tab 片段
        self.canvas.atom_clicked.connect(self._on_canvas_atom_clicked)

        # ESP Tab
        et = self._esp_tab
        et.gen_esp_requested.connect(self._gen_esp_cubes)
        et.detect_range_requested.connect(self._on_detect_esp_range)
        et.quick_peek_requested.connect(lambda kw: self._on_iso_render(kw, 0))
        et.export_png_requested.connect(lambda kw: self._on_iso_export_png(kw, 0))
        et.export_svg_requested.connect(lambda kw: self._on_iso_export_svg(kw, 0))

        # MO Tab
        mt = self._mo_tab
        mt.mo_selected_signal.connect(self._on_mo_selected)
        mt.quick_peek_requested.connect(lambda kw: self._on_iso_render(kw, 1))
        mt.export_png_requested.connect(lambda kw: self._on_iso_export_png(kw, 1))
        mt.export_svg_requested.connect(lambda kw: self._on_iso_export_svg(kw, 1))
        mt.export_gif_requested.connect(lambda kw: self._on_iso_export_gif(kw, 1))
        mt.preview_gif_requested.connect(lambda kw: self._on_iso_preview_gif(kw, 1))

        # IGMH Tab
        it = self._igmh_tab
        it.run_igmh_requested.connect(self._run_igmh)
        it.quick_peek_requested.connect(self._on_igmh_render)
        it.export_png_requested.connect(self._on_igmh_export_render)
        it.export_svg_requested.connect(self._on_igmh_export_svg)

        # 电荷 Tab
        ct = self._charge_tab
        ct.calc_requested.connect(self._run_charge_calc)
        ct.charge_type_changed.connect(self._on_charge_type_changed)
        ct.quick_peek_requested.connect(self._on_charge_peek)
        ct.export_png_requested.connect(self._on_charge_render)
        ct.export_svg_requested.connect(self._on_charge_export_svg)

        # Cub Tab
        cbt = self._cube_tab
        cbt.quick_peek_requested.connect(lambda kw: self._on_iso_render(kw, 2))
        cbt.export_png_requested.connect(lambda kw: self._on_iso_export_png(kw, 2))
        cbt.export_svg_requested.connect(lambda kw: self._on_iso_export_svg(kw, 2))
        cbt.export_gif_requested.connect(lambda kw: self._on_iso_export_gif(kw, 2))
        cbt.preview_gif_requested.connect(lambda kw: self._on_iso_preview_gif(kw, 2))

        # IGMH 画布点选
        self._igmh_tab._btn_pick_frag1.toggled.connect(lambda c: self._on_pick_target(1, c))
        self._igmh_tab._btn_pick_frag2.toggled.connect(lambda c: self._on_pick_target(2, c))
        self._igmh_tab._btn_pick_clear.clicked.connect(self._on_clear_frags)

        # 键编辑器 — 使用 StructureTab 里的 bond_editor
        be = self._structure_tab.bond_editor
        be.chk_dash_mode.toggled.connect(lambda v: (self.canvas.set_dash_bond_mode(v), self._update_dash_status()))
        # canvas bond_width 含 scale/80 缩放 → dash 补偿系数
        _DASH_SCALE = 1.5  # 补偿 canvas bw ≈ (2/3) * xyzrender _bw 的差异
        be.dash_style_combo.currentTextChanged.connect(
            lambda t: (setattr(self.canvas, 'dash_style', 'dots' if be.dash_style_combo.currentIndex() == 1 else 'dash'), self.canvas.update()))
        be.dash_changed.connect(lambda: (
            setattr(self.canvas, 'dash_len_ratio', be.dash_len_ratio * _DASH_SCALE),
            setattr(self.canvas, 'dash_gap_ratio', be.dash_gap_ratio * _DASH_SCALE),
            setattr(self.canvas, 'dash_width_ratio', be.dash_width_ratio * _DASH_SCALE),
            self._sync_dash_color(),
            self.canvas.update()))
        be._btn_undo.clicked.connect(lambda: (self.canvas.undo_last_dash_line(), self._update_dash_status()))
        be._btn_clear.clicked.connect(lambda: (self.canvas.clear_dash_lines(), self._update_dash_status()))

        # 断键模式 — 与虚线模式互斥
        be.chk_break_mode.toggled.connect(lambda v: (
            self.canvas.set_break_bond_mode(v),
            be.chk_dash_mode.setChecked(False) if v else None,
            self._update_break_status(),
        ))
        be.chk_dash_mode.toggled.connect(lambda v: (
            be.chk_break_mode.setChecked(False) if v else None,
        ))
        be.btn_break_undo.clicked.connect(lambda: (self.canvas.undo_last_broken_bond(), self._update_break_status()))
        be.btn_break_clear.clicked.connect(lambda: (self.canvas.clear_broken_bonds(), self._update_break_status()))

        # 氢原子隐藏
        st = self._structure_tab
        st._btn_hy.toggled.connect(self._on_hide_h_toggled)
        st._hy_keep_edit.textChanged.connect(self._on_hide_h_toggled)

    # ══════════════════════════════════════════════════════════════════
    #  日志 / 状态
    # ══════════════════════════════════════════════════════════════════

    def _status(self, msg):
        self._status_label.setText(msg)
        self._log(msg)

    def _log(self, msg):
        stamp = datetime.now().strftime("%H:%M:%S")
        self._log_view.appendPlainText(f"[{stamp}] {msg}")

    # ══════════════════════════════════════════════════════════════════
    #  Multiwfn 路径
    # ══════════════════════════════════════════════════════════════════

    def _browse_mw(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("选择 Multiwfn.exe"), "", tr("Multiwfn.exe (Multiwfn.exe);;所有文件 (*.*)"))
        if path:
            self._mw_edit.setText(path)
            self._mw_config["multiwfn"] = path
            _save_mw_config(path)

    # ══════════════════════════════════════════════════════════════════
    #  文件操作
    # ══════════════════════════════════════════════════════════════════

    def closeEvent(self, event):
        if self._xyzr_temp_dir and os.path.isdir(self._xyzr_temp_dir):
            shutil.rmtree(self._xyzr_temp_dir, ignore_errors=True)
        super().closeEvent(event)

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("打开分子结构文件"), "",
            tr("所有支持格式 (*.xyz *.cube *.cub *.fchk *.fch *.mol *.sdf *.mol2 *.pdb *.log *.out);;"
            "XYZ (*.xyz);;Cube (*.cube *.cub);;fchk (*.fchk *.fch);;"
            "Gaussian Log (*.log *.out);;所有文件 (*.*)"))
        if not path:
            return
        try:
            self._load_file(path)
        except Exception as e:
            QMessageBox.critical(self, tr("加载失败"), str(e))

    def _on_hide_h_toggled(self):
        """隐藏/显示氢原子，根据当前按钮状态和保留列表更新画布。"""
        st = self._structure_tab
        hide = st._btn_hy.isChecked()
        keep = set()
        try:
            text = st._hy_keep_edit.text().strip()
            if text:
                keep = {int(x.strip()) for x in text.replace(",", " ").split() if x.strip()}
        except ValueError:
            pass
        try:
            self.canvas.set_h_filter(hide, keep)
        except Exception:
            pass

    def _load_file(self, path: str):
        name = os.path.basename(path)
        self._status(tr("加载中: {}").format(name) + " ...")
        QApplication.processEvents()

        if self._xyzr_temp_dir and os.path.isdir(self._xyzr_temp_dir):
            shutil.rmtree(self._xyzr_temp_dir, ignore_errors=True)
            self._xyzr_temp_dir = None

        self.canvas.frag1_atoms.clear()
        self.canvas.frag2_atoms.clear()

        ext = os.path.splitext(path)[1].lower()
        self.file_path = path
        self._current_fchk_path = path if ext in (".fchk", ".fch") else self._current_fchk_path

        self._charge_cache.clear()
        self._charge_cmap_path = None
        self._charge_tab.set_status("")
        self._charge_tab.clear_table()
        self._charge_tab.set_buttons_enabled(False)

        # 本地解析
        if ext in (".xyz",):
            atoms, bonds = _parse_xyz_local(path)
        elif ext in (".fchk", ".fch"):
            atoms, bonds = _parse_fchk_local(path)
        else:
            atoms, bonds = [], []

        # xyzrender 加载
        if ext in (".fchk", ".fch") and atoms:
            self._xyzr_temp_dir = tempfile.mkdtemp(prefix="xyzr_fchk_")
            xyz_path = os.path.join(self._xyzr_temp_dir, "_fchk_temp.xyz")
            _write_atoms_to_xyz(atoms, xyz_path)
            self.molecule = load(xyz_path)
        else:
            try:
                self.molecule = load(path)
            except Exception:
                self.molecule = None

        if not atoms and self.molecule is not None:
            atoms, bonds, g2p = self._mol_to_canvas_data(self.molecule)
        elif ext in (".fchk", ".fch"):
            g2p = {}
            self._igmh_atoms = atoms
            self._igmh_work_dir = None
            self._igmh_sl2r = None
            self._igmh_dg = None
            self._igmh_tab.set_buttons_enabled(False)
        elif self.molecule is not None:
            _, _, g2p = self._mol_to_canvas_data(self.molecule)
        else:
            g2p = {}

        if atoms:
            self.canvas.set_data(atoms, bonds)
            self._canvas_graphid_to_pos = g2p

        # H 过滤
        hide = self._structure_tab._btn_hy.isChecked()
        keep = set()
        if hide:
            text = self._structure_tab._hy_keep_edit.text().strip()
            if text:
                try:
                    keep = {int(x.strip()) for x in text.replace(",", " ").split() if x.strip()}
                except ValueError:
                    pass
        self.canvas.set_h_filter(hide, keep)

        n_atoms = len(atoms)
        has_cube = self.molecule is not None and self.molecule.cube_data is not None
        if has_cube:
            cd = self.molecule.cube_data
            self._log(f"载入: {path}")
            self._log(f"  原子数: {n_atoms}, 体网格: {cd.grid_shape}")
            self._iso_cube_paths[2] = path
            self._cube_tab.set_buttons_enabled(True)
        elif ext in (".fchk", ".fch"):
            self._log(f"载入: {path}")
            self._log(f"  原子数: {n_atoms}")
            self._iso_cube_paths[0] = None
            self._esp_density_path = None; self._esp_path = None
            self._esp_tab.set_buttons_enabled(False)
            self._fill_mo_table()
        else:
            self._log(f"载入: {path}")
            self._log(f"  原子数: {n_atoms}")

        self._file_edit.setText(path)
        self._status(tr("已加载 {} — 左键旋转视角, 调好后点「出图」").format(name))

        # 填充元素颜色覆盖按钮
        if atoms:
            syms = sorted(set(a[1] for a in atoms))
            self._structure_tab.set_element_symbols(syms)

    @staticmethod
    def _mol_to_canvas_data(mol, hy=False):
        hide_all = hy is True
        keep_set = set(hy) if isinstance(hy, list) else None
        g2p = {}
        atoms = []
        new_idx = 0
        for nid, data in mol.graph.nodes(data=True):
            sym = data.get("symbol", "X")
            is_h = sym.capitalize() == "H"
            new_idx += 1
            if is_h:
                if hide_all:
                    continue
                if keep_set is not None and new_idx not in keep_set:
                    continue
            x, y, z = data["position"]
            an = REVERSE_SYMBOLS.get(sym.capitalize(), 0)
            atoms.append((len(atoms) + 1, sym.capitalize(), an, (float(x), float(y), float(z))))
            g2p[nid] = len(atoms)
        bonds = []
        for a1, a2 in mol.graph.edges():
            if a1 in g2p and a2 in g2p:
                bonds.append((g2p[a1], g2p[a2]))
        return atoms, bonds, g2p

    # ══════════════════════════════════════════════════════════════════
    #  结构渲染
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _resolve_hy_kwargs(hy_kw: dict, mol) -> dict:
        """将 xyzrender 的 hy / no_hy 转为正确 kwarg。

        no_hy → exclude 所有 H（绕过 xyzrender 只隐藏 C-H 的限制）
        hy=[1,3] → exclude 除指定编号外的所有 H
        hy=True → 直接透传给 xyzrender（显示全部 H）
        """
        from copy import deepcopy
        out = deepcopy(hy_kw)
        if "no_hy" in out:
            del out["no_hy"]
            if mol is not None:
                h_all_1b = [idx + 1 for idx, d in mol.graph.nodes(data=True) if d.get("symbol") == "H"]
                if h_all_1b:
                    out["exclude"] = h_all_1b
            return out
        hy_val = out.pop("hy", None)
        if isinstance(hy_val, list) and mol is not None:
            keep_1based = set(hy_val)
            h_all = [idx for idx, d in mol.graph.nodes(data=True) if d.get("symbol") == "H"]
            h_exclude = [idx + 1 for idx in h_all if (idx + 1) not in keep_1based]
            if h_exclude:
                out["exclude"] = h_exclude
        elif hy_val is True:
            out["hy"] = True  # 必须显式传给 xyzrender，默认 hy=None 会隐藏 C-H
        return out

    def _get_structure_kwargs(self):
        st = self._structure_tab
        kwargs = st.get_base_kwargs()
        hy_kw = self._resolve_hy_kwargs(st.get_hy_kwargs(), self.molecule)
        kwargs.update(hy_kw)
        kwargs.update(st.get_vdw_kwargs())
        # 高亮
        if st._chk_highlight.isChecked():
            spec = st._hl_spec.text().strip()
            if spec:
                kwargs["highlight"] = [(spec, st._highlight_color)]
        # 凸包
        if st._chk_hull.isChecked():
            spec = st._hull_spec.text().strip()
            if spec:
                if spec.lower() == "rings":
                    kwargs["hull"] = "rings"
                else:
                    indices = []
                    for part in spec.replace(",", " ").split():
                        part = part.strip()
                        if not part:
                            continue
                        if "-" in part:
                            try:
                                a, b = part.split("-", 1)
                                indices.extend(range(int(a), int(b) + 1))
                            except ValueError:
                                pass
                        else:
                            try:
                                indices.append(int(part))
                            except ValueError:
                                pass
                    if indices:
                        kwargs["hull"] = indices
                kwargs["hull_color"] = st._hull_color
                kwargs["hull_opacity"] = st._hull_opacity_slider.value() / 100.0
        # 虚线参数
        dashes = getattr(self.canvas, "custom_dash_lines", [])
        if dashes:
            ts_bonds = [(a1, a2) for a1, a2, _ in dashes]
            ts_color = dashes[0][2] if dashes else None
            kwargs["ts_bonds"] = ts_bonds
            if ts_color:
                kwargs["ts_color"] = ts_color
            kwargs["ts_dash"] = self._get_ts_dash_str()
            kwargs["ts_width"] = self._structure_tab.bond_editor.dash_width_ratio
        # 断键参数
        broken = getattr(self.canvas, "custom_broken_bonds", [])
        if broken:
            kwargs["unbond"] = [f"{a1}-{a2}" for a1, a2 in broken]
        if self._structure_tab._chk_transparent.isChecked():
            kwargs["transparent"] = True
        return self._apply_color_overrides(kwargs)

    def _apply_color_overrides(self, kwargs: dict) -> dict:
        """将 color_overrides 从 kwargs 移到 config 对象中。"""
        from xyzrender import RenderConfig
        co = kwargs.pop("color_overrides", None)
        if co:
            preset = kwargs.pop("config", None)
            if isinstance(preset, RenderConfig):
                cfg = preset
            else:
                cfg = build_config(preset or "default")
            cfg.color_overrides = co
            # 保留氢原子设置
            hy_val = kwargs.pop("hy", None)
            no_hy = kwargs.pop("no_hy", False)
            apply_hydrogen_flags(cfg, hy=hy_val, no_hy=no_hy)
            kwargs["config"] = cfg
        return kwargs

    def _do_structure_render(self):
        mol = rotate_copy_from_quat(self.molecule, self.canvas._rot_q)
        return render(mol, **self._get_structure_kwargs())

    def _on_structure_render(self, kwargs):
        if self.molecule is None:
            self._status(tr("请先打开文件"))
            return
        self._status(tr("快速预览渲染中..."))
        QApplication.processEvents()
        try:
            result = self._do_structure_render()
            tmp = os.path.join(tempfile.gettempdir(), "xyzr_quick_preview.png")
            from xyzrender.export import svg_to_png
            svg_to_png(result._svg, tmp, size=self._structure_tab._size_combo.currentText())
            self._show_preview(tmp)
            self._status(tr("预览完成"))
        except Exception as e:
            QMessageBox.critical(self, tr("渲染失败"), str(e))

    def _on_structure_export_png(self, kwargs):
        if self.molecule is None:
            QMessageBox.information(self, tr("提示"), tr("请先打开文件"))
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("保存 PNG"), "", tr("PNG (*.png);;SVG (*.svg)"))
        if not path:
            return
        self._status(tr("渲染中...")); QApplication.processEvents()
        try:
            result = self._do_structure_render()
            ext = os.path.splitext(path)[1].lower()
            if ext == ".svg":
                with open(path, "w", encoding="utf-8") as f:
                    f.write(result._svg)
            else:
                from xyzrender.export import svg_to_png
                svg_to_png(result._svg, path, size=self._structure_tab._size_combo.currentText())
                self._show_preview(path)
            self._status(tr("已保存: {}").format(os.path.basename(path)))
        except Exception as e:
            QMessageBox.critical(self, tr("渲染失败"), str(e))

    def _on_structure_export_svg(self, kwargs):
        if self.molecule is None:
            QMessageBox.information(self, tr("提示"), tr("请先打开文件"))
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("保存 SVG"), "", tr("SVG (*.svg)"))
        if not path:
            return
        self._status(tr("渲染中...")); QApplication.processEvents()
        try:
            result = self._do_structure_render()
            with open(path, "w", encoding="utf-8") as f:
                f.write(result._svg)
            self._status(tr("已保存: {}").format(os.path.basename(path)))
        except Exception as e:
            QMessageBox.critical(self, tr("渲染失败"), str(e))

    def _on_structure_export_gif(self, kwargs):
        if self.molecule is None:
            QMessageBox.information(self, tr("提示"), tr("请先打开文件"))
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("保存 GIF"), "", "GIF (*.gif)")
        if not path:
            return
        self._do_structure_gif(path, kwargs)

    def _on_structure_preview_gif(self, kwargs):
        if self.molecule is None:
            QMessageBox.information(self, tr("提示"), tr("请先打开文件"))
            return
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as f:
            path = f.name
        self._do_structure_gif(path, kwargs)

    # render_gif() 不接受的顶层 kwarg（需转移到 config 对象或直接丢弃）
    _GIF_TO_CONFIG = {"vdw", "ts_bonds", "nci_bonds"}
    _GIF_DROP = {"idx", "overlay_mol"}

    def _build_gif_config(self, kw: dict):
        """从 render kwargs 构建 RenderConfig，把 vdw/ts_bonds 等写入 config。"""
        from xyzrender import RenderConfig
        preset = kw.pop("config", None)
        if isinstance(preset, RenderConfig):
            cfg = preset
        else:
            orient = kw.pop("orient", None)
            cfg = build_config(preset or "default", orient=orient)
        # vdw → cfg.vdw_indices
        vdw = kw.pop("vdw", None)
        if vdw is True:
            cfg.vdw_indices = []  # empty list = all atoms
        elif isinstance(vdw, list):
            cfg.vdw_indices = vdw
        # ts_bonds → cfg.ts_bonds (render 用 1-indexed, config 用 0-indexed)
        ts_bonds = kw.pop("ts_bonds", None)
        if ts_bonds:
            cfg.ts_bonds = [(a - 1, b - 1) for a, b in ts_bonds]
        # nci_bonds → cfg.nci_bonds
        nci_bonds = kw.pop("nci_bonds", None)
        if nci_bonds:
            cfg.nci_bonds = [(a - 1, b - 1) for a, b in nci_bonds]
        # hy / no_hy → apply_hydrogen_flags（render_gif 收到 RenderConfig 时跳过此步）
        hy_val = kw.pop("hy", None)
        no_hy = kw.pop("no_hy", False)
        apply_hydrogen_flags(cfg, hy=hy_val, no_hy=no_hy)
        # mo_outline_width → cfg（render_gif 的 config 会覆盖 kwarg）
        mo_ow = kw.pop("mo_outline_width", None)
        if mo_ow is not None:
            cfg.mo_outline_width = mo_ow
        # surface_style → cfg
        ss = kw.pop("surface_style", None)
        if ss is not None:
            cfg.surface_style = ss
        # color_overrides → cfg
        co = kw.pop("color_overrides", None)
        if co:
            cfg.color_overrides = co
        # exclude（由 _resolve_hy_kwargs 生成）保留在 kw 中，render_gif 会处理
        return cfg

    def _do_structure_gif(self, path, kwargs):
        axis = kwargs.pop("gif_rot", "Y").lower()
        gif_fps = kwargs.pop("gif_fps", 10)
        rot_frames = kwargs.pop("rot_frames", 120)
        self._status(f"GIF 渲染中 (绕{axis}轴)..."); QApplication.processEvents()
        try:
            mol = rotate_copy_from_quat(self.molecule, self.canvas._rot_q)
            kw = self._get_structure_kwargs()
            cfg = self._build_gif_config(kw)
            for k in self._GIF_DROP:
                kw.pop(k, None)
            render_gif(mol, gif_rot=axis, gif_fps=gif_fps, rot_frames=rot_frames,
                       output=path, config=cfg, **kw)
            self._status(tr("已保存: {}").format(os.path.basename(path)))
            self._show_preview_gif(path)
        except Exception as e:
            QMessageBox.critical(self, tr("渲染失败"), str(e))

    def _show_preview(self, png_path):
        pix = QPixmap(png_path)
        if pix.isNull():
            return
        w = self._preview_label.width()
        h = self._preview_label.height()
        if w > 10 and h > 10:
            pix = pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._preview_label.setPixmap(pix)

    def _show_preview_gif(self, gif_path):
        """在预览区播放 GIF 动画"""
        movie = QMovie(gif_path)
        if not movie.isValid():
            return
        self._preview_movie = getattr(self, "_preview_movie", None)
        if self._preview_movie:
            self._preview_movie.stop()
        self._preview_movie = movie
        movie.setCacheMode(QMovie.CacheAll)
        self._preview_label.setMovie(movie)
        movie.start()
        # 在首帧加载后再缩放，确保尺寸准确
        def _scale_on_frame(_frame_num):
            lw, lh = self._preview_label.width(), self._preview_label.height()
            orig = movie.frameRect().size()
            if orig.width() > 0 and orig.height() > 0 and lw > 10 and lh > 10:
                ow, oh = orig.width(), orig.height()
                scale = min(lw / ow, lh / oh)
                movie.setScaledSize(QSize(int(ow * scale), int(oh * scale)))
                movie.frameChanged.disconnect(_scale_on_frame)
        movie.frameChanged.connect(_scale_on_frame)

    # ══════════════════════════════════════════════════════════════════
    #  ESP 生成
    # ══════════════════════════════════════════════════════════════════

    def _gen_esp_cubes(self):
        mw_exe = self._mw_edit.text().strip()
        fch = self.file_path

        if not mw_exe:
            QMessageBox.critical(self, tr("错误"), tr("请先设置 Multiwfn 路径"))
            return
        if not fch:
            QMessageBox.critical(self, tr("错误"), tr("请先选择 fchk 文件"))
            return
        ext = os.path.splitext(fch)[1].lower()
        if ext not in (".fchk", ".fch"):
            QMessageBox.critical(self, tr("错误"), tr("ESP 生成需要 fchk 文件"))
            return

        fch_name = os.path.splitext(os.path.basename(fch))[0]
        work_dir = tempfile.mkdtemp(prefix="_esp_", suffix=f"_{fch_name}")

        dst_fch = os.path.join(work_dir, os.path.basename(fch))
        shutil.copy2(fch, dst_fch)

        self._status("Multiwfn 运行中...")

        self._mw_worker = MultiwfnWorker(mw_exe, dst_fch, work_dir)
        self._mw_worker.status_signal.connect(self._log)
        self._mw_worker.progress_signal.connect(lambda v: None)
        self._mw_worker.finished_signal.connect(self._on_mw_finished)
        self._mw_worker.start()

    def _on_mw_finished(self, ok, work_dir):
        if ok:
            density_path = os.path.join(work_dir, "density.cub")
            esp_path = os.path.join(work_dir, "totesp.cub")
            if os.path.exists(density_path) and os.path.exists(esp_path):
                self._esp_density_path = density_path
                self._esp_path = esp_path
                self._iso_cube_paths[0] = density_path
                self._esp_color_cube = esp_path
                self._log(f"ESP cube 生成完毕: density.cub + totesp.cub")
                self._esp_tab.set_buttons_enabled(True)
                self._status(tr("ESP cube 生成完毕 — 点「快速预览」查看"))
            else:
                self._log("Multiwfn 完成但缺少输出文件")
                self._status(tr("Multiwfn 完成但缺少输出文件"))
        else:
            self._log("Multiwfn 执行失败")
            self._status(tr("Multiwfn 执行失败"))

    # ══════════════════════════════════════════════════════════════════
    #  ESP 范围检测
    # ══════════════════════════════════════════════════════════════════

    def _on_detect_esp_range(self):
        """点击 ESP Tab 的「检测」按钮 → 后台跑 Multiwfn 查询范围。"""
        mw_exe = self._mw_edit.text().strip()
        fch = self.file_path
        if not mw_exe or not fch:
            QMessageBox.critical(self, tr("错误"), tr("请先设置 Multiwfn 路径并选择 fchk 文件"))
            return
        self._status(tr("正在检测 ESP 范围..."))
        self._detect_range_worker = DetectRangeWorker(mw_exe, fch)
        self._detect_range_worker.finished_signal.connect(self._on_esp_range_detected)
        self._detect_range_worker.start()

    def _on_esp_range_detected(self, stdout: str):
        """解析 Multiwfn 输出，回填范围。"""
        if not stdout:
            self._status(tr("ESP 范围检测失败"))
            return
        rmin, rmax, unit = parse_esp_range(stdout)
        if rmin is None:
            self._status(tr("ESP 范围检测: 未识别到范围数据"))
            self._log(f"Multiwfn 输出 (前200字): {stdout[:200]}")
            return
        # Multiwfn 模块12 输出通常为 kcal/mol，xyzrender 的 cube 数据为 a.u.
        if unit == "kcal/mol":
            rmin /= 627.509
            rmax /= 627.509
        self._esp_tab.set_range_text(f"{rmin:.6g},{rmax:.6g}")
        self._status(tr("ESP 范围: {}").format(f"{rmin:.6g}, {rmax:.6g} a.u. ({unit})"))
        self._log(f"ESP 范围检测完成: {rmin:.6g}, {rmax:.6g} a.u.")

    # ══════════════════════════════════════════════════════════════════
    #  MO 处理
    # ══════════════════════════════════════════════════════════════════

    def _fill_mo_table(self):
        """填充 MO 轨道表格。"""
        mo = self._mo_tab
        if not self.file_path:
            return
        try:
            info = parse_fchk_mo_info(self.file_path)
        except Exception as e:
            self._log(f"解析 MO 信息失败: {e}")
            return

        n_a, n_b = info["n_alpha"], info["n_beta"]
        alpha_e = info["alpha_energies"]
        beta_e = info["beta_energies"]
        is_open = info["is_open_shell"]
        homo = info["homo_idx"]
        lumo = info["lumo_idx"]
        eV = 27.2114

        mo._mo_table_alpha.setRowCount(0)
        if mo._mo_table_beta:
            mo._mo_tabs.removeTab(1)
            mo._mo_table_beta = None

        rows_alpha = []
        for i, e in enumerate(alpha_e, 1):
            occ = (1.0 if is_open else 2.0) if i <= n_a else 0.0
            tag = ""
            if i == homo: tag = "HOMO"
            elif i == lumo: tag = "LUMO"
            rows_alpha.append((i, e, e*eV, occ, tag))
        self._fill_mo_rows(mo._mo_table_alpha, rows_alpha, "α")
        if homo and homo <= mo._mo_table_alpha.rowCount():
            mo._mo_table_alpha.selectRow(homo - 1)
            mo._mo_table_alpha.scrollToItem(
                mo._mo_table_alpha.item(homo - 1, 0), QTableWidget.PositionAtCenter)

        if is_open and beta_e:
            mo._mo_tabs.setTabText(0, tr("α 轨道"))
            mo._mo_table_beta = mo._make_mo_table()
            mo._mo_tabs.addTab(mo._mo_table_beta, tr("β 轨道"))
            rows_beta = []
            for i, e in enumerate(beta_e, 1):
                occ = 1.0 if i <= n_b else 0.0
                tag = ""
                if i == n_b: tag = "β-HOMO"
                elif i == n_b+1: tag = "β-LUMO"
                rows_beta.append((i, e, e*eV, occ, tag))
            self._fill_mo_rows(mo._mo_table_beta, rows_beta, "β")
            if n_b and n_b <= mo._mo_table_beta.rowCount():
                mo._mo_table_beta.selectRow(n_b - 1)
                mo._mo_table_beta.scrollToItem(
                    mo._mo_table_beta.item(n_b - 1, 0), QTableWidget.PositionAtCenter)
        else:
            mo._mo_tabs.setTabText(0, "Orbitals" if tr("轨道") != "轨道" else "轨道")

        self._log(f"轨道解析完成: {len(alpha_e)} MOs, HOMO={homo}, LUMO={lumo}, 开壳层={is_open}")

    def _fill_mo_rows(self, table, rows, spin):
        table.setRowCount(len(rows))
        for r, (orb, energy, ev, occ, tag) in enumerate(rows):
            it0 = QTableWidgetItem(f"{energy:.6f}"); it0.setTextAlignment(Qt.AlignCenter)
            table.setItem(r, 0, it0)
            it1 = QTableWidgetItem(f"{ev:.4f}"); it1.setTextAlignment(Qt.AlignCenter)
            table.setItem(r, 1, it1)
            it2 = QTableWidgetItem(f"{occ:.1f}"); it2.setTextAlignment(Qt.AlignCenter)
            if occ > 0: it2.setBackground(QColor("#E8F5E9"))
            if occ == 2.0:
                it2.setText("\u2b06\ufe0f\u2b07\ufe0f")  # ⬆️⬇️
            elif occ == 1.0:
                it2.setText("\u2b06\ufe0f")  # ⬆️
            elif occ == 0.0:
                it2.setText("\u2b1c")  # ⬜
            table.setItem(r, 2, it2)
            it3 = QTableWidgetItem(tag); it3.setTextAlignment(Qt.AlignCenter)
            if "HOMO" in tag:
                it3.setBackground(QColor("#FFF3E0")); it3.setFont(QFont("", -1, QFont.Bold))
            elif "LUMO" in tag:
                it3.setBackground(QColor("#E3F2FD")); it3.setFont(QFont("", -1, QFont.Bold))
            table.setItem(r, 3, it3)

    def _on_mo_selected(self, orbital):
        self._mo_selected = orbital
        self._log(f"选中轨道: {orbital}")
        self._gen_mo_cube()

    def _gen_mo_cube(self):
        if not self._mo_selected:
            QMessageBox.warning(self, tr("提示"), tr("请先在轨道表格中双击选择轨道"))
            return
        fch_path = self.file_path
        if not fch_path or not os.path.isfile(fch_path):
            QMessageBox.warning(self, tr("提示"), tr("请先打开 fchk 文件"))
            return

        orbital = self._mo_selected
        grid = self._mo_tab._mo_grid_combo.currentIndex() + 1
        self._log(f"正在生成轨道 {orbital} cube...")

        self._mo_worker = MOCubeWorker(
            self._mw_edit.text().strip(), fch_path, orbital, grid)
        self._mo_worker.status_signal.connect(self._log)
        self._mo_worker.progress_signal.connect(lambda v: None)
        self._mo_worker.finished_signal.connect(self._on_mo_cube_done)
        self._mo_worker.start()

    def _on_mo_cube_done(self, ok, cube_path):
        if ok:
            self._iso_cube_paths[1] = cube_path
            self._log(f"MO cube 已生成: {os.path.basename(cube_path)}")
            self._mo_tab.set_buttons_enabled(True)
            # 自动预览
            self._on_iso_render({}, 1)
        else:
            self._log("MO cube 生成失败")

    # ══════════════════════════════════════════════════════════════════
    #  等值面渲染 (ESP / MO / Cub)
    # ══════════════════════════════════════════════════════════════════

    def _on_iso_render(self, tab_kwargs, tab_idx):
        try:
            self._status(tr("等值面预览渲染中..."))
            QApplication.processEvents()
            result = self._iso_do_render(tab_kwargs, tab_idx)
            tmp = os.path.join(tempfile.gettempdir(), "iso_xyzr_preview.png")
            from xyzrender.export import svg_to_png
            svg_to_png(result._svg, tmp, size=self._structure_tab._size_combo.currentText())
            self._show_preview(tmp)
            self._status(tr("等值面预览完成"))
        except Exception as e:
            QMessageBox.critical(self, tr("渲染失败"), str(e))

    def _on_iso_export_png(self, tab_kwargs, tab_idx):
        path, _ = QFileDialog.getSaveFileName(self, tr("保存等值面 PNG"), "", tr("PNG (*.png)"))
        if not path:
            return
        self._status(tr("等值面渲染中...")); QApplication.processEvents()
        try:
            result = self._iso_do_render(tab_kwargs, tab_idx)
            from xyzrender.export import svg_to_png
            svg_to_png(result._svg, path, size=self._structure_tab._size_combo.currentText())
            self._show_preview(path)
            self._status(tr("已保存: {}").format(os.path.basename(path)))
        except Exception as e:
            QMessageBox.critical(self, tr("渲染失败"), str(e))

    def _on_iso_export_svg(self, tab_kwargs, tab_idx):
        path, _ = QFileDialog.getSaveFileName(self, tr("保存等值面 SVG"), "", tr("SVG (*.svg)"))
        if not path:
            return
        self._status(tr("等值面渲染中...")); QApplication.processEvents()
        try:
            result = self._iso_do_render(tab_kwargs, tab_idx)
            with open(path, "w", encoding="utf-8") as f:
                f.write(result._svg)
            self._status(tr("已保存: {}").format(os.path.basename(path)))
        except Exception as e:
            QMessageBox.critical(self, tr("渲染失败"), str(e))

    def _on_iso_export_gif(self, tab_kwargs, tab_idx):
        path, _ = QFileDialog.getSaveFileName(self, tr("保存等值面 GIF"), "", "GIF (*.gif)")
        if not path:
            return
        self._do_iso_gif(path, tab_kwargs, tab_idx)

    def _on_iso_preview_gif(self, tab_kwargs, tab_idx):
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as f:
            path = f.name
        self._do_iso_gif(path, tab_kwargs, tab_idx)

    def _do_iso_gif(self, path, tab_kwargs, tab_idx):
        axis = tab_kwargs.pop("gif_rot", "Y").lower()
        gif_fps = tab_kwargs.pop("gif_fps", 10)
        rot_frames = tab_kwargs.pop("rot_frames", 120)
        self._status(f"GIF 渲染中 (绕{axis}轴)..."); QApplication.processEvents()
        try:
            cube_path, kwargs = self._iso_build_kwargs(tab_kwargs, tab_idx)
            if not cube_path:
                QMessageBox.warning(self, tr("提示"), tr("请先加载或生成 cube 文件"))
                return
            cfg = self._build_gif_config(kwargs)
            for k in {"esp", "cmap_palette", "cbar", "cmap_range"} | self._GIF_DROP:
                kwargs.pop(k, None)
            kwargs.setdefault("canvas_size", 400)
            mol = load(cube_path)
            mol = rotate_copy_from_quat(mol, self.canvas._rot_q)
            render_gif(mol, gif_rot=axis, gif_fps=gif_fps, rot_frames=rot_frames,
                       output=path, config=cfg, **kwargs)
            self._status(tr("已保存: {}").format(os.path.basename(path)))
            self._show_preview_gif(path)
        except Exception as e:
            QMessageBox.critical(self, tr("渲染失败"), str(e))

    def _iso_build_kwargs(self, tab_kwargs, tab_idx):
        cube_path = self._iso_cube_paths[tab_idx]
        if tab_idx == 0 and not cube_path and self._esp_density_path:
            cube_path = self._esp_density_path
        if not cube_path:
            raise RuntimeError(tr("请先加载或生成 cube 文件"))

        mol = load(cube_path)

        kwargs = self._structure_tab.get_base_kwargs()
        hy_kw = self._resolve_hy_kwargs(self._structure_tab.get_hy_kwargs(), mol)
        kwargs.update(hy_kw)

        if tab_idx == 0:  # ESP
            kwargs["dens"] = True
            if self._esp_tab._chk_esp_color.isChecked() and self._esp_color_cube:
                kwargs["esp"] = self._esp_color_cube
                kwargs.pop("dens", None)
            kwargs["iso"] = tab_kwargs.get("iso", self._esp_tab._iso_esp.value() / 10000.0)
            kwargs["surface_style"] = tab_kwargs.get("surface_style", self._esp_tab._surf_esp.currentText())
            if "cmap_palette" in tab_kwargs: kwargs["cmap_palette"] = tab_kwargs["cmap_palette"]
            if "cbar" in tab_kwargs: kwargs["cbar"] = tab_kwargs["cbar"]
            if "cmap_range" in tab_kwargs: kwargs["cmap_range"] = tab_kwargs["cmap_range"]
        elif tab_idx == 1:  # MO
            mo_kw = self._mo_tab.get_kwargs()
            kwargs.update({k: v for k, v in mo_kw.items() if v is not None or k in ("mo",)})
        elif tab_idx == 2:  # Cub
            cube_kw = self._cube_tab.get_kwargs()
            kwargs.update({k: v for k, v in cube_kw.items() if v is not None or k in ("mo",)})

        # 虚线
        dashes = getattr(self.canvas, "custom_dash_lines", [])
        if dashes:
            ts_bonds = [(a1, a2) for a1, a2, _ in dashes]
            ts_color = dashes[0][2] if dashes else None
            kwargs["ts_bonds"] = ts_bonds
            if ts_color: kwargs["ts_color"] = ts_color
            kwargs["ts_dash"] = self._get_ts_dash_str()
            kwargs["ts_width"] = self._structure_tab.bond_editor.dash_width_ratio

        # 断键
        broken = getattr(self.canvas, "custom_broken_bonds", [])
        if broken:
            kwargs["unbond"] = [f"{a1}-{a2}" for a1, a2 in broken]

        if self._structure_tab._chk_transparent.isChecked():
            kwargs["transparent"] = True

        return cube_path, self._apply_color_overrides(kwargs)

    def _iso_do_render(self, tab_kwargs, tab_idx):
        cube_path, kwargs = self._iso_build_kwargs(tab_kwargs, tab_idx)
        mol = load(cube_path)
        mol = rotate_copy_from_quat(mol, self.canvas._rot_q)
        return render(mol, **kwargs)

    # ══════════════════════════════════════════════════════════════════
    #  结构 Tab 片段选择
    # ══════════════════════════════════════════════════════════════════

    def _on_frag_mode_changed(self, frag_id: int):
        st = self._structure_tab
        # 切换模式：如果已经是当前模式则关闭，否则开启
        if st._frag_mode == frag_id:
            st._set_frag_mode(0)
            self.canvas._frag_pick_target = 0
        else:
            self.canvas._frag_pick_target = frag_id
            st._set_frag_mode(frag_id)

    def _on_canvas_atom_clicked(self, atom_idx: int):
        """画布单击原子 → Shift=片段1, Ctrl=片段2, 否则按按钮。"""
        mods = QApplication.keyboardModifiers()
        if mods & Qt.ShiftModifier:
            target = 1
        elif mods & Qt.AltModifier:
            target = 2
        else:
            target = self.canvas._frag_pick_target
        if target == 0:
            return
        if target == 1:
            self.canvas.frag1_atoms.add(atom_idx)
        elif target == 2:
            self.canvas.frag2_atoms.add(atom_idx)
        self._sync_frag_fields_from_canvas()
        self.canvas.repaint()

    def _on_clear_structure_frags(self):
        st = self._structure_tab
        st._clear_fragments()
        self.canvas._frag_pick_target = 0
        self.canvas.frag1_atoms.clear()
        self.canvas.frag2_atoms.clear()
        self.canvas.repaint()

    # ══════════════════════════════════════════════════════════════════
    #  IGMH
    # ══════════════════════════════════════════════════════════════════

    def _on_canvas_box_select(self, atom_indices):
        mods = QApplication.keyboardModifiers()
        if mods & Qt.ShiftModifier:
            target = 1
        elif mods & Qt.AltModifier:
            target = 2
        else:
            target = self.canvas._frag_pick_target
        atoms_set = self.canvas.frag1_atoms if target == 1 else self.canvas.frag2_atoms
        for idx in atom_indices:
            atoms_set.add(idx)
        self._sync_frag_fields_from_canvas()
        self.canvas.repaint()

    def _on_pick_target(self, target, checked):
        if checked:
            self.canvas._frag_pick_target = target
            if target == 1:
                self._igmh_tab._btn_pick_frag2.setChecked(False)
            else:
                self._igmh_tab._btn_pick_frag1.setChecked(False)

    def _on_clear_frags(self):
        self.canvas.frag1_atoms.clear()
        self.canvas.frag2_atoms.clear()
        self._igmh_tab._igmh_frag1.clear()
        self._igmh_tab._igmh_frag2.clear()
        self.canvas.repaint()

    def _sync_frag_fields_from_canvas(self):
        f1 = _indices_to_text(self.canvas.frag1_atoms)
        f2 = _indices_to_text(self.canvas.frag2_atoms)
        self._igmh_tab._igmh_frag1.setText(f1)
        self._igmh_tab._igmh_frag2.setText(f2)
        # 同步到结构 Tab 的片段输入框
        self._structure_tab._frag1_edit.setText(f1)
        self._structure_tab._frag2_edit.setText(f2)
        self._structure_tab._frag1_indices = set(self.canvas.frag1_atoms)
        self._structure_tab._frag2_indices = set(self.canvas.frag2_atoms)

    def _run_igmh(self):
        mw_exe = self._mw_edit.text().strip()
        fch = self.file_path
        if not mw_exe:
            QMessageBox.critical(self, tr("错误"), tr("请先设置 Multiwfn 路径"))
            return
        if not fch:
            QMessageBox.critical(self, tr("错误"), tr("请先选择 fchk 文件"))
            return
        ext = os.path.splitext(fch)[1].lower()
        if ext not in (".fchk", ".fch"):
            QMessageBox.critical(self, tr("错误"), tr("IGMH 分析需要 fchk 文件"))
            return

        frag1 = self._igmh_tab._igmh_frag1.text().strip()
        frag2 = self._igmh_tab._igmh_frag2.text().strip()
        if not frag1:
            QMessageBox.critical(self, tr("错误"), tr("请输入片段1"))
            return
        if not frag2:
            QMessageBox.critical(self, tr("错误"), tr("请输入片段2"))
            return

        grid = self._igmh_tab._igmh_grid.currentIndex() + 1
        self._status(tr("IGMH 分析中..."))
        self._log(f"IGMH: frag1={frag1}, frag2={frag2}, grid={grid}")

        self._igmh_worker = IgmhWorker(mw_exe, fch, frag1, frag2, grid)
        self._igmh_worker.status_signal.connect(self._log)
        self._igmh_worker.progress_signal.connect(lambda v: self._status(tr("IGMH 分析中... {}%").format(v)))
        self._igmh_worker.finished_signal.connect(self._on_igmh_done)
        self._igmh_worker.start()

    def _on_igmh_done(self, ok, work_dir):
        if ok:
            self._igmh_work_dir = work_dir
            self._igmh_sl2r = os.path.join(work_dir, "sl2r.cub")
            self._igmh_dg = os.path.join(work_dir, "dg_inter.cub")
            self._log(f"IGMH 完成，输出目录: {work_dir}")
            self._igmh_tab.set_buttons_enabled(True)
            self._status(tr("IGMH 分析完成 — 可点击「NCI 预览」或「NCI 出图」"))
        else:
            self._log("IGMH 分析失败")
            self._status(tr("IGMH 分析失败"))

    def _on_igmh_render(self, tab_kwargs):
        if not self._igmh_sl2r or not self._igmh_dg:
            QMessageBox.warning(self, tr("提示"), tr("请先运行 IGMH 分析"))
            return
        self._status(tr("NCI 表面预览渲染中...")); QApplication.processEvents()
        try:
            result = self._do_igmh_render(tab_kwargs)
            tmp = os.path.join(tempfile.gettempdir(), "igmh_nci_preview.png")
            from xyzrender.export import svg_to_png
            svg_to_png(result._svg, tmp, size=self._structure_tab._size_combo.currentText())
            self._show_preview(tmp)
            self._status(tr("NCI 表面预览完成"))
        except Exception as e:
            QMessageBox.critical(self, tr("NCI 渲染失败"), str(e))

    def _on_igmh_export_render(self, tab_kwargs):
        if not self._igmh_sl2r or not self._igmh_dg:
            QMessageBox.warning(self, tr("提示"), tr("请先运行 IGMH 分析"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("保存 NCI 表面 PNG"), os.path.dirname(self.file_path) if self.file_path else "", tr("PNG (*.png);;SVG (*.svg)"))
        if not path:
            return
        self._status(tr("NCI 表面渲染中...")); QApplication.processEvents()
        try:
            result = self._do_igmh_render(tab_kwargs)
            ext = os.path.splitext(path)[1].lower()
            if ext == ".svg":
                with open(path, "w", encoding="utf-8") as f:
                    f.write(result._svg)
            else:
                from xyzrender.export import svg_to_png
                svg_to_png(result._svg, path, size=self._structure_tab._size_combo.currentText())
                self._show_preview(path)
            self._status(tr("已保存: {}").format(os.path.basename(path)))
        except Exception as e:
            QMessageBox.critical(self, tr("NCI 渲染失败"), str(e))

    def _on_igmh_export_svg(self, tab_kwargs):
        if not self._igmh_sl2r or not self._igmh_dg:
            QMessageBox.warning(self, tr("提示"), tr("请先运行 IGMH 分析"))
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("保存 NCI 表面 SVG"), os.path.dirname(self.file_path) if self.file_path else "", tr("SVG (*.svg)"))
        if not path:
            return
        self._status(tr("NCI SVG 渲染中...")); QApplication.processEvents()
        try:
            result = self._do_igmh_render(tab_kwargs)
            with open(path, "w", encoding="utf-8") as f:
                f.write(result._svg)
            self._status(tr("已保存: {}").format(os.path.basename(path)))
        except Exception as e:
            QMessageBox.critical(self, tr("NCI 渲染失败"), str(e))

    def _do_igmh_render(self, tab_kwargs):
        mol = load(self._igmh_sl2r)
        mol = rotate_copy_from_quat(mol, self.canvas._rot_q)
        kwargs = self._structure_tab.get_base_kwargs()
        hy_kw = self._resolve_hy_kwargs(self._structure_tab.get_hy_kwargs(), mol)
        kwargs.update(hy_kw)
        kwargs["nci"] = self._igmh_dg
        kwargs["iso"] = tab_kwargs.get("iso", self._igmh_tab._igmh_iso.value() / 1000.0)
        kwargs["nci_mode"] = tab_kwargs.get("nci_mode", "avg")
        kwargs["surface_style"] = tab_kwargs.get("surface_style", "solid")
        dashes = getattr(self.canvas, "custom_dash_lines", [])
        if dashes:
            ts_bonds = [(a1, a2) for a1, a2, _ in dashes]
            kwargs["ts_bonds"] = ts_bonds
            if dashes and dashes[0][2]: kwargs["ts_color"] = dashes[0][2]
            kwargs["ts_dash"] = self._get_ts_dash_str()
            kwargs["ts_width"] = self._structure_tab.bond_editor.dash_width_ratio
        broken = getattr(self.canvas, "custom_broken_bonds", [])
        if broken:
            kwargs["unbond"] = [f"{a1}-{a2}" for a1, a2 in broken]
        if self._structure_tab._chk_transparent.isChecked():
            kwargs["transparent"] = True
        return render(mol, **self._apply_color_overrides(kwargs))

    # ══════════════════════════════════════════════════════════════════
    #  电荷
    # ══════════════════════════════════════════════════════════════════

    def _on_charge_type_changed(self, charge_type):
        """切换电荷类型时，若已缓存则自动刷新范围值。"""
        if charge_type in self._charge_cache:
            charges = self._charge_cache[charge_type]
            vals = [c[2] for c in charges]
            max_abs = max(abs(v) for v in vals) if vals else 0.5
            ct = self._charge_tab
            ct.rmin.setText(f"{-max_abs:.3f}")
            ct.rmax.setText(f"{max_abs:.3f}")
            ct.populate_table(charges, charge_type)

    def _run_charge_calc(self):
        mw_exe = self._mw_edit.text().strip()
        cur_fch = self._current_fchk_path
        if not cur_fch or not os.path.isfile(cur_fch):
            QMessageBox.critical(self, tr("错误"), tr("请先浏览并载入 fchk 文件"))
            return

        charge_type = self._charge_tab.charge_type
        if charge_type in self._charge_cache:
            self._log(f"使用缓存: {charge_type}")
            charges = self._charge_cache[charge_type]
            self._charge_tab.set_status(f"已缓存: {len(charges)} 个原子")
            self._charge_tab.populate_table(charges, charge_type)
            self._charge_tab.set_buttons_enabled(True)
            self._gen_cmap_file(charges)
            return

        self._charge_tab.set_status("计算中...")
        self._charge_tab.progress_bar.setVisible(True); self._charge_tab.progress_bar.setValue(0)

        self._charge_worker = ChargeWorker(mw_exe, cur_fch, charge_type)
        self._charge_worker.status_signal.connect(self._log)
        self._charge_worker.progress_signal.connect(self._charge_tab.progress_bar.setValue)
        self._charge_worker.finished_signal.connect(self._on_charge_done)
        self._charge_worker.start()

    def _on_charge_done(self, charge_type, output_text):
        self._charge_tab.progress_bar.setVisible(False)

        if not output_text:
            self._charge_tab.set_status("计算失败")
            return

        charges = parse_charge_output(output_text, charge_type)
        if not charges:
            self._charge_tab.set_status("解析失败: 未找到电荷数据")
            return

        self._charge_cache[charge_type] = charges
        vals = [c[2] for c in charges]
        max_abs = max(abs(v) for v in vals) if vals else 0.5
        self._charge_tab.rmin.setText(f"{-max_abs:.3f}")
        self._charge_tab.rmax.setText(f"{max_abs:.3f}")
        self._charge_tab.set_status(f"完成: {len(charges)} 个原子, 范围 [{min(vals):.3f}, {max(vals):.3f}]")
        self._log(f"{charge_type}: {len(charges)} 个原子")

        self._charge_tab.populate_table(charges, charge_type)
        self._gen_cmap_file(charges)
        self._charge_tab.set_buttons_enabled(True)

    def _gen_cmap_file(self, charges):
        if not charges:
            return
        cmap_dir = os.path.join(os.path.dirname(__file__), "_charge_cmaps")
        os.makedirs(cmap_dir, exist_ok=True)
        cmap_path = os.path.join(cmap_dir, f"charges_{self._charge_tab.charge_type}.txt")
        with open(cmap_path, "w", encoding="utf-8") as f:
            for idx, elem, val in charges:
                f.write(f"{idx}  {val:.8f}\n")
        self._charge_cmap_path = cmap_path
        self._log(f"cmap 文件: {cmap_path}")

    def _on_charge_peek(self, tab_kwargs):
        if not self._charge_cmap_path:
            return
        try:
            result = self._do_charge_render(tab_kwargs)
            if result and result._svg:
                tmp = os.path.join(tempfile.gettempdir(), "xyzr_charge_preview.png")
                from xyzrender.export import svg_to_png
                svg_to_png(result._svg, tmp, size=self._structure_tab._size_combo.currentText())
                self._show_preview(tmp)
        except Exception as e:
            self._log(f"电荷预览失败: {e}")

    def _on_charge_render(self, tab_kwargs):
        if not self._charge_cmap_path:
            return
        try:
            result = self._do_charge_render(tab_kwargs)
            if result and result._svg:
                png_path = os.path.join(os.path.dirname(self._charge_cmap_path),
                                        f"charges_{self._charge_tab.charge_type}.png")
                from xyzrender.export import svg_to_png
                svg_to_png(result._svg, png_path, size=self._structure_tab._size_combo.currentText())
                self._log(f"电荷出图: {png_path}")
        except Exception as e:
            self._log(f"电荷出图失败: {e}")

    def _on_charge_export_svg(self, tab_kwargs):
        if not self._charge_cmap_path:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存电荷 SVG", os.path.dirname(self._charge_cmap_path) if self._charge_cmap_path else "", "SVG (*.svg)")
        if not path:
            return
        try:
            result = self._do_charge_render(tab_kwargs)
            if result and result._svg:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(result._svg)
                self._log(f"电荷 SVG 已保存: {path}")
        except Exception as e:
            self._log(f"电荷 SVG 失败: {e}")

    def _do_charge_render(self, tab_kwargs):
        mol = self.molecule
        if mol is None:
            return None
        mol = rotate_copy_from_quat(mol, self.canvas._rot_q)
        kwargs = self._structure_tab.get_base_kwargs()
        hy_kw = self._resolve_hy_kwargs(self._structure_tab.get_hy_kwargs(), mol)
        kwargs.update(hy_kw)
        kwargs["cmap"] = self._charge_cmap_path
        kwargs["atom_scale"] = self._structure_tab._atom_scale.value() / 10.0
        kwargs["bond_width"] = self._structure_tab._bond_width.value()
        for k in ("cmap_range", "cmap_palette", "cbar"):
            if k in tab_kwargs:
                kwargs[k] = tab_kwargs[k]
        dashes = getattr(self.canvas, "custom_dash_lines", [])
        if dashes:
            ts_bonds = [(a1, a2) for a1, a2, _ in dashes]
            kwargs["ts_bonds"] = ts_bonds
            if dashes[0][2]: kwargs["ts_color"] = dashes[0][2]
            kwargs["ts_dash"] = self._get_ts_dash_str()
            kwargs["ts_width"] = self._structure_tab.bond_editor.dash_width_ratio
        broken = getattr(self.canvas, "custom_broken_bonds", [])
        if broken:
            kwargs["unbond"] = [f"{a1}-{a2}" for a1, a2 in broken]
        if self._structure_tab._chk_transparent.isChecked():
            kwargs["transparent"] = True
        return render(mol, **self._apply_color_overrides(kwargs))

    # ══════════════════════════════════════════════════════════════════
    #  键编辑状态
    # ══════════════════════════════════════════════════════════════════

    def _get_ts_dash_str(self) -> str:
        """返回 ts_dash 参数：圆点模式用极小 length，线段模式用正常值。"""
        be = self._structure_tab.bond_editor
        if be.dash_style_combo.currentIndex() == 1:  # 圆点
            return f"0.1,{be.dash_gap_ratio:.1f}"
        return f"{be.dash_len_ratio:.1f},{be.dash_gap_ratio:.1f}"

    def _update_dash_status(self):
        be = self._structure_tab.bond_editor
        if not be.chk_dash_mode.isChecked():
            be.lbl_dash_status.setText("")
        elif self.canvas._dash_bond_atom1 is not None:
            n = len(self.canvas.custom_dash_lines)
            be.lbl_dash_status.setText(f"已选原子 {self.canvas._dash_bond_atom1}，再选另一个画虚线（{n} 条）")
        else:
            n = len(self.canvas.custom_dash_lines)
            be.lbl_dash_status.setText(f"已画 {n} 条虚线，在画布上点击两个原子添加")

    def _update_break_status(self):
        be = self._structure_tab.bond_editor
        if not be.chk_break_mode.isChecked():
            be.lbl_break_status.setText("")
        elif self.canvas._break_bond_atom1 is not None:
            n = len(self.canvas.custom_broken_bonds)
            be.lbl_break_status.setText(f"已选原子 {self.canvas._break_bond_atom1}，再选另一个断键（{n} 条）")
        else:
            n = len(self.canvas.custom_broken_bonds)
            be.lbl_break_status.setText(f"已断 {n} 条键，在画布上点击两个原子断键")

    def _sync_dash_color(self):
        """将键编辑器的虚线颜色同步到 canvas：更新所有已有虚线和新虚线的默认颜色。"""
        be = self._structure_tab.bond_editor
        hex_color = be.dash_color_hex
        self.canvas.dash_color_hex = hex_color
        # 重新着色所有已有虚线
        for i, (a1, a2, _) in enumerate(self.canvas.custom_dash_lines):
            self.canvas.custom_dash_lines[i] = (a1, a2, hex_color)
