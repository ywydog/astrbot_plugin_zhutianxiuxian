import json
from pathlib import Path
from typing import Any


class BossData:
    """世界 BOSS（妖王）配置加载器，提供 BOSS 参数与默认模板。"""

    DEFAULT_CONFIG: dict[str, Any] = {
        "qualified_level": 42,
        "min_players": 1,
        "base_reward": 12_000_000,
        "min_reward": 6_000_000,
        "cd_seconds": 300,
        "phantom_name": "妖王幻影",
        "killer_bonus": 1_000_000,
        "min_damage_share": 200_000,
        "reward_rank_limit": 20,
        "top_attack_skip": 2,
        "bottom_attack_skip": 4,
        "max_attack_samples": 15,
        "health_multiplier": 200,
    }

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.file_path = data_dir / "boss_config.json"
        self._config: dict[str, Any] | None = None

    def _load(self) -> dict[str, Any]:
        if not self.file_path.exists():
            return dict(self.DEFAULT_CONFIG)
        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return dict(self.DEFAULT_CONFIG)
            config = dict(self.DEFAULT_CONFIG)
            config.update(data)
            return config
        except (json.JSONDecodeError, OSError):
            return dict(self.DEFAULT_CONFIG)

    def get_config(self) -> dict[str, Any]:
        """返回合并后的 BOSS 配置。"""
        if self._config is None:
            self._config = self._load()
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """按 key 读取配置项，不存在时返回 default。"""
        return self.get_config().get(key, default)

    def qualified_level(self) -> int:
        return int(self.get("qualified_level", self.DEFAULT_CONFIG["qualified_level"]))

    def min_players(self) -> int:
        return int(self.get("min_players", self.DEFAULT_CONFIG["min_players"]))

    def base_reward(self) -> int:
        return int(self.get("base_reward", self.DEFAULT_CONFIG["base_reward"]))

    def min_reward(self) -> int:
        return int(self.get("min_reward", self.DEFAULT_CONFIG["min_reward"]))

    def cd_seconds(self) -> int:
        return int(self.get("cd_seconds", self.DEFAULT_CONFIG["cd_seconds"]))

    def phantom_name(self) -> str:
        return str(self.get("phantom_name", self.DEFAULT_CONFIG["phantom_name"]))

    def killer_bonus(self) -> int:
        return int(self.get("killer_bonus", self.DEFAULT_CONFIG["killer_bonus"]))

    def min_damage_share(self) -> int:
        return int(self.get("min_damage_share", self.DEFAULT_CONFIG["min_damage_share"]))

    def reward_rank_limit(self) -> int:
        return int(self.get("reward_rank_limit", self.DEFAULT_CONFIG["reward_rank_limit"]))
