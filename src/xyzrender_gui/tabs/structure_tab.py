"""Tab 1: 结构可视化 — xyzrender 预设、键编辑、出图。"""

import os
import tempfile

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QComboBox, QCheckBox, QLabel, QSlider, QColorDialog, QLineEdit,
    QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QSize
from PyQt5.QtGui import QFont, QColor

from ..config import XYZR_PRESETS
from ..parsing import _indices_to_text
from molcanvas.styles import STYLE_PRESETS
from ..i18n import tr, on_language_changed


class CollapsibleSection(QWidget):
    """可折叠分组：标题栏点击展开/收起内容区。"""

    def __init__(self, title: str, collapsed: bool = True, parent=None):
        super().__init__(parent)
        self._title_key = title
        self._title = title

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # 标题栏按钮（不用 _t，由 retranslate 处理箭头+文字）
        self._btn = QPushButton()
        self._btn._skip_i18n = True  # _retranslate_ui 跳过此按钮
        self._btn.setStyleSheet(
            "QPushButton { text-align: left; padding: 4px 8px; font-weight: bold; "
            "border: 1px solid #ccc; border-radius: 4px; background: #f5f5f5; }"
            "QPushButton:hover { background: #e8e8e8; }"
        )
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.clicked.connect(self.toggle)
        outer.addWidget(self._btn)

        # 内容容器
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 4, 8, 4)
        self._content_layout.setSpacing(4)
        outer.addWidget(self._content)

        self._collapsed = not collapsed  # toggle 会翻转
        self._update_arrow()
        if collapsed:
            # 初始折叠：延迟执行以确保布局正确
            self._content.setVisible(False)
            self._collapsed = True
            self._update_arrow()

    @property
    def content_layout(self):
        return self._content_layout

    def _update_arrow(self):
        arrow = "▼" if not self._collapsed else "▶"
        self._btn.setText(f"  {arrow}  {self._title}")

    def toggle(self):
        self._collapsed = not self._collapsed
        self._content.setVisible(not self._collapsed)
        self._update_arrow()

    def retranslate(self):
        self._title = tr(self._title_key)
        self._update_arrow()


