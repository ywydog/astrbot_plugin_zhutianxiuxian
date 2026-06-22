import json
from pathlib import Path


class ChengjiuData:
    """成就数据加载器。"""

    def __init__(self, data_dir: Path):
        self.items_dir = data_dir / "items"
        self._data: list[dict] | None = None

    def _load(self) -> list[dict]:
        file_path = self.items_dir / "成就列表.json"
        if not file_path.exists():
            return []
        return json.loads(file_path.read_text(encoding="utf-8"))

    def all(self) -> list[dict]:
        """返回所有成就。"""
        if self._data is None:
            self._data = self._load()
        return self._data

    def get(self, achievement_id: int) -> dict | None:
        """按 ID 获取成就。"""
        for item in self.all():
            if item.get("id") == achievement_id:
                return item
        return None
