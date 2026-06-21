import random
import time
from dataclasses import dataclass

from src.data.level_data import LevelData
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class YuanshenStatusResult:
    """元神状态查询结果。"""

    player_not_found: bool = False
    not_condensed: bool = False
    name: str = ""
    yuanshen: int = 0
    yuanshen_limit: int = 0
    level_id: int | None = None
    level_name: str = "未凝练"
    shenshi: int = 0
    neijingdi: int = 0


@dataclass
class CondenseResult:
    """凝练元神结果。"""

    player_not_found: bool = False
    not_started: bool = False
    insufficient_yuanshen: bool = False
    insufficient_mijing: bool = False
    insufficient_xiangu: bool = False
    success: bool = False
    level_id: int | None = None
    level_name: str = ""
    cost: int = 0
    required_yuanshen: int = 0
    required_mijing_level: int = 0
    required_xiangu_level: int = 0


@dataclass
class NeijingOpenResult:
    """开启内景地结果。"""

    player_not_found: bool = False
    not_condensed: bool = False
    already_open: bool = False
    insufficient_yuanshen: bool = False
    high_level_block: bool = False
    success: bool = False
    cost: int = 0
    probability: float = 0.0


@dataclass
class NeijingEnterResult:
    """进入内景地结果。"""

    player_not_found: bool = False
    not_open: bool = False
    high_level_block: bool = False
    success: bool = False
    exp_gained: int = 0
    blood_qi_gained: int = 0
    shenshi_gained: int = 0
    daoshang_reduced: float = 0.0


@dataclass
class NeijingBatchResult:
    """批量内景地修炼结果。"""

    player_not_found: bool = False
    not_condensed: bool = False
    high_level_block: bool = False
    planned: int = 0
    executed: int = 0
    success: int = 0
    failed: int = 0
    total_cost: int = 0
    messages: list[str] | None = None


@dataclass
class CultivateWithGongfaResult:
    """以功法修炼元神结果。"""

    player_not_found: bool = False
    not_condensed: bool = False
    not_learned: bool = False
    unknown_gongfa: bool = False
    limit_abnormal: bool = False
    in_cooldown: bool = False
    cooldown_remaining_minutes: int = 0
    success: bool = False
    gongfa_name: str = ""
    yuanshen_gained: int = 0
    current_yuanshen: int = 0
    yuanshen_limit: int = 0


