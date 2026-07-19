"""Tab 2: ESP 等值面可视化。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QComboBox, QCheckBox, QLabel, QSlider, QLineEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal

from ..i18n import tr, on_language_changed


class ESPTab(QWidget):
    """ESP 生成 + 渲染控制 Tab。"""

    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    gen_esp_requested = pyqtSignal()
    detect_range_requested = pyqtSignal()
    quick_peek_requested = pyqtSignal(dict)
    export_png_requested = pyqtSignal(dict)
    export_svg_requested = pyqtSignal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── ESP 生成 ──
        gb_mw = QGroupBox("Multiwfn 生成 ESP"); gb_mw._t = "Multiwfn 生成 ESP"
        mwl = QVBoxLayout(gb_mw)
        self._btn_gen_esp = QPushButton("生成 ESP Cube"); self._btn_gen_esp._t = "生成 ESP Cube"
        self._btn_gen_esp.setMaximumWidth(200)
        self._btn_gen_esp.clicked.connect(self.gen_esp_requested.emit)
        mwl.addWidget(self._btn_gen_esp)
        layout.addWidget(gb_mw)

        # ── 渲染控制 ──
        gb_er = QGroupBox("渲染"); gb_er._t = "渲染"
        erl = QVBoxLayout(gb_er)

        ih_esp = QHBoxLayout()
        _lbl = QLabel("等值:"); _lbl._t = "等值:"; ih_esp.addWidget(_lbl)
        self._iso_esp = QSlider(Qt.Horizontal); self._iso_esp.setRange(1, 200); self._iso_esp.setValue(50)
        ih_esp.addWidget(self._iso_esp)
        self._iso_esp_edit = QLineEdit("0.0050"); self._iso_esp_edit.setFixedWidth(60); self._iso_esp_edit.setAlignment(Qt.AlignRight)
        ih_esp.addWidget(self._iso_esp_edit)
        self._iso_esp.valueChanged.connect(lambda v: self._iso_esp_edit.setText(f"{v/10000:.4f}"))
        self._iso_esp_edit.returnPressed.connect(lambda: self._iso_esp.setValue(int(float(self._iso_esp_edit.text())*10000)))
        erl.addLayout(ih_esp)

        r1e = QHBoxLayout()
        _lbl = QLabel("样式:"); _lbl._t = "样式:"; r1e.addWidget(_lbl)
        self._surf_esp = QComboBox(); self._surf_esp.addItems(["solid", "mesh", "contour", "dot"])
        r1e.addWidget(self._surf_esp)
        _lbl = QLabel("调色板:"); _lbl._t = "调色板:"; r1e.addWidget(_lbl)
        self._esp_cmap = QComboBox()
        self._esp_cmap.addItems(["rainbow","coolwarm","RdBu","viridis","plasma","spectral","batlow","roma","vik","bam","managua"])
        self._esp_cmap.setCurrentText("rainbow"); r1e.addWidget(self._esp_cmap)
        erl.addLayout(r1e)

        r2e = QHBoxLayout()
        self._chk_esp_cbar = QCheckBox("色彩刻度轴"); self._chk_esp_cbar._t = "色彩刻度轴"; r2e.addWidget(self._chk_esp_cbar)
        _lbl = QLabel("范围:"); _lbl._t = "范围:"; r2e.addWidget(_lbl)
        self._esp_range = QLineEdit(""); self._esp_range.setMaximumWidth(120)
        self._esp_range.setPlaceholderText("如 -0.03,0.03"); self._esp_range._t = "如 -0.03,0.03"; r2e.addWidget(self._esp_range)
        self._btn_detect_esp = QPushButton("检测"); self._btn_detect_esp._t = "检测"
        self._btn_detect_esp.setFixedWidth(50)
        self._btn_detect_esp.clicked.connect(self.detect_range_requested.emit)
        r2e.addWidget(self._btn_detect_esp)
        self._chk_esp_sym = QCheckBox("对称"); self._chk_esp_sym._t = "对称"
        self._chk_esp_sym.setChecked(True)
        self._chk_esp_sym.toggled.connect(lambda checked: self._symmetrize_text() if checked else None)
        r2e.addWidget(self._chk_esp_sym)
        self._chk_esp_color = QCheckBox("ESP 着色"); self._chk_esp_color._t = "ESP 着色"; self._chk_esp_color.setChecked(True)
        r2e.addWidget(self._chk_esp_color); r2e.addStretch()
        erl.addLayout(r2e)

        layout.addWidget(gb_er)

        # ── 导出 ──
        gb_eo = QGroupBox("导出"); gb_eo._t = "导出"
        eol = QVBoxLayout(gb_eo)
        eoh = QHBoxLayout()
        self._btn_esp_peek = QPushButton("快速预览 400px"); self._btn_esp_peek._t = "快速预览 400px"
        self._btn_esp_peek.clicked.connect(self._on_quick_peek); self._btn_esp_peek.setEnabled(False)
        eoh.addWidget(self._btn_esp_peek)
        self._btn_esp_save = QPushButton("出图 (PNG)"); self._btn_esp_save._t = "出图 (PNG)"
        self._btn_esp_save.setObjectName("PrimaryBtn")
        self._btn_esp_save.clicked.connect(self._on_export_png); self._btn_esp_save.setEnabled(False)
        eoh.addWidget(self._btn_esp_save)
        self._btn_esp_svg = QPushButton("出图 (SVG)"); self._btn_esp_svg._t = "出图 (SVG)"
        self._btn_esp_svg.clicked.connect(self._on_export_svg); self._btn_esp_svg.setEnabled(False)
        eoh.addWidget(self._btn_esp_svg)
        eol.addLayout(eoh)
        layout.addWidget(gb_eo)
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

    def set_range_text(self, text: str):
        """外部设置范围文本（如检测到的范围），若对称模式开启则自动对称化。"""
        self._esp_range.setText(text)
        if self._chk_esp_sym.isChecked():
            self._symmetrize_text()

    def _symmetrize_text(self):
        """将范围文本对称化为 [-M, M]，M = max(abs(min), abs(max))。"""
        txt = self._esp_range.text().strip()
        if not txt:
            return
        try:
            parts = [float(x.strip()) for x in txt.split(",")]
            if len(parts) != 2:
                return
            m = max(abs(parts[0]), abs(parts[1]))
            self._esp_range.setText(f"{-m:.6g},{m:.6g}")
        except ValueError:
            pass

    def get_kwargs(self) -> dict:
        """返回 ESP 渲染参数。"""
        kwargs = dict(
            iso=self._iso_esp.value() / 10000.0,
            cmap_palette=self._esp_cmap.currentText(),
        )
        if self._chk_esp_color.isChecked():
            kwargs["dens"] = True
        if self._chk_esp_cbar.isChecked():
            kwargs["cbar"] = True
        rng = self._esp_range.text().strip()
        if rng:
            try:
                parts = [float(x.strip()) for x in rng.split(",")]
                if len(parts) == 2:
                    if self._chk_esp_sym.isChecked():
                        m = max(abs(parts[0]), abs(parts[1]))
                        kwargs["cmap_range"] = (-m, m)
                    else:
                        kwargs["cmap_range"] = (parts[0], parts[1])
            except ValueError:
                pass
        return kwargs

    def set_buttons_enabled(self, enabled):
        self._btn_esp_peek.setEnabled(enabled)
        self._btn_esp_save.setEnabled(enabled)
        self._btn_esp_svg.setEnabled(enabled)

    def _on_quick_peek(self):
        self.quick_peek_requested.emit(self.get_kwargs())

    def _on_export_png(self):
        self.export_png_requested.emit(self.get_kwargs())

    def _on_export_svg(self):
        self.export_svg_requested.emit(self.get_kwargs())
