from dataclasses import dataclass, field
from typing import Any

from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class ReincarnationPromptResult:
    player_not_found: bool = False
    reason: str = ""
    prompt: str = ""


@dataclass
class ReincarnationConfirmResult:
    confirmed: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""


@dataclass
class ReincarnationResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""
    new_linggen: dict[str, Any] = field(default_factory=dict)


class ReincarnationService:
    """轮回服务：九世轮回，重置修为换取天赋。"""

    LINGGEN_BY_TURN: list[dict[str, Any]] = [
        {"id": 700991, "name": "一转轮回体", "type": "转生", "eff": 0.3, "法球倍率": 0.2},
        {"id": 700992, "name": "二转轮回体", "type": "转生", "eff": 0.35, "法球倍率": 0.23},
        {"id": 700993, "name": "三转轮回体", "type": "转生", "eff": 0.4, "法球倍率": 0.26},
        {"id": 700994, "name": "四转轮回体", "type": "转生", "eff": 0.45, "法球倍率": 0.3},
        {"id": 700995, "name": "五转轮回体", "type": "转生", "eff": 0.5, "法球倍率": 0.33},
        {"id": 700996, "name": "六转轮回体", "type": "转生", "eff": 0.55, "法球倍率": 0.36},
        {"id": 700997, "name": "七转轮回体", "type": "转生", "eff": 0.6, "法球倍率": 0.39},
        {"id": 700998, "name": "八转轮回体", "type": "转生", "eff": 0.65, "法球倍率": 0.42},
        {"id": 700999, "name": "九转轮回体", "type": "转生", "eff": 1.0, "法球倍率": 1.0},
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
        return f"xiuxian:player:{user_id}:lunhui"

    def _build_linggen(self, turn: int) -> dict[str, Any]:
        base = self.LINGGEN_BY_TURN[turn - 1]
        return {
            **base,
            "攻击": 0,
            "防御": 0,
            "生命": 0,
            "生命本源": 0,
        }

    # ---------- 多轮确认 ----------

    async def start_reincarnation(self, user_id: str) -> ReincarnationPromptResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ReincarnationPromptResult(player_not_found=True)

        if player.get("lunhui", 0) >= 9:
            return ReincarnationPromptResult(reason="你已经轮回完结！")

        if player.get("level_id", 1) < 42:
            return ReincarnationPromptResult(reason="法境未到仙无法轮回！")

        already = await self.state_service.get(self._pending_key(user_id), 0)
        if already == 1:
            return ReincarnationPromptResult(reason="请再次输入#轮回！")

        prompt = (
            "轮回之术乃逆天造化之术，须清空仙人所有的修为气血才可施展。\n"
            "传说只有得到\"轮回阵旗\"进行辅助轮回，才会抵御轮回之苦的十之八九。\n"
            "回复:【确认轮回】或者【先不轮回】进行选择"
        )
        return ReincarnationPromptResult(prompt=prompt)

    async def confirm_reincarnation(
        self, user_id: str, choice: str
    ) -> ReincarnationConfirmResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ReincarnationConfirmResult(player_not_found=True)

        if choice == "先不轮回":
            return ReincarnationConfirmResult(reason="放弃轮回")

        if choice == "确认轮回":
            await self.state_service.set(self._pending_key(user_id), 1)
            return ReincarnationConfirmResult(
                confirmed=True,
                message="请再次输入#轮回！",
            )

        return ReincarnationConfirmResult(
            reason="回复:【确认轮回】或者【先不轮回】进行选择"
        )

    # ---------- 执行轮回 ----------

    async def reincarnate(self, user_id: str) -> ReincarnationResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ReincarnationResult(player_not_found=True)

        already = await self.state_service.get(self._pending_key(user_id), 0)
        if already != 1:
            return ReincarnationResult(reason="请先发送 #轮回 进行确认")

        if player.get("lunhui", 0) >= 9:
            return ReincarnationResult(reason="你已经轮回完结！")

        if player.get("level_id", 1) < 42:
            return ReincarnationResult(reason="法境未到仙无法轮回！")

        # 轮回点检查
        if player.get("轮回点", 0) <= 0:
            player["current_hp"] = 10
            await self.player_service.save(user_id, player)
            await self.state_service.delete(self._pending_key(user_id))
            return ReincarnationResult(
                reason="此生轮回点已消耗殆尽，未能躲过天机！\n"
                "被天庭发现，但因为没有轮回点未被关入天牢，\n"
                "仅被警告一次，轮回失败！"
            )

        player["轮回点"] -= 1

        # 1/4 概率失败
        if self.random_provider() <= 0.25:
            player["current_hp"] = 1
            player["exp"] = player.get("exp", 0) - 10000000
            player["blood_qi"] = player.get("blood_qi", 0) + 1141919
            player["spirit_stones"] = player.get("spirit_stones", 0) - 10000000
            await self.player_service.save(user_id, player)
            await self.state_service.delete(self._pending_key(user_id))
            return ReincarnationResult(
                reason="本次轮回的最后关头，终究还是未能躲过天机！\n"
                "被天庭搜捕归案，关入天牢受尽折磨，轮回失败！"
            )

        # 轮回成功
        player["lunhui"] = player.get("lunhui", 0) + 1
        turn = player["lunhui"]

        # 退出仙宗（简化：直接删除宗门信息）
        if player.get("sect"):
            del player["sect"]

        new_linggen = self._build_linggen(turn)
        player["linggen"] = new_linggen
        player["cultivation_efficiency"] = new_linggen["eff"]
        player["level_id"] = 9
        player["power_place"] = 0
        player["current_hp"] = player.get("max_hp", 100)

        # 添加轮回功法
        await self.inventory_service.add_item(
            user_id, "功法", f"{self._turn_name(turn)}轮回", 1
        )

        # 根据轮回保护状态重置属性
        if player.get("lunhuiBH", 0) == 0:
            player["Physique_id"] = max(1, player.get("Physique_id", 1) // 2)
            player["exp"] = 0
            player["blood_qi"] = 0
        else:
            player["exp"] = max(0, player.get("exp", 0) - 10000000)
            player["blood_qi"] = max(0, player.get("blood_qi", 0) - 10000000)
            player["lunhuiBH"] = 0

        await self.player_service.save(user_id, player)
        await self.state_service.delete(self._pending_key(user_id))

        return ReincarnationResult(
            success=True,
            message=f"你已打破规则，轮回成功，现在你为{self._turn_name(turn)}轮回！",
            new_linggen=new_linggen,
        )

    def _turn_name(self, turn: int) -> str:
        names = ["一", "二", "三", "四", "五", "六", "七", "八", "九"]
        return names[turn - 1]