class YuanshenService:
    """元神体系服务：凝练元神、开启/进入内景地、批量修炼。"""

    BASE_NINGLIAN_COST = 15_000_000
    NEIJING_OPEN_BASE_COST = 15_000_000
    NEIJING_REWARD_BASE = 500_000
    HIGH_LEVEL_BLOCK_THRESHOLD = 19

    # 可用于修炼元神的功法：cd 单位分钟，ratio 为上限恢复比例
    YUANSHEN_SKILLS = {
        "前字秘": {"cd": 240, "ratio": 0.10},
        "涅槃法门·残缺": {"cd": 360, "ratio": 0.01},
    }

    def __init__(
        self,
        player_service: PlayerService,
        level_data: LevelData,
        state_service: StateService | None = None,
    ):
        self.player_service = player_service
        self.level_data = level_data
        self.state_service = state_service

    async def get_status(self, user_id: str) -> YuanshenStatusResult:
        """查询玩家元神状态。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return YuanshenStatusResult(player_not_found=True)

        level_id = player.get("yuanshenlevel_id")
        if level_id is None:
            return YuanshenStatusResult(
                name=player.get("name", "无名"),
                yuanshen=int(player.get("yuanshen", 0)),
                yuanshen_limit=int(player.get("yuanshen_limit", 0)),
                not_condensed=True,
                shenshi=int(player.get("shenshi", 0)),
                neijingdi=int(player.get("neijingdi", 0)),
            )

        return YuanshenStatusResult(
            name=player.get("name", "无名"),
            yuanshen=int(player.get("yuanshen", 0)),
            yuanshen_limit=int(player.get("yuanshen_limit", 0)),
            level_id=int(level_id),
            level_name=self.level_data.get_yuanshen_name(int(level_id)),
            shenshi=int(player.get("shenshi", 0)),
            neijingdi=int(player.get("neijingdi", 0)),
        )

    async def condense(self, user_id: str) -> CondenseResult:
        """凝练/升级元神。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return CondenseResult(player_not_found=True)

        level_id = player.get("yuanshenlevel_id")
        ninglian_count = int(player.get("ninglian_count", 1))
        cost = self.BASE_NINGLIAN_COST * ninglian_count

        yuanshen = int(player.get("yuanshen", 0))
        if yuanshen < cost:
            return CondenseResult(
                not_started=level_id is None,
                insufficient_yuanshen=True,
                required_yuanshen=cost,
            )

        mijing_level = int(player.get("mijing_level_id", 1))
        xiangu_level = int(player.get("xiangu_level_id", 1))

        if level_id is None:
            # 首次凝练
            player["yuanshen"] = yuanshen - cost
            player["ninglian_count"] = ninglian_count + 1
            player["yuanshenlevel_id"] = 0
            await self.player_service.save(user_id, player)
            return CondenseResult(
                success=True,
                level_id=0,
                level_name=self.level_data.get_yuanshen_name(0),
                cost=cost,
            )

        level_id = int(level_id)
        # 继续凝练需要秘境/仙古达到一定等级
        if mijing_level > 1 or xiangu_level > 1:
            required_mijing = 10 + level_id
            required_xiangu = 8 + level_id
            if mijing_level > 1 and mijing_level < required_mijing:
                return CondenseResult(
                    insufficient_mijing=True,
                    required_mijing_level=required_mijing,
                )
            if xiangu_level > 1 and xiangu_level < required_xiangu:
                return CondenseResult(
                    insufficient_xiangu=True,
                    required_xiangu_level=required_xiangu,
                )

        player["yuanshen"] = yuanshen - cost
        player["ninglian_count"] = ninglian_count + 1
        player["yuanshenlevel_id"] = level_id + 1
        await self.player_service.save(user_id, player)

        return CondenseResult(
            success=True,
            level_id=level_id + 1,
            level_name=self.level_data.get_yuanshen_name(level_id + 1),
            cost=cost,
        )

    async def open_neijing(self, user_id: str) -> NeijingOpenResult:
        """开启内景地（概率）。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return NeijingOpenResult(player_not_found=True)

        level_id = player.get("yuanshenlevel_id")
        if level_id is None:
            return NeijingOpenResult(not_condensed=True)

        mijing_level = int(player.get("mijing_level_id", 1))
        xiangu_level = int(player.get("xiangu_level_id", 1))
        if mijing_level > self.HIGH_LEVEL_BLOCK_THRESHOLD or xiangu_level > self.HIGH_LEVEL_BLOCK_THRESHOLD:
            return NeijingOpenResult(high_level_block=True)

        if int(player.get("neijingdi", 0)) == 1:
            return NeijingOpenResult(already_open=True)

        cost = self.NEIJING_OPEN_BASE_COST * (mijing_level + xiangu_level)
        yuanshen = int(player.get("yuanshen", 0))
        if yuanshen < cost:
            return NeijingOpenResult(insufficient_yuanshen=True, cost=cost)

        probability = 0.1 + int(level_id) * 0.1
        success = random.random() <= probability

        player["yuanshen"] = yuanshen - cost
        if success:
            player["neijingdi"] = 1
        await self.player_service.save(user_id, player)

        return NeijingOpenResult(
            success=success,
            cost=cost,
            probability=probability,
        )

    async def enter_neijing(self, user_id: str) -> NeijingEnterResult:
        """进入内景地领取奖励。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return NeijingEnterResult(player_not_found=True)

        mijing_level = int(player.get("mijing_level_id", 1))
        xiangu_level = int(player.get("xiangu_level_id", 1))
        if mijing_level > self.HIGH_LEVEL_BLOCK_THRESHOLD or xiangu_level > self.HIGH_LEVEL_BLOCK_THRESHOLD:
            return NeijingEnterResult(high_level_block=True)

        if int(player.get("neijingdi", 0)) != 1:
            return NeijingEnterResult(not_open=True)

        reward = self.NEIJING_REWARD_BASE
        physique_id = int(player.get("physique_id", 1))
        level_id = int(player.get("level_id", 1))
        zuizhong = (mijing_level + xiangu_level) * level_id * physique_id * reward
        daoshang_reduce = 0.1 * (mijing_level + xiangu_level)

        player["exp"] = int(player.get("exp", 0)) + zuizhong
        player["blood_qi"] = int(player.get("blood_qi", 0)) + zuizhong
        player["shenshi"] = int(player.get("shenshi", 0)) + zuizhong
        player["daoshang"] = max(0.0, float(player.get("daoshang", 0)) - daoshang_reduce)
        player["neijingdi"] = 0
        await self.player_service.save(user_id, player)

        return NeijingEnterResult(
            success=True,
            exp_gained=zuizhong,
            blood_qi_gained=zuizhong,
            shenshi_gained=zuizhong,
            daoshang_reduced=daoshang_reduce,
        )

    async def neijing_batch(self, user_id: str, times: int) -> NeijingBatchResult:
        """批量开启并进入内景地。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return NeijingBatchResult(player_not_found=True)

        if player.get("yuanshenlevel_id") is None:
            return NeijingBatchResult(not_condensed=True)

        mijing_level = int(player.get("mijing_level_id", 1))
        xiangu_level = int(player.get("xiangu_level_id", 1))
        if mijing_level > self.HIGH_LEVEL_BLOCK_THRESHOLD or xiangu_level > self.HIGH_LEVEL_BLOCK_THRESHOLD:
            return NeijingBatchResult(high_level_block=True)

        times = max(1, min(times, 50))
        level_id = int(player.get("yuanshenlevel_id", 0))
        probability = 0.1 + level_id * 0.1
        reward = self.NEIJING_REWARD_BASE
        physique_id = int(player.get("physique_id", 1))
        cultivation_level = int(player.get("level_id", 1))

        messages: list[str] = []
        success = 0
        failed = 0
        total_cost = 0
        executed = 0

        for i in range(times):
            cost = self.NEIJING_OPEN_BASE_COST * (mijing_level + xiangu_level)
            yuanshen = int(player.get("yuanshen", 0))
            if yuanshen < cost:
                messages.append(
                    f"【中止】第{i + 1}次：元神不足（需{cost}，仅剩{yuanshen}）"
                )
                messages.append(f"剩余未执行：{times - i} 次")
                break

            executed += 1
            player["yuanshen"] = yuanshen - cost
            total_cost += cost

            if random.random() <= probability:
                success += 1
                zuizhong = (mijing_level + xiangu_level) * cultivation_level * physique_id * reward
                daoshang_reduce = 0.1 * (mijing_level + xiangu_level)
                player["exp"] = int(player.get("exp", 0)) + zuizhong
                player["blood_qi"] = int(player.get("blood_qi", 0)) + zuizhong
                player["shenshi"] = int(player.get("shenshi", 0)) + zuizhong
                player["daoshang"] = max(0.0, float(player.get("daoshang", 0)) - daoshang_reduce)
                messages.append(
                    f"第{i + 1}次：开启成功，已进入内景地，获得修为/血气/神识 +{zuizhong}，道伤 -{daoshang_reduce:.1f}"
                )
            else:
                failed += 1
                messages.append(f"第{i + 1}次：开启失败，损失元神 {cost}")

        player["neijingdi"] = 0
        await self.player_service.save(user_id, player)

        return NeijingBatchResult(
            planned=times,
            executed=executed,
            success=success,
            failed=failed,
            total_cost=total_cost,
            messages=messages,
        )

    async def cultivate_with_gongfa(
        self, user_id: str, gongfa_name: str
    ) -> CultivateWithGongfaResult:
        """以指定功法修炼元神，恢复元神强度。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return CultivateWithGongfaResult(player_not_found=True)

        if player.get("yuanshenlevel_id") is None:
            return CultivateWithGongfaResult(not_condensed=True)

        cfg = self.YUANSHEN_SKILLS.get(gongfa_name)
        if cfg is None:
            return CultivateWithGongfaResult(unknown_gongfa=True, gongfa_name=gongfa_name)

        learned = player.get("learned_gongfa", [])
        if gongfa_name not in learned:
            return CultivateWithGongfaResult(
                not_learned=True, gongfa_name=gongfa_name
            )

        limit = int(player.get("yuanshen_limit", 0))
        if limit <= 0:
            return CultivateWithGongfaResult(
                limit_abnormal=True, gongfa_name=gongfa_name
            )

        if self.state_service is not None:
            cd_key = f"xiulian_yuanshen_{gongfa_name}_{user_id}"
            last = await self.state_service.get(cd_key)
            now_ms = int(time.time() * 1000)
            cd_ms = cfg["cd"] * 60 * 1000
            if last is not None and now_ms - int(last) < cd_ms:
                remain_ms = cd_ms - (now_ms - int(last))
                return CultivateWithGongfaResult(
                    in_cooldown=True,
                    gongfa_name=gongfa_name,
                    cooldown_remaining_minutes=max(1, remain_ms // 60000),
                )

        yuanshen = int(player.get("yuanshen", 0))
        add = max(1, int(limit * cfg["ratio"]))
        player["yuanshen"] = yuanshen + add

        if self.state_service is not None:
            cd_key = f"xiulian_yuanshen_{gongfa_name}_{user_id}"
            await self.state_service.set(cd_key, int(time.time() * 1000))

        await self.player_service.save(user_id, player)

        return CultivateWithGongfaResult(
            success=True,
            gongfa_name=gongfa_name,
            yuanshen_gained=add,
            current_yuanshen=player["yuanshen"],
            yuanshen_limit=limit,
        )
