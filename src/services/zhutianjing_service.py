import random
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@dataclass
class ZhutianjingResult:
    """诸天镜操作结果。"""

    success: bool = False
    player_not_found: bool = False
    target_not_found: bool = False
    message: str = ""
    lines: list[str] = field(default_factory=list)


class ZhutianjingService:
    """诸天镜服务：穿越、救赎、魔法少女进阶、库洛牌。"""

    DATA_KEY = "zhutianjing_data"
    MIRROR_ITEM = "诸天镜"
    HOPE_SHARD_ITEM = "希望碎片"
    ITEM_CATEGORY = "道具"

    STAGES = ["魔法少女", "愿望化身", "希望化身", "圆环之理"]

    EVENTS = [
        {
            "name": "魔女盛宴的救赎",
            "desc": "你聆听魔女哭泣般的摇篮曲，用希望之光将其温柔净化。",
            "rewards": [
                {"kind": "exp", "amount": 50},
                {"kind": "spirit_stones", "amount": 100},
                {"kind": "item", "category": "道具", "name": "悲叹之种", "amount": 1},
            ],
        },
        {
            "name": "时间线残影",
            "desc": "一道熟悉的时间残影闪过，你窥见了另一条时间线上的自己。",
            "rewards": [
                {"kind": "exp", "amount": 30},
                {"kind": "blood_qi", "amount": 20},
            ],
        },
        {
            "name": "丘比的契约诱惑",
            "desc": "丘比摇着尾巴提出契约，你坚定地拒绝了它。",
            "rewards": [
                {"kind": "spirit_stones", "amount": 30},
                {"kind": "item", "category": "道具", "name": "希望碎片", "amount": 1},
            ],
        },
        {
            "name": "圆环之理的碎片",
            "desc": "粉色的光芒温柔地包裹了你，那是圆环之理的一缕眷顾。",
            "rewards": [
                {"kind": "exp", "amount": 100},
                {"kind": "item", "category": "道具", "name": "希望碎片", "amount": 2},
            ],
        },
        {
            "name": "迷途魔法少女的指引",
            "desc": "你指引了一位迷途的魔法少女，她赠予你一份谢礼。",
            "rewards": [
                {"kind": "exp", "amount": 20},
                {"kind": "bonus", "key": "attack_bonus", "amount": 1},
            ],
        },
    ]

    CARDS = [
        {"name": "风", "buff": {"attack_bonus": 5}},
        {"name": "水", "buff": {"defense_bonus": 5}},
        {"name": "火", "buff": {"attack_bonus": 3, "hp_bonus": 3}},
        {"name": "地", "buff": {"defense_bonus": 3, "hp_bonus": 5}},
        {"name": "光", "buff": {"attack_bonus": 5, "defense_bonus": 5, "hp_bonus": 5}},
    ]

    def __init__(
        self,
        player_service: PlayerService,
        inventory_service: InventoryService,
        data_dir: Path,
    ):
        self.player_service = player_service
        self.inventory_service = inventory_service
        self.data_dir = data_dir

    def _ensure_data(self, player: dict[str, Any]) -> dict[str, Any]:
        """确保玩家拥有诸天镜数据。"""
        defaults = {
            "entered_count": 0,
            "saved_count": 0,
            "magic_girl_stage": 0,
            "cards": [],
            "intimacy": {},
            "last_enter_date": "",
        }
        data = player.setdefault(self.DATA_KEY, {})
        for key, value in defaults.items():
            data.setdefault(key, value)
        return data

    async def enter_mirror(self, user_id: str) -> ZhutianjingResult:
        """穿越诸天镜，获得随机事件奖励。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return ZhutianjingResult(player_not_found=True, message="玩家不存在，请先创建角色。")

        data = self._ensure_data(player)
        used_item = False

        if await self.inventory_service.has_item(
            user_id, self.ITEM_CATEGORY, self.MIRROR_ITEM, 1
        ):
            await self.inventory_service.remove_item(
                user_id, self.ITEM_CATEGORY, self.MIRROR_ITEM, 1
            )
            used_item = True
        else:
            today = date.today().isoformat()
            if data.get("last_enter_date") == today:
                return ZhutianjingResult(
                    message="今日免费穿越次数已用完，需要消耗「诸天镜」x1。"
                )
            data["last_enter_date"] = today

        data["entered_count"] += 1
        event = random.choice(self.EVENTS)
        lines = [
            f"🌌 {event['name']}",
            event["desc"],
            "",
            "【本次收获】",
        ]

        for reward in event["rewards"]:
            kind = reward["kind"]
            amount = reward["amount"]
            if kind == "exp":
                await self.player_service.add_exp(user_id, amount)
                lines.append(f"修为 +{amount}")
            elif kind == "spirit_stones":
                await self.player_service.add_spirit_stones(user_id, amount)
                lines.append(f"灵石 +{amount}")
            elif kind == "blood_qi":
                await self.player_service.add_blood_qi(user_id, amount)
                lines.append(f"血气 +{amount}")
            elif kind == "item":
                category = reward.get("category", self.ITEM_CATEGORY)
                await self.inventory_service.add_item(
                    user_id, category, reward["name"], amount
                )
                lines.append(f"{reward['name']} x{amount}")
            elif kind == "bonus":
                await self._add_player_bonus(user_id, reward["key"], amount)
                lines.append(f"{reward['key']} +{amount}")

        # 重新加载以合并诸天镜数据，避免覆盖奖励写入
        player = await self.player_service.load(user_id)
        player[self.DATA_KEY] = data
        await self.player_service.save(user_id, player)

        lines.append("")
        lines.append(f"累计穿越次数：{data['entered_count']}次")
        if used_item:
            lines.append("本次消耗：诸天镜 x1")
        else:
            lines.append("本次为今日免费穿越")

        return ZhutianjingResult(success=True, lines=lines)

    async def _add_player_bonus(self, user_id: str, key: str, amount: int) -> None:
        """给玩家增加一项属性加成。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return
        player[key] = player.get(key, 0) + amount
        await self.player_service.save(user_id, player)

    async def redeem(self, user_id: str, target_id: str) -> ZhutianjingResult:
        """救赎一名玩家，增加救赎计数与亲密度。"""
        caster = await self.player_service.load(user_id)
        if caster is None:
            return ZhutianjingResult(player_not_found=True, message="施法者不存在。")

        target = await self.player_service.load(target_id)
        if target is None:
            return ZhutianjingResult(
                target_not_found=True, message="目标玩家不存在于诸天万界中。"
            )

        data = self._ensure_data(caster)
        data["saved_count"] += 1
        data["intimacy"][target_id] = data["intimacy"].get(target_id, 0) + 1

        await self.player_service.add_exp(target_id, 10)
        await self.player_service.add_spirit_stones(target_id, 50)

        player = await self.player_service.load(user_id)
        player[self.DATA_KEY] = data
        await self.player_service.save(user_id, player)

        return ZhutianjingResult(
            success=True,
            message=(
                f"✨ 你施展救赎之光，将 {target.get('name', '无名')} 从困境中解救！\n"
                f"救赎次数：{data['saved_count']} | 对 TA 的亲密度：{data['intimacy'][target_id]}"
            ),
        )

    async def advance_magic_girl(self, user_id: str) -> ZhutianjingResult:
        """魔法少女进阶，消耗希望碎片与灵石获得属性提升。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return ZhutianjingResult(player_not_found=True, message="玩家不存在。")

        data = self._ensure_data(player)
        stage = data["magic_girl_stage"]
        if stage >= len(self.STAGES) - 1:
            return ZhutianjingResult(message="你已经达到了圆环之理的巅峰。")

        next_stage = stage + 1
        cost_shards = next_stage * 50
        cost_stones = next_stage * 500

        if not await self.inventory_service.has_item(
            user_id, self.ITEM_CATEGORY, self.HOPE_SHARD_ITEM, cost_shards
        ):
            count = await self.inventory_service.get_count(
                user_id, self.ITEM_CATEGORY, self.HOPE_SHARD_ITEM
            )
            return ZhutianjingResult(
                message=f"希望碎片不足，需要 {cost_shards} 个，当前 {count} 个。"
            )

        if player.get("spirit_stones", 0) < cost_stones:
            return ZhutianjingResult(
                message=f"灵石不足，需要 {cost_stones} 个，当前 {player.get('spirit_stones', 0)} 个。"
            )

        await self.inventory_service.remove_item(
            user_id, self.ITEM_CATEGORY, self.HOPE_SHARD_ITEM, cost_shards
        )

        # 重新加载玩家，避免覆盖纳戒修改
        player = await self.player_service.load(user_id)
        player["spirit_stones"] = player.get("spirit_stones", 0) - cost_stones
        data["magic_girl_stage"] = next_stage
        player["attack_bonus"] = player.get("attack_bonus", 0) + next_stage * 3
        player["defense_bonus"] = player.get("defense_bonus", 0) + next_stage * 2
        player["hp_bonus"] = player.get("hp_bonus", 0) + next_stage * 5
        player[self.DATA_KEY] = data

        await self.player_service.save(user_id, player)

        return ZhutianjingResult(
            success=True,
            message=(
                f"🌸 魔法少女进阶成功！\n"
                f"当前阶段：{self.STAGES[next_stage]}（{next_stage}）\n"
                f"消耗：希望碎片 x{cost_shards}、灵石 x{cost_stones}"
            ),
        )

    async def get_mirror_stats(self, user_id: str) -> ZhutianjingResult:
        """查看当前诸天镜状态。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return ZhutianjingResult(player_not_found=True, message="玩家不存在。")

        data = self._ensure_data(player)
        await self.player_service.save(user_id, player)

        stage_name = self.STAGES[data["magic_girl_stage"]]
        cards = data["cards"]
        lines = [
            "---【诸天镜】---",
            f"穿越次数：{data['entered_count']}",
            f"救赎次数：{data['saved_count']}",
            f"魔法少女阶段：{stage_name}（{data['magic_girl_stage']}）",
            f"库洛牌：{', '.join(cards) if cards else '无'}",
        ]

        return ZhutianjingResult(success=True, lines=lines)

    async def draw_clow_card(self, user_id: str) -> ZhutianjingResult:
        """抽取一张库洛牌，获得临时属性增益。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return ZhutianjingResult(player_not_found=True, message="玩家不存在。")

        data = self._ensure_data(player)
        card = random.choice(self.CARDS)
        data["cards"].append(card["name"])
        if len(data["cards"]) > 10:
            data["cards"].pop(0)

        buff_texts = []
        for key, amount in card["buff"].items():
            player[key] = player.get(key, 0) + amount
            buff_texts.append(f"{key} +{amount}")

        player[self.DATA_KEY] = data
        await self.player_service.save(user_id, player)

        return ZhutianjingResult(
            success=True,
            message=(
                f"🃏 你抽到了库洛牌「{card['name']}」！\n"
                f"增益效果：{', '.join(buff_texts)}"
            ),
        )
