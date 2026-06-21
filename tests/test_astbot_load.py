import shutil
import sys
from pathlib import Path
from typing import Any, cast

import pytest

from astrbot.core.star import star_manager as star_manager_module
from astrbot.core.star.star_manager import PluginManager


class MockContext:
    def __init__(self):
        self.stars = []
        self._star_manager = None

    def get_all_stars(self):
        return self.stars

    def get_registered_star(self, name):
        for s in self.stars:
            if getattr(s, "root_dir_name", None) == name or getattr(s, "name", None) == name:
                return s
        return None


def _clear_star_state():
    star_manager_module.star_map.clear()
    star_manager_module.star_registry.clear()
    star_manager_module.star_handlers_registry.clear()


@pytest.fixture
def plugin_manager(tmp_path, monkeypatch):
    _clear_star_state()

    plugin_dir = tmp_path / "data" / "plugins"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    ctx = MockContext()
    pm = PluginManager(cast(Any, ctx), cast(Any, {}))
    monkeypatch.setattr(pm, "plugin_store_path", str(plugin_dir))
    monkeypatch.setattr(
        "astrbot.core.star.star_manager.get_astrbot_plugin_path",
        lambda: str(plugin_dir),
    )

    # 将当前插件目录复制到临时插件目录
    src_dir = Path(__file__).parent.parent.resolve()
    dst_dir = plugin_dir / "astrbot_plugin_zhutianxiuxian"
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    shutil.copytree(src_dir, dst_dir, ignore=shutil.ignore_patterns(".pytest_cache", "__pycache__"))

    # 让 data.plugins.xxx 可导入，需要把 tmp_path 加入 sys.path
    tmp_root = str(tmp_path)
    if tmp_root not in sys.path:
        sys.path.insert(0, tmp_root)

    yield pm

    if tmp_root in sys.path:
        sys.path.remove(tmp_root)

    _clear_star_state()


@pytest.mark.asyncio
async def test_plugin_loads_successfully(plugin_manager):
    """插件应能被 AstrBot 的 PluginManager 加载成功。"""
    success, error = await plugin_manager.load()

    assert success, f"插件加载失败: {error}"

    module_path = "data.plugins.astrbot_plugin_zhutianxiuxian.main"
    metadata = star_manager_module.star_map.get(module_path)
    assert metadata is not None
    assert metadata.star_cls is not None
    assert metadata.star_cls_type is not None

    handlers = star_manager_module.star_handlers_registry.get_handlers_by_module_name(module_path)
    assert len(handlers) >= 2
