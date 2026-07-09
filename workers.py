"""XYZRender-Viewer 后台线程：Multiwfn 计算 (ESP / MO / IGMH / 电荷)。"""

import os
import shutil
import subprocess
import threading

from PyQt5.QtCore import QThread, pyqtSignal

from .config import CMD_ESPISO, CHARGE_TYPES, _filter_mw_line, _parse_mw_progress


class MultiwfnWorker(QThread):
    """后台运行 Multiwfn 生成 ESP cube 文件 (density.cub + totesp.cub)。"""

    status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)  # success, work_dir

    def __init__(self, multiwfn_exe, fch_path, work_dir):
        super().__init__()
        self._mw_exe = multiwfn_exe
        self._fch = fch_path
        self._work_dir = work_dir

    def run(self):
        fch_name = os.path.basename(self._fch)

        if not os.path.isfile(self._fch):
            self.status_signal.emit("fchk 文件不存在")
            self.finished_signal.emit(False, self._work_dir)
            return

        cmd_file = os.path.join(self._work_dir, "_mw_cmd.txt")
        with open(cmd_file, "w", encoding="ascii") as f:
            f.write(CMD_ESPISO)

        cmd = f'"{self._mw_exe}" "{fch_name}" -ESPrhoiso 0.001 < _mw_cmd.txt'
        self.status_signal.emit("启动 Multiwfn...")
        self.progress_signal.emit(2)

        try:
            proc = subprocess.Popen(
                cmd, shell=True, cwd=self._work_dir,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )
        except Exception as e:
            self.status_signal.emit(f"启动失败: {e}")
            self.finished_signal.emit(False, self._work_dir)
            return

        stdout_lines: list[str] = []
        read_done = threading.Event()

        def _read_stdout():
            try:
                for line in proc.stdout:
                    stdout_lines.append(line)
            except Exception:
                pass
            read_done.set()

        reader = threading.Thread(target=_read_stdout, daemon=True)
        reader.start()

        last_progress = 0.0
        total_lines_seen = 0

        while not read_done.is_set() or proc.poll() is None:
            new_lines = len(stdout_lines)
            for i in range(total_lines_seen, new_lines):
                line = stdout_lines[i]
                pct = _parse_mw_progress(line)
                if pct is not None:
                    if pct < last_progress - 0.05:
                        last_progress = 0.0
                    if pct > last_progress:
                        last_progress = pct
                        overall = 5 + int(pct * 90)
                        self.progress_signal.emit(overall)
                        self.status_signal.emit(f"计算中... {int(pct * 100)}%")
            total_lines_seen = new_lines
            read_done.wait(0.2)
            if proc.poll() is not None and not read_done.is_set():
                read_done.wait(2.0)

        reader.join(timeout=3)
        proc.wait()
        self.progress_signal.emit(90)

        key_lines = []
        for line in stdout_lines:
            filtered = _filter_mw_line(line)
            if filtered and len(key_lines) < 15:
                key_lines.append(filtered)
        summary = "\n".join(key_lines) if key_lines else "(无关键输出)"
        self.status_signal.emit(f"Multiwfn 执行完毕\n{summary}")

        if proc.returncode not in (0, 24):
            self.status_signal.emit(f"Multiwfn 异常退出 (code={proc.returncode})")
            self.finished_signal.emit(False, self._work_dir)
            return

        density_path = os.path.join(self._work_dir, "density.cub")
        esp_path = os.path.join(self._work_dir, "totesp.cub")
        self.progress_signal.emit(93)

        missing = []
        for label, fp in [("density.cub", density_path), ("totesp.cub", esp_path)]:
            if not os.path.exists(fp):
                missing.append(label)
            else:
                size_kb = os.path.getsize(fp) // 1024
                self.status_signal.emit(f"{label} 已生成 ({size_kb} KB)")

        if missing:
            self.status_signal.emit(f"缺少输出文件: {', '.join(missing)}")
            self.finished_signal.emit(False, self._work_dir)
            return

        self.progress_signal.emit(96)
        from xyzrender.cube import parse_cube
        dc = parse_cube(density_path)
        ec = parse_cube(esp_path)
        if dc.grid_shape != ec.grid_shape:
            self.status_signal.emit(
                f"网格不匹配! Density={dc.grid_shape} ESP={ec.grid_shape}")
            self.finished_signal.emit(False, self._work_dir)
            return

        self.status_signal.emit(f"网格尺寸一致: {dc.grid_shape}")
        self.progress_signal.emit(100)
        self.finished_signal.emit(True, self._work_dir)


