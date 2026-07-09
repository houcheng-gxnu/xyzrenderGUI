"""Tab: Cub 文件 — 直接加载 cube 文件的等值面渲染。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QComboBox, QCheckBox, QLabel, QSlider, QLineEdit, QColorDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor


class CubeTab(QWidget):
    """直接载入 cube 文件并渲染等值面，支持正负瓣独立着色。"""

    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    quick_peek_requested = pyqtSignal(dict)
    export_png_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pos_color = "#6495ed"   # cornflowerblue
        self._neg_color = "#cd5c5c"   # indianred
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── 渲染控制 ──
        gb_cr = QGroupBox("渲染")
        crl = QVBoxLayout(gb_cr)

        ih_c = QHBoxLayout(); ih_c.addWidget(QLabel("等值:"))
        self._iso_cube = QSlider(Qt.Horizontal); self._iso_cube.setRange(1,200); self._iso_cube.setValue(50)
        ih_c.addWidget(self._iso_cube)
        self._iso_cube_label = QLabel("0.050")
        ih_c.addWidget(self._iso_cube_label)
        self._iso_cube.valueChanged.connect(lambda v: self._iso_cube_label.setText(f"{v/1000:.3f}"))
        crl.addLayout(ih_c)

        sh_c = QHBoxLayout(); sh_c.addWidget(QLabel("样式:"))
        self._surf_cube = QComboBox(); self._surf_cube.addItems(["solid","mesh","contour","dot"])
        sh_c.addWidget(self._surf_cube); sh_c.addStretch(); crl.addLayout(sh_c)

        oh_c = QHBoxLayout(); oh_c.addWidget(QLabel("透明度:"))
        self._cube_opacity = QSlider(Qt.Horizontal); self._cube_opacity.setRange(1,100); self._cube_opacity.setValue(100)
        oh_c.addWidget(self._cube_opacity)
        self._cube_opacity_label = QLabel("1.00")
        oh_c.addWidget(self._cube_opacity_label)
        self._cube_opacity.valueChanged.connect(lambda v: self._cube_opacity_label.setText(f"{v/100:.2f}"))
        crl.addLayout(oh_c)

        # ── 正负瓣分色 ──
        col_h = QHBoxLayout()
        col_h.addWidget(QLabel("正瓣:"))
        self._btn_pos = QPushButton(); self._btn_pos.setFixedSize(22,22)
        self._btn_pos.setStyleSheet(f"background-color:{self._pos_color};border:1px solid #888;border-radius:2px;")
        self._btn_pos.clicked.connect(self._pick_pos_color)
        col_h.addWidget(self._btn_pos)
        col_h.addSpacing(12)
        col_h.addWidget(QLabel("负瓣:"))
        self._btn_neg = QPushButton(); self._btn_neg.setFixedSize(22,22)
        self._btn_neg.setStyleSheet(f"background-color:{self._neg_color};border:1px solid #888;border-radius:2px;")
        self._btn_neg.clicked.connect(self._pick_neg_color)
        col_h.addWidget(self._btn_neg)
        col_h.addStretch()
        crl.addLayout(col_h)

        ol_h = QHBoxLayout()
        self._cube_outlined = QCheckBox("描边风格 (opaque + 轮廓线)")
        self._cube_outlined.toggled.connect(lambda c: self._cube_outline.setValue(5 if c else 0))
        ol_h.addWidget(self._cube_outlined)
        ol_h.addWidget(QLabel("轮廓宽:"))
        self._cube_outline = QSlider(Qt.Horizontal); self._cube_outline.setRange(0,20); self._cube_outline.setValue(0)
        self._cube_outline_label = QLabel("0")
        self._cube_outline.valueChanged.connect(lambda v: self._cube_outline_label.setText(str(v)))
        ol_h.addWidget(self._cube_outline); ol_h.addWidget(self._cube_outline_label)
        crl.addLayout(ol_h)
        layout.addWidget(gb_cr)

        # ── 导出 ──
        gb_cout = QGroupBox("导出")
        col = QVBoxLayout(gb_cout)
        self._btn_cube_peek = QPushButton("Cube 预览"); self._btn_cube_peek.setObjectName("PrimaryBtn"); self._btn_cube_peek.setEnabled(False)
        self._btn_cube_peek.clicked.connect(self._on_quick_peek)
        col.addWidget(self._btn_cube_peek)
        self._btn_cube_save = QPushButton("保存 Cube 图 (PNG)"); self._btn_cube_save.setEnabled(False)
        self._btn_cube_save.clicked.connect(self._on_export_png)
        col.addWidget(self._btn_cube_save)
        layout.addWidget(gb_cout)
        layout.addStretch()

    def _pick_pos_color(self):
        c = QColorDialog.getColor(QColor(self._pos_color), self, "正瓣颜色")
        if c.isValid():
            self._pos_color = c.name()
            self._btn_pos.setStyleSheet(f"background-color:{self._pos_color};border:1px solid #888;border-radius:2px;")

    def _pick_neg_color(self):
        c = QColorDialog.getColor(QColor(self._neg_color), self, "负瓣颜色")
        if c.isValid():
            self._neg_color = c.name()
            self._btn_neg.setStyleSheet(f"background-color:{self._neg_color};border:1px solid #888;border-radius:2px;")

    def get_kwargs(self) -> dict:
        """Cub 文件渲染参数（当作 MO 渲染以支持正负瓣分色 + 描边）。"""
        kwargs = dict(
            mo=True,
            iso=self._iso_cube.value() / 1000.0,
            surface_style=self._surf_cube.currentText(),
            opacity=self._cube_opacity.value() / 100.0,
            mo_pos_color=self._pos_color,
            mo_neg_color=self._neg_color,
        )
        if self._cube_outline.value() > 0:
            kwargs["mo_outline_width"] = self._cube_outline.value()
        if self._cube_outlined.isChecked():
            kwargs["flat_mo"] = True
        return kwargs

    def set_buttons_enabled(self, enabled):
        self._btn_cube_peek.setEnabled(enabled)
        self._btn_cube_save.setEnabled(enabled)

    def _on_quick_peek(self):
        self.quick_peek_requested.emit(self.get_kwargs())

    def _on_export_png(self):
        self.export_png_requested.emit(self.get_kwargs())
