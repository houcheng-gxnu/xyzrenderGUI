"""Tab: Cub 文件 — 直接加载 cube 文件的等值面渲染。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QComboBox, QCheckBox, QLabel, QSlider, QLineEdit, QColorDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from ..i18n import tr, on_language_changed


class CubeTab(QWidget):
    """直接载入 cube 文件并渲染等值面，支持正负瓣独立着色。"""

    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    quick_peek_requested = pyqtSignal(dict)
    export_png_requested = pyqtSignal(dict)
    export_svg_requested = pyqtSignal(dict)
    export_gif_requested = pyqtSignal(dict)
    preview_gif_requested = pyqtSignal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pos_color = "#00aaff"
        self._neg_color = "#ff557f"
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── 渲染控制 ──
        gb_cr = QGroupBox("渲染"); gb_cr._t = "渲染"
        crl = QVBoxLayout(gb_cr)

        # 等值 + 透明度
        r1 = QHBoxLayout()
        _lbl = QLabel("等值:"); _lbl._t = "等值:"; r1.addWidget(_lbl)
        self._iso_cube = QSlider(Qt.Horizontal); self._iso_cube.setRange(1,200); self._iso_cube.setValue(50)
        r1.addWidget(self._iso_cube, 1)
        self._iso_cube_edit = QLineEdit("0.050"); self._iso_cube_edit.setFixedWidth(60); self._iso_cube_edit.setAlignment(Qt.AlignRight)
        r1.addWidget(self._iso_cube_edit)
        self._iso_cube.valueChanged.connect(lambda v: self._iso_cube_edit.setText(f"{v/1000:.3f}"))
        self._iso_cube_edit.returnPressed.connect(lambda: self._iso_cube.setValue(int(float(self._iso_cube_edit.text())*1000)))
        r1.addSpacing(20)
        _lbl = QLabel("透明度:"); _lbl._t = "透明度:"; r1.addWidget(_lbl)
        self._cube_opacity = QSlider(Qt.Horizontal); self._cube_opacity.setRange(1,100); self._cube_opacity.setValue(50)
        r1.addWidget(self._cube_opacity, 1)
        self._cube_opacity_edit = QLineEdit("0.50"); self._cube_opacity_edit.setFixedWidth(60); self._cube_opacity_edit.setAlignment(Qt.AlignRight)
        r1.addWidget(self._cube_opacity_edit)
        self._cube_opacity.valueChanged.connect(lambda v: self._cube_opacity_edit.setText(f"{v/100:.2f}"))
        self._cube_opacity_edit.returnPressed.connect(lambda: self._cube_opacity.setValue(int(float(self._cube_opacity_edit.text())*100)))
        crl.addLayout(r1)

        # 平滑 + 精度
        r2 = QHBoxLayout()
        _lbl = QLabel("平滑:"); _lbl._t = "平滑:"; r2.addWidget(_lbl)
        self._cube_blur = QSlider(Qt.Horizontal); self._cube_blur.setRange(0,30); self._cube_blur.setValue(15)
        r2.addWidget(self._cube_blur, 1)
        self._cube_blur_edit = QLineEdit("1.5"); self._cube_blur_edit.setFixedWidth(60); self._cube_blur_edit.setAlignment(Qt.AlignRight)
        r2.addWidget(self._cube_blur_edit)
        self._cube_blur.valueChanged.connect(lambda v: self._cube_blur_edit.setText(f"{v/10:.1f}"))
        self._cube_blur_edit.returnPressed.connect(lambda: self._cube_blur.setValue(int(float(self._cube_blur_edit.text())*10)))
        r2.addSpacing(20)
        _lbl = QLabel("精度x"); _lbl._t = "精度x"; r2.addWidget(_lbl)
        self._cube_upsample = QSlider(Qt.Horizontal); self._cube_upsample.setRange(1,5); self._cube_upsample.setValue(3)
        r2.addWidget(self._cube_upsample, 1)
        self._cube_upsample_edit = QLineEdit("3"); self._cube_upsample_edit.setFixedWidth(60); self._cube_upsample_edit.setAlignment(Qt.AlignRight)
        r2.addWidget(self._cube_upsample_edit)
        self._cube_upsample.valueChanged.connect(lambda v: self._cube_upsample_edit.setText(str(v)))
        self._cube_upsample_edit.returnPressed.connect(lambda: self._cube_upsample.setValue(int(self._cube_upsample_edit.text())))
        crl.addLayout(r2)

        # 样式 + 正负瓣 + 描边
        r3 = QHBoxLayout()
        _lbl = QLabel("样式:"); _lbl._t = "样式:"; r3.addWidget(_lbl)
        self._surf_cube = QComboBox(); self._surf_cube.addItems(["solid","mesh","contour","dot"])
        r3.addWidget(self._surf_cube)
        r3.addSpacing(12)
        _lbl = QLabel("正瓣:"); _lbl._t = "正瓣:"; r3.addWidget(_lbl)
        self._btn_pos = QPushButton(); self._btn_pos.setFixedSize(22,22)
        self._btn_pos.setStyleSheet(f"background-color:{self._pos_color};border:1px solid #888;border-radius:2px;")
        self._btn_pos.clicked.connect(self._pick_pos_color)
        r3.addWidget(self._btn_pos)
        r3.addSpacing(8)
        _lbl = QLabel("负瓣:"); _lbl._t = "负瓣:"; r3.addWidget(_lbl)
        self._btn_neg = QPushButton(); self._btn_neg.setFixedSize(22,22)
        self._btn_neg.setStyleSheet(f"background-color:{self._neg_color};border:1px solid #888;border-radius:2px;")
        self._btn_neg.clicked.connect(self._pick_neg_color)
        r3.addWidget(self._btn_neg)
        r3.addSpacing(12)
        self._cube_outlined = QCheckBox("描边"); self._cube_outlined._t = "描边"
        self._cube_outlined.setChecked(True)
        self._cube_outlined.toggled.connect(lambda c: self._cube_outline.setValue(5 if c else 0))
        r3.addWidget(self._cube_outlined)
        _lbl = QLabel("描边宽度:"); _lbl._t = "描边宽度:"; r3.addWidget(_lbl)
        self._cube_outline = QSlider(Qt.Horizontal); self._cube_outline.setRange(0,20); self._cube_outline.setValue(5)
        self._cube_outline.setMaximumWidth(240)
        r3.addWidget(self._cube_outline)
        self._cube_outline_edit = QLineEdit("5"); self._cube_outline_edit.setFixedWidth(60); self._cube_outline_edit.setAlignment(Qt.AlignRight)
        r3.addWidget(self._cube_outline_edit)
        self._cube_outline.valueChanged.connect(lambda v: self._cube_outline_edit.setText(str(v)))
        self._cube_outline_edit.returnPressed.connect(lambda: self._cube_outline.setValue(int(self._cube_outline_edit.text())))
        r3.addStretch()
        crl.addLayout(r3)
        layout.addWidget(gb_cr)

        # ── 导出 ──
        gb_cout = QGroupBox("导出"); gb_cout._t = "导出"
        col = QVBoxLayout(gb_cout)
        cbtn_row = QHBoxLayout()
        self._btn_cube_peek = QPushButton("Cube 预览"); self._btn_cube_peek._t = "Cube 预览"; self._btn_cube_peek.setObjectName("PrimaryBtn"); self._btn_cube_peek.setEnabled(False)
        self._btn_cube_peek.clicked.connect(self._on_quick_peek)
        cbtn_row.addWidget(self._btn_cube_peek)
        self._btn_cube_save = QPushButton("保存 Cube 图 (PNG)"); self._btn_cube_save._t = "保存 Cube 图 (PNG)"; self._btn_cube_save.setEnabled(False)
        self._btn_cube_save.clicked.connect(self._on_export_png)
        cbtn_row.addWidget(self._btn_cube_save)
        self._btn_cube_svg = QPushButton("保存 Cube 图 (SVG)"); self._btn_cube_svg._t = "保存 Cube 图 (SVG)"; self._btn_cube_svg.setEnabled(False)
        self._btn_cube_svg.clicked.connect(self._on_export_svg)
        cbtn_row.addWidget(self._btn_cube_svg)
        col.addLayout(cbtn_row)
        oh_gif = QHBoxLayout()
        _lbl = QLabel(tr("旋转GIF:")); _lbl._t = "旋转GIF:"; oh_gif.addWidget(_lbl)
        self._gif_axis = QComboBox(); self._gif_axis.addItems(["X", "Y", "Z"]); self._gif_axis.setCurrentText("Y")
        self._gif_axis._t_items = ["X", "Y", "Z"]
        oh_gif.addWidget(self._gif_axis)
        _lbl = QLabel("FPS:"); _lbl._t = "FPS:"; oh_gif.addWidget(_lbl)
        self._gif_fps = QLineEdit("10"); self._gif_fps.setFixedWidth(40); self._gif_fps.setAlignment(Qt.AlignRight)
        oh_gif.addWidget(self._gif_fps)
        _lbl = QLabel("帧:"); _lbl._t = "帧:"; oh_gif.addWidget(_lbl)
        self._gif_frames = QLineEdit("120"); self._gif_frames.setFixedWidth(45); self._gif_frames.setAlignment(Qt.AlignRight)
        oh_gif.addWidget(self._gif_frames)
        self._btn_preview_gif = QPushButton(tr("预览 GIF")); self._btn_preview_gif._t = "预览 GIF"
        self._btn_preview_gif.clicked.connect(self._on_preview_gif)
        oh_gif.addWidget(self._btn_preview_gif)
        self._btn_gif = QPushButton(tr("保存 GIF")); self._btn_gif._t = "保存 GIF"
        self._btn_gif.clicked.connect(self._on_export_gif)
        oh_gif.addWidget(self._btn_gif)
        oh_gif.addStretch()
        col.addLayout(oh_gif)
        layout.addWidget(gb_cout)
        layout.addStretch()

        self._retranslate_ui()
        on_language_changed(self._retranslate_ui)

    def _retranslate_ui(self):
        for w in self.findChildren((QLabel, QPushButton, QCheckBox)):
            if hasattr(w, '_t'):
                w.setText(tr(w._t))
        for w in self.findChildren(QGroupBox):
            if hasattr(w, '_t'):
                w.setTitle(tr(w._t))
        idx = self._gif_axis.currentIndex()
        self._gif_axis.clear()
        self._gif_axis.addItems(["X", "Y", "Z"])
        self._gif_axis.setCurrentIndex(idx)

    def _pick_pos_color(self):
        c = QColorDialog.getColor(QColor(self._pos_color), self, tr("正瓣颜色"))
        if c.isValid():
            self._pos_color = c.name()
            self._btn_pos.setStyleSheet(f"background-color:{self._pos_color};border:1px solid #888;border-radius:2px;")

    def _pick_neg_color(self):
        c = QColorDialog.getColor(QColor(self._neg_color), self, tr("负瓣颜色"))
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
            mo_blur=self._cube_blur.value() / 10.0,
            mo_upsample=self._cube_upsample.value(),
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
        self._btn_cube_svg.setEnabled(enabled)

    def _on_quick_peek(self):
        self.quick_peek_requested.emit(self.get_kwargs())

    def _on_export_png(self):
        self.export_png_requested.emit(self.get_kwargs())

    def _on_export_svg(self):
        self.export_svg_requested.emit(self.get_kwargs())

    def _on_preview_gif(self):
        kw = self.get_kwargs()
        kw["gif_rot"] = self._gif_axis.currentText()
        try: kw["gif_fps"] = int(self._gif_fps.text())
        except ValueError: kw["gif_fps"] = 10
        try: kw["rot_frames"] = int(self._gif_frames.text())
        except ValueError: kw["rot_frames"] = 120
        self.preview_gif_requested.emit(kw)

    def _on_export_gif(self):
        kw = self.get_kwargs()
        kw["gif_rot"] = self._gif_axis.currentText()
        try: kw["gif_fps"] = int(self._gif_fps.text())
        except ValueError: kw["gif_fps"] = 10
        try: kw["rot_frames"] = int(self._gif_frames.text())
        except ValueError: kw["rot_frames"] = 120
        self.export_gif_requested.emit(kw)
