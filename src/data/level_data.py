import json
from pathlib import Path


class LevelData:
    """境界数据加载器。"""

    def __init__(self, data_dir: Path):
        self.levels_dir = data_dir / "levels"
        self._cultivation: list[dict] | None = None
        self._physique: list[dict] | None = None
        self._mijing: list[dict] | None = None
        self._xiangu: list[dict] | None = None
        self._yuanshen: list[dict] | None = None

    def _load(self, filename: str) -> list[dict]:
        file_path = self.levels_dir / filename
        if not file_path.exists():
            return []
        return json.loads(file_path.read_text(encoding="utf-8"))

    @property
    def cultivation_levels(self) -> list[dict]:
        if self._cultivation is None:
            self._cultivation = self._load("练气境界.json")
        return self._cultivation

    @property
    def physique_levels(self) -> list[dict]:
        if self._physique is None:
            self._physique = self._load("炼体境界.json")
        return self._physique

    @property
    def mijing_levels(self) -> list[dict]:
        if self._mijing is None:
            self._mijing = self._load("秘境体系.json")
        return self._mijing

    @property
    def xiangu_levels(self) -> list[dict]:
        if self._xiangu is None:
            self._xiangu = self._load("仙古今世法.json")
        return self._xiangu

    @property
    def yuanshen_levels(self) -> list[dict]:
        if self._yuanshen is None:
            self._yuanshen = self._load("元神境界.json")
        return self._yuanshen

    def _get_name(self, levels: list[dict], level_id: int) -> str:
        for item in levels:
            if item.get("level_id") == level_id:
                return item.get("level", "未知")
        return "未知"

    def get_cultivation_name(self, level_id: int) -> str:
        return self._get_name(self.cultivation_levels, level_id)

    def get_physique_name(self, level_id: int) -> str:
        return self._get_name(self.physique_levels, level_id)

    def get_mijing_name(self, level_id: int) -> str:
        return self._get_name(self.mijing_levels, level_id)

    def get_xiangu_name(self, level_id: int) -> str:
        return self._get_name(self.xiangu_levels, level_id)

    def get_xiangu(self, level_id: int) -> dict | None:
        for item in self.xiangu_levels:
            if item.get("level_id") == level_id:
                return item
        return None

    def get_yuanshen_name(self, level_id: int) -> str:
        return self._get_name(self.yuanshen_levels, level_id)

    def get_cultivation_exp_required(self, level_id: int) -> int:
        for item in self.cultivation_levels:
            if item.get("level_id") == level_id:
                return item.get("exp", 0)
        return 0

    def get_cultivation_stats(self, level_id: int) -> dict[str, int | float]:
        """获取指定练气境界的基础战斗属性。"""
        for item in self.cultivation_levels:
            if item.get("level_id") == level_id:
                return {
                    "attack": item.get("基础攻击", 0),
                    "defense": item.get("基础防御", 0),
                    "hp": item.get("基础血量", 0),
                    "crit_rate": item.get("基础暴击", 0),
                }
        return {"attack": 0, "defense": 0, "hp": 0, "crit_rate": 0}

    def get_physique_exp_required(self, level_id: int) -> int:
        for item in self.physique_levels:
            if item.get("level_id") == level_id:
                return item.get("exp", 0)
        return 0

    def max_cultivation_level(self) -> int:
        levels = [item.get("level_id", 0) for item in self.cultivation_levels]
        return max(levels) if levels else 0

    def max_physique_level(self) -> int:
        levels = [item.get("level_id", 0) for item in self.physique_levels]
        return max(levels) if levels else 0

    def max_mijing_level(self) -> int:
        levels = [item.get("level_id", 0) for item in self.mijing_levels]
        return max(levels) if levels else 0

    def max_xiangu_level(self) -> int:
        levels = [item.get("level_id", 0) for item in self.xiangu_levels]
        return max(levels) if levels else 0

    def max_yuanshen_level(self) -> int:
        levels = [item.get("level_id", 0) for item in self.yuanshen_levels]
        return max(levels) if levels else 0
