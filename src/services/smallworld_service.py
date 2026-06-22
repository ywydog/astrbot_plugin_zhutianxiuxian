import json
import random
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@dataclass
class SmallworldResult:
    """小世界操作结果。"""

    success: bool = False
    player_not_found: bool = False
    no_world: bool = False
    message: str = ""
    lines: list[str] = field(default_factory=list)


class SmallworldService:
    """小世界（洞府家园）服务：开辟、演化、种植、分身收获。"""

    DATA_FILE = "smallworld/smallworlds.json"

    # 小世界等级配置
    WORLD_LEVELS: dict[int, dict[str, Any]] = {
        1: {
            "name": "混沌初开",
            "spirit_density": 1000,
            "area": "十里方圆",
            "time_flow": "1:1",
            "field_limit": 1,
            "materials": {"世界石": 1},
        },
        2: {
            "name": "鸿蒙小界",
            "spirit_density": 3000,
            "area": "百里方圆",
            "time_flow": "1:2",
            "field_limit": 3,
            "materials": {
                "世界石": 3,
                "玄渊真水": 1,
                "元虚罡风": 1,
                "太初燧火": 1,
                "须弥神土": 1,
            },
        },
        3: {
            "name": "紫府洞天",
            "spirit_density": 5000,
            "area": "千里方圆",
            "time_flow": "1:3",
            "field_limit": 5,
            "materials": {"世界石": 5, "造化玉碟": 1},
        },
        4: {
            "name": "太虚仙境",
            "spirit_density": 10000,
            "area": "万里山河",
            "time_flow": "1:4",
            "field_limit": 8,
            "materials": {"世界石": 10, "混沌母气": 10},
        },
        5: {
            "name": "洪荒世界",
            "spirit_density": 30000,
            "area": "十万里疆域",
            "time_flow": "1:8",
            "field_limit": 12,
            "materials": {"世界石": 20},
        },
    }

    # 神药生长阶段：时长（秒）
    SHENYAO_STAGES: dict[int, dict[str, Any]] = {
        1: {"name": "萌芽", "duration": 3600, "desc": "种子破土而出，嫩芽初现"},
        2: {"name": "幼苗", "duration": 10800, "desc": "枝叶舒展，初具药形"},
        3: {"name": "成长期", "duration": 21600, "desc": "药株茁壮，散发神性光辉"},
        4: {"name": "开花期", "duration": 43200, "desc": "神花绽放，道韵流转"},
        5: {"name": "成熟期", "duration": 0, "desc": "神药成熟，可采摘"},
    }

    # 神药种子配置
    SHENYAO_SEEDS: dict[str, dict[str, Any]] = {
        "麒麟神药种子": {
            "harvest": "麒麟神药",
            "spirit_density": 3000,
            "environments": ["仙泉"],
        },
        "玄武神药种子": {
            "harvest": "玄武神药",
            "spirit_density": 3000,
            "environments": ["仙泉"],
        },
        "蟠桃仙种": {
            "harvest": "蟠桃仙果",
            "spirit_density": 3000,
            "environments": ["仙泉"],
        },
        "真龙不死药种子": {
            "harvest": "真龙不死药",
            "spirit_density": 5000,
            "environments": ["龙穴"],
        },
        "大夏神药种子": {
            "harvest": "大夏神药",
            "spirit_density": 3000,
            "environments": [],
        },
        "九妙不死药种子": {
            "harvest": "九妙不死药",
            "spirit_density": 8000,
            "environments": ["仙坟"],
        },
        "悟道古茶树幼苗": {
            "harvest": "悟道古茶树",
            "spirit_density": 10000,
            "environments": ["仙坟", "仙泉"],
        },
    }

    # 环境道具映射
    ENVIRONMENT_ITEMS: dict[str, str] = {
        "混沌源石": "混沌土",
        "仙泉之眼": "仙泉",
        "龙魂精魄": "龙穴",
        "雷池核心": "雷池",
        "仙坟土": "仙坟",
        "星辰核心": "星辰矿脉",
        "生命之种": "生命古树",
        "时间沙漏": "时间碎片",
    }

    # 特殊资源池（演化时随机获得）
    SPECIAL_RESOURCES = [
        "先天灵泉",
        "星辰矿脉",
        "混沌灵根",
        "太初神木",
        "鸿蒙紫气",
        "大道金莲",
        "虚空晶石",
        "时间碎片",
        "生命古树",
    ]

    # 基础资源产量：每小时
    BASE_PRODUCTION: dict[int, dict[str, int]] = {
        1: {"灵石": 100000, "仙馐果": 50},
        2: {"灵石": 200000, "仙馐果": 100, "灵矿": 5},
        3: {"灵石": 300000, "仙馐果": 100, "灵矿": 10, "仙果": 5},
        4: {
            "灵石": 500000,
            "仙馐果": 200,
            "灵矿": 10,
            "仙果": 10,
            "混沌元液": 3,
        },
        5: {
            "灵石": 800000,
            "仙馐果": 300,
            "灵矿": 20,
            "仙果": 15,
            "混沌元液": 5,
        },
    }

    # 特殊资源对基础产量的加成倍率
    RESOURCE_MULTIPLIERS: dict[str, tuple[str, int]] = {
        "先天灵泉": ("仙馐果", 15),
        "星辰矿脉": ("灵矿", 15),
        "混沌灵根": ("混沌元液", 15),
        "太初神木": ("仙果", 15),
        "虚空晶石": ("灵石", 15),
    }

    # 神药收获时直接给予的修为/血气奖励
    SHENYAO_REWARDS: dict[str, tuple[int, int]] = {
        "九妙不死药": (35_000_000, 35_000_000),
        "真龙不死药": (8_000_000, 8_000_000),
        "神凰不死药": (8_000_000, 8_000_000),
        "麒麟神药": (5_000_000, 5_000_000),
        "玄武神药": (5_000_000, 5_000_000),
        "蟠桃仙果": (15_000_000, 15_000_000),
    }

    # 浇灌道具效果：推进阶段数
    WATER_ITEMS: dict[str, int] = {
        "草木精华露": 1,
        "岁月流金沙": 2,
        "掌天灵液": 3,
    }

    CREATE_MIN_LEVEL = 42
    UPGRADE_MIN_LEVEL = 47
    AVATAR_EXP_COST = 1_000_000
    MAX_HARVEST_HOURS = 24

    def __init__(
        self,
        player_service: PlayerService,
        inventory_service: InventoryService,
        data_dir: Path,
    ):
        self.player_service = player_service
        self.inventory_service = inventory_service
        self.data_dir = data_dir
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

    def _find_index(self, data: list[dict[str, Any]], user_id: str) -> int:
        for i, item in enumerate(data):
            if item.get("user_id") == user_id:
                return i
        return -1

    def _now(self) -> float:
        return time.time()

    def _format_time(self, timestamp: float) -> str:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    def _get_level_config(self, level: int) -> dict[str, Any] | None:
        return self.WORLD_LEVELS.get(level)

    def _parse_time_flow(self, time_flow: str) -> int:
        """解析时间流速，如 1:2 返回 2。"""
        parts = time_flow.split(":")
        if len(parts) != 2:
            return 1
        try:
            return int(parts[1]) // int(parts[0])
        except (ValueError, ZeroDivisionError):
            return 1

    def _build_world(
        self, user_id: str, player: dict[str, Any], world_name: str
    ) -> dict[str, Any]:
        config = self.WORLD_LEVELS[1]
        now = self._now()
        return {
            "user_id": user_id,
            "player_name": player.get("name", "无名"),
            "world_name": world_name,
            "level": 1,
            "spirit_density": config["spirit_density"],
            "area": config["area"],
            "time_flow": config["time_flow"],
            "field_limit": config["field_limit"],
            "special_resources": [],
            "fields": [],
            "avatar": None,
            "events": [],
            "created_at": now,
            "last_upgrade_time": None,
        }

    async def create_small_world(
        self, user_id: str, world_name: str
    ) -> SmallworldResult:
        """开辟小世界。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return SmallworldResult(player_not_found=True)

        if player.get("level_id", 1) < self.CREATE_MIN_LEVEL:
            return SmallworldResult(
                message="开辟小世界需要成仙（练气境界达到仙人境）。"
            )

        data = self._load()
        if self._find_index(data, user_id) != -1:
            return SmallworldResult(message="你已经开辟过小世界了。")

        config = self.WORLD_LEVELS[1]
        for item_name, amount in config["materials"].items():
            if not await self.inventory_service.has_item(
                user_id, "材料", item_name, amount
            ):
                return SmallworldResult(
                    message=f"开辟小世界需要 {item_name} x{amount}"
                )

        for item_name, amount in config["materials"].items():
            await self.inventory_service.remove_item(
                user_id, "材料", item_name, amount
            )

        world = self._build_world(user_id, player, world_name)
        data.append(world)
        self._save(data)

        texts = [
            "你以无上法力撕裂虚空，于混沌中开辟出一方小世界！",
            "掌中世界，心中乾坤！",
            "虚空震荡，法则重组！一方新世界在你手中诞生！",
            "混沌初开，鸿蒙始分！",
        ]
        lines = [
            texts[random.randint(0, len(texts) - 1)],
            f"◇◇◇【{world['world_name']}】◇◇◇",
            f"等级：{config['name']}（1级）",
            f"灵气浓度：{world['spirit_density']}",
            f"面积：{world['area']}",
            f"时间流速：{world['time_flow']}",
            f"特殊资源：{'、'.join(world['special_resources']) or '无'}",
            "「此界初成，尚需精心培育方能成为洞天福地」",
        ]
        return SmallworldResult(success=True, lines=lines)

    async def upgrade_small_world(self, user_id: str) -> SmallworldResult:
        """演化小世界。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return SmallworldResult(player_not_found=True)

        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return SmallworldResult(no_world=True, message="请先开辟小世界。")

        world = data[idx]
        next_level = world["level"] + 1
        config = self.WORLD_LEVELS.get(next_level)
        if config is None:
            return SmallworldResult(
                message=f"你的小世界已达到最高等级（{world['level']}级）。"
            )

        if player.get("level_id", 1) < self.UPGRADE_MIN_LEVEL:
            return SmallworldResult(message="演化小世界需要大罗金仙修为。")

        for item_name, amount in config["materials"].items():
            if not await self.inventory_service.has_item(
                user_id, "材料", item_name, amount
            ):
                return SmallworldResult(
                    message=f"演化小世界需要 {item_name} x{amount}"
                )

        for item_name, amount in config["materials"].items():
            await self.inventory_service.remove_item(
                user_id, "材料", item_name, amount
            )

        existing_resources = list(world.get("special_resources", []))
        world["level"] = next_level
        world["spirit_density"] = config["spirit_density"]
        world["area"] = config["area"]
        world["time_flow"] = config["time_flow"]
        world["field_limit"] = config["field_limit"]
        world["special_resources"] = existing_resources
        world["last_upgrade_time"] = self._now()

        # 随机获得 1-2 个新特殊资源
        pool = [r for r in self.SPECIAL_RESOURCES if r not in existing_resources]
        new_resources: list[str] = []
        if pool:
            count = min(2, len(pool))
            new_resources = random.sample(pool, count)
            world["special_resources"].extend(new_resources)

        self._save(data)

        texts = [
            f"天地震荡，法则重组！你的小世界【{world['world_name']}】成功晋升为【{config['name']}】！",
            f"鸿蒙演化，世界晋升！【{world['world_name']}】已升级为【{config['name']}】！",
            "乾坤再造，世界升华！你的小世界完成蜕变！",
            "大道共鸣，世界跃迁！",
        ]
        lines = [
            texts[random.randint(0, len(texts) - 1)],
            f"◇◇◇【{world['world_name']}】◇◇◇",
            f"等级：{config['name']}（{world['level']}级）",
            f"灵气浓度：{world['spirit_density']}",
            f"面积：{world['area']}",
            f"时间流速：{world['time_flow']}",
            f"药田容量：{len(world['fields'])}/{world['field_limit']}",
            f"特殊资源：{'、'.join(world['special_resources']) or '无'}",
        ]
        if new_resources:
            lines.append(f"新增特殊资源：{'、'.join(new_resources)}")
        lines.append("「世界晋升，大道可期！」")
        return SmallworldResult(success=True, lines=lines)

    async def get_small_world(self, user_id: str) -> dict[str, Any] | None:
        """获取玩家小世界数据。"""
        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return None
        return data[idx]

    async def create_avatar(self, user_id: str) -> SmallworldResult:
        """将分身化入小世界。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return SmallworldResult(player_not_found=True)

        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return SmallworldResult(no_world=True, message="请先开辟小世界。")

        world = data[idx]
        if world.get("avatar"):
            return SmallworldResult(message="你已化入分身在小世界中，无需再次化入。")

        if player.get("exp", 0) < self.AVATAR_EXP_COST:
            return SmallworldResult(
                message=f"化入分身需要 {self.AVATAR_EXP_COST} 修为，"
                f"你只有 {player.get('exp', 0)} 修为。"
            )

        player["exp"] = player.get("exp", 0) - self.AVATAR_EXP_COST
        await self.player_service.save(user_id, player)

        now = self._now()
        world["avatar"] = {
            "created_at": now,
            "last_harvest_time": now,
        }
        self._save(data)

        return SmallworldResult(
            success=True,
            message=f"你消耗 {self.AVATAR_EXP_COST} 修为，"
            f"化出一道分身进入【{world['world_name']}】！\n"
            "分身将自动收集资源，最多积累 24 小时。",
        )

    def _calculate_resources(
        self, world: dict[str, Any], hours: float
    ) -> dict[str, int]:
        """根据小世界等级和特殊资源计算资源产量。"""
        base = self.BASE_PRODUCTION.get(world["level"], self.BASE_PRODUCTION[1]).copy()
        resources = {k: int(v * hours) for k, v in base.items()}

        for resource, (target, multiplier) in self.RESOURCE_MULTIPLIERS.items():
            if resource in world.get("special_resources", []) and target in resources:
                resources[target] = resources[target] * multiplier

        return resources

    def _advance_crops(
        self, world: dict[str, Any], real_seconds: float
    ) -> tuple[list[str], list[str]]:
        """
        推进药田作物生长。
        返回 (grown_messages, harvested_names)。
        """
        time_ratio = self._parse_time_flow(world.get("time_flow", "1:1"))
        spirit_density = world.get("spirit_density", 1000)
        special_resources = world.get("special_resources", [])
        time_fragment_bonus = 2.0 if "时间碎片" in special_resources else 1.0
        fields = world.get("fields", [])

        grown: list[str] = []
        harvested: list[str] = []
        now = self._now()

        for i in range(len(fields) - 1, -1, -1):
            crop = fields[i]
            seed_name = crop.get("seed_name", "")
            seed_config = self.SHENYAO_SEEDS.get(seed_name)
            if seed_config is None:
                continue

            stage = crop.get("current_stage", 1)
            if stage >= 5:
                continue

            required_density = seed_config.get("spirit_density", 1000)
            growth_rate = (spirit_density / required_density) * time_fragment_bonus
            effective_seconds = real_seconds * time_ratio * growth_rate

            stage_start = crop.get("stage_start_time", now)
            accumulated = crop.get("accumulated_seconds", 0) + effective_seconds

            while stage < 5:
                stage_info = self.SHENYAO_STAGES.get(stage)
                if stage_info is None:
                    break
                duration = stage_info.get("duration", 0)
                if stage == 5 or duration <= 0:
                    break
                if accumulated >= duration:
                    accumulated -= duration
                    stage += 1
                    stage_name = self.SHENYAO_STAGES.get(stage, {}).get("name", "未知")
                    grown.append(f"【{seed_config['harvest']}】进入 {stage_name} 阶段")
                    crop["growth_log"].append(
                        f"{self._format_time(now)}: 进入【{stage_name}】阶段"
                    )
                else:
                    break

            crop["current_stage"] = stage
            crop["accumulated_seconds"] = accumulated
            crop["stage_start_time"] = now

            if stage >= 5:
                harvested.append(seed_config["harvest"])
                fields.pop(i)

        return grown, harvested

    async def harvest_resources(self, user_id: str) -> SmallworldResult:
        """收获小世界资源。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return SmallworldResult(player_not_found=True)

        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return SmallworldResult(no_world=True, message="请先开辟小世界。")

        world = data[idx]
        avatar = world.get("avatar")
        if avatar is None:
            return SmallworldResult(
                no_world=True, message="请先使用 #将分身化入小世界 创建分身。"
            )

        time_ratio = self._parse_time_flow(world.get("time_flow", "1:1"))
        now = self._now()
        last_harvest = avatar.get("last_harvest_time", now)
        hours_passed = (now - last_harvest) / 3600
        effective_hours = min(hours_passed * time_ratio, self.MAX_HARVEST_HOURS)

        if effective_hours <= 0:
            return SmallworldResult(message="距离上次收获时间太短，暂无资源可收获。")

        resources = self._calculate_resources(world, effective_hours)

        # 发放资源
        for resource, amount in resources.items():
            if resource == "灵石":
                await self.player_service.add_spirit_stones(user_id, amount)
            elif resource == "仙馐果":
                await self.inventory_service.add_item(user_id, "食材", resource, amount)
            elif resource == "灵矿":
                await self.inventory_service.add_item(user_id, "道具", resource, amount)
            else:
                # 仙果、混沌元液按原设计归为丹药
                await self.inventory_service.add_item(user_id, "丹药", resource, amount)

        # 推进神药生长并自动收获成熟作物
        grown, harvested = self._advance_crops(world, hours_passed * 3600)

        # 神药直接奖励
        for shenyao in harvested:
            exp_reward, blood_reward = self.SHENYAO_REWARDS.get(shenyao, (0, 0))
            if exp_reward:
                await self.player_service.add_exp(user_id, exp_reward)
                await self.player_service.add_blood_qi(user_id, blood_reward)
            category = "道具" if shenyao == "悟道古茶树" else "丹药"
            await self.inventory_service.add_item(user_id, category, shenyao, 1)

        avatar["last_harvest_time"] = now
        self._save(data)

        resource_list = "、".join(f"{k}x{v}" for k, v in resources.items())
        lines = [
            f"成功收获分身收集的资源：{resource_list}",
            f"时间流速 {world.get('time_flow', '1:1')}（加速 {time_ratio} 倍）",
        ]
        if harvested:
            lines.append("【神药成熟】")
            lines.extend(f"收获【{item}】" for item in harvested)
        if grown:
            lines.append("【神药生长】")
            lines.extend(grown)
        lines.append(f"分身将继续在【{world['world_name']}】中收集资源。")
        return SmallworldResult(success=True, lines=lines)

    async def plant_shenyao(
        self, user_id: str, seed_name: str
    ) -> SmallworldResult:
        """栽种神药种子。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return SmallworldResult(player_not_found=True)

        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return SmallworldResult(no_world=True, message="请先开辟小世界。")

        world = data[idx]
        fields = world.setdefault("fields", [])
        field_limit = world.get("field_limit", 0)
        if len(fields) >= field_limit:
            return SmallworldResult(
                message=f"药田已满（{len(fields)}/{field_limit}），"
                "升级小世界可增加药田容量。"
            )

        # 模糊匹配种子
        matched_seed = None
        matched_key = ""
        for key in self.SHENYAO_SEEDS:
            if key in seed_name or seed_name in key:
                matched_seed = self.SHENYAO_SEEDS[key]
                matched_key = key
                break

        if matched_seed is None:
            return SmallworldResult(
                message="未找到该种子，请发送 #种植指南 查看可用种子。"
            )

        if not await self.inventory_service.has_item(user_id, "草药", matched_key, 1):
            count = await self.inventory_service.get_count(
                user_id, "草药", matched_key
            )
            return SmallworldResult(
                message=f"需要【{matched_key}】x1，你当前拥有 {count} 个。"
            )

        # 检查种植条件
        if world.get("spirit_density", 0) < matched_seed.get("spirit_density", 0):
            return SmallworldResult(
                message=(
                    f"灵气浓度不足（需要 {matched_seed['spirit_density']}，"
                    f"当前 {world['spirit_density']}）。"
                )
            )

        missing_envs = [
            env
            for env in matched_seed.get("environments", [])
            if env not in world.get("special_resources", [])
        ]
        if missing_envs:
            return SmallworldResult(
                message=(
                    f"缺少特殊环境：{'、'.join(missing_envs)}。"
                    "使用 #使用[道具]创造环境 创建所需环境。"
                )
            )

        await self.inventory_service.remove_item(user_id, "草药", matched_key, 1)

        now = self._now()
        fields.append(
            {
                "seed_name": matched_key,
                "current_stage": 1,
                "stage_start_time": now,
                "accumulated_seconds": 0,
                "planted_at": now,
                "growth_log": [f"{self._format_time(now)}: 种植【{matched_key}】"],
            }
        )
        self._save(data)

        stage_name = self.SHENYAO_STAGES[1]["name"]
        lines = [
            f"成功种植【{matched_key}】！",
            f"当前阶段：{stage_name}",
            f"阶段描述：{self.SHENYAO_STAGES[1].get('desc', '')}".strip(),
            f"预计成熟：{self._estimate_growth_time(matched_seed, world)}",
        ]
        if len(fields) >= field_limit:
            lines.append(
                f"⚠️ 药田已满（{len(fields)}/{field_limit}），无法种植更多作物。"
            )
        return SmallworldResult(success=True, lines=lines)

    def _estimate_growth_time(
        self, seed_config: dict[str, Any], world: dict[str, Any]
    ) -> str:
        """估算神药从种植到成熟的总时长。"""
        total_seconds = sum(
            self.SHENYAO_STAGES[s]["duration"]
            for s in range(1, 5)
            if s in self.SHENYAO_STAGES
        )
        time_ratio = self._parse_time_flow(world.get("time_flow", "1:1"))
        spirit_density = world.get("spirit_density", 1000)
        required_density = seed_config.get("spirit_density", 1000)
        growth_rate = spirit_density / required_density
        if "时间碎片" in world.get("special_resources", []):
            growth_rate *= 2
        adjusted = total_seconds / (time_ratio * growth_rate)
        days = int(adjusted // 86400)
        hours = int((adjusted % 86400) // 3600)
        return f"{days}天{hours}小时"

    async def water_single_crop(
        self, user_id: str, item_name: str, position: int
    ) -> SmallworldResult:
        """使用特殊道具浇灌单个作物，position 为 1-based。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return SmallworldResult(player_not_found=True)

        if item_name not in self.WATER_ITEMS:
            return SmallworldResult(message="该道具不能用于浇灌。")

        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return SmallworldResult(no_world=True, message="请先开辟小世界。")

        world = data[idx]
        fields = world.get("fields", [])
        if not fields:
            return SmallworldResult(message="药田中没有作物。")

        pos = position - 1
        if pos < 0 or pos >= len(fields):
            return SmallworldResult(
                message=f"位置无效，请选择 1-{len(fields)} 号作物。"
            )

        crop = fields[pos]
        seed_name = crop.get("seed_name", "")
        seed_config = self.SHENYAO_SEEDS.get(seed_name)
        if seed_config is None:
            return SmallworldResult(message="该作物配置异常，无法浇灌。")

        if crop.get("current_stage", 1) >= 5:
            return SmallworldResult(
                message=f"【{seed_name}】已成熟，无需浇灌。"
            )

        if not await self.inventory_service.has_item(user_id, "道具", item_name, 1):
            count = await self.inventory_service.get_count(user_id, "道具", item_name)
            return SmallworldResult(
                message=f"需要【{item_name}】x1，你当前拥有 {count} 个。"
            )

        await self.inventory_service.remove_item(user_id, "道具", item_name, 1)

        stages_to_advance = self.WATER_ITEMS[item_name]
        current_stage = crop.get("current_stage", 1)
        new_stage = min(current_stage + stages_to_advance, 5)
        advanced = new_stage - current_stage
        crop["current_stage"] = new_stage
        crop["accumulated_seconds"] = 0
        now = self._now()
        crop["stage_start_time"] = now
        crop["growth_log"].append(
            f"{self._format_time(now)}: 使用【{item_name}】浇灌，"
            f"推进 {advanced} 个阶段至【{self.SHENYAO_STAGES[new_stage]['name']}】"
        )

        lines = [
            f"成功使用【{item_name}】浇灌第 {position} 号作物！",
        ]
        if new_stage >= 5:
            harvest = seed_config["harvest"]
            category = "道具" if harvest == "悟道古茶树" else "丹药"
            await self.inventory_service.add_item(user_id, category, harvest, 1)
            fields.pop(pos)
            lines.append(f"作物：{seed_name} 直接成熟！")
            lines.append(f"收获：【{harvest}】x1，已自动存入纳戒。")
        else:
            stage_name = self.SHENYAO_STAGES[new_stage]["name"]
            next_stage = self.SHENYAO_STAGES.get(new_stage + 1, {}).get("name", "成熟")
            lines.append(f"作物：{seed_name} 推进 {advanced} 个生长阶段")
            lines.append(f"当前：{stage_name}")
            lines.append(f"下一阶段：{next_stage}")

        self._save(data)

        if fields:
            lines.append("\n当前药田概览：")
            lines.extend(self._format_crop_list(fields))
        return SmallworldResult(success=True, lines=lines)

    async def water_all_crops(self, user_id: str) -> SmallworldResult:
        """使用乾坤造化瓶浇灌全部作物。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return SmallworldResult(player_not_found=True)

        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return SmallworldResult(no_world=True, message="请先开辟小世界。")

        world = data[idx]
        fields = world.get("fields", [])
        if not fields:
            return SmallworldResult(message="药田中没有作物。")

        item_name = "乾坤造化瓶"
        if not await self.inventory_service.has_item(user_id, "道具", item_name, 1):
            count = await self.inventory_service.get_count(user_id, "道具", item_name)
            return SmallworldResult(
                message=f"需要【{item_name}】x1，你当前拥有 {count} 个。"
            )

        await self.inventory_service.remove_item(user_id, "道具", item_name, 1)

        harvested: list[str] = []
        now = self._now()
        for i in range(len(fields) - 1, -1, -1):
            crop = fields[i]
            seed_config = self.SHENYAO_SEEDS.get(crop.get("seed_name", ""))
            if seed_config is None:
                continue
            if crop.get("current_stage", 1) >= 5:
                continue
            crop["current_stage"] += 1
            crop["accumulated_seconds"] = 0
            crop["stage_start_time"] = now
            stage_name = self.SHENYAO_STAGES[crop["current_stage"]]["name"]
            crop["growth_log"].append(
                f"{self._format_time(now)}: 使用【{item_name}】群体浇灌，"
                f"进入【{stage_name}】阶段"
            )
            if crop["current_stage"] >= 5:
                harvest = seed_config["harvest"]
                harvested.append(harvest)
                category = "道具" if harvest == "悟道古茶树" else "丹药"
                await self.inventory_service.add_item(user_id, category, harvest, 1)
                fields.pop(i)

        self._save(data)

        lines = [
            f"成功使用【{item_name}】！",
            "小世界内所有作物生长加速！",
        ]
        if harvested:
            lines.append("以下作物已成熟并收获：")
            lines.extend(f"- {item}" for item in harvested)
        else:
            lines.append("所有作物进入下一生长阶段。")
        return SmallworldResult(success=True, lines=lines)

    async def create_environment(
        self, user_id: str, item_name: str
    ) -> SmallworldResult:
        """使用道具创造特殊环境。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return SmallworldResult(player_not_found=True)

        if not item_name or item_name not in self.ENVIRONMENT_ITEMS:
            return SmallworldResult(
                message=(
                    "【小世界环境创造指南】\n"
                    "指令：#使用[道具名]创造环境\n"
                    "可用道具及效果：\n"
                    "- 混沌源石 → 混沌土\n"
                    "- 仙泉之眼 → 仙泉\n"
                    "- 龙魂精魄 → 龙穴\n"
                    "- 雷池核心 → 雷池\n"
                    "- 仙坟土 → 仙坟\n"
                    "- 星辰核心 → 星辰矿脉\n"
                    "- 生命之种 → 生命古树\n"
                    "- 时间沙漏 → 时间碎片"
                )
            )

        environment = self.ENVIRONMENT_ITEMS[item_name]

        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return SmallworldResult(no_world=True, message="请先开辟小世界。")

        world = data[idx]
        if environment in world.get("special_resources", []):
            return SmallworldResult(
                message=f"你的小世界已拥有【{environment}】环境。"
            )

        if not await self.inventory_service.has_item(user_id, "材料", item_name, 1):
            count = await self.inventory_service.get_count(user_id, "材料", item_name)
            return SmallworldResult(
                message=f"需要【{item_name}】x1，你当前拥有 {count} 个。"
            )

        await self.inventory_service.remove_item(user_id, "材料", item_name, 1)
        world.setdefault("special_resources", []).append(environment)
        self._save(data)

        desc = {
            "混沌土": "提升混沌属性神药生长速度",
            "仙泉": "提升水属性神药生长速度",
            "龙穴": "提升龙属性神药生长速度",
            "雷池": "提升雷属性神药生长速度",
            "仙坟": "提升阴属性神药生长速度",
            "星辰矿脉": "增加灵矿产量",
            "生命古树": "增加仙馐果产量",
            "时间碎片": "加速所有作物生长",
        }
        return SmallworldResult(
            success=True,
            message=(
                f"成功使用【{item_name}】在小世界创造【{environment}】环境！\n"
                f"效果：{desc.get(environment, '特殊环境效果')}"
            ),
        )

    async def force_ripen_all(self, user_id: str) -> SmallworldResult:
        """管理员催熟所有作物。"""
        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return SmallworldResult(no_world=True, message="请先开辟小世界。")

        world = data[idx]
        fields = world.get("fields", [])
        if not fields:
            return SmallworldResult(message="药田中没有作物。")

        harvested: list[str] = []
        now = self._now()
        for i in range(len(fields) - 1, -1, -1):
            crop = fields[i]
            seed_config = self.SHENYAO_SEEDS.get(crop.get("seed_name", ""))
            if seed_config is None:
                continue
            crop["current_stage"] = 5
            crop["accumulated_seconds"] = 0
            crop["stage_start_time"] = now
            harvest = seed_config["harvest"]
            harvested.append(harvest)
            category = "道具" if harvest == "悟道古茶树" else "丹药"
            await self.inventory_service.add_item(user_id, category, harvest, 1)
            fields.pop(i)

        self._save(data)

        lines = [
            "【管理员催熟】",
            "你以无上伟力催熟小世界所有作物！",
            "成功收获以下神药：",
        ]
        lines.extend(f"- {item}" for item in harvested)
        return SmallworldResult(success=True, lines=lines)

    def _format_crop_list(self, fields: list[dict[str, Any]]) -> list[str]:
        lines = []
        for i, crop in enumerate(fields):
            seed_config = self.SHENYAO_SEEDS.get(crop.get("seed_name", ""))
            if seed_config is None:
                lines.append(f"{i + 1}号: 未知作物")
                continue
            stage = crop.get("current_stage", 1)
            progress = "▰" * stage + "▱" * (5 - stage)
            stage_name = self.SHENYAO_STAGES.get(stage, {}).get("name", "未知")
            lines.append(f"{i + 1}号: {crop['seed_name']} [{progress}] {stage_name}")
        return lines

    def _format_view(self, world: dict[str, Any]) -> list[str]:
        """格式化小世界信息为文本。"""
        config = self.WORLD_LEVELS.get(world["level"], {})
        level_name = config.get("name", f"未知等级{world['level']}")
        time_ratio = self._parse_time_flow(world.get("time_flow", "1:1"))

        lines = [
            f"---【{world.get('world_name', '未命名小世界')}】---",
            f"开辟者：{world.get('player_name', '无名')}",
            f"等级：{level_name}（{world.get('level', 1)}级）",
            f"开辟时间：{self._format_time(world.get('created_at', 0))}",
        ]
        if world.get("last_upgrade_time"):
            lines.append(
                f"上次升级：{self._format_time(world['last_upgrade_time'])}"
            )
        lines.extend(
            [
                f"灵气浓度：{world.get('spirit_density', 0)}",
                f"面积：{world.get('area', '未知')}",
                f"时间流速：{world.get('time_flow', '1:1')}（加速 {time_ratio} 倍）",
                f"药田容量：{len(world.get('fields', []))}/{world.get('field_limit', 0)}",
                f"特殊资源：{'、'.join(world.get('special_resources', [])) or '无'}",
            ]
        )

        # 药田信息
        lines.append("---【神药药田】---")
        fields = world.get("fields", [])
        if fields:
            for i, crop in enumerate(fields):
                seed_config = self.SHENYAO_SEEDS.get(crop.get("seed_name", ""))
                if seed_config is None:
                    lines.append(f"{i + 1}号: 未知作物")
                    continue
                stage = crop.get("current_stage", 1)
                stage_name = self.SHENYAO_STAGES.get(stage, {}).get("name", "未知")
                lines.append(f"{i + 1}号: {crop['seed_name']} [{stage_name}]")
                if stage < 5:
                    lines.append(f"  预计成熟：{self._estimate_growth_time(seed_config, world)}")
        else:
            lines.append("药田暂无神药种植")

        # 分身信息
        avatar = world.get("avatar")
        if avatar:
            lines.append("---【分身状态】---")
            now = self._now()
            last_harvest = avatar.get("last_harvest_time", now)
            hours_passed = (now - last_harvest) / 3600
            effective_hours = min(hours_passed * time_ratio, self.MAX_HARVEST_HOURS)
            resources = self._calculate_resources(world, effective_hours)
            resource_list = "、".join(f"{k}x{v}" for k, v in resources.items())
            lines.append(f"分身已收集资源：{effective_hours:.1f} 小时")
            lines.append(f"可收获资源：{resource_list or '无'}")
            lines.append(
                f"上次收获：{self._format_time(last_harvest)}"
            )
            lines.append("最大积累：24 小时资源")

        level_desc = {
            1: "「混沌初开，万物始生」",
            2: "「鸿蒙初判，阴阳始分」",
            3: "「紫府洞天，仙家福地」",
            4: "「太虚仙境，超凡脱俗」",
            5: "「洪荒世界，开天辟地」",
        }
        lines.append(level_desc.get(world.get("level", 1), "「此界玄妙，难以言表」"))
        return lines

    async def view_small_world(self, user_id: str) -> SmallworldResult:
        """查看小世界信息。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return SmallworldResult(player_not_found=True)

        data = self._load()
        idx = self._find_index(data, user_id)
        if idx == -1:
            return SmallworldResult(no_world=True, message="请先开辟小世界。")

        world = data[idx]
        # 查看时推进一下生长状态，让玩家看到最新情况
        self._advance_crops(world, 0)
        self._save(data)
        return SmallworldResult(success=True, lines=self._format_view(world))

    def planting_help(self) -> str:
        """种植指南文本。"""
        lines = [
            "【小世界神药种植指南】",
            "指令：#小世界栽种[种子名]",
            "可用种子列表：",
        ]
        for name, config in self.SHENYAO_SEEDS.items():
            requirements = []
            if config.get("spirit_density"):
                requirements.append(f"灵气≥{config['spirit_density']}")
            if config.get("environments"):
                requirements.append(f"需要{'、'.join(config['environments'])}")
            req_text = f"（{'，'.join(requirements)}）" if requirements else ""
            lines.append(f"- {name} → {config['harvest']} {req_text}")
        lines.extend(
            [
                "",
                "提示：",
                "1. 使用 #我的小世界 查看当前种植情况",
                "2. 使用 #使用[道具]创造环境 创建特殊环境",
                "3. 使用 #浇灌小世界作物 可群体催熟",
            ]
        )
        return "\n".join(lines)
