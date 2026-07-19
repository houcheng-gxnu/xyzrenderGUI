"""XYZRender GUI — 分子结构 + 等值面 (ESP/MO/电子密度) 可视化

整合版 PyQt5 GUI:
- 左: MolCanvas (纯 QPainter 3D 分子渲染, 鼠标旋转/缩放)
- 右: 共用文件栏 + Tab 面板
  Tab 1: 结构可视化 (预设 / 出图)
  Tab 2: 等值面可视化 (ESP / MO / 电子密度 → Multiwfn → xyzrender)

用法:
  xyzrender-gui                      # 安装后直接用命令启动
  python -m xyzrender_gui.main      # 模块方式 (推荐)
  python src/xyzrender_gui/main.py  # 直接运行 (源码)
  pyinstaller src/xyzrender_gui/main.py ...  # 打包
"""

import os
import sys
import multiprocessing
multiprocessing.freeze_support()

# PyInstaller --onefile 子进程中 stdout/stderr 可能为 None
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

from PyQt5.QtWidgets import QApplication
from xyzrender_gui.config import LIGHT_QSS
from xyzrender_gui.viewer import XYZRenderViewer


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(LIGHT_QSS)
    # 应用图标（任务栏）
    _icon = os.path.join(os.path.dirname(__file__), "icon.png")
    if os.path.exists(_icon):
        from PyQt5.QtGui import QIcon
        app.setWindowIcon(QIcon(_icon))
    win = XYZRenderViewer()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
