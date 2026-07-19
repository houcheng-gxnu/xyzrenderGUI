"""XYZRender-Viewer 弹窗：MO 浏览器。"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QGroupBox, QListWidget, QListWidgetItem,
    QAbstractItemView,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

from .parsing import parse_fchk_mo_info


class MOBrowserDialog(QDialog):
    """轨道浏览器弹窗 — 以紧凑表格展示 MO 信息，支持双击选中。"""

    orbital_selected = None  # will be set via return value pattern

    def __init__(self, fchk_path, parent=None):
        super().__init__(parent)
        self.fchk_path = fchk_path
        self.mo_info = None
        self._selected_orbital = None
        self.setWindowTitle("轨道浏览器")
        self.resize(700, 500)
        self._setup_ui()
        self._parse_and_fill()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        gb = QGroupBox("分子轨道 (双击行选择)")
        gb_layout = QVBoxLayout(gb)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["轨道", "能量 (a.u.)", "占据", "类型"])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.cellDoubleClicked.connect(self._on_double_click)
        gb_layout.addWidget(self._table)
        layout.addWidget(gb)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        from PyQt5.QtWidgets import QPushButton
        btn_fill = QPushButton("重新解析")
        btn_fill.clicked.connect(self._on_fill)
        btn_layout.addWidget(btn_fill)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.reject)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

    def _parse_and_fill(self):
        try:
            self.mo_info = parse_fchk_mo_info(self.fchk_path)
        except Exception as e:
            self._table.setRowCount(1)
            self._table.setItem(0, 0, QTableWidgetItem(f"解析失败: {e}"))
            return

        n_a = self.mo_info["n_alpha"]
        n_b = self.mo_info["n_beta"]
        alpha_e = self.mo_info["alpha_energies"]
        beta_e = self.mo_info["beta_energies"]
        is_open = self.mo_info["is_open_shell"]
        homo = self.mo_info["homo_idx"]
        lumo = self.mo_info["lumo_idx"]

        rows = []
        for i, e in enumerate(alpha_e, 1):
            occ = (1.0 if is_open else 2.0) if i <= n_a else 0.0
            tag = ""
            if i == homo: tag = "HOMO"
            elif i == lumo: tag = "LUMO"
            rows.append((str(i), e, occ, tag, False))

        if is_open and beta_e:
            for i, e in enumerate(beta_e, 1):
                occ = 1.0 if i <= n_b else 0.0
                tag = ""
                if i == n_b: tag = "β-HOMO"
                elif i == n_b + 1: tag = "β-LUMO"
                rows.append((f"β{i}", e, occ, tag, True))

        self._fill_rows(rows, is_open)

    def _fill_rows(self, rows, is_open):
        self._table.setRowCount(len(rows))
        for r, (label, energy, occ, tag, is_beta) in enumerate(rows):
            it0 = QTableWidgetItem(label)
            it0.setTextAlignment(Qt.AlignCenter)
            if is_beta:
                it0.setForeground(QColor("#E74C3C"))
            self._table.setItem(r, 0, it0)

            it1 = QTableWidgetItem(f"{energy:.6f}")
            it1.setTextAlignment(Qt.AlignCenter)
            self._table.setItem(r, 1, it1)

            it2 = QTableWidgetItem(f"{occ:.1f}")
            it2.setTextAlignment(Qt.AlignCenter)
            if occ > 0:
                it2.setBackground(QColor("#E8F5E9"))
            self._table.setItem(r, 2, it2)

            it3 = QTableWidgetItem(tag)
            it3.setTextAlignment(Qt.AlignCenter)
            if "HOMO" in tag:
                it3.setBackground(QColor("#FFF3E0"))
                it3.setFont(QFont("", -1, QFont.Bold))
            elif "LUMO" in tag:
                it3.setBackground(QColor("#E3F2FD"))
                it3.setFont(QFont("", -1, QFont.Bold))
            self._table.setItem(r, 3, it3)

    def _on_double_click(self, row, _col):
        it = self._table.item(row, 0)
        if it:
            self._selected_orbital = it.text().strip()
            self.accept()

    def _on_fill(self):
        self._parse_and_fill()

    @property
    def selected_orbital(self):
        return self._selected_orbital
