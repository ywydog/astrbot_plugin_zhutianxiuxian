import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@dataclass
class PataResult:
    """镇妖塔 / 锻神池挑战结果。"""

    success: bool = False
    player_not_found: bool = False
    in_cooldown: bool = False
    cooldown_seconds: int = 0
    win: bool = False
    current_floor: int = 0
    current_stage: int = 0
    floors_gained: int = 0
    stages_gained: int = 0
    spirit_stones: int = 0
    exp: int = 0
    blood_qi: int = 0
    source_stones: int = 0
    message: str = ""


class PataService:
    """爬塔服务：镇妖塔、锻神池挑战。"""

    # 每层/段 BOSS 三围基数（hp, atk, def）
    ZHENYAO_BASE = {"hp": 2500, "atk": 2500, "def": 2500}
    SHENPO_BASE = {"hp": 4000, "atk": 4000, "def": 4000}

    # 挑战冷却：1 小时
    COOLDOWN_SECONDS = 3600
    # 自动挑战上限
    AUTO_LIMIT = 50000

    def __init__(
        self,
        player_service: PlayerService,
        inventory_service: InventoryService,
        data_dir: Path,
    ):
        self.player_service = player_service
        self.inventory_service = inventory_service
        self.data_dir = data_dir

    @staticmethod
    def _now() -> float:
        return time.time()

    def _player_power(self, player: dict[str, Any]) -> int:
        return (
            int(player.get("attack_bonus", 0))
            + int(player.get("defense_bonus", 0))
            + int(player.get("hp_bonus", 0))
            + int(player.get("level_id", 1)) * 10000
        )

    def _boss_power(self, level: int, base: dict[str, int]) -> int:
        level = max(1, level)
        return (
            base["hp"] * level
            + base["atk"] * level
            + base["def"] * level
        )

    def _check_cooldown(
        self, player: dict[str, Any], key: str, now: float
    ) -> tuple[bool, int]:
        last = player.get(key, 0) or 0
        elapsed = now - last
        if elapsed < self.COOLDOWN_SECONDS:
            return True, int(self.COOLDOWN_SECONDS - elapsed)
        return False, 0

    def _set_cooldown(self, player: dict[str, Any], key: str, now: float) -> None:
        player[key] = now

    def _zhenyao_reward(self, floor: int) -> dict[str, int]:
        return {
            "spirit_stones": 100 * floor,
            "exp": 50 * floor,
            "blood_qi": 25 * floor,
        }

    def _shenpo_reward(self, stage: int) -> dict[str, int]:
        return {
            "source_stones": 50 * stage,
            "blood_qi": 100 * stage,
        }

    async def challenge_zhenyao(self, user_id: str) -> PataResult:
        """挑战镇妖塔下一层。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return PataResult(player_not_found=True)

        now = self._now()
        in_cd, remain = self._check_cooldown(
            player, "zhenyao_last_challenge", now
        )
        if in_cd:
            return PataResult(
                success=False,
                in_cooldown=True,
                cooldown_seconds=remain,
                current_floor=player.get("zhenyao_floor", 0),
            )

        current_floor = player.get("zhenyao_floor", 0)
        target_floor = current_floor + 1
        player_power = self._player_power(player)
        boss_power = self._boss_power(target_floor, self.ZHENYAO_BASE)

        self._set_cooldown(player, "zhenyao_last_challenge", now)

        if player_power > boss_power * 1.2:
            rewards = self._zhenyao_reward(target_floor)
            player["zhenyao_floor"] = target_floor
            player["spirit_stones"] = player.get("spirit_stones", 0) + rewards["spirit_stones"]
            player["exp"] = player.get("exp", 0) + rewards["exp"]
            player["blood_qi"] = player.get("blood_qi", 0) + rewards["blood_qi"]
            await self.player_service.save(user_id, player)
            return PataResult(
                success=True,
                win=True,
                current_floor=target_floor,
                floors_gained=1,
                spirit_stones=rewards["spirit_stones"],
                exp=rewards["exp"],
                blood_qi=rewards["blood_qi"],
                message=f"挑战镇妖塔第 {target_floor} 层成功！",
            )

        await self.player_service.save(user_id, player)
        return PataResult(
            success=True,
            win=False,
            current_floor=current_floor,
            message=f"挑战镇妖塔第 {target_floor} 层失败，实力不足。",
        )

    async def auto_challenge_zhenyao(self, user_id: str) -> PataResult:
        """一键挑战镇妖塔，直到失败或达到上限。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return PataResult(player_not_found=True)

        now = self._now()
        in_cd, remain = self._check_cooldown(
            player, "zhenyao_last_challenge", now
        )
        if in_cd:
            return PataResult(
                success=False,
                in_cooldown=True,
                cooldown_seconds=remain,
                current_floor=player.get("zhenyao_floor", 0),
            )

        self._set_cooldown(player, "zhenyao_last_challenge", now)

        floors_gained = 0
        total_spirit = 0
        total_exp = 0
        total_blood = 0

        while floors_gained < self.AUTO_LIMIT:
            current_floor = player.get("zhenyao_floor", 0)
            target_floor = current_floor + 1
            player_power = self._player_power(player)
            boss_power = self._boss_power(target_floor, self.ZHENYAO_BASE)
            if player_power <= boss_power * 1.2:
                break
            rewards = self._zhenyao_reward(target_floor)
            player["zhenyao_floor"] = target_floor
            player["spirit_stones"] = player.get("spirit_stones", 0) + rewards["spirit_stones"]
            player["exp"] = player.get("exp", 0) + rewards["exp"]
            player["blood_qi"] = player.get("blood_qi", 0) + rewards["blood_qi"]
            floors_gained += 1
            total_spirit += rewards["spirit_stones"]
            total_exp += rewards["exp"]
            total_blood += rewards["blood_qi"]

        await self.player_service.save(user_id, player)
        current_floor = player.get("zhenyao_floor", 0)
        return PataResult(
            success=True,
            win=floors_gained > 0,
            current_floor=current_floor,
            floors_gained=floors_gained,
            spirit_stones=total_spirit,
            exp=total_exp,
            blood_qi=total_blood,
            message=f"一键镇妖塔结束，共通过 {floors_gained} 层，当前第 {current_floor} 层。",
        )

    async def get_zhenyao(self, user_id: str) -> PataResult:
        """查询镇妖塔当前层数。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return PataResult(player_not_found=True)
        return PataResult(
            success=True,
            current_floor=player.get("zhenyao_floor", 0),
            message=f"当前镇妖塔层数：{player.get('zhenyao_floor', 0)}",
        )

    async def challenge_shenpo(self, user_id: str) -> PataResult:
        """挑战锻神池下一段。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return PataResult(player_not_found=True)

        now = self._now()
        in_cd, remain = self._check_cooldown(
            player, "shenpo_last_challenge", now
        )
        if in_cd:
            return PataResult(
                success=False,
                in_cooldown=True,
                cooldown_seconds=remain,
                current_stage=player.get("shenpo_stage", 0),
            )

        current_stage = player.get("shenpo_stage", 0)
        target_stage = current_stage + 1
        player_power = self._player_power(player)
        boss_power = self._boss_power(target_stage, self.SHENPO_BASE)

        self._set_cooldown(player, "shenpo_last_challenge", now)

        if player_power > boss_power * 1.2:
            rewards = self._shenpo_reward(target_stage)
            player["shenpo_stage"] = target_stage
            player["source_stones"] = player.get("source_stones", 0) + rewards["source_stones"]
            player["blood_qi"] = player.get("blood_qi", 0) + rewards["blood_qi"]
            await self.player_service.save(user_id, player)
            return PataResult(
                success=True,
                win=True,
                current_stage=target_stage,
                stages_gained=1,
                source_stones=rewards["source_stones"],
                blood_qi=rewards["blood_qi"],
                message=f"挑战锻神池第 {target_stage} 段成功！",
            )

        await self.player_service.save(user_id, player)
        return PataResult(
            success=True,
            win=False,
            current_stage=current_stage,
            message=f"挑战锻神池第 {target_stage} 段失败，实力不足。",
        )

    async def auto_challenge_shenpo(self, user_id: str) -> PataResult:
        """一键锻神池，直到失败或达到上限。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return PataResult(player_not_found=True)

        now = self._now()
        in_cd, remain = self._check_cooldown(
            player, "shenpo_last_challenge", now
        )
        if in_cd:
            return PataResult(
                success=False,
                in_cooldown=True,
                cooldown_seconds=remain,
                current_stage=player.get("shenpo_stage", 0),
            )

        self._set_cooldown(player, "shenpo_last_challenge", now)

        stages_gained = 0
        total_source = 0
        total_blood = 0

        while stages_gained < self.AUTO_LIMIT:
            current_stage = player.get("shenpo_stage", 0)
            target_stage = current_stage + 1
            player_power = self._player_power(player)
            boss_power = self._boss_power(target_stage, self.SHENPO_BASE)
            if player_power <= boss_power * 1.2:
                break
            rewards = self._shenpo_reward(target_stage)
            player["shenpo_stage"] = target_stage
            player["source_stones"] = player.get("source_stones", 0) + rewards["source_stones"]
            player["blood_qi"] = player.get("blood_qi", 0) + rewards["blood_qi"]
            stages_gained += 1
            total_source += rewards["source_stones"]
            total_blood += rewards["blood_qi"]

        await self.player_service.save(user_id, player)
        current_stage = player.get("shenpo_stage", 0)
        return PataResult(
            success=True,
            win=stages_gained > 0,
            current_stage=current_stage,
            stages_gained=stages_gained,
            source_stones=total_source,
            blood_qi=total_blood,
            message=f"一键锻神池结束，共通过 {stages_gained} 段，当前第 {current_stage} 段。",
        )

    async def get_shenpo(self, user_id: str) -> PataResult:
        """查询锻神池当前段数。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return PataResult(player_not_found=True)
        return PataResult(
            success=True,
            current_stage=player.get("shenpo_stage", 0),
            message=f"当前锻神池段数：{player.get('shenpo_stage', 0)}",
        )
