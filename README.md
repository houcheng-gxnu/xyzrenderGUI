# XYZRender GUI

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/GUI-PyQt5-blue.svg?style=flat-square" alt="PyQt5">
  <img src="https://img.shields.io/badge/Backend-xyzrender%20%26%20molcanvas-green.svg?style=flat-square" alt="Backend">
</p>

A **PyQt5**-based graphical interface for molecular structure and isosurface
visualization. It integrates the [`xyzrender`](https://github.com/houcheng-gxnu/xyzrender)
3D molecular rendering engine with the [`Multiwfn`](http://sobereva.com/multiwfn/)
wave-function analysis toolkit into a single interactive application.

> 中文文档见 [README_zh_CN.md](./README_zh_CN.md).

---

## Features

| Module | Description |
|--------|-------------|
| **Structure** | Rotatable / zoomable 3D canvas with rendering presets (HoukMol / ball-and-stick / tube …) |
| **ESP** | Generate electrostatic-potential cube files via Multiwfn and render color-mapped isosurfaces |
| **MO** | Parse orbital energies from fchk, generate selected orbital cube files and visualize them |
| **IGMH** | Inter-fragment interaction visualization (dg_inter + sl2r), with box-selection of fragments |
| **Charge** | ADCH / Hirshfeld / Mulliken / CM5 / SCPA / VDD atomic charges, colored by colormap |
| **Cube** | Directly load and view `.cube` grid files |
| **TS dashes** | Mark bonds as dashed lines (transition-state structures), adjustable style & color |
| **H filter** | Hide / show hydrogen atoms with optional index preservation |
| **Export** | Save figures as PNG / SVG |

---

## Dependencies

- **Python** ≥ 3.10
- **PyQt5** — GUI framework
- **[xyzrender](https://github.com/houcheng-gxnu/xyzrender)** — rendering engine (SVG output)
- **molcanvas** — lightweight QPainter molecular canvas (bundled with xyzrender)
- **[Multiwfn](http://sobereva.com/multiwfn/)** — wave-function analysis (ESP / MO / IGMH / charge)

---

## Installation

### From source (recommended)

```bash
git clone https://github.com/houcheng-gxnu/xyzrenderGUI.git
cd xyzrenderGUI

# Install the GUI and its Python dependencies
pip install -e .

# Install the rendering backend (xyzrender, which also provides molcanvas)
pip install git+https://github.com/houcheng-gxnu/xyzrender.git
```

### Or just the runtime dependencies

```bash
pip install -r requirements.txt
```

### Multiwfn setup

Download [Multiwfn](http://sobereva.com/multiwfn/), then browse to `Multiwfn.exe`
in the **File** panel of the GUI. The path is saved automatically to `xyzrender_viewer.ini`.

---

## Quick start

After installation, launch from the command line:

```bash
xyzrender-gui
```

Or run from source:

```bash
python -m xyzrender_gui.main
```

---

### Supported file formats

| Format | Extensions | Notes |
|--------|-----------|-------|
| XYZ | `.xyz` | Atomic coordinates |
| Gaussian fchk | `.fchk` `.fch` | Wave-function (required for ESP/MO/IGMH/charge) |
| Cube | `.cube` `.cub` | Grid data |
| MOL / SDF | `.mol` `.sdf` | Molecular structure |
| MOL2 | `.mol2` | Tripos format |
| PDB | `.pdb` | Protein Data Bank |
| Gaussian Log | `.log` `.out` | Output files |

---

## Project structure

```
xyzrenderGUI/
├── pyproject.toml          # Project metadata / build config
├── requirements.txt        # Python dependencies
├── LICENSE                 # MIT License
├── README.md               # English docs
├── README_zh_CN.md         # Chinese docs
├── src/
│   └── xyzrender_gui/      # Main package
│       ├── __init__.py
│       ├── main.py         # Entry point (command: xyzrender-gui)
│       ├── viewer.py       # Main window, layout & signal wiring
│       ├── config.py       # QSS styles, Multiwfn config, charge types
│       ├── parsing.py      # fchk/XYZ parsing, charge output parsing
│       ├── workers.py      # Multiwfn background threads (ESP/MO/IGMH/Charge)
│       ├── dialogs.py      # MO orbital browser dialog
│       ├── i18n.py         # zh / en UI strings
│       ├── icon.png        # Application icon
│       └── tabs/
│           ├── structure_tab.py
│           ├── esp_tab.py
│           ├── mo_tab.py
│           ├── igmh_tab.py
│           ├── charge_tab.py
│           └── cube_tab.py
└── tests/                  # Tests
```

---

## Keyboard / mouse

| Action | How |
|--------|-----|
| Rotate | Left-drag |
| Pan | Right-drag |
| Zoom | Mouse wheel |
| Reset view | Double-click canvas |

---

## License

Released under the [MIT License](./LICENSE).
