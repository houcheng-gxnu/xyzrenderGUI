"""Tab 3: MO 轨道浏览 + 等值面渲染。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QComboBox, QCheckBox, QLabel, QSlider, QLineEdit, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QColorDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont

from ..i18n import tr, on_language_changed


class MOTab(QWidget):
    """MO 轨道浏览 + cube 生成 + 渲染控制。"""

    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    mo_selected_signal = pyqtSignal(str)         # 双击选中轨道
    gen_mo_cube_requested = pyqtSignal()
    quick_peek_requested = pyqtSignal(dict)
    export_png_requested = pyqtSignal(dict)
    export_svg_requested = pyqtSignal(dict)
    export_gif_requested = pyqtSignal(dict)
    preview_gif_requested = pyqtSignal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── 轨道浏览器 ──
        gb_mogen = QGroupBox("轨道浏览器"); gb_mogen._t = "轨道浏览器"
        mogl = QVBoxLayout(gb_mogen)
        self._mo_tabs = QTabWidget()
        self._mo_tabs.setMinimumHeight(360)
        self._mo_table_alpha = self._make_mo_table()
        self._mo_tabs.addTab(self._mo_table_alpha, "α 轨道")
        self._mo_table_beta = None
        mogl.addWidget(self._mo_tabs, 1)
        _hint = QLabel("双击行预览轨道")
        _hint._t = "双击行预览轨道"
        _hint.setStyleSheet("color: #888; font-size: 9pt; padding: 2px 0;")
        mogl.addWidget(_hint)
        layout.addWidget(gb_mogen)

        # ── 渲染控制 ──
        gb_mr = QGroupBox("渲染"); gb_mr._t = "渲染"
        mrl = QVBoxLayout(gb_mr)

        mor = QHBoxLayout()
        _lbl = QLabel("网格:"); _lbl._t = "网格:"; mor.addWidget(_lbl)
        self._mo_grid_combo = QComboBox(); self._mo_grid_combo.addItems(["1","2","3"]); self._mo_grid_combo.setCurrentIndex(1)
        self._mo_grid_combo.setMinimumWidth(60); mor.addWidget(self._mo_grid_combo)
        mor.addSpacing(6); _lbl = QLabel("样式:"); _lbl._t = "样式:"; mor.addWidget(_lbl)
        self._surf_mo = QComboBox(); self._surf_mo.addItems(["solid","mesh","contour","dot"])
        self._surf_mo.setMinimumWidth(90); mor.addWidget(self._surf_mo)
        mor.addSpacing(6); _lbl = QLabel("正瓣:"); _lbl._t = "正瓣:"; mor.addWidget(_lbl)
        self._mo_pos_color_btn = QPushButton(); self._mo_pos_color_btn.setFixedSize(22,22)
        self._mo_pos_color_btn.setStyleSheet("background-color:#00aaff;border:1px solid #888;border-radius:2px;")
        self._mo_pos_color_btn.clicked.connect(lambda: self._pick_mo_color("pos"))
        mor.addWidget(self._mo_pos_color_btn)
        mor.addSpacing(4); _lbl = QLabel("负瓣:"); _lbl._t = "负瓣:"; mor.addWidget(_lbl)
        self._mo_neg_color_btn = QPushButton(); self._mo_neg_color_btn.setFixedSize(22,22)
        self._mo_neg_color_btn.setStyleSheet("background-color:#ff557f;border:1px solid #888;border-radius:2px;")
        self._mo_neg_color_btn.clicked.connect(lambda: self._pick_mo_color("neg"))
        mor.addWidget(self._mo_neg_color_btn)
        self._mo_pos_color = "#00aaff"
        self._mo_neg_color = "#ff557f"
        mor.addSpacing(8)
        self._chk_flat_mo = QCheckBox("平面"); self._chk_flat_mo._t = "平面"; mor.addWidget(self._chk_flat_mo)
        self._chk_mo_outlined = QCheckBox("描边"); self._chk_mo_outlined._t = "描边"; self._chk_mo_outlined.setChecked(True); mor.addWidget(self._chk_mo_outlined)
        self._chk_mo_outlined.toggled.connect(self._on_outlined_toggled)
        mor.addStretch(); mrl.addLayout(mor)

        mo2 = QHBoxLayout(); _lbl = QLabel("描边宽度:"); _lbl._t = "描边宽度:"; mo2.addWidget(_lbl)
        self._mo_outline = QSlider(Qt.Horizontal); self._mo_outline.setRange(0,20); self._mo_outline.setValue(5)
        mo2.addWidget(self._mo_outline, 1)
        self._mo_outline_edit = QLineEdit("5"); self._mo_outline_edit.setFixedWidth(60); self._mo_outline_edit.setAlignment(Qt.AlignRight)
        mo2.addWidget(self._mo_outline_edit)
        self._mo_outline.valueChanged.connect(lambda v: self._mo_outline_edit.setText(str(v)))
        self._mo_outline_edit.returnPressed.connect(lambda: self._mo_outline.setValue(int(self._mo_outline_edit.text())))
        mo2.addSpacing(20); _lbl = QLabel("平滑:"); _lbl._t = "平滑:"; mo2.addWidget(_lbl)
        self._mo_blur = QSlider(Qt.Horizontal); self._mo_blur.setRange(0,30); self._mo_blur.setValue(15)
        mo2.addWidget(self._mo_blur, 1)
        self._mo_blur_edit = QLineEdit("1.5"); self._mo_blur_edit.setFixedWidth(60); self._mo_blur_edit.setAlignment(Qt.AlignRight)
        mo2.addWidget(self._mo_blur_edit)
        self._mo_blur.valueChanged.connect(lambda v: self._mo_blur_edit.setText(f"{v/10:.1f}"))
        self._mo_blur_edit.returnPressed.connect(lambda: self._mo_blur.setValue(int(float(self._mo_blur_edit.text())*10)))
        mo2.addStretch(); mrl.addLayout(mo2)

        mo3 = QHBoxLayout(); _lbl = QLabel("透明:"); _lbl._t = "透明:"; mo3.addWidget(_lbl)
        self._mo_opacity = QSlider(Qt.Horizontal); self._mo_opacity.setRange(10,100); self._mo_opacity.setValue(60)
        mo3.addWidget(self._mo_opacity, 1)
        self._mo_opacity_edit = QLineEdit("0.60"); self._mo_opacity_edit.setFixedWidth(60); self._mo_opacity_edit.setAlignment(Qt.AlignRight)
        mo3.addWidget(self._mo_opacity_edit)
        self._mo_opacity.valueChanged.connect(lambda v: self._mo_opacity_edit.setText(f"{v/100:.2f}"))
        self._mo_opacity_edit.returnPressed.connect(lambda: self._mo_opacity.setValue(int(float(self._mo_opacity_edit.text())*100)))
        mo3.addSpacing(20); _lbl = QLabel("精度x"); _lbl._t = "精度x"; mo3.addWidget(_lbl)
        self._mo_upsample = QSlider(Qt.Horizontal); self._mo_upsample.setRange(1,5); self._mo_upsample.setValue(3)
        mo3.addWidget(self._mo_upsample, 1)
        self._mo_upsample_edit = QLineEdit("3"); self._mo_upsample_edit.setFixedWidth(60); self._mo_upsample_edit.setAlignment(Qt.AlignRight)
        mo3.addWidget(self._mo_upsample_edit)
        self._mo_upsample.valueChanged.connect(lambda v: self._mo_upsample_edit.setText(str(v)))
        self._mo_upsample_edit.returnPressed.connect(lambda: self._mo_upsample.setValue(int(self._mo_upsample_edit.text())))
        mo3.addStretch(); mrl.addLayout(mo3)

        mo4 = QHBoxLayout(); _lbl = QLabel("等值:"); _lbl._t = "等值:"; mo4.addWidget(_lbl)
        self._iso_mo = QSlider(Qt.Horizontal); self._iso_mo.setRange(1,200); self._iso_mo.setValue(50)
        mo4.addWidget(self._iso_mo, 1)
        self._iso_mo_edit = QLineEdit("0.050"); self._iso_mo_edit.setFixedWidth(60); self._iso_mo_edit.setAlignment(Qt.AlignRight)
        mo4.addWidget(self._iso_mo_edit)
        self._iso_mo.valueChanged.connect(lambda v: self._iso_mo_edit.setText(f"{v/1000:.3f}"))
        self._iso_mo_edit.returnPressed.connect(lambda: self._iso_mo.setValue(int(float(self._iso_mo_edit.text())*1000)))
        mo4.addStretch(); mrl.addLayout(mo4)

        layout.addWidget(gb_mr)

        # ── 导出 ──
        gb_moout = QGroupBox("导出"); gb_moout._t = "导出"
        mool = QVBoxLayout(gb_moout)
        moh = QHBoxLayout()
        self._btn_mo_peek = QPushButton("快速预览 400px"); self._btn_mo_peek._t = "快速预览 400px"; self._btn_mo_peek.setEnabled(False)
        self._btn_mo_peek.clicked.connect(self._on_quick_peek)
        moh.addWidget(self._btn_mo_peek)
        self._btn_mo_save = QPushButton("出图 (PNG)"); self._btn_mo_save._t = "出图 (PNG)"; self._btn_mo_save.setEnabled(False)
        self._btn_mo_save.setObjectName("PrimaryBtn")
        self._btn_mo_save.clicked.connect(self._on_export_png)
        moh.addWidget(self._btn_mo_save)
        self._btn_mo_svg = QPushButton("出图 (SVG)"); self._btn_mo_svg._t = "出图 (SVG)"; self._btn_mo_svg.setEnabled(False)
        self._btn_mo_svg.clicked.connect(self._on_export_svg)
        moh.addWidget(self._btn_mo_svg)
        mool.addLayout(moh)
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
        mool.addLayout(oh_gif)
        layout.addWidget(gb_moout)
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
        # MO table headers
        headers = [tr("能量 (a.u.)"), tr("能量 (eV)"), tr("占据"), tr("标记")]
        self._mo_table_alpha.setHorizontalHeaderLabels(headers)
        if self._mo_table_beta is not None:
            self._mo_table_beta.setHorizontalHeaderLabels(headers)
        # Tab texts
        if self._mo_table_beta is not None:
            self._mo_tabs.setTabText(0, tr("α 轨道"))
            self._mo_tabs.setTabText(1, tr("β 轨道"))
        else:
            self._mo_tabs.setTabText(0, "Orbitals" if tr("轨道") != "轨道" else "轨道")

    def _make_mo_table(self):
        t = QTableWidget()
        t.setColumnCount(4)
        t.setHorizontalHeaderLabels([tr("能量 (a.u.)"), tr("能量 (eV)"), tr("占据"), tr("标记")])
        hdr = t.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        t.setSelectionBehavior(QTableWidget.SelectRows)
        t.setAlternatingRowColors(True)
        t.setEditTriggers(QTableWidget.NoEditTriggers)
        t.setStyleSheet("""
            QTableWidget {
                background: #FAFAFA;
                alternate-background-color: #F0F5FA;
                gridline-color: #E0E0E0;
                border: 1px solid #D0D0D0;
            }
            QTableWidget::item { padding: 2px 6px; }
            QHeaderView::section {
                background: #FFFFFF;
                color: #333333;
                padding: 4px;
                border: none;
                border-bottom: 2px solid #B0BEC5;
                font-weight: bold;
            }
        """)
        t.cellDoubleClicked.connect(self._on_row_dblclick)
        return t

    def _on_row_dblclick(self, row, _col):
        table = self._mo_tabs.currentWidget()
        orb = str(row + 1)
        if table is self._mo_table_beta:
            orb = f"b{orb}"
        self.mo_selected_signal.emit(orb)

    def _pick_mo_color(self, which):
        cur = self._mo_pos_color if which == "pos" else self._mo_neg_color
        label = tr("正瓣颜色") if which == "pos" else tr("负瓣颜色")
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
        # 从当前表格获取选中行
        table = self._mo_tabs.currentWidget()
        rows = set(i.row() for i in table.selectedItems()) if table is not None else set()
        if rows:
            row = next(iter(rows))
            orb = str(row + 1)
            if table is self._mo_table_beta:
                orb = f"b{orb}"
            self.mo_selected_signal.emit(orb)
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