class BondEditPanel(QWidget):
    """键编辑面板（虚线 / 断键）—— 独立 widget，便于复用。"""

    dash_changed = pyqtSignal()
    break_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        grp = QGroupBox("键编辑（点击画布两个原子画虚线或断键，xyzrender 出图同步）"); grp._t = "键编辑（点击画布两个原子画虚线或断键，xyzrender 出图同步）"
        layout = QVBoxLayout(grp)
        layout.setSpacing(4)

        # ── 第一行：虚线控制 ──
        r1 = QHBoxLayout(); r1.setSpacing(6)
        self.chk_dash_mode = QCheckBox("虚线"); self.chk_dash_mode._t = "虚线"
        r1.addWidget(self.chk_dash_mode)
        _lbl = QLabel(); _lbl._t = "样式:"; r1.addWidget(_lbl)
        self.dash_style_combo = QComboBox()
        self.dash_style_combo.addItems(["线段", "圆点"])
        self.dash_style_combo.setFixedWidth(110)
        r1.addWidget(self.dash_style_combo)
        self.btn_dash_color = QPushButton("  ")
        self.btn_dash_color.setFixedSize(26, 26)
        self.btn_dash_color.setStyleSheet("background-color: #000000; border: 1px solid #555; border-radius: 2px;")
        self.btn_dash_color.clicked.connect(self._pick_dash_color)
        r1.addWidget(self.btn_dash_color)
        r1.addSpacing(12)
        btn_undo = QPushButton("撤销虚线"); btn_undo._t = "撤销虚线"
        btn_undo.setFixedWidth(160)
        r1.addWidget(btn_undo)
        btn_clear = QPushButton("清除虚线"); btn_clear._t = "清除虚线"
        btn_clear.setFixedWidth(160)
        r1.addWidget(btn_clear)
        r1.addSpacing(8)
        self.lbl_dash_status = QLabel("")
        self.lbl_dash_status.setStyleSheet("color: #666; font-size: 9pt;")
        r1.addWidget(self.lbl_dash_status)
        r1.addStretch()
        layout.addLayout(r1)

        # ── 第二行：虚线参数 ──
        r2 = QHBoxLayout(); r2.setSpacing(6)
        _lbl = QLabel(" Len%:"); _lbl._t = "Len%:"; r2.addWidget(_lbl)
        self._xyzr_dash_len = QSlider(Qt.Horizontal)
        self._xyzr_dash_len.setRange(50, 250); self._xyzr_dash_len.setValue(120)
        r2.addWidget(self._xyzr_dash_len, 1)
        self._lbl_dash_len = QLabel("120%")
        self._xyzr_dash_len.valueChanged.connect(self._on_params_changed)
        r2.addWidget(self._lbl_dash_len)
        _lbl = QLabel("  Gap%:"); _lbl._t = "Gap%:"; r2.addWidget(_lbl)
        self._xyzr_dash_gap = QSlider(Qt.Horizontal)
        self._xyzr_dash_gap.setRange(50, 400); self._xyzr_dash_gap.setValue(220)
        r2.addWidget(self._xyzr_dash_gap, 1)
        self._lbl_dash_gap = QLabel("220%")
        self._xyzr_dash_gap.valueChanged.connect(self._on_params_changed)
        r2.addWidget(self._lbl_dash_gap)
        _lbl = QLabel("  W%:"); _lbl._t = "W%:"; r2.addWidget(_lbl)
        self._xyzr_dash_width = QSlider(Qt.Horizontal)
        self._xyzr_dash_width.setRange(50, 250); self._xyzr_dash_width.setValue(120)
        r2.addWidget(self._xyzr_dash_width, 1)
        self._lbl_dash_width = QLabel("120%")
        self._xyzr_dash_width.valueChanged.connect(self._on_params_changed)
        r2.addWidget(self._lbl_dash_width)
        layout.addLayout(r2)

        # ── 第三行：断键控制 ──
        r3 = QHBoxLayout(); r3.setSpacing(6)
        self.chk_break_mode = QCheckBox("断键"); self.chk_break_mode._t = "断键"
        r3.addWidget(self.chk_break_mode)
        r3.addSpacing(12)
        self.btn_break_undo = QPushButton("撤销断键"); self.btn_break_undo._t = "撤销断键"
        self.btn_break_undo.setFixedWidth(160)
        r3.addWidget(self.btn_break_undo)
        self.btn_break_clear = QPushButton("清除断键"); self.btn_break_clear._t = "清除断键"
        self.btn_break_clear.setFixedWidth(160)
        r3.addWidget(self.btn_break_clear)
        r3.addSpacing(8)
        self.lbl_break_status = QLabel("")
        self.lbl_break_status.setStyleSheet("color: #666; font-size: 9pt;")
        r3.addWidget(self.lbl_break_status)
        r3.addStretch()
        layout.addLayout(r3)

        self._btn_undo = btn_undo
        self._btn_clear = btn_clear
        outer.addWidget(grp)

        self._retranslate_ui()
        on_language_changed(self._retranslate_ui)

    def _retranslate_ui(self):
        for w in self.findChildren((QLabel, QPushButton, QCheckBox)):
            if hasattr(w, '_skip_i18n'):
                continue
            if hasattr(w, '_t'):
                w.setText(tr(w._t))
        for w in self.findChildren(QGroupBox):
            if hasattr(w, '_t'):
                w.setTitle(tr(w._t))
        for w in self.findChildren(CollapsibleSection):
            w.retranslate()
        idx = self.dash_style_combo.currentIndex()
        self.dash_style_combo.clear()
        self.dash_style_combo.addItems([tr("线段"), tr("圆点")])
        self.dash_style_combo.setCurrentIndex(idx)

    def _pick_dash_color(self):
        col = QColorDialog.getColor()
        if col.isValid():
            self.btn_dash_color.setStyleSheet(
                f"background-color: {col.name()}; border: 1px solid #555; border-radius: 2px;")
            self.dash_changed.emit()

    def _on_params_changed(self):
        dl, dg, dw = self._xyzr_dash_len.value(), self._xyzr_dash_gap.value(), self._xyzr_dash_width.value()
        self._lbl_dash_len.setText(f"{dl}%")
        self._lbl_dash_gap.setText(f"{dg}%")
        self._lbl_dash_width.setText(f"{dw}%")
        self.dash_changed.emit()

    @property
    def dash_len_ratio(self): return self._xyzr_dash_len.value() / 100.0

    @property
    def dash_gap_ratio(self): return self._xyzr_dash_gap.value() / 100.0

    @property
    def dash_width_ratio(self): return self._xyzr_dash_width.value() / 100.0

    @property
    def dash_color_hex(self):
        ss = self.btn_dash_color.styleSheet()
        if "background-color:" in ss:
            return ss.split("background-color:")[1].split(";")[0].strip()
        return "#000000"

    def dash_style(self):
        return "dots" if self.dash_style_combo.currentIndex() == 1 else "dash"


