from dataclasses import dataclass, field
from typing import Any

from src.data.level_data import LevelData
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@dataclass
class XianguBreakthroughResult:
    success: bool = False
    player_not_found: bool = False
    not_ready: bool = False
    already_max: bool = False
    already_extreme: bool = False
    insufficient_resources: bool = False
    missing_items: list[dict[str, Any]] = field(default_factory=list)
    missing_gongfa: str = ""
    message: str = ""
    level_name: str = ""
    extreme_name: str = ""
    exp_cost: int = 0
    blood_qi_cost: int = 0
    attack_bonus: int = 0
    defense_bonus: int = 0
    hp_bonus: int = 0


class XianguJinshiService:
    """仙骨金身/仙古今世法冲关服务。"""

    # 前置条件
    REQUIRE_LEVEL_ID = 42
    REQUIRE_PHYSIQUE_ID = 42

    # 普通冲关基础消耗（修为+血气）
    BASE_EXP_COST = 500_000

    # 各境界普通突破额外需求
    NORMAL_REQUIREMENTS: dict[int, dict[str, Any]] = {
        1: {
            "blood_qi": 500_000,
            "items": [
                {"name": "朱厌真血", "category": "道具", "quantity": 1},
                {"name": "螭龙真血", "category": "道具", "quantity": 1},
                {"name": "饕餮真血", "category": "道具", "quantity": 1},
            ],
            "gongfa": ["青鳞鹰宝术", "狻猊宝术", "朱雀宝术", "原始真解"],
        },
        2: {
            "items": [
                {"name": "猴儿酒", "category": "丹药", "quantity": 10},
                {"name": "不老泉", "category": "丹药", "quantity": 1},
                {"name": "太一真水", "category": "道具", "quantity": 1},
                {"name": "金翅大鹏鸟血肉", "category": "道具", "quantity": 1},
            ],
            "gongfa": ["原始真解神引篇"],
        },
        3: {
            "need_extreme": [2, 3],
        },
        4: {
            "need_extreme": [2, 3, 4],
            "gongfa": ["原始真解神引篇"],
        },
        5: {
            "need_extreme": [2, 3, 4, 5],
            "items": [
                {"name": "万灵图", "category": "道具", "quantity": 1},
            ],
        },
        6: {
            "need_extreme": [2, 3, 4, 5, 6],
            "items": [
                {"name": "五行涅槃法", "category": "功法", "quantity": 1},
            ],
        },
    }

    # 极境突破额外需求
    EXTREME_REQUIREMENTS: dict[int, dict[str, Any]] = {
        2: {
            "blood_qi": 1_000_000,
            "items": [
                {"name": "朱雀真血", "category": "道具", "quantity": 1},
                {"name": "狻猊真血", "category": "道具", "quantity": 1},
                {"name": "饕餮真血", "category": "道具", "quantity": 1},
            ],
            "special_physique": ["荒古圣体", "天生至尊"],
        },
        3: {
            "items": [{"name": "柳神本源", "category": "道具", "quantity": 1}],
        },
        4: {
            "items": [{"name": "鲲鹏神液", "category": "道具", "quantity": 5}],
        },
        5: {
            "items": [{"name": "原始真解神引篇", "category": "功法", "quantity": 1}],
        },
        6: {
            "items": [{"name": "万灵图", "category": "道具", "quantity": 1}],
        },
        7: {
            "items": [{"name": "五行涅槃法", "category": "功法", "quantity": 1}],
        },
    }

    def __init__(
        self,
        player_service: PlayerService,
        inventory_service: InventoryService,
        level_data: LevelData,
    ):
        self.player_service = player_service
        self.inventory_service = inventory_service
        self.level_data = level_data

    async def _get_extreme_states(self, user_id: str) -> list[str]:
        player = await self.player_service.load(user_id)
        if player is None:
            return []
        return player.setdefault("extreme_states", [])

    async def _add_extreme_state(self, user_id: str, level_id: int) -> None:
        player = await self.player_service.load(user_id)
        if player is None:
            return
        states = player.setdefault("extreme_states", [])
        key = str(level_id)
        if key not in states:
            states.append(key)
        await self.player_service.save(user_id, player)

    # ---------- 工具方法 ----------

    def _calculate_cost(self, xiangu_level_id: int) -> int:
        """计算当前境界普通冲关消耗。"""
        return self.BASE_EXP_COST * xiangu_level_id

    def _get_level_name(self, level_id: int) -> str:
        name = self.level_data.get_xiangu_name(level_id)
        return name or "未知境界"

    def _has_any_gongfa(self, player: dict[str, Any], names: list[str]) -> bool:
        learned = player.get("learned_gongfa", [])
        return any(name in learned for name in names)

    async def _check_items(
        self, user_id: str, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        missing = []
        for req in items:
            have = await self.inventory_service.get_count(
                user_id, req["category"], req["name"]
            )
            if have < req["quantity"]:
                missing.append(
                    {
                        "name": req["name"],
                        "category": req["category"],
                        "required": req["quantity"],
                        "current": have,
                    }
                )
        return missing

    async def _consume_items(
        self, user_id: str, items: list[dict[str, Any]]
    ) -> None:
        for req in items:
            await self.inventory_service.remove_item(
                user_id,
                req["category"],
                req["name"],
                req["quantity"],
            )

    # ---------- 普通冲关 ----------

    async def breakthrough(
        self, user_id: str, extreme: bool = False
    ) -> XianguBreakthroughResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return XianguBreakthroughResult(player_not_found=True)

        # 初始化仙骨金身相关字段
        player.setdefault("extreme_states", [])
        player.setdefault("dongtian_count", 0)
        player.setdefault("hualing_stage", 0)

        if player.get("level_id", 1) < self.REQUIRE_LEVEL_ID:
            return XianguBreakthroughResult(
                not_ready=True,
                message=f"需练气/炼体境界达到 {self.REQUIRE_LEVEL_ID}（地仙）方可冲关仙古。",
            )

        if player.get("physique_id", 1) < self.REQUIRE_PHYSIQUE_ID:
            return XianguBreakthroughResult(
                not_ready=True,
                message="需肉身成圣（炼体境界≥42）方可冲关仙古。",
            )

        if player.get("mijing_level_id", 1) > 1:
            return XianguBreakthroughResult(
                not_ready=True,
                message="仙古今世法与人体秘境体系不可兼修。",
            )

        xiangu_level_id = int(player.get("xiangu_level_id", 1))
        next_level_id = xiangu_level_id + 1
        next_level = self.level_data.get_xiangu(next_level_id)
        if next_level is None:
            return XianguBreakthroughResult(
                already_max=True, message="你已破关至最高境界。"
            )

        if extreme:
            return await self._extreme_breakthrough(user_id, player, xiangu_level_id)

        return await self._normal_breakthrough(user_id, player, xiangu_level_id)

    async def _normal_breakthrough(
        self, user_id: str, player: dict[str, Any], current_level_id: int
    ) -> XianguBreakthroughResult:
        next_level_id = current_level_id + 1
        req = self.NORMAL_REQUIREMENTS.get(current_level_id, {})
        cost = self._calculate_cost(current_level_id)

        # 检查前置极境
        need_extreme = req.get("need_extreme", [])
        states = player.get("extreme_states", [])
        missing_extreme = [
            str(lv) for lv in need_extreme if str(lv) not in states
        ]
        if missing_extreme:
            return XianguBreakthroughResult(
                not_ready=True,
                message=f"需先达成以下极境：{', '.join(missing_extreme)}",
            )

        # 检查功法
        gongfa_list = req.get("gongfa", [])
        if gongfa_list and not self._has_any_gongfa(player, gongfa_list):
            return XianguBreakthroughResult(
                not_ready=True,
                missing_gongfa=gongfa_list[0],
                message=f"需掌握以下功法之一：{', '.join(gongfa_list)}",
            )

        # 检查物品
        items = req.get("items", [])
        missing_items = await self._check_items(user_id, items)
        if missing_items:
            lines = [
                f"{m['name']}：需{m['required']}，有{m['current']}"
                for m in missing_items
            ]
            return XianguBreakthroughResult(
                insufficient_resources=True,
                missing_items=missing_items,
                message="资源不足：\n" + "\n".join(lines),
            )

        # 检查血气/修为
        blood_qi_need = req.get("blood_qi", cost)
        exp_need = req.get("exp", cost)
        if player.get("blood_qi", 0) < blood_qi_need or player.get("exp", 0) < exp_need:
            return XianguBreakthroughResult(
                insufficient_resources=True,
                exp_cost=exp_need,
                blood_qi_cost=blood_qi_need,
                message=(
                    f"修为/血气不足。"
                    f"需要修为 {exp_need:,}、血气 {blood_qi_need:,}。"
                ),
            )

        # 消耗并突破
        player["exp"] = player.get("exp", 0) - exp_need
        player["blood_qi"] = player.get("blood_qi", 0) - blood_qi_need
        await self._consume_items(user_id, items)

        player["xiangu_level_id"] = next_level_id
        if next_level_id == 3:
            player["dongtian_count"] = 10
        if next_level_id == 4:
            player["hualing_stage"] = 3

        await self.player_service.save(user_id, player)

        return XianguBreakthroughResult(
            success=True,
            level_name=self._get_level_name(next_level_id),
            exp_cost=exp_need,
            blood_qi_cost=blood_qi_need,
            message=f"冲关成功！当前境界：{self._get_level_name(next_level_id)}",
        )

    async def _extreme_breakthrough(
        self, user_id: str, player: dict[str, Any], current_level_id: int
    ) -> XianguBreakthroughResult:
        next_level_id = current_level_id + 1
        req = self.EXTREME_REQUIREMENTS.get(next_level_id, {})
        states = player.get("extreme_states", [])

        if str(next_level_id) in states:
            return XianguBreakthroughResult(
                already_extreme=True,
                message=f"你已成就{self._get_level_name(next_level_id)}极境。",
            )

        # 特殊体质可减免血气要求
        is_special = player.get("linggen", {}).get("name") in req.get(
            "special_physique", []
        )
        blood_qi_need = 0 if is_special else req.get("blood_qi", 0)
        exp_need = req.get("exp", self._calculate_cost(current_level_id) * 2)

        # 检查物品
        items = req.get("items", [])
        missing_items = await self._check_items(user_id, items)
        if missing_items:
            lines = [
                f"{m['name']}：需{m['required']}，有{m['current']}"
                for m in missing_items
            ]
            return XianguBreakthroughResult(
                insufficient_resources=True,
                missing_items=missing_items,
                message="极境资源不足：\n" + "\n".join(lines),
            )

        # 检查能量
        if player.get("blood_qi", 0) < blood_qi_need or player.get("exp", 0) < exp_need:
            return XianguBreakthroughResult(
                insufficient_resources=True,
                exp_cost=exp_need,
                blood_qi_cost=blood_qi_need,
                message=(
                    f"修为/血气不足以冲击极境。"
                    f"需要修为 {exp_need:,}、血气 {blood_qi_need:,}。"
                ),
            )

        # 消耗并突破
        player["exp"] = player.get("exp", 0) - exp_need
        player["blood_qi"] = player.get("blood_qi", 0) - blood_qi_need
        await self._consume_items(user_id, items)

        states.append(str(next_level_id))
        player["extreme_states"] = states

        # 应用极境加成
        level_info = self.level_data.get_xiangu(next_level_id)
        if level_info:
            bonus = level_info.get("极境加成", {})
            player["attack_bonus"] = player.get("attack_bonus", 0) + bonus.get(
                "攻击加成", 0
            )
            player["defense_bonus"] = player.get("defense_bonus", 0) + bonus.get(
                "防御加成", 0
            )
            player["hp_bonus"] = player.get("hp_bonus", 0) + bonus.get(
                "血量加成", 0
            )

        await self.player_service.save(user_id, player)
        await self._add_extreme_state(user_id, next_level_id)

        extreme_name = level_info.get("极境名称", "极境") if level_info else "极境"
        return XianguBreakthroughResult(
            success=True,
            level_name=self._get_level_name(next_level_id),
            extreme_name=extreme_name,
            exp_cost=exp_need,
            blood_qi_cost=blood_qi_need,
            attack_bonus=bonus.get("攻击加成", 0) if level_info else 0,
            defense_bonus=bonus.get("防御加成", 0) if level_info else 0,
            hp_bonus=bonus.get("血量加成", 0) if level_info else 0,
            message=f"打破极境！成就【{extreme_name}】",
        )
