import json
from pathlib import Path


class ItemCatalog:
    """物品目录加载器，按类别加载 JSON 物品列表。"""

    def __init__(self, data_dir: Path):
        self.items_dir = data_dir / "items"
        self._cache: dict[str, list[dict]] = {}

    def _load(self, filename: str) -> list[dict]:
        file_path = self.items_dir / filename
        if not file_path.exists():
            return []
        return json.loads(file_path.read_text(encoding="utf-8"))

    def get_items(self, filename: str) -> list[dict]:
        """获取指定文件中的物品列表。"""
        if filename not in self._cache:
            self._cache[filename] = self._load(filename)
        return self._cache[filename]

    def find_item(self, name: str, filename: str | None = None) -> dict | None:
        """按名称查找物品；若指定文件则只在该文件中查找。"""
        if filename is not None:
            for item in self.get_items(filename):
                if item.get("name") == name:
                    return item
            return None

        for cached in self._cache.values():
            for item in cached:
                if item.get("name") == name:
                    return item
        return None
