"""Tab: IGMH 分析 — 片段定义 + NCI 表面渲染。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QComboBox, QCheckBox, QLabel, QSlider, QLineEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal

from ..i18n import tr, on_language_changed


class IGMHTab(QWidget):
    """IGMH 片段定义 + NCI 表面渲染控制。"""

    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    run_igmh_requested = pyqtSignal()
    quick_peek_requested = pyqtSignal(dict)
    export_png_requested = pyqtSignal(dict)
    export_svg_requested = pyqtSignal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── 片段定义 ──
        gb_frag = QGroupBox("片段定义 (用于 IGMH 分析)"); gb_frag._t = "片段定义 (用于 IGMH 分析)"
        fgl = QVBoxLayout(gb_frag)

        fh1 = QHBoxLayout(); _lbl = QLabel("片段1:"); _lbl._t = "片段1:"; fh1.addWidget(_lbl)
        self._igmh_frag1 = QLineEdit(); self._igmh_frag1.setPlaceholderText("如 1-5,10-12"); self._igmh_frag1._t = "如 1-5,10-12"
        fh1.addWidget(self._igmh_frag1); fgl.addLayout(fh1)

        fh2 = QHBoxLayout(); _lbl = QLabel("片段2:"); _lbl._t = "片段2:"; fh2.addWidget(_lbl)
        self._igmh_frag2 = QLineEdit(); self._igmh_frag2.setPlaceholderText("如 6-9 或 c (补集)"); self._igmh_frag2._t = "如 6-9 或 c (补集)"
        fh2.addWidget(self._igmh_frag2); fgl.addLayout(fh2)

        # 画布点选片段
        fh_pick = QHBoxLayout()
        _lbl = QLabel("画布点选片段:"); _lbl._t = "画布点选片段:"; fh_pick.addWidget(_lbl)
        self._btn_pick_frag1 = QPushButton("选片段1 (蓝)"); self._btn_pick_frag1._t = "选片段1 (蓝)"; self._btn_pick_frag1.setCheckable(True); self._btn_pick_frag1.setChecked(True)
        fh_pick.addWidget(self._btn_pick_frag1)
        self._btn_pick_frag2 = QPushButton("选片段2 (红)"); self._btn_pick_frag2._t = "选片段2 (红)"; self._btn_pick_frag2.setCheckable(True)
        fh_pick.addWidget(self._btn_pick_frag2)
        self._btn_pick_clear = QPushButton("清除片段"); self._btn_pick_clear._t = "清除片段"
        fh_pick.addWidget(self._btn_pick_clear)
        fh_pick.addStretch()
        fgl.addLayout(fh_pick)

        fh3 = QHBoxLayout()
        _lbl = QLabel("网格质量:"); _lbl._t = "网格质量:"; fh3.addWidget(_lbl)
        self._igmh_grid = QComboBox(); self._igmh_grid.addItems(["1 (快速)", "2 (标准)", "3 (精细)"])
        self._igmh_grid.setCurrentIndex(1)
        fh3.addWidget(self._igmh_grid); fh3.addStretch()
        fgl.addLayout(fh3)

        self._btn_igmh_run = QPushButton("运行 IGMH 分析"); self._btn_igmh_run._t = "运行 IGMH 分析"
        self._btn_igmh_run.setObjectName("PrimaryBtn")
        self._btn_igmh_run.clicked.connect(self.run_igmh_requested.emit)
        fgl.addWidget(self._btn_igmh_run)
        layout.addWidget(gb_frag)

        # ── NCI 表面渲染 ──
        gb_nci = QGroupBox("NCI 表面渲染"); gb_nci._t = "NCI 表面渲染"
        ncil = QVBoxLayout(gb_nci)

        r1i = QHBoxLayout()
        _lbl = QLabel("等值:"); _lbl._t = "等值:"; r1i.addWidget(_lbl)
        self._igmh_iso = QSlider(Qt.Horizontal); self._igmh_iso.setRange(1,100); self._igmh_iso.setValue(5)
        self._igmh_iso_edit = QLineEdit("0.005"); self._igmh_iso_edit.setFixedWidth(60); self._igmh_iso_edit.setAlignment(Qt.AlignRight)
        self._igmh_iso.valueChanged.connect(lambda v: self._igmh_iso_edit.setText(f"{v/1000:.3f}"))
        self._igmh_iso_edit.returnPressed.connect(lambda: self._igmh_iso.setValue(int(float(self._igmh_iso_edit.text())*1000)))
        r1i.addWidget(self._igmh_iso); r1i.addWidget(self._igmh_iso_edit)
        ncil.addLayout(r1i)

        r2i = QHBoxLayout()
        _lbl = QLabel("着色:"); _lbl._t = "着色:"; r2i.addWidget(_lbl)
        self._igmh_mode = QComboBox(); self._igmh_mode.addItems(["avg", "pixel", "uniform"])
        r2i.addWidget(self._igmh_mode)
        _lbl = QLabel("样式:"); _lbl._t = "样式:"; r2i.addWidget(_lbl)
        self._igmh_surf = QComboBox(); self._igmh_surf.addItems(["solid", "mesh"])
        r2i.addWidget(self._igmh_surf); r2i.addStretch()
        ncil.addLayout(r2i)
        layout.addWidget(gb_nci)

        # ── 导出 ──
        gb_io = QGroupBox("导出"); gb_io._t = "导出"
        iol = QVBoxLayout(gb_io)
        ioh = QHBoxLayout()
        self._btn_igmh_peek = QPushButton("NCI 预览"); self._btn_igmh_peek._t = "NCI 预览"; self._btn_igmh_peek.setEnabled(False)
        self._btn_igmh_peek.clicked.connect(self._on_quick_peek)
        ioh.addWidget(self._btn_igmh_peek)
        self._btn_igmh_nci = QPushButton("NCI 出图 (PNG)"); self._btn_igmh_nci._t = "NCI 出图 (PNG)"; self._btn_igmh_nci.setEnabled(False)
        self._btn_igmh_nci.setObjectName("PrimaryBtn")
        self._btn_igmh_nci.clicked.connect(self._on_export_png)
        ioh.addWidget(self._btn_igmh_nci)
        self._btn_igmh_svg = QPushButton("NCI 出图 (SVG)"); self._btn_igmh_svg._t = "NCI 出图 (SVG)"; self._btn_igmh_svg.setEnabled(False)
        self._btn_igmh_svg.clicked.connect(self._on_export_svg)
        ioh.addWidget(self._btn_igmh_svg)
        iol.addLayout(ioh)
        layout.addWidget(gb_io)
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
        for w in self.findChildren(QLineEdit):
            if hasattr(w, '_t'):
                w.setPlaceholderText(tr(w._t))
        # Grid quality combo items
        self._igmh_grid.clear()
        self._igmh_grid.addItems([tr("1 (快速)"), tr("2 (标准)"), tr("3 (精细)")])
        self._igmh_grid.setCurrentIndex(1)

    def set_igmh_enabled(self, enabled: bool):
        pass

    def get_kwargs(self) -> dict:
        return dict(
            iso=self._igmh_iso.value() / 1000.0,
            nci_mode=self._igmh_mode.currentText(),
            surface_style=self._igmh_surf.currentText(),
        )

    def set_buttons_enabled(self, enabled):
        self._btn_igmh_nci.setEnabled(enabled)
        self._btn_igmh_svg.setEnabled(enabled)
        self._btn_igmh_peek.setEnabled(enabled)

    def _on_quick_peek(self):
        self.quick_peek_requested.emit(self.get_kwargs())

    def _on_export_png(self):
        self.export_png_requested.emit(self.get_kwargs())

    def _on_export_svg(self):
        self.export_svg_requested.emit(self.get_kwargs())
