"""XYZRender-Viewer 主窗口 — 布局编排 + 文件加载 + 渲染出口。"""

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
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QColor

from molcanvas.canvas import MolCanvas
from molcanvas.styles import STYLE_PRESETS
from molcanvas.atoms import ATOM_RADII, REVERSE_SYMBOLS, ELEMENT_SYMBOLS

from xyzrender import load, render
from xyz_render_bridge import rotate_copy, rotate_copy_from_quat

from .config import LIGHT_QSS, _load_mw_config, _save_mw_config, DEFAULT_MULTIWFN
from .parsing import (
    parse_fchk_mo_info, parse_charge_output,
    _parse_xyz_local, _parse_fchk_local, _write_atoms_to_xyz, _indices_to_text,
)
from .workers import MultiwfnWorker, MOCubeWorker, IgmhWorker, ChargeWorker
from .tabs import StructureTab, ESPTab, MOTab, IGMHTab, ChargeTab, CubeTab


class XYZRenderViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XYZRender-Viewer — 分子结构 + 等值面可视化")
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.80), int(screen.height() * 0.80))

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

        self._mw_config = _load_mw_config()
        self._current_fchk_path = None

        self._build_ui()
        self._apply_style()
        self._status("就绪 — 打开 XYZ / cube / log / fchk 文件 | Tab 1: 结构 | Tab 2: 等值面")

    def _apply_style(self):
        self.setStyleSheet(LIGHT_QSS)

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

        gb_canvas = QGroupBox("3D 画布")
        cv = QVBoxLayout(gb_canvas); cv.setContentsMargins(4, 4, 4, 4)
        self.canvas = MolCanvas()
        self.canvas.setMinimumSize(200, 150)
        self.canvas.box_selected.connect(self._on_canvas_box_select)
        cv.addWidget(self.canvas)
        left_splitter.addWidget(gb_canvas)

        gb_preview = QGroupBox("渲染预览")
        pv = QVBoxLayout(gb_preview); pv.setContentsMargins(4, 4, 4, 4)
        self._preview_label = QLabel()
        self._preview_label.setAlignment(Qt.AlignCenter)
        self._preview_label.setMinimumHeight(60)
        self._preview_label.setStyleSheet("background:#ffffff; border:1px solid #ccc;")
        self._preview_label.setText("(等待渲染...)")
        pv.addWidget(self._preview_label)
        left_splitter.addWidget(gb_preview)
        left_splitter.setSizes([400, 250])
        left_splitter.setChildrenCollapsible(False)
        left.addWidget(left_splitter, stretch=1)

        style_bar = QHBoxLayout()
        style_bar.addWidget(QLabel("样式:"))
        self._style_combo = QComboBox()
        self._style_combo.addItems(STYLE_PRESETS.keys())
        self._style_combo.currentTextChanged.connect(lambda k: self.canvas.set_style(k))
        self._style_combo.setCurrentText("HoukMol")
        style_bar.addWidget(self._style_combo)
        style_bar.addWidget(QLabel(" 标签:"))
        self._label_combo = QComboBox()
        self._label_combo.addItems(["隐藏", "编号", "元素"])
        self._label_combo.setCurrentIndex(0)
        self._label_combo.currentIndexChanged.connect(
            lambda idx: (setattr(self.canvas, 'label_mode', [2, 1, 0][idx]), self.canvas.update()))
        style_bar.addWidget(self._label_combo)
        style_bar.addStretch()
        style_bar.addWidget(QLabel("左键旋转 | 右键平移 | 滚轮缩放"))
        left.addLayout(style_bar)

        splitter.addWidget(left_widget)

        # ── 右侧: 共用文件区 + Tab 面板 ──
        right_widget = QWidget()
        right = QVBoxLayout(right_widget)
        right.setContentsMargins(4, 8, 8, 8)
        right.setSpacing(4)

        # 文件加载
        gb_file = QGroupBox("文件")
        fl = QVBoxLayout(gb_file)
        fh = QHBoxLayout()
        self._file_edit = QLineEdit(); self._file_edit.setReadOnly(True); self._file_edit.setPlaceholderText("(未加载)")
        btn_open = QPushButton("浏览"); btn_open.setMaximumWidth(120); btn_open.clicked.connect(self._open_file)
        fh.addWidget(self._file_edit); fh.addWidget(btn_open)
        fl.addLayout(fh)
        mwh = QHBoxLayout()
        mwh.addWidget(QLabel("Multiwfn:"))
        self._mw_edit = QLineEdit(self._mw_config["multiwfn"])
        mw_btn = QPushButton("浏览..."); mw_btn.clicked.connect(self._browse_mw)
        mwh.addWidget(self._mw_edit); mwh.addWidget(mw_btn)
        fl.addLayout(mwh)
        right.addWidget(gb_file)

        # ── 创建各 Tab ──
        self._tabs = QTabWidget()
        right.addWidget(self._tabs)

        self._structure_tab = StructureTab()
        self._esp_tab = ESPTab()
        self._mo_tab = MOTab()
        self._igmh_tab = IGMHTab()
        self._charge_tab = ChargeTab()
        self._cube_tab = CubeTab()

        self._tabs.addTab(self._structure_tab, "结构")
        self._tabs.addTab(self._esp_tab, "ESP")
        self._tabs.addTab(self._mo_tab, "MO")
        self._tabs.addTab(self._igmh_tab, "IGMH")
        self._tabs.addTab(self._charge_tab, "电荷")
        self._tabs.addTab(self._cube_tab, "Cub 文件")

        # 运行日志
        tab_log = QWidget()
        logl = QVBoxLayout(tab_log); logl.setContentsMargins(0, 0, 0, 0)
        self._log_view = QPlainTextEdit(); self._log_view.setReadOnly(True); self._log_view.setMaximumBlockCount(500)
        logl.addWidget(self._log_view)
        self._tabs.addTab(tab_log, "运行日志")

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

        # ESP Tab
        et = self._esp_tab
        et.gen_esp_requested.connect(self._gen_esp_cubes)
        et.quick_peek_requested.connect(lambda kw: self._on_iso_render(kw, 0))
        et.export_png_requested.connect(lambda kw: self._on_iso_export_png(kw, 0))
        et.export_svg_requested.connect(lambda kw: self._on_iso_export_svg(kw, 0))

        # MO Tab
        mt = self._mo_tab
        mt.mo_selected_signal.connect(self._on_mo_selected)
        mt.quick_peek_requested.connect(lambda kw: self._on_iso_render(kw, 1))
        mt.export_png_requested.connect(lambda kw: self._on_iso_export_png(kw, 1))
        mt.export_svg_requested.connect(lambda kw: self._on_iso_export_svg(kw, 1))

        # IGMH Tab
        it = self._igmh_tab
        it.run_igmh_requested.connect(self._run_igmh)
        it.quick_peek_requested.connect(self._on_igmh_render)
        it.export_png_requested.connect(self._on_igmh_export_render)

        # 电荷 Tab
        ct = self._charge_tab
        ct.calc_requested.connect(self._run_charge_calc)
        ct.charge_type_changed.connect(self._on_charge_type_changed)
        ct.quick_peek_requested.connect(self._on_charge_peek)
        ct.export_png_requested.connect(self._on_charge_render)

        # Cub Tab
        cbt = self._cube_tab
        cbt.quick_peek_requested.connect(lambda kw: self._on_iso_render(kw, 2))
        cbt.export_png_requested.connect(lambda kw: self._on_iso_export_png(kw, 2))

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
            lambda t: (setattr(self.canvas, 'dash_style', {'线段': 'dash', '圆点': 'dots'}.get(t, 'dash')), self.canvas.update()))
        be.dash_changed.connect(lambda: (
            setattr(self.canvas, 'dash_len_ratio', be.dash_len_ratio * _DASH_SCALE),
            setattr(self.canvas, 'dash_gap_ratio', be.dash_gap_ratio * _DASH_SCALE),
            setattr(self.canvas, 'dash_width_ratio', be.dash_width_ratio * _DASH_SCALE),
            self._sync_dash_color(),
            self.canvas.update()))
        be._btn_undo.clicked.connect(lambda: (self.canvas.undo_last_dash_line(), self._update_dash_status()))
        be._btn_clear.clicked.connect(lambda: (self.canvas.clear_dash_lines(), self._update_dash_status()))

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
        path, _ = QFileDialog.getOpenFileName(self, "选择 Multiwfn.exe", "", "Multiwfn.exe (Multiwfn.exe);;所有文件 (*.*)")
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
            self, "打开分子结构文件", "",
            "所有支持格式 (*.xyz *.cube *.cub *.fchk *.fch *.mol *.sdf *.mol2 *.pdb *.log *.out);;"
            "XYZ (*.xyz);;Cube (*.cube *.cub);;fchk (*.fchk *.fch);;"
            "Gaussian Log (*.log *.out);;所有文件 (*.*)")
        if not path:
            return
        try:
            self._load_file(path)
        except Exception as e:
            QMessageBox.critical(self, "加载失败", str(e))

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
        self._status(f"加载中: {name} ...")
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
        self._status(f"已加载 {name} — 左键旋转视角, 调好后点「出图」")

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

    def _get_structure_kwargs(self):
        st = self._structure_tab
        kwargs = st.get_base_kwargs()
        kwargs.update(st.get_hy_kwargs())
        kwargs.update(st.get_vdw_kwargs())
        # 虚线参数
        dashes = getattr(self.canvas, "custom_dash_lines", [])
        if dashes:
            ts_bonds = [(a1, a2) for a1, a2, _ in dashes]
            ts_color = dashes[0][2] if dashes else None
            kwargs["ts_bonds"] = ts_bonds
            if ts_color:
                kwargs["ts_color"] = ts_color
            kwargs["ts_dash"] = f"{self._structure_tab.bond_editor.dash_len_ratio:.1f},{self._structure_tab.bond_editor.dash_gap_ratio:.1f}"
            kwargs["ts_width"] = self._structure_tab.bond_editor.dash_width_ratio
        return kwargs

    def _do_structure_render(self):
        mol = rotate_copy_from_quat(self.molecule, self.canvas._rot_q)
        return render(mol, **self._get_structure_kwargs())

    def _on_structure_render(self, kwargs):
        if self.molecule is None:
            self._status("请先打开文件")
            return
        self._status("快速预览渲染中...")
        QApplication.processEvents()
        try:
            result = self._do_structure_render()
            tmp = os.path.join(tempfile.gettempdir(), "xyzr_quick_preview.png")
            from xyzrender.export import svg_to_png
            svg_to_png(result._svg, tmp, size=self._structure_tab._size_combo.currentText())
            self._show_preview(tmp)
            self._status("预览完成")
        except Exception as e:
            QMessageBox.critical(self, "渲染失败", str(e))

    def _on_structure_export_png(self, kwargs):
        if self.molecule is None:
            QMessageBox.information(self, "提示", "请先打开文件")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存 PNG", "", "PNG (*.png);;SVG (*.svg)")
        if not path:
            return
        self._status("渲染中..."); QApplication.processEvents()
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
            self._status(f"已保存: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "渲染失败", str(e))

    def _on_structure_export_svg(self, kwargs):
        if self.molecule is None:
            QMessageBox.information(self, "提示", "请先打开文件")
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存 SVG", "", "SVG (*.svg)")
        if not path:
            return
        self._status("渲染中..."); QApplication.processEvents()
        try:
            result = self._do_structure_render()
            with open(path, "w", encoding="utf-8") as f:
                f.write(result._svg)
            self._status(f"已保存: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "渲染失败", str(e))

    def _show_preview(self, png_path):
        pix = QPixmap(png_path)
        if pix.isNull():
            return
        w = self._preview_label.width()
        h = self._preview_label.height()
        if w > 10 and h > 10:
            pix = pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._preview_label.setPixmap(pix)

    # ══════════════════════════════════════════════════════════════════
    #  ESP 生成
    # ══════════════════════════════════════════════════════════════════

    def _gen_esp_cubes(self):
        mw_exe = self._mw_edit.text().strip()
        fch = self.file_path

        if not mw_exe:
            QMessageBox.critical(self, "错误", "请先设置 Multiwfn 路径")
            return
        if not fch:
            QMessageBox.critical(self, "错误", "请先选择 fchk 文件")
            return
        ext = os.path.splitext(fch)[1].lower()
        if ext not in (".fchk", ".fch"):
            QMessageBox.critical(self, "错误", "ESP 生成需要 fchk 文件")
            return

        fch_dir = os.path.dirname(os.path.abspath(fch))
        fch_name = os.path.splitext(os.path.basename(fch))[0]
        work_dir = os.path.join(fch_dir, f"_esp_{fch_name}")
        os.makedirs(work_dir, exist_ok=True)

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
                self._status("ESP cube 生成完毕 — 点「快速预览」查看")
            else:
                self._log("Multiwfn 完成但缺少输出文件")
                self._status("Multiwfn 完成但缺少输出文件")
        else:
            self._log("Multiwfn 执行失败")
            self._status("Multiwfn 执行失败")

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
            mo._mo_tabs.setTabText(0, "α 轨道")
            mo._mo_table_beta = mo._make_mo_table()
            mo._mo_tabs.addTab(mo._mo_table_beta, "β 轨道")
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
            mo._mo_tabs.setTabText(0, "轨道")

        self._log(f"轨道解析完成: {len(alpha_e)} MOs, HOMO={homo}, LUMO={lumo}, 开壳层={is_open}")

    def _fill_mo_rows(self, table, rows, spin):
        table.setRowCount(len(rows))
        for r, (orb, energy, ev, occ, tag) in enumerate(rows):
            it0 = QTableWidgetItem(str(orb)); it0.setTextAlignment(Qt.AlignCenter)
            if spin == "β": it0.setForeground(QColor("#E74C3C"))
            table.setItem(r, 0, it0)
            it1 = QTableWidgetItem(f"{energy:.6f}"); it1.setTextAlignment(Qt.AlignCenter)
            table.setItem(r, 1, it1)
            it2 = QTableWidgetItem(f"{ev:.4f}"); it2.setTextAlignment(Qt.AlignCenter)
            table.setItem(r, 2, it2)
            it3 = QTableWidgetItem(f"{occ:.1f}"); it3.setTextAlignment(Qt.AlignCenter)
            if occ > 0: it3.setBackground(QColor("#E8F5E9"))
            table.setItem(r, 3, it3)
            it4 = QTableWidgetItem(tag); it4.setTextAlignment(Qt.AlignCenter)
            if "HOMO" in tag:
                it4.setBackground(QColor("#FFF3E0")); it4.setFont(QFont("", -1, QFont.Bold))
            elif "LUMO" in tag:
                it4.setBackground(QColor("#E3F2FD")); it4.setFont(QFont("", -1, QFont.Bold))
            table.setItem(r, 4, it4)

    def _on_mo_selected(self, orbital):
        self._mo_selected = orbital
        self._log(f"选中轨道: {orbital}")
        self._gen_mo_cube()

    def _gen_mo_cube(self):
        if not self._mo_selected:
            QMessageBox.warning(self, "提示", "请先在轨道表格中双击选择轨道")
            return
        fch_path = self.file_path
        if not fch_path or not os.path.isfile(fch_path):
            QMessageBox.warning(self, "提示", "请先打开 fchk 文件")
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
            self._status("等值面预览渲染中...")
            QApplication.processEvents()
            result = self._iso_do_render(tab_kwargs, tab_idx)
            tmp = os.path.join(tempfile.gettempdir(), "iso_xyzr_preview.png")
            from xyzrender.export import svg_to_png
            svg_to_png(result._svg, tmp, size=self._structure_tab._size_combo.currentText())
            self._show_preview(tmp)
            self._status("等值面预览完成")
        except Exception as e:
            QMessageBox.critical(self, "渲染失败", str(e))

    def _on_iso_export_png(self, tab_kwargs, tab_idx):
        path, _ = QFileDialog.getSaveFileName(self, "保存等值面 PNG", "", "PNG (*.png)")
        if not path:
            return
        self._status("等值面渲染中..."); QApplication.processEvents()
        try:
            result = self._iso_do_render(tab_kwargs, tab_idx)
            from xyzrender.export import svg_to_png
            svg_to_png(result._svg, path, size=self._structure_tab._size_combo.currentText())
            self._show_preview(path)
            self._status(f"已保存: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "渲染失败", str(e))

    def _on_iso_export_svg(self, tab_kwargs, tab_idx):
        path, _ = QFileDialog.getSaveFileName(self, "保存等值面 SVG", "", "SVG (*.svg)")
        if not path:
            return
        self._status("等值面渲染中..."); QApplication.processEvents()
        try:
            result = self._iso_do_render(tab_kwargs, tab_idx)
            with open(path, "w", encoding="utf-8") as f:
                f.write(result._svg)
            self._status(f"已保存: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "渲染失败", str(e))

    def _iso_do_render(self, tab_kwargs, tab_idx):
        cube_path = self._iso_cube_paths[tab_idx]
        if tab_idx == 0 and not cube_path and self._esp_density_path:
            cube_path = self._esp_density_path
        if not cube_path:
            raise RuntimeError("请先加载或生成 cube 文件")

        mol = load(cube_path)
        mol = rotate_copy_from_quat(mol, self.canvas._rot_q)

        kwargs = self._structure_tab.get_base_kwargs()
        kwargs.update(self._structure_tab.get_hy_kwargs())

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
            kwargs["ts_dash"] = f"{self._structure_tab.bond_editor.dash_len_ratio:.1f},{self._structure_tab.bond_editor.dash_gap_ratio:.1f}"
            kwargs["ts_width"] = self._structure_tab.bond_editor.dash_width_ratio

        return render(mol, **kwargs)

    # ══════════════════════════════════════════════════════════════════
    #  IGMH
    # ══════════════════════════════════════════════════════════════════

    def _on_canvas_box_select(self, atom_indices):
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

    def _run_igmh(self):
        mw_exe = self._mw_edit.text().strip()
        fch = self.file_path
        if not mw_exe:
            QMessageBox.critical(self, "错误", "请先设置 Multiwfn 路径")
            return
        if not fch:
            QMessageBox.critical(self, "错误", "请先选择 fchk 文件")
            return
        ext = os.path.splitext(fch)[1].lower()
        if ext not in (".fchk", ".fch"):
            QMessageBox.critical(self, "错误", "IGMH 分析需要 fchk 文件")
            return

        frag1 = self._igmh_tab._igmh_frag1.text().strip()
        frag2 = self._igmh_tab._igmh_frag2.text().strip()
        if not frag1:
            QMessageBox.critical(self, "错误", "请输入片段1")
            return
        if not frag2:
            QMessageBox.critical(self, "错误", "请输入片段2")
            return

        grid = self._igmh_tab._igmh_grid.currentIndex() + 1
        self._status("IGMH 分析中...")
        self._log(f"IGMH: frag1={frag1}, frag2={frag2}, grid={grid}")

        self._igmh_worker = IgmhWorker(mw_exe, fch, frag1, frag2, grid)
        self._igmh_worker.status_signal.connect(self._log)
        self._igmh_worker.progress_signal.connect(lambda v: self._status(f"IGMH 分析中... {v}%"))
        self._igmh_worker.finished_signal.connect(self._on_igmh_done)
        self._igmh_worker.start()

    def _on_igmh_done(self, ok, work_dir):
        if ok:
            self._igmh_work_dir = work_dir
            self._igmh_sl2r = os.path.join(work_dir, "sl2r.cub")
            self._igmh_dg = os.path.join(work_dir, "dg_inter.cub")
            self._log(f"IGMH 完成，输出目录: {work_dir}")
            self._igmh_tab.set_buttons_enabled(True)
            self._status("IGMH 分析完成 — 可点击「NCI 预览」或「NCI 出图」")
        else:
            self._log("IGMH 分析失败")
            self._status("IGMH 分析失败")

    def _on_igmh_render(self, tab_kwargs):
        if not self._igmh_sl2r or not self._igmh_dg:
            QMessageBox.warning(self, "提示", "请先运行 IGMH 分析")
            return
        self._status("NCI 表面预览渲染中..."); QApplication.processEvents()
        try:
            result = self._do_igmh_render(tab_kwargs)
            tmp = os.path.join(tempfile.gettempdir(), "igmh_nci_preview.png")
            from xyzrender.export import svg_to_png
            svg_to_png(result._svg, tmp, size=self._structure_tab._size_combo.currentText())
            self._show_preview(tmp)
            self._status("NCI 表面预览完成")
        except Exception as e:
            QMessageBox.critical(self, "NCI 渲染失败", str(e))

    def _on_igmh_export_render(self, tab_kwargs):
        if not self._igmh_sl2r or not self._igmh_dg:
            QMessageBox.warning(self, "提示", "请先运行 IGMH 分析")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 NCI 表面 PNG", os.path.dirname(self.file_path) if self.file_path else "", "PNG (*.png);;SVG (*.svg)")
        if not path:
            return
        self._status("NCI 表面渲染中..."); QApplication.processEvents()
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
            self._status(f"已保存: {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "NCI 渲染失败", str(e))

    def _do_igmh_render(self, tab_kwargs):
        mol = load(self._igmh_sl2r)
        mol = rotate_copy_from_quat(mol, self.canvas._rot_q)
        kwargs = self._structure_tab.get_base_kwargs()
        kwargs.update(self._structure_tab.get_hy_kwargs())
        kwargs["nci"] = self._igmh_dg
        kwargs["iso"] = tab_kwargs.get("iso", self._igmh_tab._igmh_iso.value() / 1000.0)
        kwargs["nci_mode"] = tab_kwargs.get("nci_mode", "avg")
        kwargs["surface_style"] = tab_kwargs.get("surface_style", "solid")
        dashes = getattr(self.canvas, "custom_dash_lines", [])
        if dashes:
            ts_bonds = [(a1, a2) for a1, a2, _ in dashes]
            kwargs["ts_bonds"] = ts_bonds
            if dashes and dashes[0][2]: kwargs["ts_color"] = dashes[0][2]
            kwargs["ts_dash"] = f"{self._structure_tab.bond_editor.dash_len_ratio:.1f},{self._structure_tab.bond_editor.dash_gap_ratio:.1f}"
            kwargs["ts_width"] = self._structure_tab.bond_editor.dash_width_ratio
        return render(mol, **kwargs)

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
            QMessageBox.critical(self, "错误", "请先浏览并载入 fchk 文件")
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

    def _do_charge_render(self, tab_kwargs):
        mol = self.molecule
        if mol is None:
            return None
        mol = rotate_copy_from_quat(mol, self.canvas._rot_q)
        kwargs = self._structure_tab.get_base_kwargs()
        kwargs.update(self._structure_tab.get_hy_kwargs())
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
            kwargs["ts_dash"] = f"{self._structure_tab.bond_editor.dash_len_ratio:.1f},{self._structure_tab.bond_editor.dash_gap_ratio:.1f}"
            kwargs["ts_width"] = self._structure_tab.bond_editor.dash_width_ratio
        return render(mol, **kwargs)

    # ══════════════════════════════════════════════════════════════════
    #  键编辑状态
    # ══════════════════════════════════════════════════════════════════

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

    def _sync_dash_color(self):
        """将键编辑器的虚线颜色同步到 canvas：更新所有已有虚线和新虚线的默认颜色。"""
        be = self._structure_tab.bond_editor
        hex_color = be.dash_color_hex
        self.canvas.dash_color_hex = hex_color
        # 重新着色所有已有虚线
        for i, (a1, a2, _) in enumerate(self.canvas.custom_dash_lines):
            self.canvas.custom_dash_lines[i] = (a1, a2, hex_color)
