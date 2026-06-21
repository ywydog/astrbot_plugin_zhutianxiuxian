import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.data.level_data import LevelData
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class BattleResult:
    """单次战斗结算结果。"""

    winner: str | None = None
    loser: str | None = None
    messages: list[str] = field(default_factory=list)
    a_hp_change: int = 0
    b_hp_change: int = 0
    draw: bool = False


@dataclass
class RobResult:
    """打劫指令结果。"""

    success: bool = False
    reason: str = ""
    attacker_won: bool = False
    messages: list[str] = field(default_factory=list)
    attacker_id: str = ""
    defender_id: str = ""


@dataclass
class DuelResult:
    """比武指令结果。"""

    success: bool = False
    reason: str = ""
    winner: str | None = None
    loser: str | None = None
    messages: list[str] = field(default_factory=list)
    attacker_id: str = ""
    defender_id: str = ""


class BattleService:
    """处理玩家间战斗/PVP。"""

    MAX_ROUNDS = 50
    ROB_CD_SECONDS = 600  # 打劫冷却 10 分钟
    DUEL_CD_SECONDS = 1800  # 比武冷却 30 分钟
    IMMORTAL_LEVEL = 41
    BULLY_THRESHOLD = 12

    def __init__(
        self,
        player_service: PlayerService,
        level_data: LevelData,
        state_service: StateService,
        data_dir: Path | None = None,
    ):
        self.player_service = player_service
        self.level_data = level_data
        self.state_service = state_service
        self.data_dir = data_dir

    def compute_battle_stats(self, player: dict[str, Any]) -> dict[str, Any]:
        """根据玩家境界与加成计算战斗属性。"""
        level_id = player.get("level_id", 1)
        base = self.level_data.get_cultivation_stats(level_id)
        attack = int(base["attack"] + player.get("attack_bonus", 0))
        defense = int(base["defense"] + player.get("defense_bonus", 0))
        hp_max = int(base["hp"] + player.get("hp_bonus", 0))
        current_hp = int(player.get("current_hp", hp_max))
        crit_rate = float(base["crit_rate"])
        linggen = player.get("linggen") or {}
        magic_rate = float(linggen.get("法球倍率", 0)) if isinstance(linggen, dict) else 0.0
        return {
            "name": player.get("name", "无名"),
            "attack": attack,
            "defense": defense,
            "hp_max": hp_max,
            "current_hp": current_hp,
            "crit_rate": crit_rate,
            "magic_rate": magic_rate,
            "level_id": level_id,
        }

    async def run_battle(
        self, a_player_raw: dict[str, Any], b_player_raw: dict[str, Any]
    ) -> BattleResult:
        """执行一场 A 先手、B 后手的简化回合制战斗。"""
        a_stats = self.compute_battle_stats(a_player_raw)
        b_stats = self.compute_battle_stats(b_player_raw)
        messages: list[str] = [
            f"【战斗开始】{a_stats['name']} VS {b_stats['name']}",
        ]
        initial_a_hp = a_stats["current_hp"]
        initial_b_hp = b_stats["current_hp"]

        def deal_damage(attacker: dict[str, Any], defender: dict[str, Any]) -> tuple[int, bool]:
            is_critical = random.random() < attacker["crit_rate"]
            crit_multiplier = 2.0 if is_critical else 1.0
            base_damage = max(1, int(attacker["attack"] * 0.85 - defender["defense"]))
            damage = int(base_damage * crit_multiplier + attacker["attack"] * attacker["magic_rate"])
            damage = max(1, damage)
            defender["current_hp"] = max(0, defender["current_hp"] - damage)
            return damage, is_critical

        a = dict(a_stats)
        b = dict(b_stats)
        winner_name = None
        loser_name = None
        draw = False

        for round_num in range(1, self.MAX_ROUNDS + 1):
            damage, crit = deal_damage(a, b)
            crit_text = "（暴击）" if crit else ""
            messages.append(f"第{round_num}回合 {a['name']} 攻击造成 {damage} 伤害{crit_text}")
            if b["current_hp"] <= 0:
                winner_name = a["name"]
                loser_name = b["name"]
                messages.append(f"{a['name']} 击败了 {b['name']}")
                break

            damage, crit = deal_damage(b, a)
            crit_text = "（暴击）" if crit else ""
            messages.append(f"第{round_num}回合 {b['name']} 反击造成 {damage} 伤害{crit_text}")
            if a["current_hp"] <= 0:
                winner_name = b["name"]
                loser_name = a["name"]
                messages.append(f"{b['name']} 击败了 {a['name']}")
                break
        else:
            draw = True
            messages.append("战斗胶着，双方同时收手，判为平局")

        return BattleResult(
            winner=winner_name,
            loser=loser_name,
            messages=messages,
            a_hp_change=a["current_hp"] - initial_a_hp,
            b_hp_change=b["current_hp"] - initial_b_hp,
            draw=draw,
        )

    async def rob(
        self, attacker_id: str, defender_id: str, now: float | None = None
    ) -> RobResult:
        """打劫逻辑。"""
        import time

        now = now if now is not None else time.time()
        attacker = await self.player_service.load(attacker_id)
        defender = await self.player_service.load(defender_id)
        if attacker is None:
            return RobResult(success=False, reason="道友尚未踏入仙途")
        if defender is None:
            return RobResult(success=False, reason="对方尚未踏入仙途")
        if attacker_id == defender_id:
            return RobResult(success=False, reason="咋的，自己弄自己啊？")

        a_level = attacker.get("level_id", 1)
        d_level = defender.get("level_id", 1)
        if a_level > self.IMMORTAL_LEVEL and d_level <= self.IMMORTAL_LEVEL:
            return RobResult(success=False, reason="仙人不可对凡人出手")
        if a_level >= self.BULLY_THRESHOLD and d_level < self.BULLY_THRESHOLD:
            return RobResult(success=False, reason="不可欺负弱小")

        cd_key = f"xiuxian_player_{attacker_id}_last_rob_time"
        last_rob = await self.state_service.get(cd_key, 0)
        if now < last_rob + self.ROB_CD_SECONDS:
            remaining = int(last_rob + self.ROB_CD_SECONDS - now)
            return RobResult(
                success=False,
                reason=f"打劫正在CD中，剩余 {remaining // 60} 分 {remaining % 60} 秒",
            )

        if defender.get("current_hp", 0) < 20000:
            return RobResult(success=False, reason="对方重伤未愈，就不要再打他了")
        if defender.get("spirit_stones", 0) < 30002:
            return RobResult(success=False, reason="对方穷得叮当响，就不要再打他了")

        battle = await self.run_battle(attacker, defender)
        attacker_won = battle.winner == attacker.get("name")
        messages = battle.messages[:]

        # 应用血量变化
        attacker["current_hp"] = max(1, attacker.get("current_hp", 0) + battle.a_hp_change)
        defender["current_hp"] = max(0, defender.get("current_hp", 0) + battle.b_hp_change)

        if attacker_won:
            stolen = int(defender.get("spirit_stones", 0) * 0.2)
            defender["spirit_stones"] = max(0, defender.get("spirit_stones", 0) - stolen)
            attacker["spirit_stones"] = attacker.get("spirit_stones", 0) + stolen
            attacker["modao_value"] = attacker.get("modao_value", 0) + 1
            messages.append(f"{attacker['name']} 洗劫了 {defender['name']} 的 {stolen} 灵石")
        else:
            messages.append(f"{attacker['name']} 打劫失败，悻悻离去")

        await self.player_service.save(attacker_id, attacker)
        await self.player_service.save(defender_id, defender)
        await self.state_service.set(cd_key, now)

        return RobResult(
            success=True,
            attacker_won=attacker_won,
            messages=messages,
            attacker_id=attacker_id,
            defender_id=defender_id,
        )

    async def duel(
        self, attacker_id: str, defender_id: str, now: float | None = None
    ) -> DuelResult:
        """比武逻辑。"""
        import time

        now = now if now is not None else time.time()
        attacker = await self.player_service.load(attacker_id)
        defender = await self.player_service.load(defender_id)
        if attacker is None:
            return DuelResult(success=False, reason="道友尚未踏入仙途")
        if defender is None:
            return DuelResult(success=False, reason="对方尚未踏入仙途")
        if attacker_id == defender_id:
            return DuelResult(success=False, reason="咋的，自娱自乐？")

        a_stats = self.compute_battle_stats(attacker)
        d_stats = self.compute_battle_stats(defender)
        if a_stats["current_hp"] < a_stats["hp_max"] / 1.2:
            return DuelResult(success=False, reason="你血量未满，对方不想趁人之危")
        if d_stats["current_hp"] < d_stats["hp_max"] / 1.2:
            return DuelResult(success=False, reason="对方血量未满，不能趁人之危")

        for pid in (attacker_id, defender_id):
            cd_key = f"xiuxian_player_{pid}_last_duel_time"
            last_duel = await self.state_service.get(cd_key, 0)
            if now < last_duel + self.DUEL_CD_SECONDS:
                remaining = int(last_duel + self.DUEL_CD_SECONDS - now)
                label = "你" if pid == attacker_id else "对方"
                return DuelResult(
                    success=False,
                    reason=f"{label}比武冷却中，剩余 {remaining // 60} 分 {remaining % 60} 秒",
                )

        battle = await self.run_battle(attacker, defender)
        attacker["current_hp"] = max(1, attacker.get("current_hp", 0) + battle.a_hp_change)
        defender["current_hp"] = max(1, defender.get("current_hp", 0) + battle.b_hp_change)

        a_level = attacker.get("level_id", 1)
        d_level = defender.get("level_id", 1)
        winner_name = battle.winner
        if winner_name == attacker.get("name"):
            attacker["blood_qi"] = attacker.get("blood_qi", 0) + 1000 * d_level
            defender["blood_qi"] = defender.get("blood_qi", 0) + 500 * a_level
            attacker["spirit_stones"] = attacker.get("spirit_stones", 0) + 10 * a_level
            defender["spirit_stones"] = defender.get("spirit_stones", 0) + 10 * a_level
        elif winner_name == defender.get("name"):
            attacker["blood_qi"] = attacker.get("blood_qi", 0) + 500 * d_level
            defender["blood_qi"] = defender.get("blood_qi", 0) + 1000 * a_level
            attacker["spirit_stones"] = attacker.get("spirit_stones", 0) + 10 * a_level
            defender["spirit_stones"] = defender.get("spirit_stones", 0) + 10 * a_level
        else:
            attacker["blood_qi"] = attacker.get("blood_qi", 0) + 200 * d_level
            defender["blood_qi"] = defender.get("blood_qi", 0) + 200 * a_level

        await self.player_service.save(attacker_id, attacker)
        await self.player_service.save(defender_id, defender)
        for pid in (attacker_id, defender_id):
            await self.state_service.set(f"xiuxian_player_{pid}_last_duel_time", now)

        return DuelResult(
            success=True,
            winner=winner_name,
            loser=battle.loser,
            messages=battle.messages,
            attacker_id=attacker_id,
            defender_id=defender_id,
        )
