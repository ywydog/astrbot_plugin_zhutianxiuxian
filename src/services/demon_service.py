from dataclasses import dataclass, field
from typing import Any

from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class DemonUpgradeResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""
    need_choice: bool = False


@dataclass
class DemonRealmResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    action: str = "魔界"
    minutes: int = 60


@dataclass
class DemonSacrificeResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""
    rewards: dict[str, int] = field(default_factory=dict)


@dataclass
class DemonCultivateResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""
    mo_dao_gained: int = 0
    exp_gained: int = 0


class DemonService:
    """魔头系统服务：供奉魔石、堕入魔界、献祭魔石、修炼魔功。"""

    DEMON_ROOTS: list[dict[str, Any]] = [
        {"id": 100991, "name": "一重魔功", "eff": 0.36, "法球倍率": 0.23, "cost": 10},
        {"id": 100992, "name": "二重魔功", "eff": 0.42, "法球倍率": 0.27, "cost": 20, "rate": 0.9},
        {"id": 100993, "name": "三重魔功", "eff": 0.48, "法球倍率": 0.31, "cost": 30, "rate": 0.7},
        {"id": 100994, "name": "四重魔功", "eff": 0.54, "法球倍率": 0.36, "cost": 30, "rate": 0.6},
        {"id": 100995, "name": "五重魔功", "eff": 0.6, "法球倍率": 0.4, "cost": 40, "rate": 0.5},
        {"id": 100996, "name": "六重魔功", "eff": 0.66, "法球倍率": 0.43, "cost": 40, "rate": 0.4},
        {"id": 100997, "name": "七重魔功", "eff": 0.72, "法球倍率": 0.47, "cost": 50, "rate": 0.3},
        {"id": 100998, "name": "八重魔功", "eff": 0.78, "法球倍率": 0.5, "cost": 50, "rate": 0.25},
        {"id": 100999, "name": "九重魔功", "eff": 1.2, "法球倍率": 1.2, "cost": 50, "rate": 0.2},
    ]

    DEFAULT_SACRIFICE_REWARDS: list[dict[str, str]] = [
        {"name": "魔气精华", "class": "材料"},
        {"name": "血魂珠", "class": "材料"},
        {"name": "阴煞石", "class": "材料"},
        {"name": "噬魂草", "class": "草药"},
        {"name": "幽冥铁", "class": "材料"},
    ]

    def __init__(
        self,
        player_service: PlayerService,
        inventory_service: InventoryService,
        state_service: StateService,
        random_provider=None,
    ):
        self.player_service = player_service
        self.inventory_service = inventory_service
        self.state_service = state_service
        self.random_provider = random_provider or __import__("random").random

    def _pending_key(self, user_id: str) -> str:
        return f"xiuxian:player:{user_id}:demon_choice"

    def _last_practice_key(self, user_id: str) -> str:
        return f"xiuxian:player:{user_id}:lastPracticeTime"

    def _is_demon(self, player: dict[str, Any]) -> bool:
        linggen = player.get("linggen", {})
        return linggen.get("type") in ("魔头", "天魔")

    def _is_shenghui(self, player: dict[str, Any]) -> bool:
        return player.get("linggen", {}).get("type") == "神慧者"

    # ---------- 供奉魔石 / 魔根升级 ----------

    async def upgrade_demon_root(self, user_id: str) -> DemonUpgradeResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return DemonUpgradeResult(player_not_found=True)

        if player.get("魔道值", 0) < 1000 and not self._is_demon(player):
            return DemonUpgradeResult(reason="你不是魔头")

        count = await self.inventory_service.get_count(user_id, "道具", "魔石")
        if count <= 0:
            return DemonUpgradeResult(reason="你没有魔石")

        linggen = player.get("linggen", {})
        name = linggen.get("name", "")

        # 非魔头灵根需要确认转生
        if not self._is_demon(player):
            await self.state_service.set(self._pending_key(user_id), {"step": "convert"})
            return DemonUpgradeResult(
                need_choice=True,
                message='一旦转为魔根，将会舍弃当前灵根。回复:【放弃魔根】或者【转世魔根】进行选择',
            )

        current_index = next(
            (i for i, r in enumerate(self.DEMON_ROOTS) if r["name"] == name), -1
        )
        if current_index == -1:
            # 默认按一重魔功处理
            current_index = 0
            linggen = self.DEMON_ROOTS[0].copy()

        if current_index >= len(self.DEMON_ROOTS) - 1:
            return DemonUpgradeResult(reason="魔功已达最高境界")

        next_root = self.DEMON_ROOTS[current_index + 1]
        if count < next_root["cost"]:
            return DemonUpgradeResult(
                reason=f'魔石不足{next_root["cost"]}个，当前魔石数量{count}个'
            )

        await self.inventory_service.remove_item(
            user_id, "道具", "魔石", next_root["cost"]
        )
        if self.random_provider() < next_root.get("rate", 1.0):
            player["linggen"] = {
                "id": next_root["id"],
                "name": next_root["name"],
                "type": "魔头",
                "eff": next_root["eff"],
                "法球倍率": next_root["法球倍率"],
                "攻击": 0,
                "防御": 0,
                "生命": 0,
                "生命本源": 0,
            }
            player["cultivation_efficiency"] = next_root["eff"]
            await self.player_service.save(user_id, player)
            return DemonUpgradeResult(
                success=True,
                message=f'恭喜你，灵根突破成功，当前灵根{next_root["name"]}！',
            )

        return DemonUpgradeResult(reason="灵根突破失败")

    async def handle_convert_choice(
        self, user_id: str, choice: str
    ) -> DemonUpgradeResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return DemonUpgradeResult(player_not_found=True)

        pending = await self.state_service.get(self._pending_key(user_id), None)
        if pending is None or pending.get("step") != "convert":
            return DemonUpgradeResult(reason="选择无效")

        if choice == "放弃魔根":
            await self.state_service.delete(self._pending_key(user_id))
            return DemonUpgradeResult(message="重拾道心，继续修行")

        if choice == "转世魔根":
            count = await self.inventory_service.get_count(user_id, "道具", "魔石")
            if count < 10:
                return DemonUpgradeResult(reason="你魔石不足10个")
            await self.inventory_service.remove_item(user_id, "道具", "魔石", 10)
            first = self.DEMON_ROOTS[0]
            player["linggen"] = {
                "id": first["id"],
                "name": first["name"],
                "type": "魔头",
                "eff": first["eff"],
                "法球倍率": first["法球倍率"],
                "攻击": 0,
                "防御": 0,
                "生命": 0,
                "生命本源": 0,
            }
            player["cultivation_efficiency"] = first["eff"]
            await self.player_service.save(user_id, player)
            await self.state_service.delete(self._pending_key(user_id))
            return DemonUpgradeResult(
                success=True, message="恭喜你，转世魔头成功！"
            )

        return DemonUpgradeResult(reason="回复:【放弃魔根】或者【转世魔根】进行选择")

    # ---------- 堕入魔界 ----------

    async def enter_demon_realm(self, user_id: str) -> DemonRealmResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return DemonRealmResult(player_not_found=True)

        if player.get("魔道值", 0) < 100 and not self._is_demon(player):
            return DemonRealmResult(reason="你并非真正的魔")

        if player.get("exp", 0) < 4000000:
            return DemonRealmResult(reason="修为不足")

        player["魔道值"] = player.get("魔道值", 0) - 100
        player["exp"] = player.get("exp", 0) - 4000000
        await self.player_service.save(user_id, player)

        return DemonRealmResult(success=True, action="魔界", minutes=60)

    # ---------- 献祭魔石 ----------

    async def sacrifice_spirit_stones(
        self, user_id: str, times: int = 1
    ) -> DemonSacrificeResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return DemonSacrificeResult(player_not_found=True)

        if times <= 0:
            return DemonSacrificeResult(reason="献祭次数必须大于0")

        is_shenghui = self._is_shenghui(player)
        if not is_shenghui and player.get("魔道值", 0) < 100 and not self._is_demon(player):
            return DemonSacrificeResult(reason="你并非真正的魔")

        cost_per_time = 1 if is_shenghui else 8
        total_cost = times * cost_per_time
        count = await self.inventory_service.get_count(user_id, "道具", "魔石")
        if count < total_cost:
            return DemonSacrificeResult(
                reason=f"魔石不足，需要{total_cost}个，当前只有{count}个"
            )

        await self.inventory_service.remove_item(user_id, "道具", "魔石", total_cost)

        rewards: dict[str, int] = {}
        for _ in range(times):
            item = self.DEFAULT_SACRIFICE_REWARDS[
                int(self.random_provider() * len(self.DEFAULT_SACRIFICE_REWARDS))
            ]
            name = item["name"]
            rewards[name] = rewards.get(name, 0) + 1
            await self.inventory_service.add_item(user_id, item["class"], name, 1)

        reward_text = ", ".join(f"{name}×{qty}" for name, qty in rewards.items())
        if is_shenghui:
            msg = f"献祭完成！获得：{reward_text}"
        else:
            msg = f"献祭完成！消耗魔石{total_cost}个，获得：{reward_text}"

        return DemonSacrificeResult(success=True, message=msg, rewards=rewards)

    # ---------- 修炼魔功 ----------

    async def cultivate_demon_art(
        self, user_id: str, now_ms: int | None = None
    ) -> DemonCultivateResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return DemonCultivateResult(player_not_found=True)

        if player.get("魔道值", 0) < 100 and not self._is_demon(player):
            return DemonCultivateResult(reason="你并非真正的魔")

        import time
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        last_raw = await self.state_service.get(self._last_practice_key(user_id), None)
        if last_raw is not None:
            try:
                last_ms = int(last_raw)
                if now_ms - last_ms < 86400000:
                    return DemonCultivateResult(reason="你今天已经修炼过魔功了。")
            except (TypeError, ValueError):
                pass

        moqi = int(self.random_provider() * (800 - 150 + 1)) + 150
        exp = 150000
        player["魔道值"] = player.get("魔道值", 0) + moqi
        player["exp"] = player.get("exp", 0) + exp

        has_wanhunfan = await self.inventory_service.has_item(
            user_id, "道具", "万魂幡", 1
        )
        extra_msg = ""
        if has_wanhunfan:
            moqi_extra = int(self.random_provider() * (3500 - 1200 + 1)) + 1200
            exp_extra = 1500000 * player.get("level_id", 1)
            player["魔道值"] = player.get("魔道值", 0) + moqi_extra
            player["exp"] = player.get("exp", 0) + exp_extra
            moqi += moqi_extra
            exp += exp_extra
            extra_msg = "万魂幡炼化魂魄，魔气滔天。"

        await self.player_service.save(user_id, player)
        await self.state_service.set(self._last_practice_key(user_id), now_ms)

        return DemonCultivateResult(
            success=True,
            message=f"修炼魔功成功。{extra_msg}",
            mo_dao_gained=moqi,
            exp_gained=exp,
        )
