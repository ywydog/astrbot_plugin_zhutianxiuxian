import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from src.data.occupation_data import OccupationData
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class OccupationInfoResult:
    player_not_found: bool = False
    occupation: str = ""
    occupation_level: int = 1
    occupation_exp: int = 0
    secondary: dict[str, Any] | None = None


@dataclass
class ChangeOccupationResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    occupation: str = ""
    secondary_name: str = ""


@dataclass
class OccupationActionResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    action: str = ""
    minutes: int = 0


@dataclass
class OccupationSettlementResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    action: str = ""
    minutes: int = 0
    message: str = ""
    items: list[dict[str, Any]] = field(default_factory=list)
    exp_gained: int = 0


@dataclass
class CraftResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    name: str = ""
    quantity: int = 0
    exp_gained: int = 0
    quality: str = ""


class OccupationService:
    """职业系统服务：转职、副职、职业动作、炼制/制作/打造。"""

    ACTION_CONFIG: dict[str, dict[str, Any]] = {
        "采药": {
            "occupation": "采药师",
            "cycle": 15,
            "min_minutes": 30,
            "max_minutes": 240,
            "error_msg": "您采药，您配吗？",
        },
        "采矿": {
            "occupation": "采矿师",
            "cycle": 30,
            "min_minutes": 30,
            "max_minutes": 240,
            "error_msg": "你挖矿许可证呢？非法挖矿，罚款200灵石",
            "penalty_spirit_stones": -200,
        },
        "狩猎": {
            "occupation": "猎户",
            "cycle": 15,
            "min_minutes": 30,
            "max_minutes": 240,
            "error_msg": "你的狩猎许可证呢？盗猎是吧？罚款2000灵石。",
            "penalty_spirit_stones": -2000,
        },
        "寻源": {
            "occupation": "源师",
            "cycle": 15,
            "min_minutes": 30,
            "max_minutes": 240,
            "error_msg": "您又不是源师，怎么寻找源脉？",
        },
        "寻脉定源": {
            "occupation": "源天师",
            "cycle": 15,
            "min_minutes": 30,
            "max_minutes": 240,
            "error_msg": "您并非源天师，没有拘禁山川龙脉改天换地的能力又怎么定源？",
        },
        "地脉引气": {
            "occupation": "源地师",
            "cycle": 15,
            "min_minutes": 30,
            "max_minutes": 240,
            "error_msg": "您又不是源地师，怎么感知地脉流转，引导山川精气？",
        },
    }

    def __init__(
        self,
        player_service: PlayerService,
        state_service: StateService,
        inventory_service: InventoryService,
        occupation_data: OccupationData,
        random_provider: Callable[[], float] | None = None,
    ):
        self.player_service = player_service
        self.state_service = state_service
        self.inventory_service = inventory_service
        self.occupation_data = occupation_data
        self._random = random_provider or random.random

    # ---------- 基础工具 ----------

    def _state_key(self, user_id: str) -> str:
        return f"xiuxian:player:{user_id}:action"

    def _fuzhi_key(self, user_id: str) -> str:
        return f"xiuxian:player:{user_id}:fuzhi"

    def _get_current_occupation(self, player: dict[str, Any]) -> str:
        occ = player.get("occupation", [])
        if isinstance(occ, list):
            return occ[0] if occ else ""
        return str(occ) if occ else ""

    def _set_current_occupation(self, player: dict[str, Any], name: str) -> None:
        player["occupation"] = name

    async def _get_action(self, user_id: str) -> dict[str, Any] | None:
        return await self.state_service.get(self._state_key(user_id), None)

    async def _set_action(self, user_id: str, action: dict[str, Any] | None) -> None:
        if action is None:
            await self.state_service.delete(self._state_key(user_id))
        else:
            await self.state_service.set(self._state_key(user_id), action)

    def _normalize_minutes(self, minutes: int, cycle: int, min_minutes: int, max_minutes: int) -> int:
        minutes = max(min_minutes, min(minutes, max_minutes))
        return (minutes // cycle) * cycle

    async def _add_occupation_exp(self, user_id: str, amount: int) -> None:
        player = await self.player_service.load(user_id)
        if player is None:
            return
        current_exp = player.get("occupation_exp", 0) + amount
        player["occupation_exp"] = current_exp
        level = player.get("occupation_level", 1)
        while True:
            required = self.occupation_data.get_occupation_exp_required(level)
            if current_exp >= required and level < 60:
                current_exp -= required
                level += 1
            else:
                break
        player["occupation_level"] = level
        player["occupation_exp"] = current_exp
        await self.player_service.save(user_id, player)

    # ---------- 职业信息 ----------

    async def get_info(self, user_id: str) -> OccupationInfoResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return OccupationInfoResult(player_not_found=True)

        secondary = await self.state_service.get(self._fuzhi_key(user_id), None)
        return OccupationInfoResult(
            occupation=self._get_current_occupation(player),
            occupation_level=player.get("occupation_level", 1),
            occupation_exp=player.get("occupation_exp", 0),
            secondary=secondary,
        )

    # ---------- 转职 ----------

    async def change_occupation(self, user_id: str, name: str) -> ChangeOccupationResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ChangeOccupationResult(player_not_found=True)

        target = self.occupation_data.find_occupation(name)
        if target is None:
            return ChangeOccupationResult(reason=f"没有[{name}]这项职业")

        current = self._get_current_occupation(player)
        if current == name:
            return ChangeOccupationResult(reason=f"你已经是[{current}]了，可使用[职业转化凭证]重新转职")

        # 等级限制：采矿师需要练气 17 层，猎户需要练气 25 层
        level_id = player.get("level_id", 1)
        if name == "采矿师" and level_id < 17:
            return ChangeOccupationResult(reason="包工头：就你这小身板还来挖矿？再去修炼几年吧")
        if name == "猎户" and level_id < 25:
            return ChangeOccupationResult(reason="就你这点修为做猎户？怕不是光头强砍不到树来转的？")

        # 检查转职凭证
        cert_name = f"{name}转职凭证"
        has_cert = await self.inventory_service.has_item(user_id, "道具", cert_name, 1)
        if not has_cert:
            return ChangeOccupationResult(reason=f"你没有【{cert_name}】")

        # 保存原职业到副职
        if current:
            await self.state_service.set(
                self._fuzhi_key(user_id),
                {
                    "职业名": current,
                    "职业经验": player.get("occupation_exp", 0),
                    "职业等级": player.get("occupation_level", 1),
                },
            )

        # 扣除凭证
        await self.inventory_service.remove_item(user_id, "道具", cert_name, 1)

        # 设置新职业
        self._set_current_occupation(player, name)
        player["occupation_level"] = 1
        player["occupation_exp"] = 0
        await self.player_service.save(user_id, player)

        secondary = await self.state_service.get(self._fuzhi_key(user_id), None)
        secondary_name = secondary["职业名"] if secondary else ""
        return ChangeOccupationResult(
            success=True,
            occupation=name,
            secondary_name=secondary_name,
        )

    async def change_occupation_from_liehu(self, user_id: str, name: str) -> ChangeOccupationResult:
        """猎户专属转职，无需凭证。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return ChangeOccupationResult(player_not_found=True)

        current = self._get_current_occupation(player)
        if current != "猎户":
            return ChangeOccupationResult(reason="你不是猎户，无法自选职业")

        target = self.occupation_data.find_occupation(name)
        if target is None:
            return ChangeOccupationResult(reason=f"没有[{name}]这项职业")

        self._set_current_occupation(player, name)
        await self.player_service.save(user_id, player)
        return ChangeOccupationResult(success=True, occupation=name)

    async def swap_secondary_occupation(self, user_id: str) -> ChangeOccupationResult:
        """转换副职：当前职业与副职互换。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return ChangeOccupationResult(player_not_found=True)

        secondary = await self.state_service.get(self._fuzhi_key(user_id), None)
        if not secondary:
            return ChangeOccupationResult(reason="您还没有副职哦")

        current = self._get_current_occupation(player)
        current_exp = player.get("occupation_exp", 0)
        current_level = player.get("occupation_level", 1)

        # 当前职业写入副职
        await self.state_service.set(
            self._fuzhi_key(user_id),
            {
                "职业名": current,
                "职业经验": current_exp,
                "职业等级": current_level,
            },
        )

        # 副职写入当前职业
        self._set_current_occupation(player, secondary["职业名"])
        player["occupation_exp"] = secondary["职业经验"]
        player["occupation_level"] = secondary["职业等级"]
        await self.player_service.save(user_id, player)

        return ChangeOccupationResult(
            success=True,
            occupation=secondary["职业名"],
            secondary_name=current,
        )

    # ---------- 职业动作 ----------

    async def start_action(
        self,
        user_id: str,
        action_name: str,
        minutes: int,
        now: float | None = None,
    ) -> OccupationActionResult:
        config = self.ACTION_CONFIG.get(action_name)
        if config is None:
            return OccupationActionResult(reason="未知职业动作")

        player = await self.player_service.load(user_id)
        if player is None:
            return OccupationActionResult(player_not_found=True)

        current = self._get_current_occupation(player)
        if current != config["occupation"]:
            penalty = config.get("penalty_spirit_stones")
            if penalty is not None:
                await self.player_service.add_spirit_stones(user_id, penalty)
            return OccupationActionResult(reason=config["error_msg"])

        action = await self._get_action(user_id)
        if action and action.get("end_time", 0) > (now or time.time()) * 1000:
            return OccupationActionResult(
                reason=f"正在{action.get('action', '修炼')}中",
            )

        minutes = self._normalize_minutes(
            minutes,
            config["cycle"],
            config["min_minutes"],
            config["max_minutes"],
        )
        now_ms = int((now if now is not None else time.time()) * 1000)
        await self._set_action(
            user_id,
            {
                "action": action_name,
                "start_time": now_ms,
                "end_time": now_ms + minutes * 60 * 1000,
                "time": minutes * 60 * 1000,
            },
        )
        return OccupationActionResult(success=True, action=action_name, minutes=minutes)

    async def end_action(
        self,
        user_id: str,
        action_name: str,
        now: float | None = None,
    ) -> OccupationSettlementResult:
        config = self.ACTION_CONFIG.get(action_name)
        if config is None:
            return OccupationSettlementResult(reason="未知职业动作")

        player = await self.player_service.load(user_id)
        if player is None:
            return OccupationSettlementResult(player_not_found=True)

        action = await self._get_action(user_id)
        if not action or action.get("action") != action_name:
            return OccupationSettlementResult(reason=f"你当前没有进行{action_name}")

        now_ms = int((now if now is not None else time.time()) * 1000)
        start_time = action.get("start_time", action.get("end_time", now_ms) - action.get("time", 0))
        elapsed_ms = min(now_ms - start_time, action.get("time", 0))
        elapsed_minutes = int(elapsed_ms / 1000 / 60)

        cycle = config["cycle"]
        settled_minutes = (elapsed_minutes // cycle) * cycle
        if settled_minutes < cycle:
            await self._set_action(user_id, None)
            return OccupationSettlementResult(
                reason=f"{action_name}时间不足 {cycle} 分钟，未获得收益",
            )

        result = await self._settle_action(user_id, action_name, settled_minutes, player)
        await self._set_action(user_id, None)
        return result

    async def _settle_action(
        self,
        user_id: str,
        action_name: str,
        minutes: int,
        player: dict[str, Any],
    ) -> OccupationSettlementResult:
        occ_level = player.get("occupation_level", 1)
        rate = self.occupation_data.get_occupation_rate(occ_level)
        items: list[dict[str, Any]] = []
        exp = 0
        message = ""

        if action_name == "采药":
            exp = minutes * 10
            k = 1.0
            if player.get("level_id", 1) < 22:
                k = 0.5
            if player.get("level_id", 1) >= 36:
                total = (minutes / 480) * (occ_level * 3 + 11)
                herb_probs = [
                    0.17, 0.22, 0.17, 0.17, 0.17, 0.024, 0.024, 0.024, 0.024,
                    0.024, 0.024, 0.024, 0.012, 0.011,
                ]
            else:
                total = (minutes / 480) * (occ_level * 2 + 12) * k
                herb_probs = [0.2, 0.3, 0.2, 0.2, 0.2, 0, 0, 0, 0, 0, 0, 0, 0, 0]
            herb_names = [
                "万年凝血草", "万年何首乌", "万年血精草", "万年甜甜花",
                "万年清心草", "古神藤", "万年太玄果", "炼骨花",
                "魔蕴花", "万年清灵草", "万年天魂菊", "仙蕴花",
                "仙缘草", "太玄仙草",
            ]
            for name, prob in zip(herb_names, herb_probs):
                amount = int(prob * total)
                if amount > 0:
                    await self.inventory_service.add_item(user_id, "草药", name, amount)
                    items.append({"name": name, "quantity": amount})

        elif action_name == "采矿":
            exp = minutes * 10
            base = int((1.8 + self._random() * 0.4) * minutes)
            end_amount = int(4 * (rate + 1) * base)
            end_amount = int(end_amount * player.get("level_id", 1) / 40)
            num = int(((rate / 12) * minutes) / 30)
            A = ["金色石胚", "棕色石胚", "绿色石胚", "红色石胚", "蓝色石胚"]
            B = ["金色妖石", "棕色妖石", "绿色妖石", "红色妖石", "蓝色妖石"]
            xuanze = int(self._random() * len(A))
            await self.inventory_service.add_item(user_id, "材料", "庚金", end_amount)
            await self.inventory_service.add_item(user_id, "材料", "玄土", end_amount)
            await self.inventory_service.add_item(user_id, "材料", A[xuanze], num)
            await self.inventory_service.add_item(user_id, "材料", B[xuanze], int(num / 48))
            items = [
                {"name": "庚金", "quantity": end_amount},
                {"name": "玄土", "quantity": end_amount},
                {"name": A[xuanze], "quantity": num},
                {"name": B[xuanze], "quantity": int(num / 48)},
            ]

        elif action_name == "狩猎":
            exp = minutes * 100
            amount = int((3 + self._random() * 0.5) * minutes * 12)
            amount = int(amount * (occ_level / 60))
            hunt_items = ["野兔", "野鸡", "野猪", "野牛", "野羊"]
            for name in hunt_items:
                await self.inventory_service.add_item(user_id, "食材", name, amount)
                items.append({"name": name, "quantity": amount})

        elif action_name in ("寻源", "寻脉定源", "地脉引气"):
            exp = minutes * 100
            base = int((1.8 + self._random() * 0.4) * minutes)
            rare = int(minutes / 30)
            level_factor = player.get("level_id", 1) / 80 if player.get("level_id", 1) <= 21 else player.get("level_id", 1) / 40

            if action_name == "寻源":
                a1 = int(3 * (rate + 1) * base * level_factor)
                a2 = int(2 * (rate + 0.7) * rare * level_factor)
                a3 = int(1 * (rate + 0.5) * rare * level_factor)
                await self.inventory_service.add_item(user_id, "道具", "下品源石", a1)
                await self.inventory_service.add_item(user_id, "道具", "中品源石", a1)
                await self.inventory_service.add_item(user_id, "道具", "上品源石", a2)
                await self.inventory_service.add_item(user_id, "道具", "神源石", a3)
                await self.inventory_service.add_item(user_id, "丹药", "凡源药", a3)
                items = [
                    {"name": "下品源石", "quantity": a1},
                    {"name": "中品源石", "quantity": a1},
                    {"name": "上品源石", "quantity": a2},
                    {"name": "神源石", "quantity": a3},
                    {"name": "凡源药", "quantity": a3},
                ]
            elif action_name == "寻脉定源":
                a1 = int(3 * (rate + 1) * base * level_factor)
                a2 = int(2 * (rate + 0.7) * rare * level_factor)
                a3 = int(1 * (rate + 0.5) * rare * level_factor)
                await self.inventory_service.add_item(user_id, "道具", "超品源石", a1)
                await self.inventory_service.add_item(user_id, "道具", "上品神源石", a2)
                await self.inventory_service.add_item(user_id, "丹药", "神源液", a2)
                await self.inventory_service.add_item(user_id, "道具", "超品神源石", a3)
                await self.inventory_service.add_item(user_id, "丹药", "神源药", a3)
                if self._random() > 0.85:
                    await self.inventory_service.add_item(user_id, "道具", "龙脉精华", 1)
                    items.append({"name": "龙脉精华", "quantity": 1})
                items = [
                    {"name": "超品源石", "quantity": a1},
                    {"name": "上品神源石", "quantity": a2},
                    {"name": "神源液", "quantity": a2},
                    {"name": "超品神源石", "quantity": a3},
                    {"name": "神源药", "quantity": a3},
                ] + items
            else:  # 地脉引气
                a2 = int(4 * (rate + 0.7) * rare * level_factor)
                a3 = int(1 * (rate + 0.5) * rare * level_factor)
                await self.inventory_service.add_item(user_id, "道具", "上品源石", a2)
                await self.inventory_service.add_item(user_id, "道具", "超品源石", a2)
                await self.inventory_service.add_item(user_id, "道具", "神源石", a2)
                await self.inventory_service.add_item(user_id, "丹药", "地源药", a3)
                items = [
                    {"name": "上品源石", "quantity": a2},
                    {"name": "超品源石", "quantity": a2},
                    {"name": "神源石", "quantity": a2},
                    {"name": "地源药", "quantity": a3},
                ]

        await self._add_occupation_exp(user_id, exp)
        message = f"【{player.get('name', '无名')}】{action_name}归来，获得{exp}点职业经验"
        return OccupationSettlementResult(
            success=True,
            action=action_name,
            minutes=minutes,
            message=message,
            items=items,
            exp_gained=exp,
        )

    # ---------- 炼制 / 制作 / 打造 ----------

    async def craft_danfang(
        self,
        user_id: str,
        name: str,
        quantity: int = 1,
    ) -> CraftResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return CraftResult(player_not_found=True)

        if self._get_current_occupation(player) != "炼丹师":
            return CraftResult(reason="丹是上午炼的，药是中午吃的，人是下午走的")

        recipe = self.occupation_data.find_recipe("danfang", name)
        if recipe is None:
            return CraftResult(reason=f"世界上没有丹药[{name}]的配方")

        level_limit = recipe.get("level_limit", 0)
        if level_limit > player.get("occupation_level", 1):
            return CraftResult(reason=f"{level_limit}级炼丹师才能炼制{name}")

        quantity = max(1, quantity)
        materials = recipe.get("materials", [])
        material_type = "丹药" if name == "天命轮回丹" else "草药"
        for material in materials:
            need = material.get("amount", 1) * quantity
            stock = await self.inventory_service.get_count(user_id, material_type, material["name"])
            if stock < need:
                return CraftResult(
                    reason=f"纳戒中拥有{material['name']}({material_type}){stock}份，炼制需要{need}份"
                )

        for material in materials:
            await self.inventory_service.remove_item(
                user_id,
                material_type,
                material["name"],
                material.get("amount", 1) * quantity,
            )

        # 仙宠炼丹加成（简化）
        pet_double = False
        pet = player.get("仙宠")
        if isinstance(pet, dict) and pet.get("type") == "炼丹" and self._random() < pet.get("加成", 0):
            quantity *= 2
            pet_double = True

        exp = recipe.get("exp", [0, 0])
        total_exp = int(exp[1] * quantity) if isinstance(exp, list) and len(exp) > 1 else int(exp * quantity) if isinstance(exp, (int, float)) else 0

        special = name in ("神心丹", "九阶淬体丹", "九阶玄元丹", "起死回生丹", "天命轮回丹")
        if special:
            quality = ""
            await self.inventory_service.add_item(user_id, "丹药", name, quantity)
        else:
            rand = self._random()
            level = player.get("occupation_level", 1)
            if rand >= 0.1 + (level * 3) / 100:
                quality = "凡品"
                await self.inventory_service.add_item(user_id, "丹药", f"凡品{name}", quantity)
            else:
                quality = "极品" if self._random() >= 0.4 else "仙品"
                await self.inventory_service.add_item(user_id, "丹药", f"{quality}{name}", quantity)

        await self._add_occupation_exp(user_id, total_exp)
        return CraftResult(
            success=True,
            name=name,
            quantity=quantity,
            exp_gained=total_exp,
            quality=quality,
        )

    async def craft_zhizuo(
        self,
        user_id: str,
        name: str,
        quantity: int = 1,
    ) -> CraftResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return CraftResult(player_not_found=True)

        if self._get_current_occupation(player) != "符师":
            return CraftResult(reason="符道玄奥，非符师不可妄为！")

        recipe = self.occupation_data.find_recipe("zhizuo", name)
        if recipe is None:
            return CraftResult(reason=f"符道秘录中无「{name}」记载")

        level_limit = recipe.get("level_limit", 0)
        if level_limit > player.get("occupation_level", 1):
            return CraftResult(reason=f"需达「符师{level_limit}重境」方可制作")

        quantity = max(1, quantity)
        materials = recipe.get("materials", [])
        for material in materials:
            need = material.get("amount", 1) * quantity
            category = material.get("class", "道具")
            stock = await self.inventory_service.get_count(user_id, category, material["name"])
            if stock < need:
                return CraftResult(
                    reason=f"「{material['name']}」不足！需{need}份，仅存{stock}份"
                )

        for material in materials:
            category = material.get("class", "道具")
            await self.inventory_service.remove_item(
                user_id,
                category,
                material["name"],
                material.get("amount", 1) * quantity,
            )

        product_class = recipe.get("class", "道具")
        await self.inventory_service.add_item(user_id, product_class, name, quantity)

        pet = player.get("仙宠")
        if isinstance(pet, dict) and pet.get("type") == "制符" and self._random() < pet.get("加成", 0):
            await self.inventory_service.add_item(user_id, product_class, name, quantity)
            quantity *= 2

        exp = recipe.get("exp", [0, 0])
        total_exp = int(exp[1] * quantity) if isinstance(exp, list) and len(exp) > 1 else int(exp * quantity) if isinstance(exp, (int, float)) else 0
        await self._add_occupation_exp(user_id, total_exp)

        return CraftResult(success=True, name=name, quantity=quantity, exp_gained=total_exp)

    async def craft_equipment(
        self,
        user_id: str,
        name: str,
    ) -> CraftResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return CraftResult(player_not_found=True)

        if self._get_current_occupation(player) != "炼器师":
            return CraftResult(reason="铜都不炼你还炼器？")

        recipe = self.occupation_data.find_recipe("tuzhi", name)
        if recipe is None:
            return CraftResult(reason=f"世界上没有[{name}]的图纸")

        materials = recipe.get("materials", [])
        for material in materials:
            need = material.get("amount", 1)
            stock = await self.inventory_service.get_count(user_id, "材料", material["name"])
            if stock < need:
                return CraftResult(
                    reason=f"纳戒中拥有{material['name']}×{stock}，打造需要{need}份"
                )

        for material in materials:
            await self.inventory_service.remove_item(
                user_id,
                "材料",
                material["name"],
                material.get("amount", 1),
            )

        rate = recipe.get("rate", 0.5)
        occ_level = player.get("occupation_level", 1)
        if occ_level > 0:
            occ_rate = self.occupation_data.get_occupation_rate(occ_level)
            extra = occ_rate * 10 * 0.025
            rate *= 1 + extra
            if occ_level >= 24:
                rate = 0.8

        if self._random() > rate:
            return CraftResult(reason="打造装备时火候失控，打造失败！")

        quality_index = int(self._random() * 7)
        quality_index = min(quality_index, 6)
        quality = ["劣", "普", "优", "精", "极", "绝", "顶"][quality_index]

        await self.inventory_service.add_item(user_id, "装备", name, 1, quality=quality)

        exp = recipe.get("exp", [0, 0])
        total_exp = int(exp[0]) if isinstance(exp, list) and exp else int(exp) if isinstance(exp, (int, float)) else 0
        await self._add_occupation_exp(user_id, total_exp)

        return CraftResult(success=True, name=name, quantity=1, exp_gained=total_exp, quality=quality)
