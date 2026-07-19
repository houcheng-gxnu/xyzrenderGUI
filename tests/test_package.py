"""XYZRender GUI 包基础冒烟测试。

config 模块只依赖标准库，可在无 PyQt5 / xyzrender / molcanvas 的环境下导入，
因此作为包结构正确性的最小校验。若环境中已安装 PyQt5，则进一步校验入口模块可导入。
"""

import importlib.util


def _import_config():
    from xyzrender_gui import config
    return config


def test_package_importable():
    """包可被导入，且 config 模块暴露关键常量。"""
    config = _import_config()
    assert isinstance(config.CHARGE_TYPES, dict)
    assert len(config.CHARGE_TYPES) > 0
    assert config.DEFAULT_MULTIWFN
    assert isinstance(config.LIGHT_QSS, str) and config.LIGHT_QSS.strip()


def test_charge_types_known():
    """常见电荷类型应当存在。"""
    config = _import_config()
    for name in ("ADCH", "Hirshfeld", "Mulliken", "CM5", "SCPA", "VDD"):
        assert name in config.CHARGE_TYPES, f"缺少电荷类型: {name}"


def test_main_importable_when_pyqt5_present():
    """若已安装 PyQt5，则入口模块应当可成功导入。"""
    import pytest

    if importlib.util.find_spec("PyQt5") is None:
        pytest.skip("PyQt5 未安装，跳过 GUI 入口导入测试")
    from xyzrender_gui import main  # noqa: F401

    assert hasattr(main, "main")
