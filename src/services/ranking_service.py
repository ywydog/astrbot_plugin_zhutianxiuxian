from pathlib import Path
from typing import Any

from src.services.player_service import PlayerService


class RankingService:
    """排行榜服务：扫描所有玩家并按指定维度排序。"""

    DEFAULT_LIMIT = 20

    def __init__(self, player_service: PlayerService, data_dir: Path | None = None):
        self.player_service = player_service
        self.data_dir = data_dir

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
