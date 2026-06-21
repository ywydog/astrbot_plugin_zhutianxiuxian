import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.data.boss_data import BossData
from src.services.battle_service import BattleService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class BossInitResult:
    success: bool = False
    reason: str = ""
    health: int = 0
    reward: int = 0


@dataclass
class BossChallengeResult:
    success: bool = False
    reason: str = ""
    damage: int = 0
    boss_killed: bool = False
    messages: list[str] = field(default_factory=list)
    player_id: str = ""


@dataclass
class BossCloseResult:
    success: bool = False
    reason: str = ""


class BossService:
    """世界 BOSS（妖王）系统。"""

    BOSS_STATUS_KEY = "xiuxian_world_boss_status"
    BOSS_RECORDS_KEY = "xiuxian_world_boss_records"
    BOSS_CD_KEY = "xiuxian_player_{}_boss_cd"

    def __init__(
        self,
        battle_service: BattleService,
        player_service: PlayerService,
        state_service: StateService,
        boss_data: BossData | None = None,
        data_dir: Path | None = None,
    ):
        self.battle_service = battle_service
        self.player_service = player_service
        self.state_service = state_service
        self.boss_data = boss_data or BossData(data_dir or Path("."))
        self.data_dir = data_dir

    async def _load_status(self) -> dict[str, Any] | None:
        return await self.state_service.get(self.BOSS_STATUS_KEY)

    async def _save_status(self, status: dict[str, Any]) -> None:
        await self.state_service.set(self.BOSS_STATUS_KEY, status)

    async def _load_records(self) -> dict[str, Any]:
        records = await self.state_service.get(self.BOSS_RECORDS_KEY)
        if records is None:
            return {"damage": {}, "names": {}}
        return records

    async def _save_records(self, records: dict[str, Any]) -> None:
        await self.state_service.set(self.BOSS_RECORDS_KEY, records)

    async def _scan_qualified_players(self) -> list[dict[str, Any]]:
        """扫描达到境界要求的玩家。"""
        players: list[dict[str, Any]] = []
        players_dir = self.player_service.players_dir
        if not players_dir.exists():
            return players
        for file_path in players_dir.glob("*.json"):
            user_id = file_path.stem
            player = await self.player_service.load(user_id)
            if player and player.get("level_id", 1) >= self.boss_data.qualified_level():
                players.append(player)
        return players

    async def _calculate_average_attack(self, players: list[dict[str, Any]]) -> int:
        if not players:
            return 0
        attacks = []
        for player in players:
            stats = self.battle_service.compute_battle_stats(player)
            attacks.append(stats["attack"])
        attacks.sort(reverse=True)
        max_samples = self.boss_data.get("max_attack_samples", 15)
        top_skip = self.boss_data.get("top_attack_skip", 2)
        bottom_skip = self.boss_data.get("bottom_attack_skip", 4)
        if len(attacks) > max_samples:
            valid = attacks[top_skip:-bottom_skip]
        else:
            valid = attacks
        return int(sum(valid) / len(valid)) if valid else 0

    async def initialize_boss(self) -> BossInitResult:
        """根据达标玩家数量与平均攻击生成妖王。"""
        players = await self._scan_qualified_players()
        if len(players) < self.boss_data.min_players():
            return BossInitResult(success=False, reason="没有符合条件的玩家，妖王开启失败")

        average_attack = await self._calculate_average_attack(players)
        player_quantity = len(players)
        reward = (
            self.boss_data.min_reward()
            if player_quantity < 5
            else self.boss_data.base_reward()
        )
        x = average_attack * 0.01
        health_multiplier = self.boss_data.get("health_multiplier", 200)
        health = int(x * 150 * player_quantity * health_multiplier)

        status = {
            "health": health,
            "max_health": health,
            "killed_time": -1,
            "reward": reward,
        }
        await self._save_status(status)
        await self._save_records({"damage": {}, "names": {}})
        return BossInitResult(success=True, health=health, reward=reward)

    async def get_status(self) -> dict[str, Any]:
        status = await self._load_status()
        if status is None:
            return {"alive": False}
        alive = status.get("killed_time", -1) == -1 and status.get("health", 0) > 0
        return {
            "alive": alive,
            "health": status.get("health", 0),
            "max_health": status.get("max_health", 0),
            "reward": status.get("reward", 0),
            "killed_time": status.get("killed_time", -1),
        }

    async def close_boss(self) -> BossCloseResult:
        await self.state_service.delete(self.BOSS_STATUS_KEY)
        await self.state_service.delete(self.BOSS_RECORDS_KEY)
        return BossCloseResult(success=True)

    async def _check_cd(self, user_id: str, now: float) -> tuple[bool, int]:
        cd_key = self.BOSS_CD_KEY.format(user_id)
        last_challenge = await self.state_service.get(cd_key, 0)
        remaining = int(last_challenge + self.boss_data.cd_seconds() - now)
        if now < last_challenge + self.boss_data.cd_seconds():
            return True, remaining
        return False, 0

    async def challenge(
        self, user_id: str, now: float | None = None
    ) -> BossChallengeResult:
        import time

        now = now if now is not None else time.time()
        status = await self._load_status()
        if status is None:
            return BossChallengeResult(success=False, reason="妖王未开启")

        if status.get("killed_time", -1) != -1 or status.get("health", 0) <= 0:
            return BossChallengeResult(success=False, reason="妖王已被击杀或正在刷新")

        player = await self.player_service.load(user_id)
        if player is None:
            return BossChallengeResult(success=False, reason="道友尚未踏入仙途")

        if player.get("level_id", 1) < self.boss_data.qualified_level():
            return BossChallengeResult(success=False, reason="你在仙界吗？境界不足无法参与")

        stats = self.battle_service.compute_battle_stats(player)
        if stats["current_hp"] < stats["hp_max"] * 0.1:
            return BossChallengeResult(success=False, reason="还是先疗伤吧，别急着参战了")

        in_cd, remaining = await self._check_cd(user_id, now)
        if in_cd:
            return BossChallengeResult(
                success=False,
                reason=f"正在CD中，剩余 {remaining // 60} 分 {remaining % 60} 秒",
            )

        # 生成妖王幻影
        phantom_name = self.boss_data.phantom_name()
        boss_phantom = {
            "name": phantom_name,
            "attack": int(stats["attack"] * (0.8 + 0.6 * random.random())),
            "defense": int(stats["defense"] * (0.8 + 0.6 * random.random())),
            "current_hp": int(stats["hp_max"] * (0.8 + 0.6 * random.random())),
            "hp_max": int(stats["hp_max"] * (0.8 + 0.6 * random.random())),
            "crit_rate": stats["crit_rate"],
            "magic_rate": stats["magic_rate"],
            "level_id": 99,
            "linggen": player.get("linggen", {}),
        }

        battle = await self.battle_service.run_battle(player, boss_phantom)
        player_name = player.get("name", "无名")
        messages = battle.messages[:]
        max_health = status.get("max_health", 1)
        player_stats = self.battle_service.compute_battle_stats(player)
        base_harm = max(1, int(player_stats["attack"] * 0.85 - boss_phantom["defense"]))

        player_won = battle.winner == player_name
        if player_won:
            damage = int(max_health * 0.05 + base_harm * 6)
            messages.append(f"{player_name} 击败了【{phantom_name}】，重创妖王，造成伤害 {damage}")
        else:
            damage = int(max_health * 0.03 + base_harm * 4)
            messages.append(f"{player_name} 被【{phantom_name}】击败，只对妖王造成 {damage} 伤害")

        damage = max(1, damage)
        status["health"] = max(0, status["health"] - damage)
        boss_killed = status["health"] <= 0

        # 记录伤害
        records = await self._load_records()
        records["damage"][user_id] = records["damage"].get(user_id, 0) + damage
        records["names"][user_id] = player_name
        await self._save_records(records)
        await self._save_status(status)
        await self.state_service.set(self.BOSS_CD_KEY.format(user_id), now)

        # 应用玩家血量变化
        player["current_hp"] = max(1, player.get("current_hp", 0) + battle.a_hp_change)
        await self.player_service.save(user_id, player)

        if boss_killed:
            status["killed_time"] = now
            await self._save_status(status)
            messages.append("妖王被击杀！玩家们可以根据贡献获得奖励！")
            await self._distribute_rewards(status, records, messages, user_id)

        return BossChallengeResult(
            success=True,
            damage=damage,
            boss_killed=boss_killed,
            messages=messages,
            player_id=user_id,
        )

    async def _distribute_rewards(
        self,
        status: dict[str, Any],
        records: dict[str, Any],
        messages: list[str],
        killer_id: str,
    ) -> None:
        """根据贡献分配奖励。"""
        reward_pool = status.get("reward", 0)
        damage_map = records.get("damage", {})
        names = records.get("names", {})
        if not damage_map:
            return

        total_damage = sum(damage_map.values())
        killer_bonus = self.boss_data.killer_bonus()
        min_share = self.boss_data.min_damage_share()
        rank_limit = self.boss_data.reward_rank_limit()

        # 击杀者额外奖励
        killer = await self.player_service.load(killer_id)
        if killer:
            killer["spirit_stones"] = killer.get("spirit_stones", 0) + killer_bonus
            await self.player_service.save(killer_id, killer)
            messages.append(
                f"{killer.get('name', '无名')} 亲手结果了妖王，额外获得 {killer_bonus} 灵石"
            )

        sorted_players = sorted(
            damage_map.items(), key=lambda x: x[1], reverse=True
        )
        for rank, (uid, dmg) in enumerate(sorted_players, start=1):
            player = await self.player_service.load(uid)
            if player is None:
                continue
            if rank <= rank_limit:
                share = int(dmg / total_damage * reward_pool) if total_damage else 0
                share = max(min_share, share)
            else:
                share = min_share
            player["spirit_stones"] = player.get("spirit_stones", 0) + share
            await self.player_service.save(uid, player)
            messages.append(
                f"第 {rank} 名 {names.get(uid, '无名')} 伤害 {dmg}，获得 {share} 灵石"
            )

    async def get_damage_list(self) -> list[dict[str, Any]]:
        records = await self._load_records()
        damage_map = records.get("damage", {})
        names = records.get("names", {})
        sorted_items = sorted(damage_map.items(), key=lambda x: x[1], reverse=True)
        return [
            {
                "rank": i,
                "user_id": uid,
                "name": names.get(uid, "无名"),
                "damage": dmg,
            }
            for i, (uid, dmg) in enumerate(sorted_items, start=1)
        ]
