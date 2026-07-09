"""XYZRender-Viewer 解析工具：fchk MO 信息、电荷输出、XYZ/fchk 本地解析。"""

import re
import math
from molcanvas.atoms import ATOM_RADII, REVERSE_SYMBOLS, ELEMENT_SYMBOLS
from .config import CHARGE_TYPES


def parse_fchk_mo_info(fchk_path):
    """从 fchk 文件解析轨道信息。
    Returns: dict with n_alpha, n_beta, n_basis, is_open_shell,
             alpha_energies, beta_energies, homo_idx, lumo_idx
    """
    with open(fchk_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    def _read_int(label):
        m = re.search(rf"^{label}\s+I\s+(\d+)", content, re.MULTILINE)
        return int(m.group(1)) if m else None

    def _read_float_array(label):
        m = re.search(
            rf"^{label}\s+R\s+N=\s+(\d+)\s*\n([\s\S]+?)(?=\n\w|\Z)",
            content, re.MULTILINE)
        if not m:
            return []
        return [float(x) for x in m.group(2).split()]

    n_alpha = _read_int("Number of alpha electrons") or 0
    n_beta  = _read_int("Number of beta electrons")  or 0
    n_basis = _read_int("Number of basis functions")  or 0
    alpha_e = _read_float_array("Alpha Orbital Energies")
    beta_e  = _read_float_array("Beta Orbital Energies")
    is_open = bool(beta_e)
    homo_idx = n_alpha
    lumo_idx = n_alpha + 1 if n_basis > n_alpha else None

    return {
        "n_alpha": n_alpha, "n_beta": n_beta, "n_basis": n_basis,
        "is_open_shell": is_open,
        "alpha_energies": alpha_e,
        "beta_energies": beta_e if is_open else None,
        "homo_idx": homo_idx, "lumo_idx": lumo_idx,
    }


def parse_charge_output(output_text, charge_type="ADCH"):
    """解析 Multiwfn 电荷输出，返回 [(序号, 元素符号, 电荷值), ...]"""
    results = []
    cfg = CHARGE_TYPES.get(charge_type, {})
    markers = cfg.get("marker", [])

    if charge_type == "SCPA":
        pattern = re.compile(r"Atom\s+(\d+)\(([^)]+?)\s*\)\s+Population:\s+[-\d.]+\s+Atomic charge:\s*([-\d.]+)")
        for line in output_text.splitlines():
            m = pattern.search(line)
            if m:
                results.append((int(m.group(1)), m.group(2).strip(), float(m.group(3))))
        return results

    pattern_std = re.compile(r"Atom\s+(\d+)\(([^)]+?)\s*\):\s+([-\d.]+)")
    pattern_mul = re.compile(r"Atom\s+(\d+)\((\w+)\s*\)\s+Population:\s+[-\d.]+\s+Net charge:\s*([-\d.]+)")

    in_section = False
    for line in output_text.splitlines():
        for marker in markers:
            if marker in line:
                in_section = True
                break
        if not in_section:
            continue
        m = pattern_std.search(line)
        if not m:
            m = pattern_mul.search(line)
        if m:
            results.append((int(m.group(1)), m.group(2).strip(), float(m.group(3))))
        elif "----------" in line and results:
            break
        elif "Total net charge" in line and results:
            break
        elif "Calculation took" in line and results:
            break
    return results


def _parse_xyz_local(path: str):
    """返回 (atoms, bonds) 给 MolCanvas.set_data()。"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    n = int(lines[0].strip())
    atoms = []
    for i, line in enumerate(lines[2:2 + n], 1):
        parts = line.strip().split()
        if len(parts) < 4:
            continue
        elem = parts[0].capitalize()
        x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
        an = REVERSE_SYMBOLS.get(elem, 0)
        atoms.append((i, elem, an, (x, y, z)))
    bonds = []
    for i, (idx1, sym1, _, (x1, y1, z1)) in enumerate(atoms):
        r1 = ATOM_RADII.get(sym1, 1.5)
        for j in range(i + 1, len(atoms)):
            idx2, sym2, _, (x2, y2, z2) = atoms[j]
            r2 = ATOM_RADII.get(sym2, 1.5)
            d = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)
            if d < r1 + r2 + 0.45:
                bonds.append((idx1, idx2))
    return atoms, bonds


def _write_atoms_to_xyz(atoms, path):
    """把 MolCanvas 格式的 atoms 列表写入 .xyz 文件，供 xyzrender 加载。"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"{len(atoms)}\n")
        f.write("generated from fchk\n")
        for _idx, sym, _an, (x, y, z) in atoms:
            f.write(f"{sym:<3s} {x:12.6f} {y:12.6f} {z:12.6f}\n")


def _indices_to_text(indices_set):
    """将原子编号集合转为紧凑文本，如 {1,2,3,5,7} → '1-3,5,7'"""
    if not indices_set:
        return ""
    nums = sorted(indices_set)
    ranges = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
        else:
            ranges.append((start, prev))
            start = prev = n
    ranges.append((start, prev))
    parts = []
    for s, e in ranges:
        if s == e:
            parts.append(str(s))
        else:
            parts.append(f"{s}-{e}")
    return ",".join(parts)


def _parse_fchk_local(path: str):
    """返回 (atoms, bonds) 给 MolCanvas.set_data()。"""
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    m_nums = re.search(r"Atomic numbers\s+I\s+N=\s+(\d+)\s*\n([\s\S]+?)(?=\n\w|\Z)", content)
    if not m_nums:
        return [], []

    atomic_nums = list(map(int, m_nums.group(2).split()))

    m_coords = re.search(r"Current cartesian coordinates\s+R\s+N=\s+(\d+)\s*\n([\s\S]+?)(?=\n\w|\Z)", content)
    if not m_coords:
        return [], []

    coords_raw = list(map(float, m_coords.group(2).split()))
    if len(coords_raw) < len(atomic_nums) * 3:
        return [], []

    bohr_to_ang = 0.529177210903

    atoms = []
    for i, an in enumerate(atomic_nums):
        x = coords_raw[i * 3] * bohr_to_ang
        y = coords_raw[i * 3 + 1] * bohr_to_ang
        z = coords_raw[i * 3 + 2] * bohr_to_ang
        elem = ELEMENT_SYMBOLS.get(an, "X")
        atoms.append((i + 1, elem, an, (x, y, z)))

    bonds = []
    for i, (idx1, sym1, _, (x1, y1, z1)) in enumerate(atoms):
        r1 = ATOM_RADII.get(sym1, 1.5)
        for j in range(i + 1, len(atoms)):
            idx2, sym2, _, (x2, y2, z2) = atoms[j]
            r2 = ATOM_RADII.get(sym2, 1.5)
            d = math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)
            if d < r1 + r2 + 0.45:
                bonds.append((idx1, idx2))
    return atoms, bonds
