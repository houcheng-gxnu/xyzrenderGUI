"""Tab 1: 结构可视化 — xyzrender 预设、键编辑、出图。"""

import os
import tempfile

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QComboBox, QCheckBox, QLabel, QSlider, QColorDialog, QLineEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal

from ..config import XYZR_PRESETS
from ..parsing import _indices_to_text
from molcanvas.styles import STYLE_PRESETS


class BondEditPanel(QWidget):
    """键编辑面板（虚线模式）—— 独立 widget，便于复用。"""

    dash_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        grp = QGroupBox("键编辑（点击画布两个原子画虚线，xyzrender 出图同步）")
        layout = QVBoxLayout(grp)
        layout.setSpacing(6)

        dash_row = QHBoxLayout()
        self.chk_dash_mode = QCheckBox("虚线模式")
        dash_row.addWidget(self.chk_dash_mode)
        dash_row.addWidget(QLabel(" 样式:"))
        self.dash_style_combo = QComboBox()
        self.dash_style_combo.addItems(["线段", "圆点"])
        self.dash_style_combo.setMaximumWidth(70)
        dash_row.addWidget(self.dash_style_combo)
        self.btn_dash_color = QPushButton("  ")
        self.btn_dash_color.setFixedSize(24, 24)
        self.btn_dash_color.setStyleSheet("background-color: #000000; border: 1px solid #555; border-radius: 2px;")
        self.btn_dash_color.clicked.connect(self._pick_dash_color)
        dash_row.addWidget(self.btn_dash_color)
        dash_row.addStretch()
        layout.addLayout(dash_row)

        xyzr_dash_row = QHBoxLayout()
        xyzr_dash_row.addWidget(QLabel(" Dash Len%:"))
        self._xyzr_dash_len = QSlider(Qt.Horizontal)
        self._xyzr_dash_len.setRange(50, 250); self._xyzr_dash_len.setValue(120)
        xyzr_dash_row.addWidget(self._xyzr_dash_len, 1)
        self._lbl_dash_len = QLabel("120%")
        self._xyzr_dash_len.valueChanged.connect(self._on_params_changed)
        xyzr_dash_row.addWidget(self._lbl_dash_len)
        xyzr_dash_row.addWidget(QLabel("  Gap%:"))
        self._xyzr_dash_gap = QSlider(Qt.Horizontal)
        self._xyzr_dash_gap.setRange(50, 400); self._xyzr_dash_gap.setValue(220)
        xyzr_dash_row.addWidget(self._xyzr_dash_gap, 1)
        self._lbl_dash_gap = QLabel("220%")
        self._xyzr_dash_gap.valueChanged.connect(self._on_params_changed)
        xyzr_dash_row.addWidget(self._lbl_dash_gap)
        xyzr_dash_row.addWidget(QLabel("  W%:"))
        self._xyzr_dash_width = QSlider(Qt.Horizontal)
        self._xyzr_dash_width.setRange(50, 250); self._xyzr_dash_width.setValue(120)
        xyzr_dash_row.addWidget(self._xyzr_dash_width, 1)
        self._lbl_dash_width = QLabel("120%")
        self._xyzr_dash_width.valueChanged.connect(self._on_params_changed)
        xyzr_dash_row.addWidget(self._lbl_dash_width)
        layout.addLayout(xyzr_dash_row)

        btn_row = QHBoxLayout()
        btn_undo = QPushButton("撤销"); layout_btns = btn_row
        btn_clear = QPushButton("清除全部")
        btn_row.addWidget(btn_undo); btn_row.addWidget(btn_clear)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.lbl_dash_status = QLabel("")
        self.lbl_dash_status.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self.lbl_dash_status)

        self._btn_undo = btn_undo
        self._btn_clear = btn_clear
        outer.addWidget(grp)

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
        m = {"线段": "dash", "圆点": "dots"}
        return m.get(self.dash_style_combo.currentText(), "dash")


