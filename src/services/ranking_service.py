from pathlib import Path
from typing import Any

from src.data.level_data import LevelData
from src.services.player_service import PlayerService


class RankingService:
    """排行榜服务：扫描所有玩家并按指定维度排序。"""

    DEFAULT_LIMIT = 20

    def __init__(
        self,
        player_service: PlayerService,
        data_dir: Path | None = None,
        level_data: LevelData | None = None,
    ):
        self.player_service = player_service
        self.data_dir = data_dir
        self.level_data = level_data

    async def _scan_players(self) -> list[dict[str, Any]]:
        """扫描所有玩家存档。"""
        players: list[dict[str, Any]] = []
        players_dir = self.player_service.players_dir
        if not players_dir.exists():
            return players
        for file_path in players_dir.glob("*.json"):
            user_id = file_path.stem
            player = await self.player_service.load(user_id)
            if player:
                players.append(player)
        return players

    async def _get_ranking(
        self,
        score_func: callable,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """通用排行榜计算。"""
        players = await self._scan_players()
        limit = limit if limit is not None else self.DEFAULT_LIMIT

        scored = []
        for player in players:
            score = score_func(player)
            scored.append(
                {
                    "user_id": player.get("id", ""),
                    "name": player.get("name", "无名"),
                    "level_id": player.get("level_id", 1),
                    "score": score,
                }
            )

        scored.sort(key=lambda x: x["score"], reverse=True)
        for rank, item in enumerate(scored[:limit], start=1):
            item["rank"] = rank
        return scored[:limit]

    async def get_modao_ranking(self, limit: int | None = None) -> list[dict[str, Any]]:
        """魔道榜：按魔道值排序。"""
        return await self._get_ranking(
            lambda p: int(p.get("modao_value", 0)),
            limit=limit,
        )

    async def get_enhance_ranking(self, limit: int | None = None) -> list[dict[str, Any]]:
        """强化榜：按攻击、防御、生命加成总和排序。"""
        return await self._get_ranking(
            lambda p: int(
                p.get("attack_bonus", 0)
                + p.get("defense_bonus", 0)
                + p.get("hp_bonus", 0)
            ),
            limit=limit,
        )

    async def get_exp_ranking(self, limit: int | None = None) -> list[dict[str, Any]]:
        """天榜：按修为排序。"""
        return await self._get_ranking(
            lambda p: int(p.get("exp", 0)),
            limit=limit,
        )

    async def get_spirit_stones_ranking(
        self, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """灵榜：按灵石排序。"""
        return await self._get_ranking(
            lambda p: int(p.get("spirit_stones", 0)),
            limit=limit,
        )

    async def get_power_ranking(self, limit: int | None = None) -> list[dict[str, Any]]:
        """战力榜：按综合战力排序。"""
        return await self._get_ranking(
            lambda p: int(
                (
                    p.get("attack_bonus", 0)
                    + p.get("defense_bonus", 0) * 0.8
                    + p.get("hp_bonus", 0) * 0.5
                )
                * (p.get("crit_rate", 0) + 1)
            ),
            limit=limit,
        )

    def _base_stats(self, player: dict[str, Any]) -> dict[str, int | float]:
        """计算玩家基础战斗属性。"""
        if self.level_data is not None:
            return self.level_data.get_cultivation_stats(
                player.get("level_id", 1)
            )
        return {"attack": 0, "defense": 0, "hp": 0, "crit_rate": 0}

    def _power_full(
        self, player: dict[str, Any]
    ) -> int:
        """满系数战力：(攻击+防御+血量)*(暴击率+1)。"""
        stats = self._base_stats(player)
        attack = int(stats.get("attack", 0)) + int(player.get("attack_bonus", 0))
        defense = int(stats.get("defense", 0)) + int(player.get("defense_bonus", 0))
        hp = int(stats.get("hp", 0)) + int(player.get("hp_bonus", 0))
        crit = float(stats.get("crit_rate", 0)) + float(player.get("crit_rate", 0))
        return int((attack + defense + hp) * (crit + 1))

    def _power_zhizun(
        self, player: dict[str, Any]
    ) -> int:
        """至尊榜战力：(攻击+防御*0.8+血量*0.6)*(暴击率+1)。"""
        stats = self._base_stats(player)
        attack = int(stats.get("attack", 0)) + int(player.get("attack_bonus", 0))
        defense = int(stats.get("defense", 0)) + int(player.get("defense_bonus", 0))
        hp = int(stats.get("hp", 0)) + int(player.get("hp_bonus", 0))
        crit = float(stats.get("crit_rate", 0)) + float(player.get("crit_rate", 0))
        return int((attack + defense * 0.8 + hp * 0.6) * (crit + 1))

    async def get_fengshen_ranking(
        self, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """封神榜：仙人境界以上（level_id >= 42）按满系数战力排序。"""
        return await self._get_ranking(
            lambda p: (
                self._power_full(p) if p.get("level_id", 1) >= 42 else -1
            ),
            limit=limit,
        )

    async def get_zhetian_ranking(
        self, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """遮天榜：秘境体系 level_id >= 2 按满系数战力排序。"""
        return await self._get_ranking(
            lambda p: (
                self._power_full(p) if p.get("mijing_level_id", 1) >= 2 else -1
            ),
            limit=limit,
        )

    async def get_xiangu_ranking(
        self, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """完美世界榜：仙古 level_id >= 2 按满系数战力排序。"""
        return await self._get_ranking(
            lambda p: (
                self._power_full(p) if p.get("xiangu_level_id", 1) >= 2 else -1
            ),
            limit=limit,
        )

    async def get_zhizun_ranking(
        self, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """至尊榜：凡人境界（level_id < 42）按至尊战力排序。"""
        return await self._get_ranking(
            lambda p: (
                self._power_zhizun(p) if p.get("level_id", 1) < 42 else -1
            ),
            limit=limit,
        )

    async def get_zhenyao_ranking(
        self, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """镇妖塔榜：按镇妖塔层数排序。"""
        return await self._get_ranking(
            lambda p: int(p.get("zhenyao_floor", 0)),
            limit=limit,
        )

    async def get_shenpo_ranking(
        self, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """神魄榜：按神魄段数排序。"""
        return await self._get_ranking(
            lambda p: int(p.get("shenpo_stage", 0)),
            limit=limit,
        )
