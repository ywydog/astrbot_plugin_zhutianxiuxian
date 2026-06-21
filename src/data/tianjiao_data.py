import json
from pathlib import Path
from typing import Any


class TianjiaoData:
    """位面天骄数据加载器，提供天骄列表、按名称查找、位面映射。"""

    LOCATION_MAP: dict[str, float | int] = {
        "凡间": 0,
        "仙界": 1,
        "下界八域": 1.5,
        "遮天位面": 2,
        "九天十地": 2.5,
        "界海": 3,
        "时间长河": 4,
        "永恒未知之地": 5,
        "仙域": 6,
    }

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.file_path = data_dir / "位面boss列表.json"
        self._tianjiao_list: list[dict[str, Any]] | None = None

    def _load(self) -> list[dict[str, Any]]:
        if not self.file_path.exists():
            return []
        return json.loads(self.file_path.read_text(encoding="utf-8"))

    def list_tianjiao(self) -> list[dict[str, Any]]:
        """返回全部天骄数据。"""
        if self._tianjiao_list is None:
            self._tianjiao_list = self._load()
        return self._tianjiao_list

    def find_by_name(self, name: str) -> dict[str, Any] | None:
        """按名号查找天骄。"""
        for tianjiao in self.list_tianjiao():
            if tianjiao.get("名号") == name:
                return tianjiao
        return None

    def get_location_name(self, location_id: float | int) -> str:
        """将位面 ID 映射为中文名称。"""
        for name, lid in self.LOCATION_MAP.items():
            if lid == location_id:
                return name
        return f"未知位面({location_id})"
