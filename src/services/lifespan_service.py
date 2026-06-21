import time
from dataclasses import dataclass
from typing import Any

from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class LifespanReduceResult:
    """寿元批量流逝结果。"""

    processed: int = 0
    skipped_gm: int = 0
    skipped_sealed: int = 0
    high_level_count: int = 0
    special_body_count: int = 0
    base_amount: int = 0
    duration_seconds: float = 0.0
    error: str | None = None


class LifespanService:
    """寿元系统服务：负责寿元流逝计算与查询。"""

    # 默认定时任务规则（每三小时）
    DEFAULT_TASK_BASE = 1000
    DEFAULT_TASK_LOW_LEVEL_AMOUNT = 20
    DEFAULT_TASK_HIGH_LEVEL_RATIO = 0.5
    DEFAULT_TASK_LOW_LEVEL_THRESHOLD = 41
    DEFAULT_TASK_HIGH_LEVEL_THRESHOLD = 50

    # 默认手动执行规则
    DEFAULT_MANUAL_BASE = 1000
    DEFAULT_MANUAL_LOW_LEVEL_AMOUNT = 100
    DEFAULT_MANUAL_HIGH_LEVEL_RATIO = 0.5
    DEFAULT_MANUAL_LOW_LEVEL_THRESHOLD = 41
    DEFAULT_MANUAL_HIGH_LEVEL_THRESHOLD = 50

    # 特殊体质流逝系数（体质名 -> (任务系数, 手动系数)）
    SPECIAL_BODY_RATIOS: dict[str, tuple[float, float]] = {
        "圆环之理": (1.0, 0.1),
        "圣体道胎": (0.3, 0.5),
        "大成圣体": (0.3, 0.5),
        "大成霸体": (0.3, 0.5),
        "混沌体": (1.0, 0.5),
        "小成圣体": (0.5, 0.6),
        "小成霸体": (0.5, 0.6),
        "大道体": (0.5, 0.6),
        "圣体": (0.7, 0.7),
        "神体": (0.8, 0.8),
        "神王体": (0.8, 1.0),
        "转生": (0.8, 0.8),
        "魔头": (0.8, 0.8),
        "魔女": (0.8, 0.8),
        "魔法少女": (0.8, 0.8),
        "魔卡少女": (0.8, 0.8),
    }

    GM_KEYWORDS = ("管理员", "GM")

    def __init__(
        self,
        player_service: PlayerService,
        state_service: StateService,
    ):
        self.player_service = player_service
        self.state_service = state_service

    async def get_lifespan(self, user_id: str) -> int | None:
        """查询玩家当前寿元，未创建角色返回 None。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return None
        return int(player.get("shouyuan", 0))

    async def reduce_lifespan_task(self) -> LifespanReduceResult:
        """定时任务：按默认任务规则减少所有玩家寿元。"""
        return await self._reduce_all(
            base_amount=self.DEFAULT_TASK_BASE,
            low_level_amount=self.DEFAULT_TASK_LOW_LEVEL_AMOUNT,
            high_level_ratio=self.DEFAULT_TASK_HIGH_LEVEL_RATIO,
            low_level_threshold=self.DEFAULT_TASK_LOW_LEVEL_THRESHOLD,
            high_level_threshold=self.DEFAULT_TASK_HIGH_LEVEL_THRESHOLD,
            mode="task",
        )

    async def reduce_lifespan_manual(self, amount: int) -> LifespanReduceResult:
        """手动执行：按默认手动规则减少所有玩家寿元。"""
        return await self._reduce_all(
            base_amount=amount,
            low_level_amount=self.DEFAULT_MANUAL_LOW_LEVEL_AMOUNT,
            high_level_ratio=self.DEFAULT_MANUAL_HIGH_LEVEL_RATIO,
            low_level_threshold=self.DEFAULT_MANUAL_LOW_LEVEL_THRESHOLD,
            high_level_threshold=self.DEFAULT_MANUAL_HIGH_LEVEL_THRESHOLD,
            mode="manual",
        )

    async def _reduce_all(
        self,
        base_amount: int,
        low_level_amount: int,
        high_level_ratio: float,
        low_level_threshold: int,
        high_level_threshold: int,
        mode: str,
    ) -> LifespanReduceResult:
        """遍历所有玩家并扣减寿元。"""
        result = LifespanReduceResult(base_amount=base_amount)
        start_time = time.time()

        players_dir = self.player_service.players_dir
        if not players_dir.exists():
            result.duration_seconds = time.time() - start_time
            return result

        for file_path in players_dir.glob("*.json"):
            user_id = file_path.stem
            try:
                player = await self.player_service.load(user_id)
                if player is None:
                    continue

                if self._is_gm(player):
                    result.skipped_gm += 1
                    continue

                if await self._is_sealed(user_id):
                    result.skipped_sealed += 1
                    continue

                level_id = int(player.get("level_id", 1))
                if level_id > high_level_threshold:
                    result.high_level_count += 1

                linggen = player.get("linggen") or {}
                body_type = linggen.get("type", "")
                if body_type in self.SPECIAL_BODY_RATIOS:
                    result.special_body_count += 1

                reduction = self._calculate_reduction(
                    player=player,
                    base_amount=base_amount,
                    low_level_amount=low_level_amount,
                    high_level_ratio=high_level_ratio,
                    low_level_threshold=low_level_threshold,
                    high_level_threshold=high_level_threshold,
                    mode=mode,
                )

                shouyuan = int(player.get("shouyuan", 0))
                player["shouyuan"] = max(0, shouyuan - reduction)
                await self.player_service.save(user_id, player)

                result.processed += 1
            except Exception:
                pass

        result.duration_seconds = time.time() - start_time
        return result

    def _is_gm(self, player: dict[str, Any]) -> bool:
        """判断是否为管理员/GM 玩家。"""
        name = player.get("name", "")
        return any(keyword in name for keyword in self.GM_KEYWORDS)

    async def _is_sealed(self, user_id: str) -> bool:
        """判断玩家是否处于神源封印状态。"""
        action = await self.state_service.get(f"xiuxian:player:{user_id}:action")
        if isinstance(action, dict):
            return action.get("action") == "神源封印"
        return False

    def _calculate_reduction(
        self,
        player: dict[str, Any],
        base_amount: int,
        low_level_amount: int,
        high_level_ratio: float,
        low_level_threshold: int,
        high_level_threshold: int,
        mode: str,
    ) -> int:
        """根据境界与特殊体质计算本次寿元流逝量。"""
        level_id = int(player.get("level_id", 1))

        if level_id <= low_level_threshold:
            reduction = low_level_amount
        elif level_id > high_level_threshold:
            reduction = int(base_amount * high_level_ratio)
        else:
            reduction = base_amount

        linggen = player.get("linggen") or {}
        body_type = linggen.get("type", "")

        task_ratio, manual_ratio = self.SPECIAL_BODY_RATIOS.get(
            body_type, (1.0, 1.0)
        )
        ratio = task_ratio if mode == "task" else manual_ratio
        reduction = int(reduction * ratio)

        return max(0, reduction)
