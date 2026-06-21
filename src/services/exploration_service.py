import random
import time
from dataclasses import dataclass, field
from typing import Any

from src.data.exploration_data import ExplorationData
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class ExplorationResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""
    details: list[str] = field(default_factory=list)
    action: str = ""
    elapsed_minutes: int = 0


class ExplorationService:
    """管理秘境、禁地、仙府、仙境等探索活动。"""

    BASE_MINUTES = 30

    def __init__(
        self,
        player_service: PlayerService,
        state_service: StateService,
        exploration_data: ExplorationData,
    ):
        self.player_service = player_service
        self.state_service = state_service
        self.exploration_data = exploration_data

    def _state_key(self, user_id: str) -> str:
        return f"xiuxian:player:{user_id}:action"

    async def _get_action(self, user_id: str) -> dict[str, Any] | None:
        return await self.state_service.get(self._state_key(user_id), None)

    async def _set_action(self, user_id: str, action: dict[str, Any] | None) -> None:
        if action is None:
            await self.state_service.delete(self._state_key(user_id))
        else:
            await self.state_service.set(self._state_key(user_id), action)

    async def _load_player(self, user_id: str) -> dict[str, Any] | None:
        return await self.player_service.load(user_id)

    async def _is_busy(self, user_id: str, now: float) -> tuple[bool, str]:
        action = await self._get_action(user_id)
        if action and action.get("end_time", 0) > now * 1000:
            return True, f"正在{action.get('action', '行动中')}"
        return False, ""

    def _calculate_time_reduction(self, player: dict[str, Any]) -> tuple[int, list[str]]:
        """计算探索时间缩减。"""
        learned = player.get("learned_gongfa", [])
        mijing_level = player.get("mijing_level_id", 1)
        daofa = player.get("daofa_xianshu", 0)
        reduction = 0
        msgs: list[str] = []

        has_xingzi = "行字秘" in learned
        has_tianxuan = "天璇步法" in learned

        if has_xingzi:
            xingzi_reduction = 2
            texts = [
                "【行字秘·极速奥义】",
                "你足下道纹流转，身形如电，",
                "施展行字秘，速度骤增！",
            ]
            if mijing_level >= 9:
                xingzi_reduction += 1
                texts.append("脚下金莲隐现，速度更上一层")
            if mijing_level >= 16:
                xingzi_reduction += 1
                texts.append("时光碎片缭绕，触及时间领域")
            texts.append(f"时间减少{xingzi_reduction}分钟")
            reduction += xingzi_reduction
            msgs.append("\n".join(texts))
        elif has_tianxuan:
            reduction += 1
            msgs.append(
                "【天璇步法·残篇奥义】\n"
                "足下道纹流转，身形如烟似幻，\n"
                "天璇步法展动间缩地成寸！\n"
                "时间减少1分钟"
            )

        if daofa == 2:
            reduction += 2
            msgs.append("受到道法仙术加持，历练时间减少2分钟")

        return reduction, msgs

    async def _start_exploration(
        self,
        user_id: str,
        place: dict[str, Any],
        action_name: str,
        now: float | None,
        extra_msgs: list[str] | None = None,
    ) -> ExplorationResult:
        now = now or time.time()
        now_ms = int(now * 1000)

        busy, reason = await self._is_busy(user_id, now)
        if busy:
            return ExplorationResult(success=False, reason=reason)

        reduction, reduction_msgs = self._calculate_time_reduction(await self._load_player(user_id))
        minutes = max(1, self.BASE_MINUTES - reduction)

        action = {
            "action": action_name,
            "start_time": now_ms,
            "end_time": now_ms + minutes * 60 * 1000,
            "time": minutes * 60 * 1000,
            "place": place.get("name"),
        }
        await self._set_action(user_id, action)

        details = list(extra_msgs or [])
        if reduction > 0:
            details.extend(reduction_msgs)
            details.append(f"【时间缩减】总计减少：{reduction}分钟，剩余时间：{minutes}分钟")

        return ExplorationResult(
            success=True,
            message=f"开始{action_name}【{place.get('name')}】，{minutes}分钟后归来！",
            details=details,
            action=action_name,
            elapsed_minutes=minutes,
        )

    async def start_secret_place(
        self, user_id: str, place_name: str, now: float | None = None
    ) -> ExplorationResult:
        player = await self._load_player(user_id)
        if player is None:
            return ExplorationResult(player_not_found=True)

        place = self.exploration_data.find_secret_place(place_name)
        if place is None:
            return ExplorationResult(success=False, reason=f"未知的秘境：{place_name}")

        now = now or time.time()
        busy, reason = await self._is_busy(user_id, now)
        if busy:
            return ExplorationResult(success=False, reason=reason)

        # 特殊地点境界检查：永恒海需要 level_id >= 55
        if place_name == "永恒海" and player.get("level_id", 1) < 55:
            return ExplorationResult(success=False, reason="没有达到万界道祖之前还是不要去了")

        price = place.get("Price", 0)
        shouyuan = place.get("shouyuan", 0)

        if player.get("spirit_stones", 0) < price:
            return ExplorationResult(
                success=False, reason=f"没有灵石寸步难行，攒到{price}灵石才够哦~"
            )
        if player.get("shouyuan", 0) < shouyuan:
            return ExplorationResult(success=False, reason="道友这点寿元就不要去了吧，免得原地坐化了")

        player["spirit_stones"] = player.get("spirit_stones", 0) - price
        player["shouyuan"] = player.get("shouyuan", 0) - shouyuan
        player["last_dungeon_type"] = "秘境"
        player["last_dungeon_name"] = place_name
        await self.player_service.save(user_id, player)

        extra = [f"{player.get('name', '道友')}消耗了{shouyuan}寿元和{price}灵石"]
        return await self._start_exploration(
            user_id, place, "秘境历练", now, extra_msgs=extra
        )

    async def start_forbidden_area(
        self, user_id: str, place_name: str, now: float | None = None
    ) -> ExplorationResult:
        player = await self._load_player(user_id)
        if player is None:
            return ExplorationResult(player_not_found=True)

        place = self.exploration_data.find_forbidden_area(place_name)
        if place is None:
            return ExplorationResult(success=False, reason=f"未找到禁地：{place_name}")

        now = now or time.time()
        busy, reason = await self._is_busy(user_id, now)
        if busy:
            return ExplorationResult(success=False, reason=reason)

        level_id = player.get("level_id", 1)
        if level_id < 22:
            return ExplorationResult(success=False, reason="没有达到化神之前还是不要去了")
        if place_name == "诸神黄昏·旧神界" and level_id < 46:
            return ExplorationResult(success=False, reason="没有达到金仙之前还是不要去了")
        if place_name == "始源·混沌初开之地" and level_id < 64:
            return ExplorationResult(success=False, reason="没有达到无境之前还是不要去了")

        price = place.get("Price", 0)
        exp_cost = place.get("experience", 0)
        shouyuan = place.get("shouyuan", 0)

        if player.get("spirit_stones", 0) < price:
            return ExplorationResult(
                success=False, reason=f"没有灵石寸步难行，攒到{price}灵石才够哦~"
            )
        if player.get("exp", 0) < exp_cost:
            return ExplorationResult(
                success=False, reason=f"你需要积累{exp_cost}修为，才能抵抗禁地魔气！"
            )
        if player.get("shouyuan", 0) < shouyuan:
            return ExplorationResult(success=False, reason="道友这点寿元就不要去了吧，免得原地坐化了")

        player["spirit_stones"] = player.get("spirit_stones", 0) - price
        player["exp"] = player.get("exp", 0) - exp_cost
        player["shouyuan"] = player.get("shouyuan", 0) - shouyuan
        player["last_dungeon_type"] = "禁地"
        player["last_dungeon_name"] = place_name
        await self.player_service.save(user_id, player)

        descriptions = {
            "诸神黄昏·旧神界": "此地曾是神界战场，神血染红大地，神骨铺就道路。",
            "始源·混沌初开之地": "混沌初开之地，万物起源之所，大道法则交织碰撞。",
            "幽冥血海": "血海无边，怨魂哀嚎，汇聚了世间最深的怨念与诅咒。",
            "九幽魔渊": "魔气滔天，万魔蛰伏，是魔道修士的圣地。",
        }
        location_desc = descriptions.get(
            place_name,
            "禁地之中危机四伏，但也蕴藏着无尽机缘。",
        )
        extra = [
            f"{player.get('name', '道友')}消耗：{shouyuan}寿元，{price}灵石，{exp_cost}修为",
            f"【{place_name}】{location_desc}",
        ]
        return await self._start_exploration(
            user_id, place, "禁地历练", now, extra_msgs=extra
        )

    async def start_time_place(
        self, user_id: str, now: float | None = None
    ) -> ExplorationResult:
        player = await self._load_player(user_id)
        if player is None:
            return ExplorationResult(player_not_found=True)

        now = now or time.time()
        busy, reason = await self._is_busy(user_id, now)
        if busy:
            return ExplorationResult(success=False, reason=reason)

        if player.get("level_id", 1) < 21:
            return ExplorationResult(
                success=False, reason="到了地图上的地点，结果你发现，你尚未达到化神，无法抵御灵气压制"
            )

        # 仙府随机选择
        candidates = self.exploration_data.get_time_places()
        if not candidates:
            return ExplorationResult(success=False, reason="暂无仙府可探索")

        # 10% 概率被骗
        if random.random() > 0.9:
            if player.get("spirit_stones", 0) < 50000:
                return ExplorationResult(
                    success=False,
                    reason='还没看两眼就被看堂的打手撵了出去说："哪来的穷小子，不买别看"',
                )
            player["spirit_stones"] = player.get("spirit_stones", 0) - 50000
            await self.player_service.save(user_id, player)
            return ExplorationResult(
                success=False,
                reason="价格为5w，你觉得特别特别便宜，赶紧全款拿下了，历经九九八十天，到了后发现居然是仙湖游乐场！",
            )

        place = random.choice(candidates)
        place_name = place.get("name")
        price = place.get("Price", 0)

        if player.get("spirit_stones", 0) < price:
            return ExplorationResult(
                success=False, reason=f"你发现标价是{price}，你买不起赶紧溜了"
            )
        if player.get("exp", 0) < 100000:
            return ExplorationResult(
                success=False,
                reason='到了地图上的地点，发现洞府前有一句前人留下的遗言："至少有10w修为才能抵御仙威！"',
            )

        player["spirit_stones"] = player.get("spirit_stones", 0) - price
        player["exp"] = player.get("exp", 0) - 100000
        player["last_dungeon_type"] = "仙府"
        player["last_dungeon_name"] = place_name
        await self.player_service.save(user_id, player)

        extra = [
            "你在冲水堂发现有人上架了一份仙府地图",
            f"{player.get('name', '道友')}消耗了{price}灵石和100000修为",
        ]
        return await self._start_exploration(
            user_id, place, "探索仙府", now, extra_msgs=extra
        )

    async def start_fairy_realm(
        self, user_id: str, place_name: str, now: float | None = None
    ) -> ExplorationResult:
        player = await self._load_player(user_id)
        if player is None:
            return ExplorationResult(player_not_found=True)

        place = self.exploration_data.find_fairy_realm(place_name)
        if place is None:
            return ExplorationResult(success=False, reason=f"未找到仙境：{place_name}")

        now = now or time.time()
        busy, reason = await self._is_busy(user_id, now)
        if busy:
            return ExplorationResult(success=False, reason=reason)

        level_id = player.get("level_id", 1)
        lunhui = player.get("lunhui", 0)
        if level_id < 42 and lunhui == 0:
            return ExplorationResult(
                success=False, reason="仙境乃仙人之地，非成仙者不可入！"
            )
        if place_name == "杀神崖" and level_id < 50:
            return ExplorationResult(
                success=False, reason="杀神崖乃仙王喋血之地，非究极仙王不可踏足！"
            )

        price = place.get("Price", 0)
        shouyuan = place.get("shouyuan", 0)

        if player.get("spirit_stones", 0) < price:
            return ExplorationResult(
                success=False, reason=f"没有灵石寸步难行，攒到{price}灵石才够哦~"
            )
        if player.get("shouyuan", 0) < shouyuan:
            return ExplorationResult(success=False, reason="道友这点寿元就不要去了吧，免得原地坐化了")

        player["spirit_stones"] = player.get("spirit_stones", 0) - price
        player["shouyuan"] = player.get("shouyuan", 0) - shouyuan
        player["last_dungeon_type"] = "仙境"
        player["last_dungeon_name"] = place_name
        await self.player_service.save(user_id, player)

        descriptions = {
            "神域星宫": "【神域星宫·混沌之巅】神域星宫悬浮于混沌海之上，是诸天万界至高无上的存在！",
            "瑞泽云海": "【瑞泽云海·仙兽福地】瑞泽云海祥云缭绕，瑞气千条，曾是仙兽栖息之地！",
            "瑶池仙境": "【瑶池仙境·仙家福地】瑶池仙境仙气缭绕，琼楼玉宇，蟠桃仙树遍地。",
            "蓬莱仙岛": "【蓬莱仙岛·长生秘境】蓬莱仙岛隐于东海，仙草遍地，灵泉涌动。",
            "杀神崖": "【杀神崖·仙王喋血】杀神崖上，仙王喋血，神骨铺路，弥漫着无尽杀伐之气！",
        }
        location_desc = descriptions.get(
            place_name,
            "【仙境镇守】仙境之中灵气充沛，是修行悟道的绝佳之地！",
        )
        extra = [
            f"{player.get('name', '道友')}消耗：{shouyuan}寿元，{price}灵石",
            location_desc,
        ]
        return await self._start_exploration(
            user_id, place, "镇守仙境", now, extra_msgs=extra
        )

    async def give_up(self, user_id: str, now: float | None = None) -> ExplorationResult:
        player = await self._load_player(user_id)
        if player is None:
            return ExplorationResult(player_not_found=True)

        action = await self._get_action(user_id)
        if action is None:
            return ExplorationResult(success=False, reason="当前没有进行中的探索")

        await self._set_action(user_id, None)
        return ExplorationResult(
            success=True,
            message="你已逃离秘境！",
            action=action.get("action", ""),
        )

    async def get_drop_text(self, place_name: str) -> str:
        place = self.exploration_data.find_place(place_name)
        if place is None:
            return f"未找到地点：{place_name}"

        lines = [
            f"【{place.get('Grade', '未知等级')}·{place_name}】",
            f"灵石：{place.get('Price', 0)}",
            f"修为：{place.get('experience', 0)}",
            f"寿元：{place.get('shouyuan', 0)}",
        ]

        for level, label in [("one", "一等掉落"), ("two", "二等掉落"), ("three", "三等掉落"), ("four", "四等掉落")]:
            items = place.get(level, [])
            if items:
                names = [item.get("name", "未知") for item in items]
                lines.append(f"{label}：{', '.join(names)}")

        return "\n".join(lines)
