import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.services.battle_service import BattleService
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@dataclass
class CreateResult:
    """开启团本结果。"""

    success: bool = False
    reason: str = ""
    boss_name: str = ""
    max_hp: int = 0


@dataclass
class JoinResult:
    """加入团本结果。"""

    success: bool = False
    reason: str = ""
    boss_name: str = ""
    members: list[str] = field(default_factory=list)


@dataclass
class LeaveResult:
    """退出团本结果。"""

    success: bool = False
    reason: str = ""
    boss_name: str = ""


@dataclass
class AttackResult:
    """攻击团本 BOSS 结果。"""

    success: bool = False
    reason: str = ""
    damage: int = 0
    boss_killed: bool = False
    hp_remaining: int = 0
    messages: list[str] = field(default_factory=list)


@dataclass
class StatusResult:
    """团本状态查询结果。"""

    success: bool = False
    reason: str = ""
    boss_name: str = ""
    hp: int = 0
    max_hp: int = 0
    members: list[dict[str, Any]] = field(default_factory=list)
    ranking: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SettleResult:
    """团本结算结果。"""

    success: bool = False
    reason: str = ""
    rewards: list[str] = field(default_factory=list)


class TeamBossService:
    """组队 BOSS（团本）服务。"""

    MAX_MEMBERS = 5

    def __init__(
        self,
        player_service: PlayerService,
        inventory_service: InventoryService,
        data_dir: Path,
        battle_service: BattleService | None = None,
    ):
        self.player_service = player_service
        self.inventory_service = inventory_service
        self.battle_service = battle_service
        self.data_dir = data_dir
        self.team_boss_dir = data_dir / "team_boss"
        self.team_boss_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.team_boss_dir / "team_boss.json"

    def _load_data(self) -> dict[str, Any]:
        if not self.data_file.exists():
            return {}
        return json.loads(self.data_file.read_text(encoding="utf-8"))

    def _save_data(self, data: dict[str, Any]) -> None:
        self.data_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _player_power(self, player: dict[str, Any]) -> int:
        """计算玩家战力（用于伤害随机）。"""
        return int(
            player.get("attack_bonus", 0)
            + player.get("defense_bonus", 0)
            + player.get("hp_bonus", 0)
            + player.get("level_id", 1) * 10000
        )

    def _build_ranking(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        damage_map = data.get("damage", {})
        names = data.get("names", {})
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

    async def create_boss(self, user_id: str, name: str) -> CreateResult:
        """开启一个新的团本，创建者即为团长。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return CreateResult(success=False, reason="道友尚未踏入仙途")

        data = self._load_data()
        if data.get("boss") is not None:
            return CreateResult(success=False, reason="当前已有开启的团本")

        if not name:
            return CreateResult(success=False, reason="团本名称不能为空")

        power = self._player_power(player)
        max_hp = max(100000, power * 10)
        attack = max(1000, power // 5)
        defense = max(500, power // 10)

        boss = {
            "id": 1,
            "name": name,
            "hp": max_hp,
            "max_hp": max_hp,
            "attack": attack,
            "defense": defense,
            "owner_id": user_id,
            "members": [user_id],
            "created_at": time.time(),
            "settled": False,
        }
        data["boss"] = boss
        data["damage"] = {}
        data["names"] = {}
        self._save_data(data)

        return CreateResult(success=True, boss_name=name, max_hp=max_hp)

    async def join(self, user_id: str) -> JoinResult:
        """加入当前开启的团本。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return JoinResult(success=False, reason="道友尚未踏入仙途")

        data = self._load_data()
        boss = data.get("boss")
        if boss is None:
            return JoinResult(success=False, reason="当前没有开启的团本")

        if boss.get("settled"):
            return JoinResult(success=False, reason="团本已结算")

        members: list[str] = boss.get("members", [])
        if user_id in members:
            return JoinResult(
                success=False,
                reason="你已经加入了该团本",
                boss_name=boss["name"],
                members=members,
            )

        if len(members) >= self.MAX_MEMBERS:
            return JoinResult(
                success=False,
                reason="团本成员已满",
                boss_name=boss["name"],
                members=members,
            )

        members.append(user_id)
        boss["members"] = members
        self._save_data(data)

        return JoinResult(success=True, boss_name=boss["name"], members=members)

    async def leave(self, user_id: str) -> LeaveResult:
        """退出当前团本；团长退出则将团长转移给下一成员。"""
        data = self._load_data()
        boss = data.get("boss")
        if boss is None:
            return LeaveResult(success=False, reason="当前没有开启的团本")

        members: list[str] = boss.get("members", [])
        if user_id not in members:
            return LeaveResult(success=False, reason="你未加入该团本")

        members.remove(user_id)
        if not members:
            self._save_data({})
            return LeaveResult(
                success=True,
                reason="团本已关闭",
                boss_name=boss["name"],
            )

        if boss.get("owner_id") == user_id:
            boss["owner_id"] = members[0]

        boss["members"] = members
        self._save_data(data)

        return LeaveResult(success=True, boss_name=boss["name"])

    async def attack(self, user_id: str) -> AttackResult:
        """对团本 BOSS 造成伤害。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return AttackResult(success=False, reason="道友尚未踏入仙途")

        data = self._load_data()
        boss = data.get("boss")
        if boss is None:
            return AttackResult(success=False, reason="当前没有开启的团本")

        if boss.get("settled"):
            return AttackResult(success=False, reason="团本已结算")

        members: list[str] = boss.get("members", [])
        if user_id not in members:
            return AttackResult(success=False, reason="你未加入该团本")

        if boss.get("hp", 0) <= 0:
            return AttackResult(
                success=False, reason="BOSS已被击败，请结算奖励"
            )

        if self.battle_service is not None:
            stats = self.battle_service.compute_battle_stats(player)
            if stats["current_hp"] < stats["hp_max"] * 0.1:
                return AttackResult(
                    success=False, reason="还是先疗伤吧，别急着参战了"
                )

        power = self._player_power(player)
        damage = int(power * (0.8 + 0.4 * random.random()))
        damage = max(1, damage)

        boss["hp"] = max(0, boss["hp"] - damage)
        boss_killed = boss["hp"] <= 0

        damage_map = data.setdefault("damage", {})
        damage_map[user_id] = damage_map.get(user_id, 0) + damage

        names = data.setdefault("names", {})
        names[user_id] = player.get("name", "无名")

        self._save_data(data)

        player_name = player.get("name", "无名")
        messages = [f"{player_name} 对 {boss['name']} 造成 {damage} 点伤害"]
        if boss_killed:
            messages.append(f"{boss['name']} 被击败了！")

        return AttackResult(
            success=True,
            damage=damage,
            boss_killed=boss_killed,
            hp_remaining=boss["hp"],
            messages=messages,
        )

    async def status(self) -> StatusResult:
        """查看团本 BOSS 状态与伤害排行。"""
        data = self._load_data()
        boss = data.get("boss")
        if boss is None:
            return StatusResult(success=False, reason="当前没有开启的团本")

        members: list[dict[str, Any]] = []
        for uid in boss.get("members", []):
            player = await self.player_service.load(uid)
            name = player.get("name", "无名") if player else "无名"
            power = self._player_power(player) if player else 0
            members.append(
                {
                    "user_id": uid,
                    "name": name,
                    "power": power,
                    "is_owner": uid == boss.get("owner_id"),
                }
            )

        ranking = self._build_ranking(data)

        return StatusResult(
            success=True,
            boss_name=boss["name"],
            hp=boss.get("hp", 0),
            max_hp=boss.get("max_hp", 0),
            members=members,
            ranking=ranking,
        )

    async def settle(self, user_id: str) -> SettleResult:
        """结算团本奖励，仅团长可在 BOSS 被击败后执行。"""
        data = self._load_data()
        boss = data.get("boss")
        if boss is None:
            return SettleResult(success=False, reason="当前没有开启的团本")

        if boss.get("owner_id") != user_id:
            return SettleResult(success=False, reason="只有团长可以结算团本")

        if boss.get("hp", 0) > 0:
            return SettleResult(success=False, reason="BOSS还未被击败")

        if boss.get("settled"):
            return SettleResult(success=False, reason="团本已结算")

        damage_map = data.get("damage", {})
        names = data.get("names", {})
        total_damage = max(1, sum(damage_map.values()))

        max_hp = boss.get("max_hp", 0)
        reward_stones = max(10000, max_hp // 10)
        reward_exp = max(1000, max_hp // 100)
        reward_blood = max(100, max_hp // 200)

        rewards: list[str] = []
        sorted_players = sorted(
            damage_map.items(), key=lambda x: x[1], reverse=True
        )
        for rank, (uid, dmg) in enumerate(sorted_players, start=1):
            share_stones = max(1, int(dmg / total_damage * reward_stones))
            share_exp = max(1, int(dmg / total_damage * reward_exp))
            share_blood = max(1, int(dmg / total_damage * reward_blood))

            await self.player_service.add_spirit_stones(uid, share_stones)
            await self.player_service.add_exp(uid, share_exp)
            await self.player_service.add_blood_qi(uid, share_blood)

            name = names.get(uid, "无名")
            rewards.append(
                f"第{rank}名 {name} 伤害{dmg}，获得灵石{share_stones}、"
                f"经验{share_exp}、血气{share_blood}"
            )

            if rank == 1:
                await self.inventory_service.add_item(uid, "道具", "团本宝箱", 1)
                rewards.append(f"{name} 输出第一，额外获得团本宝箱")

        boss["settled"] = True
        self._save_data(data)

        return SettleResult(success=True, rewards=rewards)

    async def close_boss(self) -> SettleResult:
        """强制关闭当前团本（用于管理命令）。"""
        self._save_data({})
        return SettleResult(success=True, rewards=["团本已关闭"])
