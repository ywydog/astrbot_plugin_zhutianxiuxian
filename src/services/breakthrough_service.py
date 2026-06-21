from dataclasses import dataclass

from src.data.level_data import LevelData
from src.services.player_service import PlayerService


@dataclass
class BreakthroughResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    old_level: int = 0
    new_level: int = 0
    required_exp: int = 0
    level_name: str = ""


@dataclass
class AutoBreakthroughResult:
    player_not_found: bool = False
    total_levels: int = 0
    final_level: int = 0
    level_name: str = ""
    reason: str = ""


class BreakthroughService:
    """境界突破服务。"""

    def __init__(self, player_service: PlayerService, level_data: LevelData):
        self.player_service = player_service
        self.level_data = level_data

    async def _auto_upgrade(self, attempt_fn, name_fn) -> AutoBreakthroughResult:
        """循环尝试突破，直到资源不足或达到最高境界。"""
        result = AutoBreakthroughResult()
        while True:
            r = await attempt_fn()
            if r.player_not_found:
                return AutoBreakthroughResult(player_not_found=True)
            if not r.success:
                result.reason = r.reason
                result.final_level = r.old_level
                result.level_name = name_fn(r.old_level)
                return result
            result.total_levels += 1
            result.final_level = r.new_level
            result.level_name = r.level_name

    async def _do_upgrade(
        self,
        user_id: str,
        level_key: str,
        resource_key: str,
        resource_name: str,
        max_level_fn,
        required_fn,
        name_fn,
        levels_fn,
        cost_spirit_stones: int = 0,
    ) -> BreakthroughResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return BreakthroughResult(player_not_found=True)

        current_level = player.get(level_key, 1)
        max_level = max_level_fn()

        if current_level >= max_level:
            return BreakthroughResult(
                success=False,
                reason="已达最高境界",
                old_level=current_level,
            )

        required_resource = required_fn(current_level)
        current_resource = player.get(resource_key, 0)

        if current_resource < required_resource:
            return BreakthroughResult(
                success=False,
                reason=f"{resource_name}不足",
                old_level=current_level,
                required_exp=required_resource,
            )

        if cost_spirit_stones > 0:
            spirit_stones = player.get("spirit_stones", 0)
            if spirit_stones < cost_spirit_stones:
                return BreakthroughResult(
                    success=False,
                    reason=f"灵石不足，幸运突破需要 {cost_spirit_stones} 灵石",
                    old_level=current_level,
                )
            player["spirit_stones"] = spirit_stones - cost_spirit_stones

        player[resource_key] = current_resource - required_resource
        player[level_key] = current_level + 1

        new_level_info = None
        for item in levels_fn():
            if item.get("level_id") == player[level_key]:
                new_level_info = item
                break
        if new_level_info:
            hp_bonus = new_level_info.get("基础血量", 0)
            if hp_bonus:
                player["current_hp"] = player.get("current_hp", 0) + hp_bonus

        await self.player_service.save(user_id, player)

        return BreakthroughResult(
            success=True,
            old_level=current_level,
            new_level=player[level_key],
            level_name=name_fn(player[level_key]),
        )

    async def attempt_cultivation_breakthrough(self, user_id: str) -> BreakthroughResult:
        return await self._do_upgrade(
            user_id,
            level_key="level_id",
            resource_key="exp",
            resource_name="修为",
            max_level_fn=self.level_data.max_cultivation_level,
            required_fn=self.level_data.get_cultivation_exp_required,
            name_fn=self.level_data.get_cultivation_name,
            levels_fn=lambda: self.level_data.cultivation_levels,
        )

    async def attempt_cultivation_lucky_breakthrough(self, user_id: str) -> BreakthroughResult:
        return await self._do_upgrade(
            user_id,
            level_key="level_id",
            resource_key="exp",
            resource_name="修为",
            max_level_fn=self.level_data.max_cultivation_level,
            required_fn=self.level_data.get_cultivation_exp_required,
            name_fn=self.level_data.get_cultivation_name,
            levels_fn=lambda: self.level_data.cultivation_levels,
            cost_spirit_stones=500,
        )

    async def attempt_physique_breakthrough(self, user_id: str) -> BreakthroughResult:
        return await self._do_upgrade(
            user_id,
            level_key="physique_id",
            resource_key="blood_qi",
            resource_name="血气",
            max_level_fn=self.level_data.max_physique_level,
            required_fn=self.level_data.get_physique_exp_required,
            name_fn=self.level_data.get_physique_name,
            levels_fn=lambda: self.level_data.physique_levels,
        )

    async def attempt_physique_lucky_breakthrough(self, user_id: str) -> BreakthroughResult:
        return await self._do_upgrade(
            user_id,
            level_key="physique_id",
            resource_key="blood_qi",
            resource_name="血气",
            max_level_fn=self.level_data.max_physique_level,
            required_fn=self.level_data.get_physique_exp_required,
            name_fn=self.level_data.get_physique_name,
            levels_fn=lambda: self.level_data.physique_levels,
            cost_spirit_stones=500,
        )

    async def attempt_cultivation_auto_breakthrough(self, user_id: str) -> AutoBreakthroughResult:
        return await self._auto_upgrade(
            lambda: self.attempt_cultivation_breakthrough(user_id),
            self.level_data.get_cultivation_name,
        )

    async def attempt_physique_auto_breakthrough(self, user_id: str) -> AutoBreakthroughResult:
        return await self._auto_upgrade(
            lambda: self.attempt_physique_breakthrough(user_id),
            self.level_data.get_physique_name,
        )
