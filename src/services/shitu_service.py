import random
import time
from dataclasses import dataclass, field
from typing import Any

from src.data.shitu_data import ShituData, ShituShopData
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class ShituActionResult:
    success: bool = False
    player_not_found: bool = False
    target_not_found: bool = False
    reason: str = ""
    message: str = ""


@dataclass
class ShituListResult:
    masters: list[dict[str, str]] = field(default_factory=list)


@dataclass
class ShituShopResult:
    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ShituExchangeResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""


@dataclass
class ShituTrialResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""
    remaining_hp: int = 0


class ShituService:
    """师徒系统服务：收徒、拜师、解除关系、师徒试炼、积分兑换。"""

    CD_KEY = "xiuxian:player:{user_id}:shitu_cd"
    ACTION_COOLDOWN_MS = 60 * 60 * 1000  # 开启收徒 / 拜师冷却 1 小时
    DISSOLVE_COOLDOWN_MS = 24 * 60 * 60 * 1000  # 解除关系冷却 24 小时
    BOSS_MAX_HP = 100_000_000

    def __init__(
        self,
        player_service: PlayerService,
        state_service: StateService,
        inventory_service: InventoryService,
        shitu_data: ShituData,
        shop_data: ShituShopData,
        random_provider=None,
    ):
        self.player_service = player_service
        self.state_service = state_service
        self.inventory_service = inventory_service
        self.shitu_data = shitu_data
        self.shop_data = shop_data
        self.random_provider = random_provider or __import__("random").random

    def _cd_key(self, user_id: str) -> str:
        return self.CD_KEY.format(user_id=user_id)

    def _remaining(self, now_ms: int, last_time: int, timeout_ms: int) -> str:
        remaining_ms = last_time + timeout_ms - now_ms
        if remaining_ms <= 0:
            return ""
        minutes = remaining_ms // 60000
        seconds = (remaining_ms % 60000) // 1000
        return f"还需要 {minutes} 分 {seconds} 秒"

    def _is_qualified_master(self, player: dict[str, Any]) -> bool:
        """是否满足收徒资格：轮回九世或拥有九重魔功。"""
        if player.get("lunhui", 0) >= 9:
            return True
        linggen = player.get("linggen", {})
        if linggen.get("id") == 100999:
            return True
        return False

    # ---------- 开启 / 关闭收徒 ----------

    async def open_recruitment(
        self, user_id: str, now_ms: int | None = None
    ) -> ShituActionResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ShituActionResult(player_not_found=True)

        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        last_raw = await self.state_service.get(self._cd_key(user_id), None)
        if last_raw is not None:
            try:
                last_time = int(last_raw)
                if now_ms < last_time + self.ACTION_COOLDOWN_MS:
                    return ShituActionResult(
                        reason=f"距离再次开启收徒\n{self._remaining(now_ms, last_time, self.ACTION_COOLDOWN_MS)}"
                    )
            except (TypeError, ValueError):
                pass

        if not self._is_qualified_master(player):
            return ShituActionResult(reason="没有轮回过九世的人不能收徒!")

        record = self.shitu_data.ensure_master_record(user_id)
        if record.get("apprentice"):
            return ShituActionResult(reason="需要等这个徒弟出师后才能再次收徒!")

        if record.get("recruiting") == 1:
            return ShituActionResult(reason="你已经开启收徒了")

        record["recruiting"] = 1
        self.shitu_data.save(self.shitu_data.records)
        await self.state_service.set(self._cd_key(user_id), now_ms)
        return ShituActionResult(success=True, message="成功开启收徒")

    async def close_recruitment(self, user_id: str) -> ShituActionResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ShituActionResult(player_not_found=True)

        record = self.shitu_data.ensure_master_record(user_id)
        if record.get("recruiting") == 1:
            record["recruiting"] = 0
            self.shitu_data.save(self.shitu_data.records)
            return ShituActionResult(success=True, message="成功关闭收徒")

        return ShituActionResult(reason="你就没开启收徒")

    # ---------- 拜师 ----------

    async def apprentice(
        self,
        user_id: str,
        master_id: str,
        now_ms: int | None = None,
    ) -> ShituActionResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ShituActionResult(player_not_found=True)

        if not await self.player_service.exists(master_id):
            return ShituActionResult(target_not_found=True, reason="对方尚未踏入仙途")

        if user_id == master_id:
            return ShituActionResult(reason="自己拜自己是吧")

        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        last_raw = await self.state_service.get(self._cd_key(user_id), None)
        if last_raw is not None:
            try:
                last_time = int(last_raw)
                if now_ms < last_time + self.ACTION_COOLDOWN_MS:
                    return ShituActionResult(
                        reason=f"距离再次拜师\n{self._remaining(now_ms, last_time, self.ACTION_COOLDOWN_MS)}"
                    )
            except (TypeError, ValueError):
                pass

        if self.shitu_data.get_by_apprentice(user_id):
            return ShituActionResult(reason="你都有师傅了还拜什么师？")

        if player.get("level_id", 1) > 50:
            return ShituActionResult(reason="你这修为都能当师傅了，拜师？")

        # 检查是否已出师过
        for record in self.shitu_data.records:
            if user_id in record.get("graduated_apprentices", []):
                return ShituActionResult(reason="你曾拜入过师门且已出师")

        master_record = self.shitu_data.get_by_master(master_id)
        if master_record is None or master_record.get("recruiting") != 1:
            return ShituActionResult(reason="他并没有开启收徒，换个人吧。")

        if master_record.get("apprentice"):
            return ShituActionResult(reason="他已经有徒弟了，换个人吧。")

        master_record["apprentice"] = user_id
        master_record["recruiting"] = 0
        self.shitu_data.save(self.shitu_data.records)
        await self.state_service.set(self._cd_key(user_id), now_ms)
        return ShituActionResult(success=True, message="成功拜师")

    # ---------- 解除关系 ----------

    async def dissolve(
        self, user_id: str, now_ms: int | None = None
    ) -> ShituActionResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ShituActionResult(player_not_found=True)

        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        last_raw = await self.state_service.get(self._cd_key(user_id), None)
        if last_raw is not None:
            try:
                last_time = int(last_raw)
                if now_ms < last_time + self.DISSOLVE_COOLDOWN_MS:
                    return ShituActionResult(
                        reason=f"距离再次解除关系\n{self._remaining(now_ms, last_time, self.DISSOLVE_COOLDOWN_MS)}"
                    )
            except (TypeError, ValueError):
                pass

        apprentice_record = self.shitu_data.get_by_apprentice(user_id)
        if apprentice_record:
            # 徒弟解除
            self._reset_record(apprentice_record)
            apprentice_record["recruiting"] = 1
            self.shitu_data.save(self.shitu_data.records)
            await self.state_service.set(self._cd_key(user_id), now_ms)
            return ShituActionResult(
                success=True, message="解除成功，24小时后才能再次拜师"
            )

        master_record = self.shitu_data.get_by_master(user_id)
        if master_record:
            if not master_record.get("apprentice"):
                return ShituActionResult(reason="你还没收过徒弟")

            # 师傅解除
            task_stage = master_record.get("task_stage", 0)
            self._reset_record(master_record)
            if task_stage > 3:
                master_record["recruiting"] = 0
                extra = "你解除了任务阶段大于3的徒弟，24小时后才能再次收徒"
            else:
                master_record["recruiting"] = 1
                extra = ""
            self.shitu_data.save(self.shitu_data.records)
            await self.state_service.set(self._cd_key(user_id), now_ms)
            message = "解除成功，24小时后才能再次拜师"
            if extra:
                message += f"\n{extra}"
            return ShituActionResult(success=True, message=message)

        return ShituActionResult(reason="你有徒弟或者师傅？")

    def _reset_record(self, record: dict[str, Any]) -> None:
        record["apprentice"] = ""
        record["task_stage"] = 0
        record["renwu1"] = 0
        record["renwu2"] = 0
        record["renwu3"] = 0

    # ---------- 查询 ----------

    async def get_master_list(self) -> ShituListResult:
        masters = []
        for record in self.shitu_data.records:
            if record.get("recruiting") != 1:
                continue
            master_id = record.get("master")
            player = await self.player_service.load(master_id)
            if player is None:
                continue
            masters.append(
                {"user_id": master_id, "name": player.get("name", "无名")}
            )

        if len(masters) > 5:
            masters = random.sample(masters, 5)
        return ShituListResult(masters=masters)

    async def get_my_apprentice(self, user_id: str) -> dict[str, Any] | None:
        record = self.shitu_data.get_by_master(user_id)
        if record is None or not record.get("apprentice"):
            return None
        apprentice = await self.player_service.load(record["apprentice"])
        if apprentice is None:
            return None
        return {
            "apprentice_id": record["apprentice"],
            "apprentice_name": apprentice.get("name", "无名"),
            "task_stage": record.get("task_stage", 0),
            "boss_hp": record.get("boss_hp", self.BOSS_MAX_HP),
        }

    async def get_my_master(self, user_id: str) -> dict[str, Any] | None:
        record = self.shitu_data.get_by_apprentice(user_id)
        if record is None:
            return None
        master = await self.player_service.load(record["master"])
        if master is None:
            return None
        return {
            "master_id": record["master"],
            "master_name": master.get("name", "无名"),
            "task_stage": record.get("task_stage", 0),
            "boss_hp": record.get("boss_hp", self.BOSS_MAX_HP),
        }

    # ---------- 任务 / 试炼 ----------

    async def submit_task(self, user_id: str) -> ShituActionResult:
        """徒弟提交任务，推进任务阶段。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return ShituActionResult(player_not_found=True)

        record = self.shitu_data.get_by_apprentice(user_id)
        if record is None:
            return ShituActionResult(reason="只能由徒弟提交任务")

        stage = record.get("task_stage", 0)
        if stage >= 5:
            return ShituActionResult(reason="任务已全部完成，去挑战师徒试炼吧")

        record["task_stage"] = stage + 1
        self.shitu_data.save(self.shitu_data.records)
        return ShituActionResult(
            success=True,
            message=f"任务提交成功，当前任务阶段：{record['task_stage']}/5",
        )

    async def trial_boss(self, user_id: str) -> ShituTrialResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ShituTrialResult(player_not_found=True)

        record = self.shitu_data.get_by_master(user_id) or self.shitu_data.get_by_apprentice(user_id)
        if record is None:
            return ShituTrialResult(reason="你还没拜师&收徒过！")

        if record.get("task_stage", 0) != 5:
            return ShituTrialResult(reason="你的任务还没到此阶段")

        boss_hp = record.get("boss_hp", self.BOSS_MAX_HP)
        if boss_hp <= 0:
            return ShituTrialResult(reason="你已经通过了师徒试炼")

        if player.get("current_hp", 0) < 10000:
            return ShituTrialResult(reason="你都伤成这样了,先回回血再打吧")

        attack = player.get("attack", 0)
        total_damage = 0
        is_master = record.get("master") == user_id

        for _round in range(1, 7):
            if is_master:
                damage = max(0, attack - int(self.random_provider() * 50_000_000))
            else:
                multiplier = int(self.random_provider() * 5)
                damage = attack * multiplier
            total_damage += damage
            boss_hp -= damage
            if boss_hp <= 0:
                break

        record["boss_hp"] = max(0, boss_hp)

        if boss_hp <= 0:
            # 徒弟出师
            apprentice_id = record.get("apprentice")
            if apprentice_id:
                record.setdefault("graduated_apprentices", []).append(apprentice_id)
            self._reset_record(record)
            self.shitu_data.save(self.shitu_data.records)
            return ShituTrialResult(
                success=True,
                message="恭喜你通过了师徒试炼！",
                remaining_hp=0,
            )

        player["current_hp"] = 0
        await self.player_service.save(user_id, player)
        self.shitu_data.save(self.shitu_data.records)
        return ShituTrialResult(
            message=f"这次并没有一口气通过试炼呢，再接再厉！\n道祖虚影剩余血量:{record['boss_hp']}",
            remaining_hp=record["boss_hp"],
        )

    # ---------- 积分商城 ----------

    async def get_shop_items(self) -> ShituShopResult:
        return ShituShopResult(items=list(self.shop_data.items))

    async def exchange(
        self, user_id: str, item_name: str
    ) -> ShituExchangeResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ShituExchangeResult(player_not_found=True)

        item = self.shop_data.get(item_name)
        if item is None:
            return ShituExchangeResult(
                reason=f"师徒商店还没有这样的东西:{item_name}"
            )

        cost = item.get("积分", 0)
        points = player.get("shitu_points", 0)
        if points < cost:
            return ShituExchangeResult(
                reason=f"积分不足,还需{cost - points}积分兑换{item_name}"
            )

        player["shitu_points"] = points - cost
        await self.player_service.save(user_id, player)
        await self.inventory_service.add_item(
            user_id, item.get("class", "道具"), item_name, 1
        )
        return ShituExchangeResult(
            success=True,
            message=(
                f"兑换成功! 获得[{item_name}],"
                f"剩余[{player['shitu_points']}]积分\n"
                f"可以在【我的纳戒】中查看"
            ),
        )

    # ---------- 数据同步 ----------

    async def sync(self, user_id: str) -> ShituActionResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ShituActionResult(player_not_found=True)

        for record in self.shitu_data.records:
            record.setdefault("apprentice", "")
            record.setdefault("task_stage", 0)
            record.setdefault("renwu1", 0)
            record.setdefault("renwu2", 0)
            record.setdefault("renwu3", 0)
            record.setdefault("boss_hp", self.BOSS_MAX_HP)
            record.setdefault("graduated_apprentices", [])
            record.setdefault("recruiting", 0)

        self.shitu_data.save(self.shitu_data.records)
        return ShituActionResult(success=True, message="同步完成")