class MOCubeWorker(QThread):
    """后台运行 Multiwfn 生成单个 MO cube 文件。"""

    status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)  # ok, cube_path

    def __init__(self, multiwfn_exe, fch_path, orbital, grid_quality):
        super().__init__()
        self._mw_exe = multiwfn_exe
        self._fch = fch_path
        self._orb = orbital
        self._grid = grid_quality

    def run(self):
        fch_name = os.path.basename(self._fch)
        fch_dir = os.path.dirname(os.path.abspath(self._fch))
        work_dir = os.path.join(fch_dir, f"_mo_tmp_{self._orb}")
        os.makedirs(work_dir, exist_ok=True)

        tmp_fch = os.path.join(work_dir, fch_name)
        shutil.copy2(self._fch, tmp_fch)

        self.status_signal.emit("启动 Multiwfn (MO)...")
        self.progress_signal.emit(5)

        inputs = (
            "\n" + fch_name + "\n5\n4\n" + self._orb + "\n"
            + str(self._grid) + "\n2\n0\nq\n"
        )

        try:
            proc = subprocess.run(
                self._mw_exe, input=inputs, capture_output=True,
                cwd=work_dir, timeout=600,
                encoding="utf-8", errors="replace",
            )
        except FileNotFoundError:
            self.status_signal.emit("Multiwfn.exe 未找到")
            self.finished_signal.emit(False, "")
            return
        except subprocess.TimeoutExpired:
            self.status_signal.emit("Multiwfn 超时 (600s)")
            self.finished_signal.emit(False, "")
            return

        self.progress_signal.emit(90)

        mo_cube = os.path.join(work_dir, "MOvalue.cub")
        if not os.path.exists(mo_cube):
            self.status_signal.emit("MOvalue.cub 未生成, Multiwfn 执行失败")
            self.finished_signal.emit(False, "")
            return

        self.progress_signal.emit(95)

        stem = os.path.splitext(fch_name)[0]
        dst = os.path.join(fch_dir, f"{stem}_MO{self._orb}.cub")
        shutil.move(mo_cube, dst)

        try:
            shutil.rmtree(work_dir)
        except OSError:
            pass

        self.status_signal.emit(f"MO cube 已生成: {os.path.basename(dst)}")
        self.progress_signal.emit(100)
        self.finished_signal.emit(True, dst)


class IgmhWorker(QThread):
    """后台运行 Multiwfn 生成 IGMH 分析 (dg_inter.cub + sl2r.cub)。"""

    status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)  # ok, work_dir

    def __init__(self, multiwfn_exe, fch_path, frag1, frag2, grid_quality):
        super().__init__()
        self._mw_exe = multiwfn_exe
        self._fch = fch_path
        self._frag1 = frag1
        self._frag2 = frag2
        self._grid = grid_quality

    def run(self):
        fch_name = os.path.basename(self._fch)
        fch_dir = os.path.dirname(os.path.abspath(self._fch))
        stem = os.path.splitext(fch_name)[0]
        work_dir = os.path.join(fch_dir, f"_igmh_{stem}")
        os.makedirs(work_dir, exist_ok=True)

        if not os.path.isfile(self._fch):
            self.status_signal.emit("fchk 文件不存在")
            self.finished_signal.emit(False, work_dir)
            return

        tmp_fch = os.path.join(work_dir, fch_name)
        shutil.copy2(self._fch, tmp_fch)

        input_seq = (
            "\n" + fch_name + "\n"
            "20\n"
            "11\n"
            "2\n"
            + self._frag1 + "\n"
            + self._frag2 + "\n"
            + str(self._grid) + "\n"
            "2\n"
            "3\n"
            "0\n"
            "0\n"
            "q\n"
        )

        self.status_signal.emit("启动 Multiwfn (IGMH)...")
        self.progress_signal.emit(2)

        try:
            proc = subprocess.run(
                self._mw_exe, input=input_seq, capture_output=True,
                cwd=work_dir, timeout=900,
                encoding="utf-8", errors="replace",
            )
        except FileNotFoundError:
            self.status_signal.emit("Multiwfn.exe 未找到")
            self.finished_signal.emit(False, work_dir)
            return
        except subprocess.TimeoutExpired:
            self.status_signal.emit("Multiwfn 超时 (900s)")
            self.finished_signal.emit(False, work_dir)
            return

        self.progress_signal.emit(90)

        expected = ["dg_inter.cub", "sl2r.cub"]
        missing = []
        for fn in expected:
            fp = os.path.join(work_dir, fn)
            if os.path.exists(fp):
                size_kb = os.path.getsize(fp) // 1024
                self.status_signal.emit(f"{fn} 已生成 ({size_kb} KB)")
            else:
                missing.append(fn)

        if missing:
            self.status_signal.emit(f"缺少输出文件: {', '.join(missing)}")
            self.finished_signal.emit(False, work_dir)
            return

        self.status_signal.emit("IGMH 分析完成")
        self.progress_signal.emit(100)
        self.finished_signal.emit(True, work_dir)


class ChargeWorker(QThread):
    """后台运行 Multiwfn 计算原子电荷。"""

    status_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str, str)  # charge_type, output_text

    def __init__(self, multiwfn_exe, fch_path, charge_type):
        super().__init__()
        self._mw_exe = multiwfn_exe
        self._fch = fch_path
        self._charge_type = charge_type

    def run(self):
        try:
            cfg = CHARGE_TYPES.get(self._charge_type)
            if not cfg:
                self.finished_signal.emit(self._charge_type, "")
                return
            input_seq = cfg["input_seq"]
            self.status_signal.emit(f"计算 {self._charge_type} 电荷...")
            import locale
            encoding = locale.getpreferredencoding(do_setlocale=False) or "utf-8"
            work_dir = os.path.dirname(self._fch) or None
            proc = subprocess.run(
                [self._mw_exe, self._fch],
                input=input_seq,
                capture_output=True,
                text=True,
                encoding=encoding,
                errors="replace",
                timeout=900,
                cwd=work_dir,
            )
            self.progress_signal.emit(90)
            self.status_signal.emit(f"{self._charge_type} 计算完成")
            self.progress_signal.emit(100)
            self.finished_signal.emit(self._charge_type, proc.stdout)
        except subprocess.TimeoutExpired:
            self.status_signal.emit("Multiwfn 超时 (900s)")
            self.finished_signal.emit(self._charge_type, "")
        except FileNotFoundError:
            self.status_signal.emit("Multiwfn.exe 未找到")
            self.finished_signal.emit(self._charge_type, "")
        except Exception as e:
            self.status_signal.emit(f"错误: {e}")
            self.finished_signal.emit(self._charge_type, "")
