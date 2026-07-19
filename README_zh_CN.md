# XYZRender GUI

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PyQt5-blue.svg?style=flat-square" alt="PyQt5">
  <img src="https://img.shields.io/badge/Backend-xyzrender%20%26%20molcanvas-green.svg?style=flat-square" alt="Backend">
</p>

基于 **PyQt5** 的分子结构与等值面可视化图形界面，将 [`xyzrender`](https://github.com/houcheng-gxnu/xyzrender) 三维分子渲染引擎与 [`Multiwfn`](http://sobereva.com/multiwfn/) 量子化学分析工具整合为一体化的交互式应用。

> 英文文档见 [README.md](./README.md)。

---

## 功能概览

| 模块 | 功能 |
|------|------|
| **结构可视化** | 可旋转 / 缩放的 3D 分子画布，多种渲染预设（HoukMol / 球棍 / 管状等） |
| **ESP 等值面** | 调用 Multiwfn 生成静电势密度 / 势能 cube 文件，彩色映射等值面渲染 |
| **MO 分子轨道** | 从 fchk 解析轨道能级表，生成指定轨道的 cube 文件并可视化 |
| **IGMH 分析** | 片段间相互作用可视化（dg_inter + sl2r），支持画布框选原子分组 |
| **电荷计算** | ADCH / Hirshfeld / Mulliken / CM5 / SCPA / VDD 原子电荷，按色板着色 |
| **Cube 文件** | 直接加载 cube 文件查看等值面 |
| **过渡态虚线** | 手动标注化学键为虚线（过渡态结构），可调虚线样式与颜色 |
| **H 原子过滤** | 一键隐藏 / 显示氢原子，可指定保留编号 |
| **导出** | 支持 PNG / SVG 出图 |

---

## 界面布局

```
┌──────────────────────────┬──────────────────────────┐
│  3D 分子画布              │  文件加载                 │
│  (鼠标旋转/缩放/平移)      │  ┌─────────────────────┐ │
│                          │  │ 结构 │ESP│MO│IGMH│...│ │
│                          │  │  (参数面板 + 操作按钮)  │ │
├──────────────────────────┤  ├─────────────────────┤ │
│  渲染预览                  │  │     运行日志          │ │
└──────────────────────────┴──────────────────────────┘
```

---

## 依赖

- **Python** ≥ 3.10
- **PyQt5** — GUI 框架
- **[xyzrender](https://github.com/houcheng-gxnu/xyzrender)** — 分子结构渲染引擎（SVG 输出）
- **molcanvas** — 轻量级 QPainter 分子画布（实时 3D 预览，随 xyzrender 提供）
- **[Multiwfn](http://sobereva.com/multiwfn/)** — 量子化学波函数分析（ESP / MO / IGMH / 电荷计算）

---

## 安装

### 方式一：从源码安装（推荐）

```bash
git clone https://github.com/houcheng-gxnu/xyzrenderGUI.git
cd xyzrenderGUI

# 安装 GUI 及其 Python 依赖
pip install -e .

# 安装渲染后端 xyzrender（含 molcanvas），请从源码安装
pip install git+https://github.com/houcheng-gxnu/xyzrender.git
```

### 方式二：仅安装运行依赖

```bash
pip install -r requirements.txt
```

### Multiwfn 配置

下载 [Multiwfn](http://sobereva.com/multiwfn/) 后，在程序 **文件** 栏中浏览选择 `Multiwfn.exe` 路径，配置将自动保存至 `xyzrender_viewer.ini`。

---

## 快速开始

安装后可直接使用命令启动：

```bash
xyzrender-gui
```

或从源码运行：

```bash
python -m xyzrender_gui.main
```

---

### 支持的文件格式

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| XYZ | `.xyz` | 原子坐标文件 |
| Gaussian fchk | `.fchk` `.fch` | 波函数文件（ESP/MO/IGMH/电荷分析必需） |
| Cube | `.cube` `.cub` | 格点数据文件 |
| MOL / SDF | `.mol` `.sdf` | 分子结构文件 |
| MOL2 | `.mol2` | Tripos 分子格式 |
| PDB | `.pdb` | Protein Data Bank 格式 |
| Gaussian Log | `.log` `.out` | 输出文件 |

---

## 典型工作流

### 1. 结构可视化
`打开 XYZ/fchk → 切换样式 → 调整视角 → 快速预览 → 导出 PNG/SVG`

### 2. ESP 静电势分析
`打开 fchk → ESP 选项卡 → 设置等值面参数 → 生成 cube → 预览 → 导出`

### 3. MO 分子轨道
`打开 fchk → MO 选项卡 → 从轨道表选择 → 生成 MO cube → 预览`

### 4. IGMH 相互作用
`打开 fchk → 画布框选片段 → IGMH 选项卡 → 运行分析 → 预览`

### 5. 原子电荷着色
`打开 fchk → 电荷选项卡 → 选择电荷类型 → 计算 → 选色板 → 渲染出图`

---

## 项目结构

```
xyzrenderGUI/
├── pyproject.toml          # 项目元数据 / 构建配置
├── requirements.txt        # Python 依赖
├── LICENSE                 # MIT License
├── README.md               # 英文文档
├── README_zh_CN.md         # 中文文档
├── src/
│   └── xyzrender_gui/      # 主程序包
│       ├── __init__.py
│       ├── main.py         # 入口 (命令: xyzrender-gui)
│       ├── viewer.py       # 主窗口，布局与信号编排
│       ├── config.py       # QSS 样式、Multiwfn 配置、电荷类型定义
│       ├── parsing.py      # fchk/XYZ 解析、电荷输出解析
│       ├── workers.py      # Multiwfn 后台线程 (ESP/MO/IGMH/Charge)
│       ├── dialogs.py      # MO 轨道浏览器弹窗
│       ├── i18n.py         # 中 / 英 界面文本
│       ├── icon.png        # 应用图标
│       └── tabs/
│           ├── structure_tab.py  # 结构可视化参数面板
│           ├── esp_tab.py        # ESP 等值面参数面板
│           ├── mo_tab.py         # MO 轨道参数面板
│           ├── igmh_tab.py       # IGMH 分析参数面板
│           ├── charge_tab.py     # 电荷计算与着色面板
│           └── cube_tab.py       # Cube 文件查看面板
└── tests/                  # 测试
```

---

## 快捷键

| 操作 | 方式 |
|------|------|
| 旋转 | 鼠标左键拖拽 |
| 平移 | 鼠标右键拖拽 |
| 缩放 | 鼠标滚轮 |
| 重置视角 | 双击画布 |

---

## 技术说明

- **xyzrender** 负责高质量 SVG 渲染输出（预设样式、原子着色、等值面投影）
- **molcanvas** 提供实时交互式 QPainter 3D 预览，轻量无 OpenGL 依赖
- **Multiwfn** 通过 `subprocess` 管道调用，输入命令序列，解析输出完成计算
- 旋转状态通过四元数在 canvas 和 xyzrender 之间同步，确保预览与出图视角一致

---

## License

本项目基于 [MIT License](./LICENSE) 开源。
