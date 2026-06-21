from dataclasses import dataclass, field
from typing import Any

from src.data.linggen_data import LinggenData
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class LinggenInfoResult:
    player_not_found: bool = False
    linggen: dict[str, Any] = field(default_factory=dict)


@dataclass
class AwakenResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""
    new_linggen: dict[str, Any] = field(default_factory=dict)


@dataclass
class ElysiaPromptResult:
    player_not_found: bool = False
    reason: str = ""
    prompt: str = ""


@dataclass
class ElysiaChoiceResult:
    success: bool = False
    player_not_found: bool = False
    reason: str = ""
    message: str = ""
    need_count_input: bool = False
    new_linggen: dict[str, Any] = field(default_factory=dict)


class LinggenService:
    """灵根觉醒服务：处理爱莉希雅、流萤、圣体、霸体、妖体等觉醒线。"""

    def __init__(
        self,
        player_service: PlayerService,
        inventory_service: InventoryService,
        state_service: StateService,
        linggen_data: LinggenData,
    ):
        self.player_service = player_service
        self.inventory_service = inventory_service
        self.state_service = state_service
        self.linggen_data = linggen_data

    # ---------- 基础工具 ----------

    def _pending_key(self, user_id: str) -> str:
        return f"xiuxian:player:{user_id}:linggen_choice"

    def _get_linggen(self, player: dict[str, Any]) -> dict[str, Any]:
        return player.get("linggen", {})

    def _set_linggen(self, player: dict[str, Any], linggen: dict[str, Any]) -> None:
        player["linggen"] = linggen
        player["cultivation_efficiency"] = linggen.get("eff", 1.0)

    def _is_life_source_full(self, player: dict[str, Any]) -> bool:
        linggen = self._get_linggen(player)
        expected = 100 + linggen.get("生命本源", 0)
        return player.get("life_source", 100) >= expected

    async def _ensure_saint_completion(self, user_id: str, player: dict[str, Any]) -> None:
        if "圣体秘境完成度" not in player:
            player["圣体秘境完成度"] = {
                "轮海": 0,
                "道宫": 0,
                "四极": 0,
                "化龙": 0,
            }
            await self.player_service.save(user_id, player)

    # ---------- 灵根信息 ----------

    async def get_info(self, user_id: str) -> LinggenInfoResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return LinggenInfoResult(player_not_found=True)
        return LinggenInfoResult(linggen=self._get_linggen(player))

    # ---------- 往世乐土（爱莉希雅）多轮流程 ----------

    async def start_elysia_ritual(self, user_id: str) -> ElysiaPromptResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ElysiaPromptResult(player_not_found=True)

        has = await self.inventory_service.has_item(user_id, "道具", "往世乐土之章", 1)
        if not has:
            return ElysiaPromptResult(reason='你尚未获得"往世乐土之章"，无法开启仪式。')

        await self.state_service.set(
            self._pending_key(user_id),
            {"step": "choice"},
        )

        prompt = (
            "诸天万界忽而响起水晶轻鸣，一座被岁月尘封的「往世乐土」在星空中绽放。\n"
            "十三道刻印环绕成环，终末的英桀之座于花海中显形。\n"
            "无瑕的少女踏花而来，微笑询问：\n"
            "「嗨，想和我一起，让这个世界……变成你喜欢的样子吗？」\n"
            "\n"
            "【往世乐土】已激活！\n"
            "请选择你的回应——\n"
            "1. 「我愿意献此身灵根，化作无瑕之人。」（覆盖灵根）\n"
            "2. 「我愿与你并肩，而非取代。」（消耗往世乐土之章，召唤次数+1/个）\n"
            "（30 秒内回复 1 或 2）"
        )
        return ElysiaPromptResult(prompt=prompt)

    async def handle_elysia_choice(
        self, user_id: str, choice: str
    ) -> ElysiaChoiceResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ElysiaChoiceResult(player_not_found=True)

        pending = await self.state_service.get(self._pending_key(user_id), None)
        if pending is None or pending.get("step") != "choice":
            return ElysiaChoiceResult(reason="选择无效，乐土之门已闭合。")

        if choice == "1":
            return await self._elysia_overwrite(user_id, player)
        if choice == "2":
            count = await self.inventory_service.get_count(user_id, "道具", "往世乐土之章")
            if count <= 0:
                await self.state_service.delete(self._pending_key(user_id))
                return ElysiaChoiceResult(reason='你没有可消耗的"往世乐土之章"。')
            await self.state_service.set(
                self._pending_key(user_id),
                {"step": "count", "max_count": count},
            )
            return ElysiaChoiceResult(
                need_count_input=True,
                message=f"你选择与爱莉希雅并肩作战。\n当前拥有往世乐土之章×{count}。\n请输入要消耗的数量（1~{count}）：",
            )

        await self.state_service.delete(self._pending_key(user_id))
        return ElysiaChoiceResult(reason="选择无效，已超时。乐土之门悄然闭合……")

    async def _elysia_overwrite(
        self, user_id: str, player: dict[str, Any]
    ) -> ElysiaChoiceResult:
        path = self.linggen_data.get_path("elysia")
        if path is None:
            await self.state_service.delete(self._pending_key(user_id))
            return ElysiaChoiceResult(reason="灵根数据缺失。")

        materials = path.get("overwrite_materials", {})
        for name, need in materials.items():
            has = await self.inventory_service.get_count(user_id, "道具", name)
            if has < need:
                await self.state_service.delete(self._pending_key(user_id))
                return ElysiaChoiceResult(
                    reason=f"【无瑕之人】材料不足！\n{name}×{need}（{has}/{need}）"
                )

        # 扣除材料
        await self.inventory_service.remove_item(
            user_id, "道具", path["awaken_item"], 1
        )
        for name, need in materials.items():
            await self.inventory_service.remove_item(user_id, "道具", name, need)

        new_linggen = self._build_linggen(path)
        self._set_linggen(player, new_linggen)
        player["life_source"] = 100 + new_linggen.get("生命本源", 0)
        await self.player_service.save(user_id, player)
        await self.state_service.delete(self._pending_key(user_id))

        return ElysiaChoiceResult(
            success=True,
            message="灵根已变更为：无瑕之人·爱莉希雅",
            new_linggen=new_linggen,
        )

    async def handle_elysia_count(
        self, user_id: str, count: int
    ) -> ElysiaChoiceResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return ElysiaChoiceResult(player_not_found=True)

        pending = await self.state_service.get(self._pending_key(user_id), None)
        if pending is None or pending.get("step") != "count":
            return ElysiaChoiceResult(reason="输入无效，乐土之门已闭合。")

        max_count = pending.get("max_count", 0)
        if count < 1 or count > max_count:
            return ElysiaChoiceResult(
                reason=f"输入无效，请输入1~{max_count}之间的整数。"
            )

        await self.inventory_service.remove_item(
            user_id, "道具", "往世乐土之章", count
        )
        player["爱莉希雅召唤次数"] = player.get("爱莉希雅召唤次数", 0) + count
        await self.player_service.save(user_id, player)
        await self.state_service.delete(self._pending_key(user_id))

        return ElysiaChoiceResult(
            success=True,
            message=f"消耗往世乐土之章×{count}，爱莉希雅召唤次数 +{count}",
        )

    # ---------- 真我觉醒 ----------

    async def awaken_zhenwo(self, user_id: str) -> AwakenResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return AwakenResult(player_not_found=True)

        linggen = self._get_linggen(player)
        if linggen.get("name") not in ["爱莉希雅", "人之律者·爱莉希雅"]:
            return AwakenResult(reason="只有无瑕之人·爱莉希雅才能开启真我觉醒")

        if not self._is_life_source_full(player):
            return AwakenResult(reason="生命本源亏空，无法承载真我权柄")

        if linggen.get("type") == "无瑕之人":
            path = self.linggen_data.get_path("zhenwo_ren")
        elif linggen.get("type") == "真我·人之律者":
            path = self.linggen_data.get_path("zhenwo_shiyuan")
        else:
            return AwakenResult(reason="当前状态无法觉醒")

        return await self._awaken_with_materials(user_id, player, path)

    # ---------- 流萤觉醒 ----------

    async def awaken_liuying(self, user_id: str) -> AwakenResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return AwakenResult(player_not_found=True)

        linggen = self._get_linggen(player)
        if linggen.get("name") != "少女流萤":
            return AwakenResult(reason="只有少女流萤灵根才能开启流萤觉醒")

        if not self._is_life_source_full(player):
            return AwakenResult(reason="生命本源亏空，无法承受觉醒仪式")

        if linggen.get("type") != "星铁":
            return AwakenResult(reason="当前状态无法觉醒")

        path = self.linggen_data.get_path("liuying_xiaocheng")
        return await self._awaken_with_materials(user_id, player, path)

    # ---------- 圣体觉醒 ----------

    async def awaken_shengti(self, user_id: str) -> AwakenResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return AwakenResult(player_not_found=True)

        linggen = self._get_linggen(player)
        linggen_type = linggen.get("type", "")

        await self._ensure_saint_completion(user_id, player)
        player = await self.player_service.load(user_id)
        completion = player.get("圣体秘境完成度", {})
        values = list(completion.values())

        if linggen_type == "圣体" and player.get("mijing_level_id", 1) > 6:
            path = self.linggen_data.get_path("shengti_xiaocheng")
            reached = sum(1 for v in values if v >= path["realm_completion"]["threshold"])
            if reached < path["realm_completion"]["min_realms"]:
                return AwakenResult(
                    reason="圣体觉醒条件不足！需至少将两大秘境修炼至50%以上方可小成。"
                )
            return await self._apply_awakening(user_id, player, path)

        if linggen_type == "小成圣体" and player.get("mijing_level_id", 1) > 14:
            path = self.linggen_data.get_path("shengti_dacheng")
            if not all(v >= path["realm_completion"]["threshold"] for v in values):
                return AwakenResult(
                    reason="大成圣体觉醒条件不足！需将四大秘境全部修炼至100%圆满境界。"
                )
            return await self._apply_awakening(user_id, player, path)

        if linggen_type not in ("圣体", "小成圣体"):
            return AwakenResult(reason="血脉不符！非圣体一脉，无法觉醒圣体之威。")

        return AwakenResult(reason="觉醒条件不足！需达到更高境界且完成秘境修炼。")

    # ---------- 霸体觉醒 ----------

    async def awaken_bati(self, user_id: str) -> AwakenResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return AwakenResult(player_not_found=True)

        linggen = self._get_linggen(player)
        linggen_type = linggen.get("type", "")

        if linggen_type == "霸体" and player.get("mijing_level_id", 1) > 6:
            path = self.linggen_data.get_path("bati_xiaocheng")
            return await self._awaken_with_materials(user_id, player, path)

        if linggen_type == "小成霸体" and player.get("mijing_level_id", 1) > 14:
            path = self.linggen_data.get_path("bati_dacheng")
            learned = player.get("learned_gongfa", [])
            required = path.get("required_gongfa", [])
            if not all(g in learned for g in required):
                return AwakenResult(reason="需修炼霸拳真解方可大成。")
            if not player.get(path.get("required_flag", ""), False):
                return AwakenResult(reason="需前往霸体祖星接受祖池洗礼方可大成。")
            return await self._apply_awakening(user_id, player, path)

        if linggen_type not in ("霸体", "小成霸体"):
            return AwakenResult(reason="血脉不符！非霸体一脉，无法觉醒霸体之威。")

        return AwakenResult(reason="觉醒条件不足！需达到更高境界。")

    # ---------- 妖体觉醒 ----------

    async def awaken_yaoti(self, user_id: str) -> AwakenResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return AwakenResult(player_not_found=True)

        linggen = self._get_linggen(player)
        linggen_type = linggen.get("type", "")

        if linggen_type == "妖体" and player.get("mijing_level_id", 1) > 6:
            path = self.linggen_data.get_path("yaoti_xiaocheng")
            return await self._awaken_with_materials(user_id, player, path)

        if linggen_type == "小成妖体" and player.get("mijing_level_id", 1) > 14:
            path = self.linggen_data.get_path("yaoti_dacheng")
            learned = player.get("learned_gongfa", [])
            required = path.get("required_gongfa", [])
            if not all(g in learned for g in required):
                return AwakenResult(reason="需领悟妖帝古经方可大成。")
            return await self._apply_awakening(user_id, player, path)

        if linggen_type not in ("妖体", "小成妖体"):
            return AwakenResult(reason="血脉不符！非妖体一脉，无法觉醒妖皇之威。")

        return AwakenResult(reason="觉醒条件不足！需达到更高境界。")

    # ---------- 通用觉醒流程 ----------

    async def _awaken_with_materials(
        self,
        user_id: str,
        player: dict[str, Any],
        path: dict[str, Any] | None,
    ) -> AwakenResult:
        if path is None:
            return AwakenResult(reason="灵根数据缺失。")

        # 境界检查
        if player.get("mijing_level_id", 1) < path.get("min_mijing_level", 1):
            return AwakenResult(reason="秘境等级不足，无法承载觉醒之力。")

        # 材料检查
        materials = path.get("materials", {})
        for name, need in materials.items():
            has = await self.inventory_service.get_count(user_id, "道具", name)
            if has < need:
                return AwakenResult(reason=f"觉醒需要 {need} 个【{name}】，当前 {has}")

        # 扣除材料
        for name, need in materials.items():
            await self.inventory_service.remove_item(user_id, "道具", name, need)

        return await self._apply_awakening(user_id, player, path)

    async def _apply_awakening(
        self,
        user_id: str,
        player: dict[str, Any],
        path: dict[str, Any],
    ) -> AwakenResult:
        new_linggen = self._build_linggen(path)
        self._set_linggen(player, new_linggen)
        player["life_source"] = 100 + new_linggen.get("生命本源", 0)
        await self.player_service.save(user_id, player)

        return AwakenResult(
            success=True,
            message=f"觉醒成功，灵根已变更为【{new_linggen.get('name')}】",
            new_linggen=new_linggen,
        )

    def _build_linggen(self, path: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": path.get("id", 0),
            "name": path["name"],
            "type": path["type"],
            "归类": path.get("category", ""),
            "eff": path.get("eff", 1.0),
            "法球倍率": path.get("法球倍率", 1.0),
            "攻击": path.get("攻击", 0),
            "防御": path.get("防御", 0),
            "生命": path.get("生命", 0),
            "生命本源": path.get("生命本源", 0),
            "特殊效果": path.get("特殊效果", []),
        }
