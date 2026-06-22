import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.services.battle_service import BattleService
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@dataclass
class TiandibangResult:
    """天地榜操作结果。"""

    success: bool = False
    message: str = ""
    lines: list[str] = field(default_factory=list)
    player_not_found: bool = False
    not_registered: bool = False
    no_challenges: bool = False


@dataclass
class TiandibangRankingItem:
    """天地榜条目。"""

    user_id: str
    name: str
    level_id: int
    attack: int
    defense: int
    hp: int
    crit_rate: float
    magic_rate: float
    learned_gongfa: list[str]
    score: int = 0
    challenges_left: int = 3
    last_challenge_date: str = ""


class TiandibangService:
    """天地榜竞技场服务：报名、比试、积分、兑换与结算。"""

    DATA_FILE = "tiandibang/tiandibang.json"
    DAILY_CHALLENGES = 3
    REWARD_SPIRIT_STONES = [17_500_000, 13_000_000, 9_200_000]
    REWARD_BOXES = [5, 3, 1]

    def __init__(
        self,
        player_service: PlayerService,
        battle_service: BattleService,
        inventory_service: InventoryService,
        state_service: StateService,
        data_dir: Path,
        item_catalog=None,
    ):
        self.player_service = player_service
        self.battle_service = battle_service
        self.inventory_service = inventory_service
        self.state_service = state_service
        self.data_dir = data_dir
        self.item_catalog = item_catalog
        self._file_path = data_dir / self.DATA_FILE
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict[str, Any]]:
        if not self._file_path.exists():
            return []
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _save(self, data: list[dict[str, Any]]) -> None:
        self._file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _build_entry(self, user_id: str, player: dict[str, Any]) -> dict[str, Any]:
        stats = self.battle_service.compute_battle_stats(player)
        linggen = player.get("linggen") or {}
        return {
            "user_id": user_id,
            "name": player.get("name", "无名"),
            "level_id": player.get("level_id", 1),
            "attack": stats["attack"],
            "defense": stats["defense"],
            "hp": stats["hp_max"],
            "crit_rate": stats["crit_rate"],
            "magic_rate": stats["magic_rate"],
            "learned_gongfa": list(player.get("learned_gongfa", [])),
            "score": 0,
            "challenges_left": self.DAILY_CHALLENGES,
            "last_challenge_date": self._today(),
        }

    def _find_index(self, data: list[dict[str, Any]], user_id: str) -> int:
        for i, item in enumerate(data):
            if item.get("user_id") == user_id:
                return i
        return -1

    async def register(self, user_id: str) -> TiandibangResult:
        """报名参加天地榜。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return TiandibangResult(player_not_found=True)

        data = self._load()
        if self._find_index(data, user_id) != -1:
            return TiandibangResult(message="你已经报名天地榜了！")

        data.append(self._build_entry(user_id, player))
        self._save(data)
        return TiandibangResult(success=True, message="参赛成功！")

    async def update_attributes(self, user_id: str) -> TiandibangResult:
        """更新天地榜中的属性快照。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return TiandibangResult(player_not_found=True)

        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return TiandibangResult(not_registered=True, message="请先报名天地榜！")

        entry = self._build_entry(user_id, player)
        entry["score"] = data[idx].get("score", 0)
        entry["challenges_left"] = data[idx].get("challenges_left", self.DAILY_CHALLENGES)
        entry["last_challenge_date"] = data[idx].get("last_challenge_date", "")
        data[idx] = entry
        self._save(data)

        lines = [
            f"名次：{idx + 1}",
            f"名号：{entry['name']}",
            f"攻击：{entry['attack']}",
            f"防御：{entry['defense']}",
            f"血量：{entry['hp']}",
            f"暴击：{entry['crit_rate'] * 100:.0f}%",
            f"积分：{entry['score']}",
        ]
        return TiandibangResult(success=True, lines=lines)

    async def _ensure_daily_reset(self, entry: dict[str, Any]) -> bool:
        """如果需要则重置每日次数，返回是否进行了重置。"""
        today = self._today()
        if entry.get("last_challenge_date") != today:
            entry["challenges_left"] = self.DAILY_CHALLENGES
            entry["last_challenge_date"] = today
            return True
        return False

    async def _use_zhaibangling(self, user_id: str) -> bool:
        """尝试自动使用一枚摘榜令。"""
        if self.inventory_service is None:
            return False
        result = await self.inventory_service.remove_item(
            user_id, "道具", "摘榜令", 1
        )
        return result.success

    async def challenge(self, user_id: str) -> TiandibangResult:
        """比试：挑战前一名玩家。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return TiandibangResult(player_not_found=True)

        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return TiandibangResult(not_registered=True, message="请先报名天地榜！")

        entry = data[idx]
        await self._ensure_daily_reset(entry)

        if entry.get("challenges_left", 0) < 1:
            if await self._use_zhaibangling(user_id):
                entry["challenges_left"] = 1
            else:
                return TiandibangResult(
                    no_challenges=True, message="今日挑战次数已用完，且无摘榜令。"
                )

        entry["challenges_left"] -= 1
        self._save(data)

        # 重新加载确保排序最新
        data = self._load()
        data.sort(key=lambda x: x.get("score", 0), reverse=True)
        idx = self._find_index(data, user_id)

        a_entry = dict(data[idx])
        if idx == 0:
            # 第一名挑战灵修兽
            opponent = self._build_beast(a_entry)
            is_beast = True
        else:
            opponent = dict(data[idx - 1])
            is_beast = False

        # 根据实力差距给上方玩家加成
        atk, defense, hp = self._compute_multipliers(a_entry, opponent, is_beast)
        a_player = self._entry_to_player(a_entry, atk, defense, hp)
        b_player = self._entry_to_player(opponent, 1.0, 1.0, 1.0)

        battle = await self.battle_service.run_battle(a_player, b_player)
        a_won = battle.winner == a_player["name"]
        b_won = battle.loser == a_player["name"] or battle.draw
        draw = battle.draw

        # 重新加载并更新积分
        data = self._load()
        idx = self._find_index(data, user_id)
        entry = data[idx]

        if draw:
            entry["score"] = entry.get("score", 0) + 500
            spirit_reward = entry["score"] * 4
            result_msg = (
                f"{entry['name']}与{b_player['name']}战平，"
                f"当前积分[{entry['score']}]，获得灵石{spirit_reward}"
            )
        elif a_won:
            if is_beast:
                entry["score"] = entry.get("score", 0) + 1500
                spirit_reward = entry["score"] * 8
            else:
                entry["score"] = entry.get("score", 0) + 2000
                spirit_reward = entry["score"] * 4
            result_msg = (
                f"{entry['name']}击败了[{b_player['name']}]，"
                f"当前积分[{entry['score']}]，获得灵石{spirit_reward}"
            )
        else:
            if is_beast:
                entry["score"] = entry.get("score", 0) + 800
                spirit_reward = entry["score"] * 6
            else:
                entry["score"] = entry.get("score", 0) + 1000
                spirit_reward = entry["score"] * 2
            result_msg = (
                f"{entry['name']}被[{b_player['name']}]打败了，"
                f"当前积分[{entry['score']}]，获得灵石{spirit_reward}"
            )

        await self.player_service.add_spirit_stones(user_id, spirit_reward)
        self._save(data)

        # 重新排序
        data.sort(key=lambda x: x.get("score", 0), reverse=True)
        self._save(data)

        lines = [result_msg]
        if not draw and len(battle.messages) <= 50:
            lines.extend(battle.messages)
        return TiandibangResult(success=True, lines=lines)

    def _compute_multipliers(
        self, a_entry: dict[str, Any], b_entry: dict[str, Any], is_beast: bool
    ) -> tuple[float, float, float]:
        """根据双方攻击差距给挑战方施加属性调整。"""
        if is_beast:
            return 1.0, 1.0, 1.0
        ratio = b_entry.get("attack", 1) / max(1, a_entry.get("attack", 1))
        if ratio > 2:
            return 2.0, 2.0, 2.0
        if ratio > 1.6:
            return 1.6, 1.6, 1.6
        if ratio > 1.3:
            return 1.3, 1.3, 1.3
        return 1.0, 1.0, 1.0

    def _build_beast(self, entry: dict[str, Any]) -> dict[str, Any]:
        """为第一名生成灵修兽对手。"""
        atk = 0.8 + 0.4 * random.random()
        defense = 0.8 + 0.4 * random.random()
        hp = 0.8 + 0.4 * random.random()
        return {
            "user_id": "beast",
            "name": "灵修兽",
            "level_id": entry.get("level_id", 1),
            "attack": int(entry.get("attack", 1) * atk),
            "defense": int(entry.get("defense", 1) * defense),
            "hp": int(entry.get("hp", 1) * hp),
            "crit_rate": entry.get("crit_rate", 0),
            "magic_rate": entry.get("magic_rate", 0),
            "learned_gongfa": list(entry.get("learned_gongfa", [])),
            "score": 0,
        }

    def _entry_to_player(
        self,
        entry: dict[str, Any],
        atk_mul: float,
        def_mul: float,
        hp_mul: float,
    ) -> dict[str, Any]:
        return {
            "name": entry.get("name", "无名"),
            "attack": int(entry.get("attack", 1) * atk_mul),
            "defense": int(entry.get("defense", 1) * def_mul),
            "hp_max": int(entry.get("hp", 1) * hp_mul),
            "current_hp": int(entry.get("hp", 1) * hp_mul),
            "crit_rate": entry.get("crit_rate", 0),
            "linggen": {"法球倍率": entry.get("magic_rate", 0)},
            "level_id": entry.get("level_id", 1),
        }

    async def my_point(self, user_id: str) -> TiandibangResult:
        """查看天地榜及个人排名。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return TiandibangResult(player_not_found=True)

        data = self._load()
        data.sort(key=lambda x: x.get("score", 0), reverse=True)
        idx = self._find_index(data, user_id)
        if idx == -1:
            return TiandibangResult(not_registered=True, message="请先报名天地榜！")

        lines = ["***天地榜（每日免费三次）***\n周一 0 点清空积分"]
        display_count = min(10, len(data))
        start = 0
        if idx >= display_count and len(data) - idx < display_count:
            start = len(data) - display_count
        elif idx >= display_count:
            start = max(0, idx - 5)

        for i in range(start, start + display_count):
            if i >= len(data):
                break
            item = data[i]
            lines.append(
                f"名次：{i + 1}\n名号：{item.get('name', '无名')}\n积分：{item.get('score', 0)}"
            )

        lines.append(f"\n你的排名：第 {idx + 1} 名")
        return TiandibangResult(success=True, lines=lines)

    async def shop_list(self, user_id: str) -> TiandibangResult:
        """查看天地堂商品列表。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return TiandibangResult(player_not_found=True)

        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return TiandibangResult(not_registered=True, message="请先报名天地榜！")

        score = data[idx].get("score", 0)
        lines = [f"【天地堂】{player.get('name', '无名')} 当前积分：{score}"]
        items = []
        if self.item_catalog is not None:
            items = self.item_catalog.get_items("天地堂.json")
        if not items:
            lines.append("暂无商品")
            return TiandibangResult(success=True, lines=lines)

        for item in items:
            lines.append(
                f"{item.get('name')} | {item.get('积分', 0)} 积分 | {item.get('class', '道具')}"
            )
        lines.append("\n格式：#积分兑换 物品名*数量")
        return TiandibangResult(success=True, lines=lines)

    async def exchange(
        self, user_id: str, item_name: str, quantity: int
    ) -> TiandibangResult:
        """使用天地榜积分兑换物品。"""
        if self.item_catalog is None or self.inventory_service is None:
            return TiandibangResult(message="兑换服务未初始化。")

        player = await self.player_service.load(user_id)
        if player is None:
            return TiandibangResult(player_not_found=True)

        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return TiandibangResult(not_registered=True, message="请先报名天地榜！")

        item = self.item_catalog.find_item(item_name, "天地堂.json")
        if item is None:
            return TiandibangResult(message=f"天地堂没有{item_name}")

        price = int(item.get("积分", 0))
        total = price * quantity
        score = data[idx].get("score", 0)
        if score < total:
            return TiandibangResult(
                message=f"积分不足，还需{total - score}积分兑换{item_name}*{quantity}"
            )

        data[idx]["score"] = score - total
        self._save(data)

        category = item.get("class", "道具")
        await self.inventory_service.add_item(
            user_id, category, item_name, quantity
        )
        return TiandibangResult(
            success=True,
            message=f"兑换成功！获得[{item_name}]*{quantity}，剩余积分[{data[idx]['score']}]。",
        )

    async def settle_rewards(
        self, user_id: str, master_ids: set[str]
    ) -> TiandibangResult:
        """结算天地榜奖励（管理员）。"""
        if user_id not in master_ids:
            return TiandibangResult(message="只有主人可以执行此操作。")

        data = self._load()
        if not data:
            return TiandibangResult(message="天地榜为空，无需结算。")

        data.sort(key=lambda x: x.get("score", 0), reverse=True)
        today = datetime.now()
        is_monday = today.weekday() == 0
        lines = [f"【天地榜结算】{today.strftime('%Y/%m/%d')}"]

        for i in range(min(3, len(data))):
            item = data[i]
            reward_stones = self.REWARD_SPIRIT_STONES[i]
            reward_boxes = self.REWARD_BOXES[i]
            await self.player_service.add_spirit_stones(
                item["user_id"], reward_stones
            )
            if self.inventory_service is not None:
                await self.inventory_service.add_item(
                    item["user_id"], "盒子", "超越宝盒", reward_boxes
                )
            lines.append(
                f"第{i + 1}名：{item.get('name', '无名')}\n"
                f"  积分：{item.get('score', 0)}\n"
                f"  奖励：{reward_stones} 灵石 + 超越宝盒*{reward_boxes}"
            )

        for item in data:
            item["challenges_left"] = self.DAILY_CHALLENGES
            if is_monday:
                item["score"] = 0

        self._save(data)
        if is_monday:
            lines.append("\n天地榜积分已重置，挑战次数已恢复。")
        else:
            lines.append("\n每日挑战次数已恢复。")
        return TiandibangResult(success=True, lines=lines)

    async def reset_scores(
        self, user_id: str, master_ids: set[str]
    ) -> TiandibangResult:
        """清空所有玩家积分（管理员）。"""
        if user_id not in master_ids:
            return TiandibangResult(message="只有主人可以执行此操作。")

        data = self._load()
        for item in data:
            item["score"] = 0
            item["challenges_left"] = self.DAILY_CHALLENGES
        self._save(data)
        return TiandibangResult(success=True, message="天地榜积分已清空。")
