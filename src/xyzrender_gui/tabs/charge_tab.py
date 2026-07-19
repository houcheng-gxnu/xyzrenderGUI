"""Tab: 电荷 — Multiwfn 计算 + 原子着色渲染。"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QPushButton,
    QComboBox, QCheckBox, QLabel, QSlider, QLineEdit, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
)
from PyQt5.QtCore import Qt, pyqtSignal

from ..config import CHARGE_TYPES, CMAP_PALETTES

from ..i18n import tr, on_language_changed


class ChargeTab(QWidget):
    """电荷计算 + 原子着色渲染控制。"""

    status_signal = pyqtSignal(str)
    log_signal = pyqtSignal(str)
    calc_requested = pyqtSignal()
    charge_type_changed = pyqtSignal(str)     # 切换电荷类型时通知 viewer 刷新范围
    quick_peek_requested = pyqtSignal(dict)
    export_png_requested = pyqtSignal(dict)
    export_svg_requested = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # ── 电荷计算 (类型 + 按钮同行) ──
        gb_ch = QGroupBox("电荷计算 (需 fchk 文件)"); gb_ch._t = "电荷计算 (需 fchk 文件)"
        ch_fl = QVBoxLayout(gb_ch)

        ch_h1 = QHBoxLayout()
        _lbl = QLabel("电荷类型:"); _lbl._t = "电荷类型:"; ch_h1.addWidget(_lbl)
        self._ch_type = QComboBox()
        self._ch_type.addItems(list(CHARGE_TYPES.keys()))
        self._ch_type.setCurrentText("ADCH")
        self._ch_type.currentTextChanged.connect(self.charge_type_changed.emit)
        ch_h1.addWidget(self._ch_type, 1)
        self._btn_ch_calc = QPushButton("计算"); self._btn_ch_calc._t = "计算"
        self._btn_ch_calc.setFixedWidth(100)
        self._btn_ch_calc.clicked.connect(self.calc_requested.emit)
        ch_h1.addWidget(self._btn_ch_calc)
        ch_fl.addLayout(ch_h1)

        self._ch_status = QLabel("")
        self._ch_status.setWordWrap(True)
        ch_fl.addWidget(self._ch_status)
        self._ch_progress = QProgressBar()
        self._ch_progress.setRange(0, 100)
        self._ch_progress.setVisible(False)
        ch_fl.addWidget(self._ch_progress)
        layout.addWidget(gb_ch)

        # ── 电荷结果表格 ──
        gb_table = QGroupBox("计算结果"); gb_table._t = "计算结果"
        tbl = QVBoxLayout(gb_table)
        self._charge_table = QTableWidget()
        self._charge_table.setColumnCount(3)
        self._charge_table.setHorizontalHeaderLabels([tr("序号"), tr("元素"), tr("电荷值")])
        hdr = self._charge_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        self._charge_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._charge_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._charge_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._charge_table.verticalHeader().setVisible(False)
        self._charge_table.setMaximumHeight(200)
        self._charge_table.setStyleSheet("""
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
        self._charge_table.setAlternatingRowColors(True)
        tbl.addWidget(self._charge_table)
        layout.addWidget(gb_table)

        # ── 原子着色渲染 ──
        gb_cmap = QGroupBox("原子着色渲染"); gb_cmap._t = "原子着色渲染"
        cm_l = QVBoxLayout(gb_cmap)

        ch_h2 = QHBoxLayout()
        _lbl = QLabel("色板:"); _lbl._t = "色板:"; ch_h2.addWidget(_lbl)
        self._ch_palette = QComboBox()
        self._ch_palette.addItems(CMAP_PALETTES)
        self._ch_palette.setCurrentText("coolwarm")
        ch_h2.addWidget(self._ch_palette)
        _lbl = QLabel("范围:"); _lbl._t = "范围:"; ch_h2.addWidget(_lbl)
        self._ch_rmin = QLineEdit("-0.5")
        self._ch_rmin.setFixedWidth(60)
        ch_h2.addWidget(self._ch_rmin)
        _lbl = QLabel("~"); _lbl._t = "~"; ch_h2.addWidget(_lbl)
        self._ch_rmax = QLineEdit("0.5")
        self._ch_rmax.setFixedWidth(60)
        ch_h2.addWidget(self._ch_rmax)
        self._ch_symm = QCheckBox("对称"); self._ch_symm._t = "对称"
        self._ch_symm.setChecked(True)
        ch_h2.addWidget(self._ch_symm)
        ch_h2.addStretch()
        cm_l.addLayout(ch_h2)

        ch_h3 = QHBoxLayout()
        self._ch_cbar = QCheckBox("显示颜色条"); self._ch_cbar._t = "显示颜色条"
        self._ch_cbar.setChecked(True)
        ch_h3.addWidget(self._ch_cbar)
        ch_h3.addStretch()
        cm_l.addLayout(ch_h3)

        ch_btns = QHBoxLayout()
        self._btn_ch_peek = QPushButton("cmap 预览"); self._btn_ch_peek._t = "cmap 预览"
        self._btn_ch_peek.setEnabled(False)
        self._btn_ch_peek.clicked.connect(self._on_quick_peek)
        ch_btns.addWidget(self._btn_ch_peek)
        self._btn_ch_render = QPushButton("电荷出图 (PNG)"); self._btn_ch_render._t = "电荷出图 (PNG)"
        self._btn_ch_render.setEnabled(False)
        self._btn_ch_render.setObjectName("PrimaryBtn")
        self._btn_ch_render.clicked.connect(self._on_export_png)
        ch_btns.addWidget(self._btn_ch_render)
        self._btn_ch_svg = QPushButton("电荷出图 (SVG)"); self._btn_ch_svg._t = "电荷出图 (SVG)"; self._btn_ch_svg.setEnabled(False)
        self._btn_ch_svg.clicked.connect(self._on_export_svg)
        ch_btns.addWidget(self._btn_ch_svg)
        cm_l.addLayout(ch_btns)
        layout.addWidget(gb_cmap)
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
        # Table headers
        if hasattr(self, '_last_charge_type') and self._last_charge_type:
            self._charge_table.setHorizontalHeaderLabels([tr("序号"), tr("元素"), self._last_charge_type])
        else:
            self._charge_table.setHorizontalHeaderLabels([tr("序号"), tr("元素"), tr("电荷值")])

    # ── 表格填充 ──

    def populate_table(self, charges: list[tuple[int, str, float]], charge_type: str):
        """填充电荷结果表格 (序号, 元素符号, 电荷值)。"""
        self._last_charge_type = charge_type
        self._charge_table.setHorizontalHeaderLabels([tr("序号"), tr("元素"), charge_type])
        self._charge_table.setRowCount(len(charges))
        for row, (idx, elem, charge) in enumerate(charges):
            it_idx = QTableWidgetItem(str(idx))
            it_idx.setTextAlignment(Qt.AlignCenter)
            it_elem = QTableWidgetItem(elem)
            it_elem.setTextAlignment(Qt.AlignCenter)
            it_chg = QTableWidgetItem(f"{charge:.6f}")
            it_chg.setTextAlignment(Qt.AlignCenter)
            self._charge_table.setItem(row, 0, it_idx)
            self._charge_table.setItem(row, 1, it_elem)
            self._charge_table.setItem(row, 2, it_chg)
        self._charge_table.clearSelection()

    def clear_table(self):
        self._last_charge_type = ""
        self._charge_table.setRowCount(0)
        self._charge_table.setHorizontalHeaderLabels([tr("序号"), tr("元素"), tr("电荷值")])

    # ── kwargs ──

    def get_kwargs(self) -> dict:
        return dict(
            cmap_range=(float(self._ch_rmin.text()), float(self._ch_rmax.text())),
            cmap_palette=self._ch_palette.currentText(),
            cbar=self._ch_cbar.isChecked(),
        )

    def set_buttons_enabled(self, enabled):
        self._btn_ch_peek.setEnabled(enabled)
        self._btn_ch_render.setEnabled(enabled)
        self._btn_ch_svg.setEnabled(enabled)

    def set_status(self, text):
        self._ch_status.setText(text)

    @property
    def progress_bar(self):
        return self._ch_progress

    @property
    def charge_type(self):
        return self._ch_type.currentText()

    @property
    def rmin(self):
        return self._ch_rmin

    @property
    def rmax(self):
        return self._ch_rmax

    @property
    def symm(self):
        return self._ch_symm

    def _on_quick_peek(self):
        self.quick_peek_requested.emit(self.get_kwargs())

    def _on_export_png(self):
        self.export_png_requested.emit(self.get_kwargs())

    def _on_export_svg(self):
        self.export_svg_requested.emit(self.get_kwargs())
