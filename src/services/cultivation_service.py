import time
from dataclasses import dataclass
from typing import Any

from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class SessionResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    action: str = ""
    elapsed_minutes: int = 0
    exp_gained: int = 0
    blood_qi_gained: int = 0


class CultivationService:
    """管理闭关、降妖等持续修炼会话。"""

    def __init__(self, player_service: PlayerService, state_service: StateService):
        self.player_service = player_service
        self.state_service = state_service

    def _state_key(self, user_id: str) -> str:
        return f"xiuxian:player:{user_id}:action"

    async def _get_action(self, user_id: str) -> dict[str, Any] | None:
        return await self.state_service.get(self._state_key(user_id), None)

    async def _set_action(self, user_id: str, action: dict[str, Any] | None) -> None:
        if action is None:
            await self.state_service.delete(self._state_key(user_id))
        else:
            await self.state_service.set(self._state_key(user_id), action)

    async def get_current_action(
        self, user_id: str, now: float | None = None
    ) -> dict[str, Any] | None:
        """获取玩家当前正在进行的动作及剩余时间。"""
        action = await self._get_action(user_id)
        if not action:
            return None

        now_ms = int((now or time.time()) * 1000)
        end_time = action.get("end_time", now_ms)
        remaining_ms = max(0, end_time - now_ms)
        if remaining_ms == 0:
            return None

        minutes = remaining_ms // (1000 * 60)
        seconds = (remaining_ms % (1000 * 60)) // 1000
        return {
            "action": action.get("action", "修炼"),
            "remaining_minutes": int(minutes),
            "remaining_seconds": int(seconds),
        }

    async def start_seclusion(
        self, user_id: str, minutes: int, now: float | None = None
    ) -> SessionResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return SessionResult(player_not_found=True)

        action = await self._get_action(user_id)
        if action and action.get("end_time", 0) > (now or time.time()) * 1000:
            return SessionResult(
                success=False,
                reason=f"正在{action.get('action', '修炼')}中",
            )

        minutes = max(30, min(minutes, 240))
        now_ms = int((now or time.time()) * 1000)

        await self._set_action(
            user_id,
            {
                "action": "闭关",
                "start_time": now_ms,
                "end_time": now_ms + minutes * 60 * 1000,
                "time": minutes * 60 * 1000,
            },
        )
        return SessionResult(success=True, action="闭关", elapsed_minutes=minutes)

    async def end_seclusion(
        self, user_id: str, now: float | None = None
    ) -> SessionResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return SessionResult(player_not_found=True)

        action = await self._get_action(user_id)
        if not action or action.get("action") != "闭关":
            return SessionResult(success=False, reason="当前不在闭关中")

        now_ms = int((now or time.time()) * 1000)
        start_time = action.get("start_time", action.get("end_time", now_ms) - action.get("time", 0))
        elapsed_ms = min(now_ms - start_time, action.get("time", 0))
        elapsed_minutes = int(elapsed_ms / 1000 / 60)

        # 按 30 分钟为周期结算，不足不计
        cycle = 30
        settled_minutes = (elapsed_minutes // cycle) * cycle

        if settled_minutes < cycle:
            await self._set_action(user_id, None)
            return SessionResult(
                success=False,
                reason="闭关时间不足 30 分钟，未获得收益",
            )

        level_id = player.get("level_id", 1)
        efficiency = player.get("cultivation_efficiency", 1.0)
        exp_gained = int(settled_minutes * level_id * 10 * efficiency)

        player["exp"] = player.get("exp", 0) + exp_gained
        await self.player_service.save(user_id, player)
        await self._set_action(user_id, None)

        return SessionResult(
            success=True,
            action="闭关",
            elapsed_minutes=settled_minutes,
            exp_gained=exp_gained,
        )

    async def start_hunt(
        self, user_id: str, minutes: int, now: float | None = None
    ) -> SessionResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return SessionResult(player_not_found=True)

        action = await self._get_action(user_id)
        if action and action.get("end_time", 0) > (now or time.time()) * 1000:
            return SessionResult(
                success=False,
                reason=f"正在{action.get('action', '修炼')}中",
            )

        minutes = max(15, min(minutes, 240))
        now_ms = int((now or time.time()) * 1000)

        await self._set_action(
            user_id,
            {
                "action": "降妖",
                "start_time": now_ms,
                "end_time": now_ms + minutes * 60 * 1000,
                "time": minutes * 60 * 1000,
            },
        )
        return SessionResult(success=True, action="降妖", elapsed_minutes=minutes)

    async def end_hunt(self, user_id: str, now: float | None = None) -> SessionResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return SessionResult(player_not_found=True)

        action = await self._get_action(user_id)
        if not action or action.get("action") != "降妖":
            return SessionResult(success=False, reason="当前不在降妖中")

        now_ms = int((now or time.time()) * 1000)
        start_time = action.get("start_time", action.get("end_time", now_ms) - action.get("time", 0))
        elapsed_ms = min(now_ms - start_time, action.get("time", 0))
        elapsed_minutes = int(elapsed_ms / 1000 / 60)

        cycle = 15
        settled_minutes = (elapsed_minutes // cycle) * cycle

        if settled_minutes < cycle:
            await self._set_action(user_id, None)
            return SessionResult(
                success=False,
                reason="降妖时间不足 15 分钟，未获得收益",
            )

        physique_id = player.get("physique_id", 1)
        blood_qi_gained = int(settled_minutes * physique_id * 10)

        player["blood_qi"] = player.get("blood_qi", 0) + blood_qi_gained
        await self.player_service.save(user_id, player)
        await self._set_action(user_id, None)

        return SessionResult(
            success=True,
            action="降妖",
            elapsed_minutes=settled_minutes,
            blood_qi_gained=blood_qi_gained,
        )
