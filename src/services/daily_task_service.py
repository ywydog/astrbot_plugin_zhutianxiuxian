from dataclasses import dataclass, field
from typing import Any

from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class DailyTask:
    level: int = 1
    exp: int = 0
    renwu: int = 0  # 0=未接取, 1=已完成未领奖, 2=已领奖
    wancheng1: int = 0  # 0=未接取, 1=进行中, 2=已完成
    jilu1: int = 0
    wancheng2: int = 0
    jilu2: int = 0
    wancheng3: int = 0
    jilu3: int = 0


@dataclass
class TaskInfoResult:
    player_not_found: bool = False
    task: DailyTask = field(default_factory=DailyTask)
    player_level_id: int = 1
    physique_id: int = 1
    lingshi_record: int = 0


@dataclass
class AcceptResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    first_time: bool = False


@dataclass
class SubmitResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""
    leveled_up: bool = False


@dataclass
class RewardResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""
    leveled_up: bool = False


class DailyTaskService:
    """每日任务服务：接取、提交、领取奖励。"""

    def __init__(
        self,
        player_service: PlayerService,
        inventory_service: InventoryService,
        state_service: StateService,
    ):
        self.player_service = player_service
        self.inventory_service = inventory_service
        self.state_service = state_service

    def _record_key(self, user_id: str) -> str:
        return f"xiuxian:player:{user_id}:renwu_lingshi_jilu"

    def _last_accept_key(self, user_id: str) -> str:
        return f"xiuxian:player:{user_id}:last_renwu_time"

    def _task_from_dict(self, data: dict[str, Any]) -> DailyTask:
        return DailyTask(
            level=data.get("等级", 1),
            exp=data.get("经验", 0),
            renwu=data.get("renwu", 0),
            wancheng1=data.get("wancheng1", 0),
            jilu1=data.get("jilu1", 0),
            wancheng2=data.get("wancheng2", 0),
            jilu2=data.get("jilu2", 0),
            wancheng3=data.get("wancheng3", 0),
            jilu3=data.get("jilu3", 0),
        )

    def _task_to_dict(self, task: DailyTask) -> dict[str, Any]:
        return {
            "等级": task.level,
            "经验": task.exp,
            "renwu": task.renwu,
            "wancheng1": task.wancheng1,
            "jilu1": task.jilu1,
            "wancheng2": task.wancheng2,
            "jilu2": task.jilu2,
            "wancheng3": task.wancheng3,
            "jilu3": task.jilu3,
            "jiequ": [],
        }

    def _get_task(self, player: dict[str, Any]) -> DailyTask:
        return self._task_from_dict(player.get("daily_task", {}))

    def _set_task(self, player: dict[str, Any], task: DailyTask) -> None:
        player["daily_task"] = self._task_to_dict(task)

    def _today(self, now_ms: int) -> tuple[int, int, int]:
        import datetime
        dt = datetime.datetime.fromtimestamp(now_ms // 1000)
        return (dt.year, dt.month, dt.day)

    # ---------- 查看任务 ----------

    async def get_info(self, user_id: str) -> TaskInfoResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return TaskInfoResult(player_not_found=True)

        record = await self.state_service.get(self._record_key(user_id), 0)
        return TaskInfoResult(
            task=self._get_task(player),
            player_level_id=player.get("level_id", 1),
            physique_id=player.get("Physique_id", 1),
            lingshi_record=record,
        )

    # ---------- 接取任务 ----------

    async def accept(self, user_id: str, now_ms: int | None = None) -> AcceptResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return AcceptResult(player_not_found=True)

        import time
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        today = self._today(now_ms)
        last_raw = await self.state_service.get(self._last_accept_key(user_id), None)
        if last_raw is not None:
            try:
                last_ms = int(last_raw)
                if self._today(last_ms) == today:
                    return AcceptResult(reason="今日已经接取过任务了")
            except (TypeError, ValueError):
                pass

        task = self._get_task(player)
        # 第一次接取需要初始化存档
        if task.level == 1 and task.exp == 0 and task.renwu == 0 and task.wancheng1 == 0 and task.wancheng2 == 0 and task.wancheng3 == 0:
            if task.wancheng1 == 0 and task.wancheng2 == 0 and task.wancheng3 == 0 and task.renwu == 0:
                # 如果从来没接过，先建档案
                pass

        task.wancheng1 = 1
        task.wancheng2 = 1
        task.wancheng3 = 1
        task.renwu = 0
        task.jilu1 = 0
        task.jilu2 = 0
        task.jilu3 = 0
        self._set_task(player, task)

        await self.state_service.set(self._last_accept_key(user_id), now_ms)
        await self.state_service.set(
            self._record_key(user_id), player.get("spirit_stones", 0)
        )
        await self.player_service.save(user_id, player)

        return AcceptResult(success=True)

    # ---------- 提交任务 ----------

    async def submit(self, user_id: str) -> SubmitResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return SubmitResult(player_not_found=True)

        task = self._get_task(player)
        if task.wancheng1 == 0 and task.wancheng2 == 0 and task.wancheng3 == 0:
            return SubmitResult(reason="请先#接取每日任务！")

        if task.wancheng1 == 2 and task.wancheng2 == 2 and task.wancheng3 == 2:
            return SubmitResult(reason="任务已全部完成，请领取奖励")

        # 刷新灵石记录
        record = await self.state_service.get(self._record_key(user_id), 0)
        lingshi = player.get("spirit_stones", 0)
        if lingshi != record and (task.wancheng1 == 1 or task.wancheng2 == 1):
            if lingshi < record:
                task.jilu1 += record - lingshi
            elif lingshi > record:
                task.jilu2 += lingshi - record
            await self.state_service.set(self._record_key(user_id), lingshi)

        level = task.level
        level_id = player.get("level_id", 1)
        physique_id = player.get("Physique_id", 1)

        need1 = (level * 5 + level_id + physique_id) * 20000
        need2 = (level * 5 + level_id + physique_id) * 20000
        need3 = level + 1

        reward = (level * (level_id + physique_id)) * 3000
        exp = ((level * 5) + level_id + physique_id) * 8

        message_parts = []

        if task.jilu1 > need1 - 1 and task.wancheng1 == 1:
            task.wancheng1 = 2
            task.jilu1 = 0
            player["exp"] = player.get("exp", 0) + reward
            player["blood_qi"] = player.get("blood_qi", 0) + reward
            player["spirit_stones"] = player.get("spirit_stones", 0) + reward
            task.exp += exp
            message_parts.append(
                f"你完成了任务1，获得了：\n1.修为*{reward}\n2.血气*{reward}\n3.灵石*{reward}\n4.任务经验*{exp}"
            )

        if task.jilu2 > need2 - 1 and task.wancheng2 == 1:
            task.wancheng2 = 2
            task.jilu2 = 0
            player["exp"] = player.get("exp", 0) + reward
            player["blood_qi"] = player.get("blood_qi", 0) + reward
            player["spirit_stones"] = player.get("spirit_stones", 0) + reward
            task.exp += exp
            message_parts.append(
                f"你完成了任务2，获得了：\n1.修为*{reward}\n2.血气*{reward}\n3.灵石*{reward}\n4.任务经验*{exp}"
            )

        if task.jilu3 > need3 - 1 and task.wancheng3 == 1:
            task.wancheng3 = 2
            task.jilu3 = 0
            player["exp"] = player.get("exp", 0) + reward
            player["blood_qi"] = player.get("blood_qi", 0) + reward
            player["spirit_stones"] = player.get("spirit_stones", 0) + reward
            task.exp += exp
            message_parts.append(
                f"你完成了任务3，获得了：\n1.修为*{reward}\n2.血气*{reward}\n3.灵石*{reward}\n4.任务经验*{exp}"
            )

        leveled_up = False
        if message_parts:
            shengji = (level * 2200 + 1000) * 10 + 2333
            if task.exp > shengji - 1:
                task.level += 1
                task.exp -= shengji
                leveled_up = True

        if task.wancheng1 == 2 and task.wancheng2 == 2 and task.wancheng3 == 2:
            task.renwu = 1
            message_parts.append("你已完成全部每日任务，可以领取奖励了！")

        self._set_task(player, task)
        await self.player_service.save(user_id, player)

        if not message_parts:
            return SubmitResult(reason="你还有任务没完成哦~")

        return SubmitResult(
            success=True,
            message="\n\n".join(message_parts),
            leveled_up=leveled_up,
        )

    # ---------- 领取奖励 ----------

    async def claim_reward(self, user_id: str) -> RewardResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return RewardResult(player_not_found=True)

        task = self._get_task(player)
        if not (task.wancheng1 == 2 and task.wancheng2 == 2 and task.wancheng3 == 2 and task.renwu == 1):
            if task.renwu == 2:
                return RewardResult(reason="你已经领取了每日任务奖励了")
            return RewardResult(reason="你还有任务没完成哦~")

        level = task.level
        level_id = player.get("level_id", 1)
        physique_id = player.get("Physique_id", 1)

        reward = (level * (level_id + physique_id)) * 8000
        exp = ((level * 5) + level_id + physique_id) * 12
        keys = level

        task.renwu = 2
        task.exp += exp
        player["exp"] = player.get("exp", 0) + reward
        player["blood_qi"] = player.get("blood_qi", 0) + reward
        player["spirit_stones"] = player.get("spirit_stones", 0) + reward
        player["lottery_count"] = player.get("lottery_count", 0) + 3
        await self.inventory_service.add_item(user_id, "道具", "秘境之匙", keys)

        leveled_up = False
        shengji = (level * 2200 + 1000) * 10 + 2333
        if task.exp > shengji - 1:
            task.level += 1
            task.exp -= shengji
            leveled_up = True

        self._set_task(player, task)
        await self.player_service.save(user_id, player)

        return RewardResult(
            success=True,
            message=(
                f"你领取了每日任务奖励，获得了：\n"
                f"1.修为*{reward}\n"
                f"2.血气*{reward}\n"
                f"3.灵石*{reward}\n"
                f"4.任务经验*{exp}\n"
                f"5.秘境之匙*{keys}个\n"
                f"6.每日抽奖次数*3次"
            ),
            leveled_up=leveled_up,
        )