class StructureTab(QWidget):
    """结构可视化 Tab：预设、导出按钮。"""

    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    render_requested = pyqtSignal(dict)      # kwargs
    export_png_requested = pyqtSignal(dict)
    export_svg_requested = pyqtSignal(dict)
    export_gif_requested = pyqtSignal(dict)
    preview_gif_requested = pyqtSignal(dict)
    show_preview_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ════════════════════════════════════════════════════════════
        #  核心区（始终可见）
        # ════════════════════════════════════════════════════════════
        gb_core = QGroupBox("xyzrender 预设"); gb_core._t = "xyzrender 预设"
        cl = QVBoxLayout(gb_core); cl.setSpacing(4)

        r1 = QHBoxLayout()
        _lbl = QLabel("样式:"); _lbl._t = "样式:"; r1.addWidget(_lbl)
        self._preset_combo = QComboBox(); self._preset_combo.addItems(XYZR_PRESETS); self._preset_combo.setCurrentText("paton")
        r1.addWidget(self._preset_combo)
        _lbl = QLabel("画布:"); _lbl._t = "画布:"; r1.addWidget(_lbl)
        self._size_combo = QComboBox(); self._size_combo.addItems(["300","400","500","600","800","1000"]); self._size_combo.setCurrentText("600")
        r1.addWidget(self._size_combo)
        self._btn_hy = QPushButton("隐藏氢原子"); self._btn_hy._t_hide = "隐藏氢原子"; self._btn_hy._t_show = "显示氢原子"; self._btn_hy.setCheckable(True); self._btn_hy.setFixedWidth(200)
        self._btn_hy.toggled.connect(lambda c: self._btn_hy.setText(tr("显示氢原子") if c else tr("隐藏氢原子")))
        r1.addWidget(self._btn_hy)
        _lbl = QLabel("指定编号:"); _lbl._t = "指定编号:"; r1.addWidget(_lbl)
        self._hy_keep_edit = QLineEdit(); self._hy_keep_edit.setPlaceholderText("如 7 8 9"); self._hy_keep_edit._t = "如 7 8 9"; self._hy_keep_edit.setFixedWidth(110)
        r1.addWidget(self._hy_keep_edit)
        cl.addLayout(r1)
        layout.addWidget(gb_core)

        # ════════════════════════════════════════════════════════════
        #  折叠区：片段 & vdW
        # ════════════════════════════════════════════════════════════
        sec_frag = CollapsibleSection("片段 & vdW", collapsed=True)
        fl = sec_frag.content_layout

        f_row = QHBoxLayout()
        _lbl = QLabel("片段1:"); _lbl._t = "片段1:"; f_row.addWidget(_lbl)
        self._frag1_edit = QLineEdit(); self._frag1_edit.setPlaceholderText("如 1-5,10-12 或画布 Shift+左键"); self._frag1_edit._t = "如 1-5,10-12 或画布 Shift+左键"
        f_row.addWidget(self._frag1_edit)
        _lbl2 = QLabel("片段2:"); _lbl2._t = "片段2:"; f_row.addWidget(_lbl2)
        self._frag2_edit = QLineEdit(); self._frag2_edit.setPlaceholderText("如 6-9 或 c (补集) 或画布 Alt+左键"); self._frag2_edit._t = "如 6-9 或 c (补集) 或画布 Alt+左键"
        f_row.addWidget(self._frag2_edit)
        fl.addLayout(f_row)

        self._frag1_edit.editingFinished.connect(self._on_frag1_edit)
        self._frag2_edit.editingFinished.connect(self._on_frag2_edit)

        frag_row = QHBoxLayout()
        self._btn_frag1 = QPushButton("选片段1 (蓝)"); self._btn_frag1._t = "选片段1 (蓝)"
        self._btn_frag1.setFixedWidth(150)
        self._btn_frag1.setToolTip("画布上按住 Shift+左键选择原子")
        self._btn_frag1.clicked.connect(lambda: self._set_frag_mode(1))
        frag_row.addWidget(self._btn_frag1)

        self._btn_frag2 = QPushButton("选片段2 (红)"); self._btn_frag2._t = "选片段2 (红)"
        self._btn_frag2.setFixedWidth(150)
        self._btn_frag2.setToolTip("画布上按住 Ctrl+左键选择原子")
        self._btn_frag2.clicked.connect(lambda: self._set_frag_mode(2))
        frag_row.addWidget(self._btn_frag2)

        self._btn_frag_clear = QPushButton("清除片段"); self._btn_frag_clear._t = "清除片段"
        self._btn_frag_clear.setFixedWidth(150)
        self._btn_frag_clear.clicked.connect(self._clear_fragments)
        frag_row.addWidget(self._btn_frag_clear)

        self._btn_vdw_frag1 = QPushButton("vdW 片段1"); self._btn_vdw_frag1._t = "vdW 片段1"
        self._btn_vdw_frag1.setCheckable(True)
        self._btn_vdw_frag1.setFixedWidth(130)
        self._btn_vdw_frag1.setStyleSheet("QPushButton:checked { background-color: #4a90d9; color: white; }")
        frag_row.addWidget(self._btn_vdw_frag1)

        self._btn_vdw_frag2 = QPushButton("vdW 片段2"); self._btn_vdw_frag2._t = "vdW 片段2"
        self._btn_vdw_frag2.setCheckable(True)
        self._btn_vdw_frag2.setFixedWidth(130)
        self._btn_vdw_frag2.setStyleSheet("QPushButton:checked { background-color: #e74c3c; color: white; }")
        frag_row.addWidget(self._btn_vdw_frag2)

        self._btn_vdw_all = QPushButton("vdW 全部"); self._btn_vdw_all._t = "vdW 全部"
        self._btn_vdw_all.setCheckable(True)
        self._btn_vdw_all.setFixedWidth(130)
        self._btn_vdw_all.setStyleSheet("QPushButton:checked { background-color: #27ae60; color: white; }")
        frag_row.addWidget(self._btn_vdw_all)
        fl.addLayout(frag_row)

        frag_hint = QLabel("  画布: Shift+左键选片段1, Alt+左键选片段2"); frag_hint._t = "画布: Shift+左键选片段1, Alt+左键选片段2"
        frag_hint.setStyleSheet("color: #888; font-size: 8pt;")
        fl.addWidget(frag_hint)

        self._frag1_indices: set[int] = set()
        self._frag2_indices: set[int] = set()
        self._frag_mode = 0  # 0=off, 1=selecting frag1, 2=selecting frag2
        self._lbl_frag_status = QLabel("")
        self._lbl_frag_status.setStyleSheet("color: #666; font-size: 9pt;")
        fl.addWidget(self._lbl_frag_status)
        layout.addWidget(sec_frag)

        # ════════════════════════════════════════════════════════════
        #  折叠区：高亮 & 凸包
        # ════════════════════════════════════════════════════════════
        sec_hl = CollapsibleSection("高亮 & 凸包", collapsed=True)
        hl = sec_hl.content_layout

        hl_row = QHBoxLayout()
        self._chk_highlight = QCheckBox(tr("高亮原子")); self._chk_highlight._t = "高亮原子"
        hl_row.addWidget(self._chk_highlight)
        self._hl_spec = QLineEdit(); self._hl_spec.setPlaceholderText("如 1-3,7 或 C,N")
        self._hl_spec._t = "如 1-3,7 或 C,N"
        hl_row.addWidget(self._hl_spec)
        self._btn_hl_color = QPushButton(); self._highlight_color = "#b060d0"; self._highlight_alpha = 1.0  # orchid
        self._btn_hl_color.setFixedSize(30, 30)
        self._btn_hl_color.setStyleSheet(f"background-color: {self._highlight_color}; border: 1px solid #888; border-radius: 4px;")
        self._btn_hl_color.clicked.connect(self._pick_highlight_color)
        hl_row.addWidget(self._btn_hl_color)
        hl.addLayout(hl_row)

        hull_row = QHBoxLayout()
        self._chk_hull = QCheckBox(tr("凸包")); self._chk_hull._t = "凸包"
        hull_row.addWidget(self._chk_hull)
        self._hull_spec = QLineEdit(); self._hull_spec.setPlaceholderText("如 1-6 或 rings")
        self._hull_spec._t = "如 1-6 或 rings"
        hull_row.addWidget(self._hull_spec)
        self._btn_hull_color = QPushButton(); self._hull_color = "#87CEEB"; self._hull_opacity = 0.35
        self._btn_hull_color.setFixedSize(30, 30)
        self._btn_hull_color.setStyleSheet(f"background-color: {self._hull_color}; border: 1px solid #888; border-radius: 4px;")
        self._btn_hull_color.clicked.connect(self._pick_hull_color)
        hull_row.addWidget(self._btn_hull_color)
        _lbl = QLabel("透明:"); _lbl._t = "透明:"; hull_row.addWidget(_lbl)
        self._hull_opacity_slider = QSlider(Qt.Horizontal); self._hull_opacity_slider.setRange(5, 100); self._hull_opacity_slider.setValue(35)
        self._hull_opacity_edit = QLineEdit("0.35"); self._hull_opacity_edit.setFixedWidth(50); self._hull_opacity_edit.setAlignment(Qt.AlignRight)
        self._hull_opacity_slider.valueChanged.connect(lambda v: self._hull_opacity_edit.setText(f"{v/100:.2f}"))
        self._hull_opacity_edit.returnPressed.connect(lambda: self._hull_opacity_slider.setValue(int(float(self._hull_opacity_edit.text())*100)))
        hull_row.addWidget(self._hull_opacity_slider); hull_row.addWidget(self._hull_opacity_edit)
        hl.addLayout(hull_row)
        layout.addWidget(sec_hl)

        # ════════════════════════════════════════════════════════════
        #  折叠区：样式微调
        # ════════════════════════════════════════════════════════════
        sec_style = CollapsibleSection("样式微调", collapsed=True)
        sl = sec_style.content_layout

        slider_row = QHBoxLayout()
        _lbl = QLabel("原子:"); _lbl._t = "原子:"; slider_row.addWidget(_lbl)
        self._atom_scale = QSlider(Qt.Horizontal); self._atom_scale.setRange(10,50); self._atom_scale.setValue(25)
        self._atom_edit = QLineEdit("2.5"); self._atom_edit.setFixedWidth(50); self._atom_edit.setAlignment(Qt.AlignRight)
        self._atom_scale.valueChanged.connect(lambda v: self._atom_edit.setText(f"{v/10:.1f}"))
        self._atom_edit.returnPressed.connect(lambda: self._atom_scale.setValue(int(float(self._atom_edit.text())*10)))
        slider_row.addWidget(self._atom_scale); slider_row.addWidget(self._atom_edit)

        _lbl = QLabel("键宽:"); _lbl._t = "键宽:"; slider_row.addWidget(_lbl)
        self._bond_width = QSlider(Qt.Horizontal); self._bond_width.setRange(5,50); self._bond_width.setValue(20)
        self._bond_edit = QLineEdit("20"); self._bond_edit.setFixedWidth(50); self._bond_edit.setAlignment(Qt.AlignRight)
        self._bond_width.valueChanged.connect(lambda v: self._bond_edit.setText(str(v)))
        self._bond_edit.returnPressed.connect(lambda: self._bond_width.setValue(int(self._bond_edit.text())))
        slider_row.addWidget(self._bond_width); slider_row.addWidget(self._bond_edit)

        _lbl = QLabel("vdW透明:"); _lbl._t = "vdW透明:"; slider_row.addWidget(_lbl)
        self._vdw_opacity = QSlider(Qt.Horizontal); self._vdw_opacity.setRange(5,100); self._vdw_opacity.setValue(30)
        self._vdw_edit = QLineEdit("0.30"); self._vdw_edit.setFixedWidth(50); self._vdw_edit.setAlignment(Qt.AlignRight)
        self._vdw_opacity.valueChanged.connect(lambda v: self._vdw_edit.setText(f"{v / 100:.2f}"))
        self._vdw_edit.returnPressed.connect(lambda: self._vdw_opacity.setValue(int(float(self._vdw_edit.text())*100)))
        slider_row.addWidget(self._vdw_opacity); slider_row.addWidget(self._vdw_edit)
        sl.addLayout(slider_row)

        # 景深模糊 + 雾
        dof_row = QHBoxLayout()
        self._fog_check = QCheckBox("深度雾")
        self._fog_check._t = "深度雾"
        self._fog_check.setChecked(True)
        self._fog_check.toggled.connect(lambda on: self._fog_strength.setEnabled(on))
        dof_row.addWidget(self._fog_check)
        self._fog_strength = QSlider(Qt.Horizontal)
        self._fog_strength.setRange(1, 20)
        self._fog_strength.setValue(12)
        self._fog_strength_edit = QLineEdit("1.2")
        self._fog_strength_edit.setFixedWidth(50)
        self._fog_strength_edit.setAlignment(Qt.AlignRight)
        self._fog_strength.valueChanged.connect(lambda v: self._fog_strength_edit.setText(f"{v/10:.1f}"))
        self._fog_strength_edit.returnPressed.connect(lambda: self._fog_strength.setValue(int(float(self._fog_strength_edit.text())*10)))
        self._fog_check.toggled.connect(self._fog_strength_edit.setEnabled)
        _flbl = QLabel("强度:"); _flbl._t = "强度:"; dof_row.addWidget(_flbl)
        dof_row.addWidget(self._fog_strength)
        dof_row.addWidget(self._fog_strength_edit)
        sl.addLayout(dof_row)

        dof_row2 = QHBoxLayout()
        self._dof_check = QCheckBox("景深模糊")
        self._dof_check._t = "景深模糊"
        self._dof_check.toggled.connect(lambda on: self._dof_strength.setEnabled(on))
        dof_row2.addWidget(self._dof_check)
        self._dof_strength = QSlider(Qt.Horizontal)
        self._dof_strength.setRange(1, 20)
        self._dof_strength.setValue(6)
        self._dof_strength.setEnabled(False)
        self._dof_strength_edit = QLineEdit("6.0")
        self._dof_strength_edit.setFixedWidth(50)
        self._dof_strength_edit.setAlignment(Qt.AlignRight)
        self._dof_strength_edit.setEnabled(False)
        self._dof_strength.valueChanged.connect(lambda v: self._dof_strength_edit.setText(f"{v/10:.1f}"))
        self._dof_strength_edit.returnPressed.connect(lambda: self._dof_strength.setValue(int(float(self._dof_strength_edit.text())*10)))
        self._dof_check.toggled.connect(self._dof_strength_edit.setEnabled)
        _dlbl = QLabel("强度:"); _dlbl._t = "强度:"; dof_row2.addWidget(_dlbl)
        dof_row2.addWidget(self._dof_strength)
        dof_row2.addWidget(self._dof_strength_edit)
        sl.addLayout(dof_row2)

        layout.addWidget(sec_style)

        # ── 元素颜色覆盖 ──
        sec_elem = CollapsibleSection("元素颜色", collapsed=True)
        self._elem_table = QTableWidget()
        self._elem_table.setColumnCount(3)
        self._elem_table.setHorizontalHeaderLabels(["元素", "颜色", "HEX"])
        hdr = self._elem_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        self._elem_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._elem_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._elem_table.setAlternatingRowColors(True)
        self._elem_table.setMaximumHeight(200)
        self._elem_table.setStyleSheet("""
            QTableWidget {
                background: #FAFAFA;
                alternate-background-color: #F0F5FA;
                gridline-color: #ddd;
                font-size: 10pt;
            }
            QTableWidget::item { padding: 2px 6px; }
        """)
        self._elem_table.cellDoubleClicked.connect(self._on_elem_table_click)
        sec_elem.content_layout.addWidget(self._elem_table)
        _hint = QLabel("双击行修改颜色")
        _hint._t = "双击行修改颜色"
        _hint.setStyleSheet("color: #888; font-size: 9pt; padding: 2px 0;")
        sec_elem.content_layout.addWidget(_hint)
        self._color_overrides: dict[str, str] = {}
        layout.addWidget(sec_elem)

        # ════════════════════════════════════════════════════════════
        #  导出（始终可见）
        # ════════════════════════════════════════════════════════════
        gb_out = QGroupBox("导出"); gb_out._t = "导出"
        ol = QVBoxLayout(gb_out)
        oh = QHBoxLayout()
        self._btn_peek = QPushButton("快速预览 400px"); self._btn_peek._t = "快速预览 400px"
        self._btn_peek.clicked.connect(self._on_quick_peek)
        oh.addWidget(self._btn_peek)
        self._btn_render = QPushButton("出图 (PNG)"); self._btn_render._t = "出图 (PNG)"
        self._btn_render.setObjectName("PrimaryBtn")
        self._btn_render.clicked.connect(self._on_export_png)
        oh.addWidget(self._btn_render)
        self._btn_save_svg = QPushButton("出图 (SVG)"); self._btn_save_svg._t = "出图 (SVG)"
        self._btn_save_svg.clicked.connect(self._on_export_svg)
        oh.addWidget(self._btn_save_svg)
        ol.addLayout(oh)
        oh_gif = QHBoxLayout()
        _lbl = QLabel(tr("旋转GIF:")); _lbl._t = "旋转GIF:"; oh_gif.addWidget(_lbl)
        self._gif_axis = QComboBox(); self._gif_axis.addItems(["X", "Y", "Z"]); self._gif_axis.setCurrentText("Y")
        self._gif_axis._t_items = ["X", "Y", "Z"]
        oh_gif.addWidget(self._gif_axis)
        _lbl = QLabel("FPS:"); _lbl._t = "FPS:"; oh_gif.addWidget(_lbl)
        self._gif_fps = QLineEdit("10"); self._gif_fps.setFixedWidth(40); self._gif_fps.setAlignment(Qt.AlignRight)
        self._gif_fps._t = "10"
        oh_gif.addWidget(self._gif_fps)
        _lbl = QLabel("帧:"); _lbl._t = "帧:"; oh_gif.addWidget(_lbl)
        self._gif_frames = QLineEdit("120"); self._gif_frames.setFixedWidth(45); self._gif_frames.setAlignment(Qt.AlignRight)
        self._gif_frames._t = "120"
        oh_gif.addWidget(self._gif_frames)
        self._btn_preview_gif = QPushButton(tr("预览 GIF")); self._btn_preview_gif._t = "预览 GIF"
        self._btn_preview_gif.clicked.connect(self._on_preview_gif)
        oh_gif.addWidget(self._btn_preview_gif)
        self._btn_gif = QPushButton(tr("保存 GIF")); self._btn_gif._t = "保存 GIF"
        self._btn_gif.clicked.connect(self._on_export_gif)
        oh_gif.addWidget(self._btn_gif)
        oh_gif.addSpacing(16)
        self._chk_transparent = QCheckBox("透明背景"); self._chk_transparent._t = "透明背景"
        oh_gif.addWidget(self._chk_transparent)
        oh_gif.addStretch()
        ol.addLayout(oh_gif)
        layout.addWidget(gb_out)

        # ── 键编辑 ──
        self.bond_editor = BondEditPanel()
        layout.addWidget(self.bond_editor)
        layout.addStretch()

        self._retranslate_ui()
        on_language_changed(self._retranslate_ui)

    def _retranslate_ui(self):
        for w in self.findChildren((QLabel, QPushButton, QCheckBox)):
            if hasattr(w, '_skip_i18n'):
                continue
            if hasattr(w, '_t'):
                w.setText(tr(w._t))
        for w in self.findChildren(QGroupBox):
            if hasattr(w, '_t'):
                w.setTitle(tr(w._t))
        for w in self.findChildren(QLineEdit):
            if hasattr(w, '_t'):
                w.setPlaceholderText(tr(w._t))
        for w in self.findChildren(CollapsibleSection):
            w.retranslate()
        # btn_hy dynamic text
        if hasattr(self, '_btn_hy'):
            c = self._btn_hy.isChecked()
            self._btn_hy.setText(tr("显示氢原子") if c else tr("隐藏氢原子"))
        idx = self._gif_axis.currentIndex()
        self._gif_axis.clear()
        self._gif_axis.addItems(["X", "Y", "Z"])
        self._gif_axis.setCurrentIndex(idx)

    # ── 片段管理 ──
    def _set_frag_mode(self, mode: int):
        self._frag_mode = mode
        self._btn_frag1.setChecked(mode == 1)
        self._btn_frag2.setChecked(mode == 2)
        self._btn_frag1.setStyleSheet(
            "QPushButton { background-color: #4a90d9; color: white; }" if mode == 1 else "")
        self._btn_frag2.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: white; }" if mode == 2 else "")
        if mode == 1:
            self._lbl_frag_status.setText(tr("模式: 选择片段1"))
        elif mode == 2:
            self._lbl_frag_status.setText(tr("模式: 选择片段2"))
        else:
            self._lbl_frag_status.setText("")

    def _clear_fragments(self):
        self._frag1_indices.clear()
        self._frag2_indices.clear()
        self._frag1_edit.clear()
        self._frag2_edit.clear()
        self._set_frag_mode(0)
        self._lbl_frag_status.setText(tr("已清除"))

    def _parse_frag_edit(self, text: str) -> set[int]:
        """解析片段输入框文本，返回整数集合。"""
        indices = set()
        for part in text.replace(",", " ").split():
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    a, b = part.split("-", 1)
                    indices.update(range(int(a), int(b) + 1))
                except ValueError:
                    pass
            else:
                try:
                    indices.add(int(part))
                except ValueError:
                    pass
        return indices

    def _on_frag1_edit(self):
        text = self._frag1_edit.text().strip()
        self._frag1_indices = self._parse_frag_edit(text)
        n1, n2 = len(self._frag1_indices), len(self._frag2_indices)
        self._lbl_frag_status.setText(tr("片段1: {}个  片段2: {}个").format(n1, n2))

    def _on_frag2_edit(self):
        text = self._frag2_edit.text().strip()
        self._frag2_indices = self._parse_frag_edit(text)
        n1, n2 = len(self._frag1_indices), len(self._frag2_indices)
        self._lbl_frag_status.setText(tr("片段1: {}个  片段2: {}个").format(n1, n2))

    def add_atom_to_frag(self, atom_idx: int):
        """画布调用：将原子加入当前活跃片段。"""
        if self._frag_mode == 1:
            self._frag1_indices.add(atom_idx)
            self._frag1_edit.setText(", ".join(str(i) for i in sorted(self._frag1_indices)))
        elif self._frag_mode == 2:
            self._frag2_indices.add(atom_idx)
            self._frag2_edit.setText(", ".join(str(i) for i in sorted(self._frag2_indices)))
        n1, n2 = len(self._frag1_indices), len(self._frag2_indices)
        self._lbl_frag_status.setText(tr("片段1: {}个  片段2: {}个").format(n1, n2))

    @property
    def frag_mode(self):
        return self._frag_mode

    # ── 参数收集 ──
    def get_base_kwargs(self) -> dict:
        """返回结构渲染的通用参数。"""
        kw = dict(
            config=self._preset_combo.currentText(),
            canvas_size=int(self._size_combo.currentText()),
            orient=False,
            atom_scale=self._atom_scale.value() / 10.0,
            bond_width=self._bond_width.value(),
        )
        if self._fog_check.isChecked():
            kw["fog"] = True
            kw["fog_strength"] = self._fog_strength.value() / 10.0
        else:
            kw["fog"] = False
        if self._dof_check.isChecked():
            kw["dof"] = True
            kw["dof_strength"] = self._dof_strength.value() / 10.0
        if self._color_overrides:
            kw["color_overrides"] = dict(self._color_overrides)
        return kw

    def get_hy_kwargs(self) -> dict:
        """H 显示参数。"""
        kwargs = {}
        if self._btn_hy.isChecked():
            text = self._hy_keep_edit.text().strip()
            if text:
                try:
                    indices = [int(x) for x in text.split()]
                    if indices:
                        kwargs["hy"] = indices
                        return kwargs
                except ValueError:
                    pass
            kwargs["no_hy"] = True
        else:
            kwargs["hy"] = True
        return kwargs

    def get_vdw_kwargs(self) -> dict:
        kwargs = {}
        opacity = self._vdw_opacity.value() / 100.0
        frag1 = sorted(self._frag1_indices) if self._btn_vdw_frag1.isChecked() and self._frag1_indices else []
        frag2 = sorted(self._frag2_indices) if self._btn_vdw_frag2.isChecked() and self._frag2_indices else []
        if self._btn_vdw_all.isChecked():
            kwargs["vdw"] = True
        elif frag1 or frag2:
            kwargs["vdw"] = frag1 + frag2  # xyzrender 原生支持 vdw=[索引列表]
        if kwargs:
            kwargs["vdw_opacity"] = opacity
        return kwargs

    def _make_full_kwargs(self) -> dict:
        kwargs = self.get_base_kwargs()
        kwargs.update(self.get_hy_kwargs())
        kwargs.update(self.get_vdw_kwargs())
        if self._chk_highlight.isChecked():
            spec = self._hl_spec.text().strip()
            if spec:
                kwargs["highlight"] = [(spec, self._highlight_color)]
        if self._chk_hull.isChecked():
            spec = self._hull_spec.text().strip()
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
                kwargs["hull_color"] = self._hull_color
                kwargs["hull_opacity"] = self._hull_opacity_slider.value() / 100.0
        return kwargs

    def _pick_hull_color(self):
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor()
        if color.isValid():
            self._hull_color = color.name()
            self._btn_hull_color.setStyleSheet(
                f"background-color: {self._hull_color}; border: 1px solid #888; border-radius: 4px;")

    def _pick_highlight_color(self):
        from PyQt5.QtWidgets import QColorDialog
        from PyQt5.QtGui import QColor
        color = QColorDialog.getColor(options=QColorDialog.ShowAlphaChannel)
        if color.isValid():
            self._highlight_color = color.name()  # #RRGGBB
            self._highlight_alpha = color.alphaF()
            self._btn_hl_color.setStyleSheet(
                f"background-color: {self._highlight_color}; border: 1px solid #888; border-radius: 4px;")

    # ── 命令 ──
    def _on_quick_peek(self):
        self.render_requested.emit(self._make_full_kwargs())

    def _on_export_png(self):
        self.export_png_requested.emit(self._make_full_kwargs())

    def _on_export_svg(self):
        self.export_svg_requested.emit(self._make_full_kwargs())

    def _on_preview_gif(self):
        kw = self._make_full_kwargs()
        kw["gif_rot"] = self._gif_axis.currentText()
        try: kw["gif_fps"] = int(self._gif_fps.text())
        except ValueError: kw["gif_fps"] = 10
        try: kw["rot_frames"] = int(self._gif_frames.text())
        except ValueError: kw["rot_frames"] = 120
        self.preview_gif_requested.emit(kw)

    def _on_export_gif(self):
        kw = self._make_full_kwargs()
        kw["gif_rot"] = self._gif_axis.currentText()
        try:
            kw["gif_fps"] = int(self._gif_fps.text())
        except ValueError:
            kw["gif_fps"] = 10
        try:
            kw["rot_frames"] = int(self._gif_frames.text())
        except ValueError:
            kw["rot_frames"] = 120
        self.export_gif_requested.emit(kw)

    # ── 元素颜色覆盖 ──
    # CPK 默认色（用于色块初始背景）
    _CPK_HEX = {
        "H": "#FFFFFF", "He": "#D9FFFF", "Li": "#CC80FF", "Be": "#C2FF00",
        "B": "#FFB5B5", "C": "#909090", "N": "#3050F8", "O": "#FF0D0D",
        "F": "#90E050", "Ne": "#B3E3F5", "Na": "#AB5CF2", "Mg": "#8AFF00",
        "Al": "#BFA6A6", "Si": "#F0C8A0", "P": "#FF8000", "S": "#FFFF30",
        "Cl": "#1FF01F", "Ar": "#80D1E3", "K": "#8F40D4", "Ca": "#3DFF00",
        "Sc": "#E6E6E6", "Ti": "#BFC2C7", "V": "#A6A6AB", "Cr": "#8A99C7",
        "Mn": "#9C7AC7", "Fe": "#E06633", "Co": "#F090A0", "Ni": "#50D050",
        "Cu": "#C88033", "Zn": "#7D80B0", "Ga": "#C28F8F", "Ge": "#668F8F",
        "As": "#BD80E3", "Se": "#FFA100", "Br": "#A62929", "Kr": "#5CB8D1",
        "I": "#940094", "Ba": "#00C900", "Au": "#FFD123", "Pb": "#575961",
    }

    def set_element_symbols(self, symbols: list[str]):
        """根据分子中的元素符号，动态填充元素颜色表格。"""
        self._elem_table.setRowCount(len(symbols))
        for i, sym in enumerate(symbols):
            hex_c = self._color_overrides.get(sym, self._CPK_HEX.get(sym, "#A0A0A0"))
            # 元素符号
            it_sym = QTableWidgetItem(sym)
            it_sym.setTextAlignment(Qt.AlignCenter)
            it_sym.setFont(QFont("", -1, QFont.Bold))
            self._elem_table.setItem(i, 0, it_sym)
            # 颜色色块
            it_color = QTableWidgetItem()
            it_color.setBackground(QColor(hex_c))
            it_color.setTextAlignment(Qt.AlignCenter)
            it_color.setFlags(it_color.flags() & ~Qt.ItemIsEditable)
            self._elem_table.setItem(i, 1, it_color)
            # HEX 值
            it_hex = QTableWidgetItem(hex_c)
            it_hex.setTextAlignment(Qt.AlignCenter)
            self._elem_table.setItem(i, 2, it_hex)

    def _on_elem_table_click(self, row, col):
        """双击颜色列弹出颜色选择器。"""
        sym_item = self._elem_table.item(row, 0)
        if not sym_item:
            return
        sym = sym_item.text()
        current = self._color_overrides.get(sym, self._CPK_HEX.get(sym, "#A0A0A0"))
        color = QColorDialog.getColor(initial=QColor(current), parent=self)
        if color.isValid():
            hex_c = color.name()
            self._color_overrides[sym] = hex_c
            self._elem_table.item(row, 1).setBackground(QColor(hex_c))
            self._elem_table.item(row, 2).setText(hex_c)

    def get_color_overrides(self) -> dict[str, str]:
        return dict(self._color_overrides)
