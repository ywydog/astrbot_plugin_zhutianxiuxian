import json
from pathlib import Path
from typing import Any


class SectData:
    """宗门数据加载器。"""

    MEMBER_LIMITS = [6, 9, 12, 15, 18, 21, 24, 27]
    POOL_LIMITS = [
        2000000, 5000000, 8000000, 11000000,
        15000000, 20000000, 25000000, 30000000,
    ]

    def __init__(self, data_dir: Path):
        self.sect_dir = data_dir / "sect"
        self._sects: dict[str, dict[str, Any]] | None = None

    def _load(self) -> dict[str, dict[str, Any]]:
        file_path = self.sect_dir / "sects.json"
        if not file_path.exists():
            return {}
        return json.loads(file_path.read_text(encoding="utf-8"))

    @property
    def sects(self) -> dict[str, dict[str, Any]]:
        if self._sects is None:
            self._sects = self._load()
        return self._sects

    def get_member_limit(self, level: int) -> int:
        index = max(0, min(level - 1, len(self.MEMBER_LIMITS) - 1))
        return self.MEMBER_LIMITS[index]

    def get_pool_limit(self, level: int, power: int) -> int:
        index = max(0, min(level - 1, len(self.POOL_LIMITS) - 1))
        base = self.POOL_LIMITS[index]
        return base * (10 if power == 1 else 1)

    def get(self, name: str) -> dict[str, Any] | None:
        return self.sects.get(name)

    def list_names(self) -> list[str]:
        return list(self.sects.keys())
