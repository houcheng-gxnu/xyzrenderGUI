"""XYZRender-Viewer — 分子结构 + 等值面 (ESP/MO/电子密度) 可视化

整合版 PyQt5 GUI:
- 左: MolCanvas (纯 QPainter 3D 分子渲染, 鼠标旋转/缩放)
- 右: 共用文件栏 + Tab 面板
  Tab 1: 结构可视化 (预设 / 出图)
  Tab 2: 等值面可视化 (ESP / MO / 电子密度 → Multiwfn → xyzrender)

用法:
  cd D:/xyzrender/Code
  python -m viewer.main            # 模块方式 (推荐)
  python viewer/main.py            # 直接运行
  pyinstaller viewer/main.py ...   # 打包
"""

import os
import sys

# 确保项目根目录 (d:\xyzrender) 和 viewer 包上层 (d:\xyzrender\Code) 都在 sys.path
_VIEWER_DIR = os.path.dirname(os.path.abspath(__file__))       # ...\Code\viewer
_CODE_DIR = os.path.dirname(_VIEWER_DIR)                        # ...\Code
_PROJ_ROOT = os.path.dirname(_CODE_DIR)                         # ... (d:\xyzrender)

for _p in (_PROJ_ROOT, _CODE_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from PyQt5.QtWidgets import QApplication

# 兼容直接运行 (__name__ == "__main__") 和模块运行 (__name__ == "viewer.main")
if __name__ == "__main__":
    from viewer.config import LIGHT_QSS
    from viewer.viewer import XYZRenderViewer
else:
    from .config import LIGHT_QSS
    from .viewer import XYZRenderViewer


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(LIGHT_QSS)
    win = XYZRenderViewer()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
