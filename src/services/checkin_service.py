from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class CheckinResult:
    success: bool = False
    already_signed: bool = False
    player_not_found: bool = False
    consecutive_days: int = 0
    spirit_stones_gained: int = 0
    source_stones_gained: int = 0
    exp_gained: int = 0
    blood_qi_gained: int = 0


class CheckinService:
    """每日签到服务。"""

    def __init__(
        self,
        player_service: PlayerService,
        state_service: StateService,
        today_provider: Callable[[], str] | None = None,
    ):
        self.player_service = player_service
        self.state_service = state_service
        self.today_provider = today_provider or state_service.today_str

    def _last_sign_key(self, user_id: str) -> str:
        return f"player:{user_id}:daily_last_sign_date"

    async def daily_checkin(self, user_id: str) -> CheckinResult:
        if not await self.player_service.exists(user_id):
            return CheckinResult(player_not_found=True)

        today = self.today_provider()
        yesterday = (
            datetime.strptime(today, "%Y-%m-%d") - timedelta(days=1)
        ).strftime("%Y-%m-%d")

        last_sign_date = await self.state_service.get(
            self._last_sign_key(user_id), default=None
        )

        player = await self.player_service.load(user_id)
        assert player is not None

        if last_sign_date == today:
            return CheckinResult(
                success=False,
                already_signed=True,
                consecutive_days=player.get("consecutive_checkin_days", 0),
            )

        # 更新连续签到天数
        if last_sign_date == yesterday:
            consecutive = player.get("consecutive_checkin_days", 0) + 1
        else:
            consecutive = 1
        player["consecutive_checkin_days"] = consecutive

        # 计算奖励
        multiplier = player.get("level_id", 1) * player.get("physique_id", 1)
        multiplier += player.get("mijing_level_id", 1) * player.get("xiangu_level_id", 1)
        if multiplier < 1:
            multiplier = 1

        # 道法仙术玩家双倍奖励
        base_multiplier = 2 if player.get("daofa_xianshu") == 2 else 1

        spirit_stones = consecutive * 300 * base_multiplier * multiplier
        source_stones = consecutive * 300 * base_multiplier * multiplier
        exp = consecutive * 10000 * base_multiplier * multiplier
        blood_qi = exp

        # 发放奖励并保存玩家数据
        player["spirit_stones"] = player.get("spirit_stones", 0) + spirit_stones
        player["source_stones"] = player.get("source_stones", 0) + source_stones
        player["exp"] = player.get("exp", 0) + exp
        player["blood_qi"] = player.get("blood_qi", 0) + blood_qi
        player["consecutive_checkin_days"] = consecutive
        await self.player_service.save(user_id, player)
        await self.state_service.set(self._last_sign_key(user_id), today)

        return CheckinResult(
            success=True,
            consecutive_days=consecutive,
            spirit_stones_gained=spirit_stones,
            source_stones_gained=source_stones,
            exp_gained=exp,
            blood_qi_gained=blood_qi,
        )
