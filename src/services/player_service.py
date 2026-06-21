import json
import random
from pathlib import Path
from typing import Any

from src.constants.inventory import default_inventory


class PlayerService:
    """玩家数据服务：负责创建、读取、保存玩家存档。"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.players_dir = data_dir / "players"
        self.players_dir.mkdir(parents=True, exist_ok=True)

    def _player_file(self, user_id: str) -> Path:
        return self.players_dir / f"{user_id}.json"

    async def exists(self, user_id: str) -> bool:
        return self._player_file(user_id).exists()

    async def load(self, user_id: str) -> dict[str, Any] | None:
        file_path = self._player_file(user_id)
        if not file_path.exists():
            return None
        return json.loads(file_path.read_text(encoding="utf-8"))

    async def save(self, user_id: str, player: dict[str, Any]) -> None:
        file_path = self._player_file(user_id)
        file_path.write_text(json.dumps(player, ensure_ascii=False, indent=2), encoding="utf-8")

    async def add_spirit_stones(self, user_id: str, amount: int) -> None:
        player = await self.load(user_id)
        if player is None:
            return
        player["spirit_stones"] = player.get("spirit_stones", 0) + amount
        await self.save(user_id, player)

    async def add_source_stones(self, user_id: str, amount: int) -> None:
        player = await self.load(user_id)
        if player is None:
            return
        player["source_stones"] = player.get("source_stones", 0) + amount
        await self.save(user_id, player)

    async def add_exp(self, user_id: str, amount: int) -> None:
        player = await self.load(user_id)
        if player is None:
            return
        player["exp"] = player.get("exp", 0) + amount
        await self.save(user_id, player)

    async def add_blood_qi(self, user_id: str, amount: int) -> None:
        player = await self.load(user_id)
        if player is None:
            return
        player["blood_qi"] = player.get("blood_qi", 0) + amount
        await self.save(user_id, player)

    async def refresh_player(self, user_id: str) -> tuple[dict[str, Any], list[str]] | None:
        """刷新玩家信息：补全缺失字段并重新计算衍生属性。"""
        player = await self.load(user_id)
        if player is None:
            return None

        defaults = {
            "sex": 0,
            "name": f"路人甲{await self._next_sequence()}号",
            "motto": "这个人很懒还没有写",
            "daofa": "未开启",
            "level_id": 1,
            "physique_id": 1,
            "mijing_level_id": 1,
            "xiangu_level_id": 1,
            "shenshi": 0,
            "yuanshen": 0,
            "yuanshen_limit": 0,
            "race": 1,
            "exp": 0,
            "blood_qi": 0,
            "spirit_stones": 0,
            "source_stones": 0,
            "life_source": 100,
            "shenshi_count": 0,
            "shouyuan": 99,
            "favorability": 0,
            "breakthrough": False,
            "linggen_show": 1,
            "learned_gongfa": [],
            "satiety": 0,
            "calories": 0,
            "consecutive_checkin_days": 0,
            "daofa_blessing_days": 0,
            "attack_bonus": 0,
            "defense_bonus": 0,
            "hp_bonus": 0,
            "power_place": 0,
            "current_hp": 8000,
            "lunhui": 0,
            "lunhui_bh": 0,
            "lunhui_points": 10,
            "daofa_xianshu": 0,
            "daofa_xianshu_endtime": 0,
            "yuanshenlevel_id": None,
            "neijingdi": 0,
            "ninglian_count": 1,
            "daoshang": 0,
            "occupation": [],
            "occupation_level": 1,
            "najie": default_inventory(),
            "zhenyao_floor": 0,
            "shenpo_stage": 0,
            "modao_value": 0,
            "pets": [],
            "skin_cultivation": 0,
            "skin_equipment": 0,
            "skin_najie": 0,
            "luck": 0,
            "add_lucky_no": 0,
            "shitu_task_stage": 0,
            "shitu_points": 0,
            "attempting_level_7": False,
            "guardian": None,
            "lottery_count": 0,
            "gold_rate": 0,
            "gold_count": 0,
            "protector": "",
            "pet_treasure_status": 0,
            "pet_treasure": "",
            "pet_treasure_start_time": 0,
            "daohang": "无",
            "force": "无",
            "force_position": "",
            "wuse_jitan": 0,
        }

        fixed: list[str] = []
        for key, value in defaults.items():
            if key not in player:
                player[key] = value
                fixed.append(key)

        # 重新根据灵根计算修炼效率
        linggen = player.get("linggen")
        if linggen is None:
            linggen = self._random_talent()
            player["linggen"] = linggen
            fixed.append("linggen")
        old_eff = player.get("cultivation_efficiency")
        new_eff = linggen.get("eff", 1.0)
        player["cultivation_efficiency"] = new_eff
        if old_eff != new_eff:
            fixed.append("cultivation_efficiency")

        # 确保天资字段存在
        if "talent_grade" not in player or "talent_evaluation" not in player:
            aptitude = self._random_aptitude()
            if "talent_grade" not in player:
                player["talent_grade"] = aptitude["grade"]
                fixed.append("talent_grade")
            if "talent_evaluation" not in player:
                player["talent_evaluation"] = aptitude["evaluation"]
                fixed.append("talent_evaluation")

        # 去重并保持顺序
        seen = set()
        fixed = [k for k in fixed if not (k in seen or seen.add(k))]

        await self.save(user_id, player)
        return player, fixed

    async def create_player(self, user_id: str) -> dict[str, Any]:
        """创建新玩家；若已存在则返回已有存档。"""
        existing = await self.load(user_id)
        if existing is not None:
            return existing

        talent = self._random_talent()
        aptitude = self._random_aptitude()

        player = {
            "id": user_id,
            "sex": 0,
            "name": f"路人甲{await self._next_sequence()}号",
            "motto": "这个人很懒还没有写",
            "daofa": "未开启",
            "level_id": 1,
            "physique_id": 1,
            "mijing_level_id": 1,
            "xiangu_level_id": 1,
            "shenshi": 0,
            "yuanshen": 0,
            "yuanshen_limit": 0,
            "race": 1,
            "exp": 1,
            "blood_qi": 1,
            "spirit_stones": 10000,
            "source_stones": 0,
            "life_source": 100,
            "linggen": talent,
            "shenshi_count": 0,
            "shouyuan": 99,
            "favorability": 0,
            "breakthrough": False,
            "linggen_show": 1,
            "learned_gongfa": [],
            "cultivation_efficiency": talent.get("eff", 1.0),
            "satiety": 0,
            "calories": 0,
            "consecutive_checkin_days": 0,
            "daofa_blessing_days": 0,
            "attack_bonus": 0,
            "defense_bonus": 0,
            "hp_bonus": 0,
            "power_place": 0,
            "current_hp": 8000,
            "lunhui": 0,
            "lunhui_bh": 0,
            "lunhui_points": 10,
            "daofa_xianshu": 0,
            "daofa_xianshu_endtime": 0,
            "yuanshenlevel_id": None,
            "neijingdi": 0,
            "ninglian_count": 1,
            "daoshang": 0,
            "occupation": [],
            "occupation_level": 1,
            "najie": default_inventory(),
            "zhenyao_floor": 0,
            "shenpo_stage": 0,
            "modao_value": 0,
            "pets": [],
            "skin_cultivation": 0,
            "skin_equipment": 0,
            "skin_najie": 0,
            "luck": 0,
            "add_lucky_no": 0,
            "shitu_task_stage": 0,
            "shitu_points": 0,
            "attempting_level_7": False,
            "guardian": None,
            "lottery_count": 0,
            "gold_rate": 0,
            "gold_count": 0,
            "protector": "",
            "pet_treasure_status": 0,
            "pet_treasure": "",
            "pet_treasure_start_time": 0,
            "daohang": "无",
            "force": "无",
            "force_position": "",
            "talent_grade": aptitude["grade"],
            "talent_evaluation": aptitude["evaluation"],
            "wuse_jitan": 0,
        }

        await self.save(user_id, player)
        return player

    def _random_talent(self) -> dict[str, Any]:
        """随机生成灵根（简化版）。"""
        linggen_types = ["金", "木", "水", "火", "土"]
        # 简化：随机 1~5 种灵根
        count = random.choices([1, 2, 3, 4, 5], weights=[5, 15, 30, 30, 20])[0]
        selected = random.sample(linggen_types, count)
        return {
            "type": "、".join(selected),
            "main": selected[0],
            "eff": round(random.uniform(1.0, 2.0), 2),
        }

    def _random_aptitude(self) -> dict[str, Any]:
        """随机生成天资等级（简化版）。"""
        grades = [
            {"grade": 1, "evaluation": "平平无奇"},
            {"grade": 2, "evaluation": "略有资质"},
            {"grade": 3, "evaluation": "天资聪颖"},
            {"grade": 4, "evaluation": "绝代天骄"},
            {"grade": 5, "evaluation": "万古无一"},
        ]
        return random.choices(grades, weights=[40, 30, 20, 8, 2])[0]

    async def _next_sequence(self) -> int:
        """根据已有玩家数量生成序号。"""
        return len(list(self.players_dir.glob("*.json"))) + 1
