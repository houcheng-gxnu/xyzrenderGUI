"""Tab 3: MO 轨道浏览 + 等值面渲染。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QComboBox, QCheckBox, QLabel, QSlider, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QColorDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont


class MOTab(QWidget):
    """MO 轨道浏览 + cube 生成 + 渲染控制。"""

    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    mo_selected_signal = pyqtSignal(str)         # 双击选中轨道
    gen_mo_cube_requested = pyqtSignal()
    quick_peek_requested = pyqtSignal(dict)
    export_png_requested = pyqtSignal(dict)
    export_svg_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── 轨道浏览器 ──
        gb_mogen = QGroupBox("轨道浏览器")
        mogl = QVBoxLayout(gb_mogen)
        self._mo_tabs = QTabWidget()
        self._mo_tabs.setMinimumHeight(360)
        self._mo_table_alpha = self._make_mo_table()
        self._mo_tabs.addTab(self._mo_table_alpha, "α 轨道")
        self._mo_table_beta = None
        mogl.addWidget(self._mo_tabs, 1)
        layout.addWidget(gb_mogen)

        # ── 渲染控制 ──
        gb_mr = QGroupBox("渲染")
        mrl = QVBoxLayout(gb_mr)

        mor = QHBoxLayout()
        mor.addWidget(QLabel("网格:"))
        self._mo_grid_combo = QComboBox(); self._mo_grid_combo.addItems(["1","2","3"]); self._mo_grid_combo.setCurrentIndex(1)
        self._mo_grid_combo.setMaximumWidth(36); mor.addWidget(self._mo_grid_combo)
        mor.addSpacing(6); mor.addWidget(QLabel("样式:"))
        self._surf_mo = QComboBox(); self._surf_mo.addItems(["solid","mesh","contour","dot"])
        self._surf_mo.setMaximumWidth(64); mor.addWidget(self._surf_mo)
        mor.addSpacing(6); mor.addWidget(QLabel("正瓣:"))
        self._mo_pos_color_btn = QPushButton(); self._mo_pos_color_btn.setFixedSize(22,22)
        self._mo_pos_color_btn.setStyleSheet("background-color:#6495ed;border:1px solid #888;border-radius:2px;")
        self._mo_pos_color_btn.clicked.connect(lambda: self._pick_mo_color("pos"))
        mor.addWidget(self._mo_pos_color_btn)
        mor.addSpacing(4); mor.addWidget(QLabel("负瓣:"))
        self._mo_neg_color_btn = QPushButton(); self._mo_neg_color_btn.setFixedSize(22,22)
        self._mo_neg_color_btn.setStyleSheet("background-color:#800000;border:1px solid #888;border-radius:2px;")
        self._mo_neg_color_btn.clicked.connect(lambda: self._pick_mo_color("neg"))
        mor.addWidget(self._mo_neg_color_btn)
        self._mo_pos_color = "#6495ed"
        self._mo_neg_color = "#800000"
        mor.addSpacing(8)
        self._chk_flat_mo = QCheckBox("平面"); mor.addWidget(self._chk_flat_mo)
        self._chk_mo_outlined = QCheckBox("描边"); mor.addWidget(self._chk_mo_outlined)
        self._chk_mo_outlined.toggled.connect(self._on_outlined_toggled)
        mor.addStretch(); mrl.addLayout(mor)

        mo2 = QHBoxLayout(); mo2.addWidget(QLabel("轮廓宽:"))
        self._mo_outline = QSlider(Qt.Horizontal); self._mo_outline.setRange(0,20); self._mo_outline.setValue(0)
        mo2.addWidget(self._mo_outline, 1)
        self._mo_outline_label = QLabel("0"); mo2.addWidget(self._mo_outline_label)
        self._mo_outline.valueChanged.connect(lambda v: self._mo_outline_label.setText(str(v)))
        mo2.addSpacing(20); mo2.addWidget(QLabel("平滑:"))
        self._mo_blur = QSlider(Qt.Horizontal); self._mo_blur.setRange(0,30); self._mo_blur.setValue(8)
        mo2.addWidget(self._mo_blur, 1)
        self._mo_blur_label = QLabel("0.8"); mo2.addWidget(self._mo_blur_label)
        self._mo_blur.valueChanged.connect(lambda v: self._mo_blur_label.setText(f"{v/10:.1f}"))
        mo2.addStretch(); mrl.addLayout(mo2)

        mo3 = QHBoxLayout(); mo3.addWidget(QLabel("透明:"))
        self._mo_opacity = QSlider(Qt.Horizontal); self._mo_opacity.setRange(10,100); self._mo_opacity.setValue(60)
        mo3.addWidget(self._mo_opacity, 1)
        self._mo_opacity_label = QLabel("0.60"); mo3.addWidget(self._mo_opacity_label)
        self._mo_opacity.valueChanged.connect(lambda v: self._mo_opacity_label.setText(f"{v/100:.2f}"))
        mo3.addSpacing(20); mo3.addWidget(QLabel("精度x"))
        self._mo_upsample = QSlider(Qt.Horizontal); self._mo_upsample.setRange(1,5); self._mo_upsample.setValue(3)
        mo3.addWidget(self._mo_upsample, 1)
        self._mo_upsample_label = QLabel("3"); mo3.addWidget(self._mo_upsample_label)
        self._mo_upsample.valueChanged.connect(lambda v: self._mo_upsample_label.setText(str(v)))
        mo3.addStretch(); mrl.addLayout(mo3)

        mo4 = QHBoxLayout(); mo4.addWidget(QLabel("等值:"))
        self._iso_mo = QSlider(Qt.Horizontal); self._iso_mo.setRange(1,200); self._iso_mo.setValue(50)
        mo4.addWidget(self._iso_mo, 1)
        self._iso_mo_label = QLabel("0.050"); mo4.addWidget(self._iso_mo_label)
        self._iso_mo.valueChanged.connect(lambda v: self._iso_mo_label.setText(f"{v/1000:.3f}"))
        mo4.addStretch(); mrl.addLayout(mo4)

        layout.addWidget(gb_mr)

        # ── 导出 ──
        gb_moout = QGroupBox("导出")
        mool = QVBoxLayout(gb_moout)
        moh = QHBoxLayout()
        self._btn_mo_peek = QPushButton("快速预览 400px"); self._btn_mo_peek.setEnabled(False)
        self._btn_mo_peek.clicked.connect(self._on_quick_peek)
        moh.addWidget(self._btn_mo_peek)
        self._btn_mo_save = QPushButton("出图 (PNG)"); self._btn_mo_save.setEnabled(False)
        self._btn_mo_save.setObjectName("PrimaryBtn")
        self._btn_mo_save.clicked.connect(self._on_export_png)
        moh.addWidget(self._btn_mo_save)
        self._btn_mo_svg = QPushButton("出图 (SVG)"); self._btn_mo_svg.setEnabled(False)
        self._btn_mo_svg.clicked.connect(self._on_export_svg)
        moh.addWidget(self._btn_mo_svg)
        mool.addLayout(moh)
        layout.addWidget(gb_moout)
        layout.addStretch()

    def _make_mo_table(self):
        t = QTableWidget()
        t.setColumnCount(5)
        t.setHorizontalHeaderLabels(["轨道", "能量 (a.u.)", "能量 (eV)", "占据", "标记"])
        hdr = t.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        t.setSelectionBehavior(QTableWidget.SelectRows)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.cellDoubleClicked.connect(self._on_row_dblclick)
        return t

    def _on_row_dblclick(self, row, _col):
        table = self._mo_tabs.currentWidget()
        it = table.item(row, 0)
        if not it:
            return
        orb = it.text().strip()
        if table is self._mo_table_beta:
            orb = f"b{orb}"
        self.mo_selected_signal.emit(orb)

    def _pick_mo_color(self, which):
        cur = self._mo_pos_color if which == "pos" else self._mo_neg_color
        label = "正瓣颜色" if which == "pos" else "负瓣颜色"
        c = QColorDialog.getColor(QColor(cur), self, label)
        if c.isValid():
            color = c.name()
            if which == "pos":
                self._mo_pos_color = color
                self._mo_pos_color_btn.setStyleSheet(f"background-color:{color};border:1px solid #888;border-radius:2px;")
            else:
                self._mo_neg_color = color
                self._mo_neg_color_btn.setStyleSheet(f"background-color:{color};border:1px solid #888;border-radius:2px;")

    def _on_outlined_toggled(self, checked):
        self._mo_outline.setValue(5 if checked else 0)

    def get_kwargs(self) -> dict:
        return dict(
            iso=self._iso_mo.value() / 1000.0,
            surface_style=self._surf_mo.currentText(),
            mo=True,
            opacity=self._mo_opacity.value() / 100.0,
            mo_pos_color=self._mo_pos_color,
            mo_neg_color=self._mo_neg_color,
            mo_outline_width=self._mo_outline.value() if self._mo_outline.value() > 0 else None,
            flat_mo=True if self._chk_flat_mo.isChecked() else None,
            mo_blur=self._mo_blur.value() / 10.0,
            mo_upsample=self._mo_upsample.value(),
        )

    def set_buttons_enabled(self, enabled):
        self._btn_mo_peek.setEnabled(enabled)
        self._btn_mo_save.setEnabled(enabled)
        self._btn_mo_svg.setEnabled(enabled)

    def _on_quick_peek(self):
        self.quick_peek_requested.emit(self.get_kwargs())

    def _on_export_png(self):
        self.export_png_requested.emit(self.get_kwargs())

    def _on_export_svg(self):
        self.export_svg_requested.emit(self.get_kwargs())
