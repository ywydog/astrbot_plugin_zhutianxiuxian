import random
import time
from dataclasses import dataclass, field
from typing import Any

from src.data.shop_data import ShopData
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class LootingStartResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""


@dataclass
class LootingSettleResult:
    success: bool = False
    player_not_found: bool = False
    no_action: bool = False
    reason: str = ""
    won: bool = False
    message: str = ""
    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class LootingInspectResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""


@dataclass
class LootingResetResult:
    success: bool = False
    reason: str = ""
    message: str = ""


class LootingService:
    """洗劫系统服务：探查、洗劫、结算。"""

    ACTION_KEY = "xiuxian:player:{user_id}:action"
    CD_KEY = "xiuxian:player:{user_id}:lastxijie_time"
    DURATION_MINUTES = 15
    CD_MINUTES = 120
    SPECIAL_PLACES = {"逆道界", "终极古地", "万维梵宇"}

    def __init__(
        self,
        player_service: PlayerService,
        state_service: StateService,
        inventory_service: InventoryService,
        shop_data: ShopData,
        random_provider=None,
    ):
        self.player_service = player_service
        self.state_service = state_service
        self.inventory_service = inventory_service
        self.shop_data = shop_data
        self.random_provider = random_provider or random.random

    def _action_key(self, user_id: str) -> str:
        return self.ACTION_KEY.format(user_id=user_id)

    def _cd_key(self, user_id: str) -> str:
        return self.CD_KEY.format(user_id=user_id)

    async def _get_action(self, user_id: str) -> dict[str, Any] | None:
        return await self.state_service.get(self._action_key(user_id), None)

    async def _set_action(self, user_id: str, action: dict[str, Any] | None) -> None:
        if action is None:
            await self.state_service.delete(self._action_key(user_id))
        else:
            await self.state_service.set(self._action_key(user_id), action)

    def _is_busy(self, action: dict[str, Any] | None, now_ms: int) -> bool:
        if not action:
            return False
        return action.get("end_time", 0) > now_ms

    async def inspect(
        self,
        user_id: str,
        place_name: str,
        now_ms: int | None = None,
    ) -> LootingInspectResult:
        """探查商店状态。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return LootingInspectResult(player_not_found=True)

        shop = self.shop_data.get(place_name)
        if shop is None:
            return LootingInspectResult(reason="这方天地没有这个地方")

        action = await self._get_action(user_id)
        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        if self._is_busy(action, now_ms):
            return LootingInspectResult(reason=f"正在{action.get('action')}中，无法探查")

        price = int(shop.get("price", 0) * 0.3)
        if player.get("spirit_stones", 0) < price:
            return LootingInspectResult(reason="你需要更多的灵石去打探消息")

        player["spirit_stones"] = player.get("spirit_stones", 0) - price
        await self.player_service.save(user_id, player)

        grade = shop.get("Grade", 1)
        state = shop.get("state", 0)
        level_text = {1: "松懈", 2: "戒备", 3: "恐慌"}.get(grade, "未知")
        state_text = "营业" if state == 0 else "打烊"

        items = shop.get("one", [])
        available = [it for it in items if it.get("数量", 0) > 0]
        item_lines = "\n".join(
            f"  {it.get('name')} x{it.get('数量', 0)}" for it in available
        ) or "  暂无物品"

        return LootingInspectResult(
            success=True,
            message=(
                f"【{place_name}】\n"
                f"戒备等级：{level_text}\n"
                f"营业状态：{state_text}\n"
                f"在售物品：\n{item_lines}"
            ),
        )

    async def start(
        self,
        user_id: str,
        place_name: str,
        now_ms: int | None = None,
    ) -> LootingStartResult:
        """开始洗劫。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return LootingStartResult(player_not_found=True)

        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)

        action = await self._get_action(user_id)
        if self._is_busy(action, now_ms):
            return LootingStartResult(
                reason=f"正在{action.get('action')}中，无法洗劫"
            )

        last_time = await self.state_service.get(self._cd_key(user_id), 0)
        if last_time:
            cd_end = int(last_time) + self.CD_MINUTES * 60 * 1000
            if now_ms < cd_end:
                remaining = cd_end - now_ms
                minutes = remaining // (60 * 1000)
                seconds = (remaining % (60 * 1000)) // 1000
                return LootingStartResult(
                    reason=f"每{self.CD_MINUTES}分钟洗劫一次，正在CD中，剩余{minutes}分{seconds}秒"
                )

        shop = self.shop_data.get(place_name)
        if shop is None:
            return LootingStartResult(reason="这方天地没有这个地方")

        if shop.get("state", 0) == 1:
            return LootingStartResult(reason=f"{place_name}已经戒备森严了，还是不要硬闯好了")

        # 特殊地点校验
        special_check = await self._check_special_place(player, place_name)
        if special_check:
            return LootingStartResult(reason=special_check)

        grade = shop.get("Grade", 1)
        price = shop.get("price", 0) * grade
        if player.get("spirit_stones", 0) < price:
            return LootingStartResult(reason="灵石不足，无法进行强化")

        player["spirit_stones"] = player.get("spirit_stones", 0) - price
        player["modao_value"] = player.get("modao_value", 0) + 25 * grade
        await self.player_service.save(user_id, player)

        buff = grade + 1
        attack = player.get("attack_bonus", 0) + player.get("level_id", 1) * 10
        defense = int(player.get("defense_bonus", 0) * buff)
        hp = int(player.get("hp_bonus", 0) + player.get("current_hp", 1) * buff)
        linggen = player.get("linggen") or {}
        magic_rate = linggen.get("法球倍率", 0) if isinstance(linggen, dict) else 0

        action_time = self.DURATION_MINUTES * 60 * 1000
        await self._set_action(
            user_id,
            {
                "action": "洗劫",
                "start_time": now_ms,
                "end_time": now_ms + action_time,
                "time": action_time,
                "place": place_name,
                "grade": grade,
                "A_player": {
                    "name": player.get("name", "无名"),
                    "attack": attack,
                    "defense": defense,
                    "hp": hp,
                    "crit_rate": 0.05,
                    "magic_rate": magic_rate,
                    "modao": player.get("modao_value", 0),
                },
            },
        )
        await self.state_service.set(self._cd_key(user_id), now_ms)

        # 标记商店被打烊
        shop["state"] = 1
        self.shop_data.save(self.shop_data.shops)

        defense_pct = int((buff - buff / (1 + grade * 0.05)) * 100)
        return LootingStartResult(
            success=True,
            message=(
                f"你消费了{price}灵石，防御力和生命值提高了{defense_pct}%\n"
                f"开始前往{place_name}，祝你好运！"
            ),
        )

    async def _check_special_place(self, player: dict[str, Any], place_name: str) -> str:
        if place_name == "逆道界":
            has = await self.inventory_service.has_item(
                player.get("id", ""), "道具", "逆道令", 1
            )
            if not has:
                return (
                    "逆道界的规则之力十分恐怖，会磨灭一切天地大道，"
                    "若没有逆道令的庇护，你此去定然十死无生，想到这里你放弃了前往洗劫这个念头。"
                )
            await self.inventory_service.remove_item(
                player.get("id", ""), "道具", "逆道令", 1
            )
        elif place_name == "终极古地":
            if player.get("mijing_level_id", 1) >= 20:
                return ""
            # 简化：需要三世铜棺且秘境等级>=18
            has = await self.inventory_service.has_item(
                player.get("id", ""), "道具", "三世铜棺", 1
            )
            if not has or player.get("mijing_level_id", 1) < 18:
                return (
                    "你意识到界海的浪潮非常汹涌，每一朵浪花都是残破的宇宙，"
                    "非真正的道祖无法横渡，如果想要横渡界海去往终极古地你需要仙道领域达到仙王的修为和三世铜棺。"
                )
        elif place_name == "万维梵宇":
            if player.get("level_id", 1) < 63:
                return "你并非永恒境强者，无法超脱维宙。"
        return ""

    async def settle(
        self,
        user_id: str,
        now_ms: int | None = None,
    ) -> LootingSettleResult:
        """结算洗劫（洗劫归来）。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return LootingSettleResult(player_not_found=True)

        action = await self._get_action(user_id)
        if not action or action.get("action") != "洗劫":
            return LootingSettleResult(no_action=True, reason="当前没有进行洗劫")

        now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
        if action.get("end_time", 0) > now_ms:
            remaining = action.get("end_time", now_ms) - now_ms
            minutes = remaining // (60 * 1000)
            seconds = (remaining % (60 * 1000)) // 1000
            return LootingSettleResult(
                reason=f"洗劫进行中，剩余{minutes}分{seconds}秒，请耐心等待"
            )

        place_name = action.get("place", "")
        grade = action.get("grade", 1)
        a_stats = action.get("A_player", {})

        shop = self.shop_data.get(place_name)

        # 生成守卫
        guard = self._spawn_guard(a_stats, grade)
        first_strike = a_stats.get("modao", 0) <= 999
        winner, messages = self._run_battle(a_stats, guard, first_strike)
        player_won = winner == "player"

        if player_won:
            messages.append(
                f"{a_stats.get('name', '无名')}经过一番战斗，击败对手，开始搜刮物品。"
            )
            items_looted = await self._loot_items(user_id, shop, grade)
            if items_looted:
                item_text = "\n".join(
                    f"  {it['name']} x{it['quantity']}" for it in items_looted
                )
                messages.append("你找到了：\n" + item_text)
            else:
                messages.append("经过一番搜寻，这里已经被搬空了。")

            if shop is not None:
                shop["state"] = 0
                self.shop_data.save(self.shop_data.shops)
            await self._set_action(user_id, None)
            return LootingSettleResult(
                success=True,
                won=True,
                message="\n".join(messages),
                items=items_looted,
            )

        # 失败：被抓进地牢
        keys = grade
        await self.inventory_service.add_item(user_id, "道具", "秘境之匙", keys)
        messages.append(
            f"经过一番战斗，败下阵来，被抓进了地牢\n在地牢中你找到了秘境之匙x{keys}"
        )
        if shop is not None:
            shop["state"] = 0
            self.shop_data.save(self.shop_data.shops)

        # 禁闭 60 分钟
        prison_time = 60 * 60 * 1000
        await self._set_action(
            user_id,
            {
                "action": "禁闭",
                "start_time": now_ms,
                "end_time": now_ms + prison_time,
                "time": prison_time,
            },
        )
        return LootingSettleResult(
            success=True,
            won=False,
            message="\n".join(messages),
        )

    async def _loot_items(
        self,
        user_id: str,
        shop: dict[str, Any] | None,
        grade: int,
    ) -> list[dict[str, Any]]:
        if shop is None:
            return []

        available = [
            it for it in shop.get("one", []) if it.get("数量", 0) > 0
        ]
        if not available:
            return []

        count = grade * 2
        looted: list[dict[str, Any]] = []
        for _ in range(count):
            if not available:
                break
            item = available[int(self.random_provider() * len(available))]
            if item not in [l["source"] for l in looted]:
                looted.append({
                    "name": item["name"],
                    "quantity": item.get("数量", 1),
                    "class": item.get("class", "道具"),
                    "source": item,
                })
            # 从商店中移除该物品
            for it in shop.get("one", []):
                if it.get("name") == item["name"] and it.get("数量", 0) > 0:
                    it["数量"] = 0
                    break
            available = [
                it for it in shop.get("one", []) if it.get("数量", 0) > 0
            ]

        for entry in looted:
            await self.inventory_service.add_item(
                user_id,
                entry["class"],
                entry["name"],
                entry["quantity"],
            )
        # 移除辅助字段
        for entry in looted:
            entry.pop("source", None)

        return looted

    def _spawn_guard(self, a_stats: dict[str, Any], grade: int) -> dict[str, Any]:
        """根据玩家属性和商店等级生成守卫。"""
        base_multipliers = {1: 0.5, 2: 0.8, 3: 1.2}
        mult = base_multipliers.get(grade, 0.5)
        return {
            "name": f"{grade}级守卫",
            "attack": int(a_stats.get("attack", 1) * mult),
            "defense": int(a_stats.get("defense", 0) * mult * 0.8),
            "hp": int(a_stats.get("hp", 1) * mult),
            "crit_rate": 0.05 + grade * 0.02,
            "magic_rate": a_stats.get("magic_rate", 0) * mult,
        }

    def _run_battle(
        self,
        a_stats: dict[str, Any],
        b_stats: dict[str, Any],
        a_first: bool,
    ) -> tuple[str, list[str]]:
        """简化回合制战斗，返回(胜利方, 战斗消息)。胜利方为 'player'、'guard' 或 'draw'。"""
        a = dict(a_stats)
        b = dict(b_stats)
        messages: list[str] = [
            f"【洗劫战斗】{a['name']} VS {b['name']}",
        ]

        def deal_damage(attacker: dict[str, Any], defender: dict[str, Any]) -> int:
            is_crit = self.random_provider() < attacker.get("crit_rate", 0)
            crit_mult = 2.0 if is_crit else 1.0
            base = max(
                1,
                int(attacker.get("attack", 1) * 0.85 - defender.get("defense", 0)),
            )
            damage = int(
                base * crit_mult + attacker.get("attack", 1) * attacker.get("magic_rate", 0)
            )
            damage = max(1, damage)
            defender["hp"] = max(0, defender["hp"] - damage)
            return damage

        for round_num in range(1, 51):
            first, second = (a, b) if a_first else (b, a)
            damage = deal_damage(first, second)
            messages.append(f"第{round_num}回合 {first['name']} 造成 {damage} 伤害")
            if second["hp"] <= 0:
                if second is b:
                    messages.append(f"{a['name']} 击败了 {b['name']}")
                    return "player", messages
                messages.append(f"{b['name']} 击败了 {a['name']}")
                return "guard", messages

            damage = deal_damage(second, first)
            messages.append(f"第{round_num}回合 {second['name']} 造成 {damage} 伤害")
            if first["hp"] <= 0:
                if first is b:
                    messages.append(f"{a['name']} 击败了 {b['name']}")
                    return "player", messages
                messages.append(f"{b['name']} 击败了 {a['name']}")
                return "guard", messages

        messages.append("战斗胶着，双方同时收手，判为平局")
        return "draw", messages

    async def reset(
        self,
        place_name: str,
        user_id: str,
        master_ids: set[str],
    ) -> LootingResetResult:
        """管理员重置商店状态。"""
        if user_id not in master_ids:
            return LootingResetResult(reason="只有主人可以重置商店状态")

        shop = self.shop_data.get(place_name)
        if shop is None:
            return LootingResetResult(reason="这方天地没有这个地方")

        shop["state"] = 0
        self.shop_data.save(self.shop_data.shops)
        return LootingResetResult(success=True, message=f"{place_name}重置成功！")
