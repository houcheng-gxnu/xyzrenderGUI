"""Tab 2: ESP 等值面可视化。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QComboBox, QCheckBox, QLabel, QSlider, QLineEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal


class ESPTab(QWidget):
    """ESP 生成 + 渲染控制 Tab。"""

    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    gen_esp_requested = pyqtSignal()
    quick_peek_requested = pyqtSignal(dict)
    export_png_requested = pyqtSignal(dict)
    export_svg_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── ESP 生成 ──
        gb_mw = QGroupBox("Multiwfn 生成 ESP")
        mwl = QVBoxLayout(gb_mw)
        self._btn_gen_esp = QPushButton("生成 ESP Cube")
        self._btn_gen_esp.setMaximumWidth(200)
        self._btn_gen_esp.clicked.connect(self.gen_esp_requested.emit)
        mwl.addWidget(self._btn_gen_esp)
        layout.addWidget(gb_mw)

        # ── 渲染控制 ──
        gb_er = QGroupBox("渲染")
        erl = QVBoxLayout(gb_er)

        ih_esp = QHBoxLayout()
        ih_esp.addWidget(QLabel("等值:"))
        self._iso_esp = QSlider(Qt.Horizontal); self._iso_esp.setRange(1, 200); self._iso_esp.setValue(50)
        ih_esp.addWidget(self._iso_esp)
        self._iso_esp_label = QLabel("0.0050")
        ih_esp.addWidget(self._iso_esp_label)
        self._iso_esp.valueChanged.connect(lambda v: self._iso_esp_label.setText(f"{v/10000:.4f}"))
        erl.addLayout(ih_esp)

        r1e = QHBoxLayout()
        r1e.addWidget(QLabel("样式:"))
        self._surf_esp = QComboBox(); self._surf_esp.addItems(["solid", "mesh", "contour", "dot"])
        r1e.addWidget(self._surf_esp)
        r1e.addWidget(QLabel("调色板:"))
        self._esp_cmap = QComboBox()
        self._esp_cmap.addItems(["rainbow","coolwarm","RdBu","viridis","plasma","spectral","batlow","roma","vik","bam","managua"])
        self._esp_cmap.setCurrentText("rainbow"); r1e.addWidget(self._esp_cmap)
        erl.addLayout(r1e)

        r2e = QHBoxLayout()
        self._chk_esp_cbar = QCheckBox("色彩刻度轴"); r2e.addWidget(self._chk_esp_cbar)
        r2e.addWidget(QLabel("范围:"))
        self._esp_range = QLineEdit(""); self._esp_range.setMaximumWidth(120)
        self._esp_range.setPlaceholderText("如 -0.03,0.03"); r2e.addWidget(self._esp_range)
        self._chk_esp_color = QCheckBox("ESP 着色"); self._chk_esp_color.setChecked(True)
        r2e.addWidget(self._chk_esp_color); r2e.addStretch()
        erl.addLayout(r2e)

        layout.addWidget(gb_er)

        # ── 导出 ──
        gb_eo = QGroupBox("导出")
        eol = QVBoxLayout(gb_eo)
        eoh = QHBoxLayout()
        self._btn_esp_peek = QPushButton("快速预览 400px")
        self._btn_esp_peek.clicked.connect(self._on_quick_peek); self._btn_esp_peek.setEnabled(False)
        eoh.addWidget(self._btn_esp_peek)
        self._btn_esp_save = QPushButton("出图 (PNG)")
        self._btn_esp_save.setObjectName("PrimaryBtn")
        self._btn_esp_save.clicked.connect(self._on_export_png); self._btn_esp_save.setEnabled(False)
        eoh.addWidget(self._btn_esp_save)
        self._btn_esp_svg = QPushButton("出图 (SVG)")
        self._btn_esp_svg.clicked.connect(self._on_export_svg); self._btn_esp_svg.setEnabled(False)
        eoh.addWidget(self._btn_esp_svg)
        eol.addLayout(eoh)
        layout.addWidget(gb_eo)
        layout.addStretch()

    def get_kwargs(self) -> dict:
        """返回 ESP 渲染参数。"""
        kwargs = dict(
            iso=self._iso_esp.value() / 10000.0,
            surface_style=self._surf_esp.currentText(),
            cmap_palette=self._esp_cmap.currentText(),
        )
        if self._chk_esp_color.isChecked():
            kwargs["dens"] = True  # 会被 viewer 层替换为 esp
        if self._chk_esp_cbar.isChecked():
            kwargs["cbar"] = True
        rng = self._esp_range.text().strip()
        if rng:
            try:
                parts = [float(x.strip()) for x in rng.split(",")]
                if len(parts) == 2:
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
