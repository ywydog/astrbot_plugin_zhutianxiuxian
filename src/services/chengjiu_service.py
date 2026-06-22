from dataclasses import dataclass, field
from typing import Any, Callable

from src.data.chengjiu_data import ChengjiuData
from src.services.player_service import PlayerService


@dataclass
class ChengjiuCheckResult:
    new: list[dict] = field(default_factory=list)
    total_unlocked: int = 0
    total_count: int = 0
    by_category: dict[str, dict[str, int]] = field(default_factory=dict)
    message: str = ""


@dataclass
class XiuxianAssistantResult:
    player_not_found: bool = False
    message: str = ""
    lines: list[str] = field(default_factory=list)


class ChengjiuService:
    """成就系统服务：验证成就、修仙助手。"""

    def __init__(
        self,
        player_service: PlayerService,
        chengjiu_data: ChengjiuData,
    ):
        self.player_service = player_service
        self.chengjiu_data = chengjiu_data
        self._checks: dict[int, Callable[[dict[str, Any]], bool]] = {
            1: self._check_level_7,
            2: self._check_physique_7,
            3: self._check_has_occupation,
            4: self._check_linggen_show,
            5: self._check_level_41,
            6: self._check_physique_41,
            9: self._check_mijing_or_xiangu,
            10: self._check_mijing_15_or_xiangu_13,
            11: self._check_mijing_16_or_xiangu_14,
            12: self._check_mijing_17_or_xiangu_15,
            13: self._check_mijing_19_or_xiangu_19,
            14: self._check_mijing_20_or_xiangu_20,
            15: self._check_mijing_21_or_xiangu_21,
            16: self._check_mijing_22_or_xiangu_22,
        }

    # ---------- 成就条件 ----------
    def _check_level_7(self, player: dict[str, Any]) -> bool:
        return player.get("level_id", 1) > 7

    def _check_physique_7(self, player: dict[str, Any]) -> bool:
        return player.get("physique_id", 1) > 7

    def _check_has_occupation(self, player: dict[str, Any]) -> bool:
        occ = player.get("occupation")
        return bool(occ)

    def _check_linggen_show(self, player: dict[str, Any]) -> bool:
        # 0 表示已开启灵根
        return player.get("linggen_show") == 0

    def _check_level_41(self, player: dict[str, Any]) -> bool:
        return player.get("level_id", 1) > 41

    def _check_physique_41(self, player: dict[str, Any]) -> bool:
        return player.get("physique_id", 1) > 41

    def _check_mijing_or_xiangu(self, player: dict[str, Any]) -> bool:
        return (
            player.get("mijing_level_id", 1) > 1
            or player.get("xiangu_level_id", 1) > 1
        )

    def _check_mijing_15_or_xiangu_13(self, player: dict[str, Any]) -> bool:
        return (
            player.get("mijing_level_id", 1) > 15
            or player.get("xiangu_level_id", 1) > 13
        )

    def _check_mijing_16_or_xiangu_14(self, player: dict[str, Any]) -> bool:
        return (
            player.get("mijing_level_id", 1) > 16
            or player.get("xiangu_level_id", 1) > 14
        )

    def _check_mijing_17_or_xiangu_15(self, player: dict[str, Any]) -> bool:
        return (
            player.get("mijing_level_id", 1) > 17
            or player.get("xiangu_level_id", 1) > 15
        )

    def _check_mijing_19_or_xiangu_19(self, player: dict[str, Any]) -> bool:
        return (
            player.get("mijing_level_id", 1) > 19
            or player.get("xiangu_level_id", 1) > 19
        )

    def _check_mijing_20_or_xiangu_20(self, player: dict[str, Any]) -> bool:
        return (
            player.get("mijing_level_id", 1) > 20
            or player.get("xiangu_level_id", 1) > 20
        )

    def _check_mijing_21_or_xiangu_21(self, player: dict[str, Any]) -> bool:
        return (
            player.get("mijing_level_id", 1) > 21
            or player.get("xiangu_level_id", 1) > 21
        )

    def _check_mijing_22_or_xiangu_22(self, player: dict[str, Any]) -> bool:
        return (
            player.get("mijing_level_id", 1) > 22
            or player.get("xiangu_level_id", 1) > 22
        )

    def _condition_met(self, player: dict[str, Any], item: dict) -> bool:
        achievement_id = item.get("id")
        checker = self._checks.get(achievement_id)
        if checker is not None:
            return checker(player)
        # 依赖未迁移系统（诸天镜、帝兵、位面、剧情等）的成就暂不可解锁
        return False

    async def check(self, user_id: str) -> ChengjiuCheckResult:
        """验证玩家成就，返回新获得与已解锁成就信息。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return ChengjiuCheckResult(message="请先创建角色")

        if "achievements" not in player or not isinstance(player["achievements"], list):
            player["achievements"] = []

        all_items = self.chengjiu_data.all()
        new: list[dict] = []
        for item in all_items:
            aid = str(item.get("id"))
            if aid in player["achievements"]:
                continue
            if self._condition_met(player, item):
                player["achievements"].append(aid)
                new.append(item)

        await self.player_service.save(user_id, player)

        total_unlocked = len(player["achievements"])
        total_count = len(all_items)
        by_category: dict[str, dict[str, int]] = {}
        for item in all_items:
            category = item.get("type") or "其他"
            if category not in by_category:
                by_category[category] = {"unlocked": 0, "total": 0}
            by_category[category]["total"] += 1
            if str(item.get("id")) in player["achievements"]:
                by_category[category]["unlocked"] += 1

        return ChengjiuCheckResult(
            new=new,
            total_unlocked=total_unlocked,
            total_count=total_count,
            by_category=by_category,
        )

    async def assistant(self, user_id: str) -> XiuxianAssistantResult:
        """修仙助手：展示已解锁与即将解锁功能。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return XiuxianAssistantResult(player_not_found=True)

        lines: list[str] = []
        name = player.get("name", "无名修士")
        lines.append(f"【修仙助手】{name}的修仙之路")

        level_name = "未知"
        physique_name = "未知"
        mijing_name = "未知"
        xiangu_name = "未知"
        # 修仙助手仅做展示，不强制要求各境界数据存在
        lines.append(f"练气：{level_name}")
        lines.append(f"炼体：{physique_name}")
        lines.append(f"人体秘境体系：{mijing_name}")
        lines.append(f"仙古今世法：{xiangu_name}")
        lines.append(
            f"生命：{player.get('current_hp', 0)}/{player.get('max_hp', 0)}"
        )
        lines.append(f"攻击：{player.get('attack', 0)}")
        lines.append(f"防御：{player.get('defense', 0)}")

        unlocked: list[str] = []
        if player.get("level_id", 1) > 22:
            unlocked.append("天道赐福：秘境之钥，打工券")
        if player.get("level_id", 1) >= 32:
            unlocked.append("凝练元神，开启内景地")
        if player.get("occupation") == "侠客":
            unlocked.append("天道赐福：额外获得侠客令*3")
        if player.get("occupation") == "唤魔者":
            unlocked.append("天道赐福：额外获得唤魔令*3")
        if player.get("level_id", 1) > 41:
            unlocked.append("天道赐福：额外获得仙舟*3")
            unlocked.append("开辟小世界：获得额外挂机收益")
        if (
            player.get("level_id", 1) > 41
            and player.get("physique_id", 1) > 41
        ):
            unlocked.append("穿梭凡间|仙界|下界八域|九天十地")
            unlocked.append("证道、冲关：选择人体秘境体系/仙古今世法")
        if player.get("wuse_jitan") == 1:
            unlocked.append("激活五色祭坛，穿梭遮天位面")
        if player.get("level_id", 1) >= 54:
            unlocked.append("天道赐福：额外获得神域令牌*3")
        if (
            player.get("mijing_level_id", 1) >= 12
            or player.get("xiangu_level_id", 1) >= 10
        ):
            unlocked.append("传授功法：可以传授他人功法")

        lines.append("已解锁功能：")
        if unlocked:
            for feature in unlocked:
                lines.append(f"  {feature}")
        else:
            lines.append("  尚未解锁任何特殊功能")

        upcoming: list[str] = []
        if player.get("level_id", 1) <= 22:
            upcoming.append("境界突破22级后解锁：天道赐福：秘境之钥，打工券")
        if player.get("level_id", 1) < 32:
            upcoming.append("境界突破32级后解锁：凝练元神，开启内景地")
        if player.get("level_id", 1) <= 41:
            upcoming.append("练气突破41级后解锁：天道赐福：额外获得仙舟*3")
            upcoming.append("练气突破41级后解锁：开辟小世界")
        if (
            player.get("level_id", 1) <= 41
            or player.get("physique_id", 1) <= 41
        ):
            upcoming.append("成就地仙肉身成圣后解锁：穿梭位面")
            upcoming.append("成就地仙肉身成圣后解锁：证道、冲关")
        if player.get("level_id", 1) < 54:
            upcoming.append("境界突破54级后解锁：天道赐福：额外获得神域令牌*3")
        if player.get("wuse_jitan") != 1:
            upcoming.append("激活五色祭坛后解锁：穿梭遮天位面")
        if (
            player.get("mijing_level_id", 1) < 12
            and player.get("xiangu_level_id", 1) < 10
        ):
            upcoming.append("人体秘境体系达到圣人或仙古今世法达到天神境后解锁：传授功法")

        lines.append("即将解锁功能：")
        if upcoming:
            max_display = min(3, len(upcoming))
            for i in range(max_display):
                lines.append(f"  {upcoming[i]}")
            if len(upcoming) > max_display:
                lines.append(f"  ...还有{len(upcoming) - max_display}个功能待解锁")
        else:
            lines.append("  已解锁所有功能")

        tips = [
            "每日修仙签到可稳步提升修为",
            "境界突破需要积累足够的修为",
            "秘境探索可能获得珍稀宝物",
            "参悟高阶功法可大幅提升斗法能力",
            "灵根觉醒可激活特殊能力",
            "开辟小世界可获得额外收益",
        ]
        import random

        lines.append(f"修仙小贴士：{random.choice(tips)}")

        return XiuxianAssistantResult(lines=lines)