class StructureTab(QWidget):
    """结构可视化 Tab：预设、导出按钮。"""

    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    render_requested = pyqtSignal(dict)      # kwargs
    export_png_requested = pyqtSignal(dict)
    export_svg_requested = pyqtSignal(dict)
    show_preview_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── xyzrender 预设 ──
        gb_preset = QGroupBox("xyzrender 预设")
        pl = QVBoxLayout(gb_preset); pl.setSpacing(4)

        r1 = QHBoxLayout()
        r1.addWidget(QLabel("样式:"))
        self._preset_combo = QComboBox(); self._preset_combo.addItems(XYZR_PRESETS); self._preset_combo.setCurrentText("paton")
        r1.addWidget(self._preset_combo)
        r1.addWidget(QLabel("画布:"))
        self._size_combo = QComboBox(); self._size_combo.addItems(["300","400","500","600","800","1000"]); self._size_combo.setCurrentText("600")
        r1.addWidget(self._size_combo)
        self._btn_hy = QPushButton("隐藏氢原子"); self._btn_hy.setCheckable(True); self._btn_hy.setFixedWidth(200)
        self._btn_hy.toggled.connect(lambda c: self._btn_hy.setText("显示氢原子" if c else "隐藏氢原子"))
        r1.addWidget(self._btn_hy)
        r1.addWidget(QLabel("指定编号:"))
        self._hy_keep_edit = QLineEdit(); self._hy_keep_edit.setPlaceholderText("如 7 8 9"); self._hy_keep_edit.setFixedWidth(110)
        r1.addWidget(self._hy_keep_edit)
        self._btn_vdw = QPushButton("vdW"); self._btn_vdw.setCheckable(True); self._btn_vdw.setFixedWidth(150)
        self._btn_vdw.setToolTip("显示分子范德华表面\n(仅 xyzrender 出图, 不影响画布)")
        self._btn_vdw.setStyleSheet("QPushButton:checked { background-color: #4a90d9; color: white; }")
        r1.addWidget(self._btn_vdw)
        pl.addLayout(r1)

        ash = QHBoxLayout(); ash.addWidget(QLabel("原子:"))
        self._atom_scale = QSlider(Qt.Horizontal); self._atom_scale.setRange(10,50); self._atom_scale.setValue(25)
        self._atom_scale_label = QLabel("2.5")
        self._atom_scale.valueChanged.connect(lambda v: self._atom_scale_label.setText(f"{v/10:.1f}"))
        ash.addWidget(self._atom_scale); ash.addWidget(self._atom_scale_label); pl.addLayout(ash)

        bwh = QHBoxLayout(); bwh.addWidget(QLabel("键宽:"))
        self._bond_width = QSlider(Qt.Horizontal); self._bond_width.setRange(5,50); self._bond_width.setValue(20)
        self._bond_width_label = QLabel("20")
        self._bond_width.valueChanged.connect(lambda v: self._bond_width_label.setText(str(v)))
        bwh.addWidget(self._bond_width); bwh.addWidget(self._bond_width_label); pl.addLayout(bwh)

        vh = QHBoxLayout(); vh.addWidget(QLabel("vdW透明:"))
        self._vdw_opacity = QSlider(Qt.Horizontal); self._vdw_opacity.setRange(5,100); self._vdw_opacity.setValue(30)
        self._vdw_opacity_label = QLabel("0.30")
        self._vdw_opacity.valueChanged.connect(lambda v: self._vdw_opacity_label.setText(f"{v / 100:.2f}"))
        vh.addWidget(self._vdw_opacity); vh.addWidget(self._vdw_opacity_label); pl.addLayout(vh)

        layout.addWidget(gb_preset)

        # ── 导出 ──
        gb_out = QGroupBox("导出")
        ol = QVBoxLayout(gb_out)
        oh = QHBoxLayout()
        self._btn_peek = QPushButton("快速预览 400px")
        self._btn_peek.clicked.connect(self._on_quick_peek)
        oh.addWidget(self._btn_peek)
        self._btn_render = QPushButton("出图 (PNG)")
        self._btn_render.setObjectName("PrimaryBtn")
        self._btn_render.clicked.connect(self._on_export_png)
        oh.addWidget(self._btn_render)
        self._btn_save_svg = QPushButton("出图 (SVG)")
        self._btn_save_svg.clicked.connect(self._on_export_svg)
        oh.addWidget(self._btn_save_svg)
        ol.addLayout(oh)
        layout.addWidget(gb_out)

        # ── 键编辑 ──
        self.bond_editor = BondEditPanel()
        layout.addWidget(self.bond_editor)
        layout.addStretch()

    # ── 参数收集 ──
    def get_base_kwargs(self) -> dict:
        """返回结构渲染的通用参数。"""
        return dict(
            config=self._preset_combo.currentText(),
            canvas_size=int(self._size_combo.currentText()),
            orient=False,
            atom_scale=self._atom_scale.value() / 10.0,
            bond_width=self._bond_width.value(),
        )

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
        if self._btn_vdw.isChecked():
            kwargs["vdw"] = True
            kwargs["vdw_opacity"] = self._vdw_opacity.value() / 100.0
        return kwargs

    def _make_full_kwargs(self) -> dict:
        kwargs = self.get_base_kwargs()
        kwargs.update(self.get_hy_kwargs())
        kwargs.update(self.get_vdw_kwargs())
        return kwargs

    # ── 命令 ──
    def _on_quick_peek(self):
        self.render_requested.emit(self._make_full_kwargs())

    def _on_export_png(self):
        self.export_png_requested.emit(self._make_full_kwargs())

    def _on_export_svg(self):
        self.export_svg_requested.emit(self._make_full_kwargs())
