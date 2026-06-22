import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.constants.inventory import ITEM_CATEGORIES
from src.data.item_data import ItemCatalog
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@dataclass
class InnerWorldOpenResult:
    success: bool = False
    player_not_found: bool = False
    opened: bool = False
    message: str = ""


@dataclass
class InnerWorldResult:
    success: bool = False
    player_not_found: bool = False
    not_open: bool = False
    category: str = ""
    name: str = ""
    quantity: int = 0
    item_size: int = 0
    used_space: int = 0
    max_capacity: int = 0
    stored_count: int = 0
    taken_count: int = 0
    message: str = ""


@dataclass
class InnerWorldViewResult:
    success: bool = False
    player_not_found: bool = False
    not_open: bool = False
    message: str = ""


class InnerWorldService:
    """内景地空间仓库服务：开辟、存取、升级、一键存取、查看。"""

    DATA_FILE = "inner_world/inner_worlds.json"

    # 开辟消耗（元神）
    OPEN_COST = 5_000_000
    # 升级基础消耗（源石）= 当前等级 * BASE_UPGRADE_COST
    BASE_UPGRADE_COST = 500_000
    # 初始容量与每级增量
    BASE_CAPACITY = 500
    CAPACITY_PER_LEVEL = 500

    # 物品占用空间权重（按数量）
    ITEM_SPACE_RULES: dict[str, Any] = {
        "装备": lambda q: q * 2,
        "仙宠": lambda q: q * 3,
        "丹药": lambda q: q * 0.5,
        "道具": lambda q: q * 1,
        "功法": lambda q: q * 1.2,
        "草药": lambda q: q * 0.8,
        "食材": lambda q: q * 0.8,
        "盒子": lambda q: q * 0.5,
        "材料": lambda q: q * 1,
        "仙宠口粮": lambda q: q * 1,
        "宝石": lambda q: q * 1.5,
    }

    def __init__(
        self,
        player_service: PlayerService,
        inventory_service: InventoryService,
        item_catalog: ItemCatalog,
        data_dir: Path,
    ):
        self.player_service = player_service
        self.inventory_service = inventory_service
        self.item_catalog = item_catalog
        self._file_path = data_dir / self.DATA_FILE
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    # ---------- 数据持久化 ----------

    def _load(self) -> dict[str, Any]:
        if not self._file_path.exists():
            return {}
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self._file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _default_world(self) -> dict[str, Any]:
        world: dict[str, Any] = {
            "level": 1,
            "used_space": 0,
            "max_capacity": self.BASE_CAPACITY,
            "last_update": int(time.time()),
        }
        for category in ITEM_CATEGORIES:
            world[category] = []
        return world

    async def get_world(self, user_id: str) -> dict[str, Any] | None:
        data = self._load()
        world = data.get(user_id)
        if world is None:
            return None
        # 补全可能缺失的分类
        for category in ITEM_CATEGORIES:
            world.setdefault(category, [])
        return world

    def _set_world(self, user_id: str, world: dict[str, Any]) -> None:
        data = self._load()
        data[user_id] = world
        self._save(data)

    # ---------- 工具方法 ----------

    def _item_size(self, category: str, quantity: int) -> int:
        rule = self.ITEM_SPACE_RULES.get(category, lambda q: q * 1)
        return math.ceil(rule(quantity))

    async def _find_in_inventory(
        self, user_id: str, name: str
    ) -> tuple[str, list[dict[str, Any]]] | None:
        """在纳戒中查找物品，返回 (类别, 匹配条目列表)。装备可能按品级分多条。"""
        inventory = await self.inventory_service.load_inventory(user_id)
        if inventory is None:
            return None
        for category in ITEM_CATEGORIES:
            items = inventory.get(category, [])
            matched = [item for item in items if item.get("name") == name]
            if matched:
                return category, matched
        return None

    def _find_in_world(
        self, world: dict[str, Any], name: str
    ) -> tuple[str, list[dict[str, Any]]]:
        """在内景地中查找物品，返回 (类别, 匹配条目列表)。"""
        for category in ITEM_CATEGORIES:
            matched = [item for item in world.get(category, []) if item.get("name") == name]
            if matched:
                return category, matched
        return "", []

    @staticmethod
    def _parse_quantity(quantity_str: str, available: int) -> int | None:
        text = quantity_str.strip().lower()
        if text == "all":
            return available
        try:
            value = int(text)
        except ValueError:
            return None
        if value <= 0:
            return None
        return value

    # ---------- 开辟 ----------

    async def open(self, user_id: str) -> InnerWorldOpenResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return InnerWorldOpenResult(player_not_found=True)

        world = await self.get_world(user_id)
        if world is not None:
            return InnerWorldOpenResult(message="你已开辟过内景地空间，无需重复开辟。")

        if player.get("yuanshen", 0) < self.OPEN_COST:
            return InnerWorldOpenResult(
                message=f"你的元神并不足以开辟内景地空间，需要 {self.OPEN_COST:,} 元神。"
            )

        player["yuanshen"] = player.get("yuanshen", 0) - self.OPEN_COST
        await self.player_service.save(user_id, player)

        world = self._default_world()
        self._set_world(user_id, world)

        return InnerWorldOpenResult(
            success=True,
            opened=True,
            message="泥丸宫中轰然震动！你以无上元神之力在体内开辟出一方内景地空间，初始容量 500 格。",
        )

    # ---------- 查看 ----------

    async def view(self, user_id: str) -> InnerWorldViewResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return InnerWorldViewResult(player_not_found=True)

        world = await self.get_world(user_id)
        if world is None:
            return InnerWorldViewResult(not_open=True, message="你尚未开辟内景地空间，使用 #开辟内景地空间 开启。")

        lines = [
            "【内景地空间】",
            f"等级：{world['level']}",
            f"容量：{world['used_space']}/{world['max_capacity']} 格",
            f"剩余：{world['max_capacity'] - world['used_space']} 格",
        ]

        has_item = False
        for category in ITEM_CATEGORIES:
            items = world.get(category, [])
            if not items:
                continue
            has_item = True
            item_lines = []
            for item in items:
                qty = item.get("quantity", 1)
                pinji = item.get("pinji")
                pinji_text = f"（品级{pinji}）" if pinji is not None else ""
                item_lines.append(f"  {item['name']}{pinji_text} ×{qty}")
            lines.append(f"【{category}】")
            lines.extend(item_lines)

        if not has_item:
            lines.append("内景地中空空如也。")

        return InnerWorldViewResult(success=True, message="\n".join(lines))

    # ---------- 存入 ----------

    async def store(
        self, user_id: str, name: str, quantity_str: str
    ) -> InnerWorldResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return InnerWorldResult(player_not_found=True)

        world = await self.get_world(user_id)
        if world is None:
            return InnerWorldResult(
                not_open=True, message="你尚未开辟内景地空间，使用 #开辟内景地空间 开启。"
            )

        found = await self._find_in_inventory(user_id, name)
        if found is None:
            return InnerWorldResult(message=f"纳戒中不存在【{name}】，请检查名称。")

        category, matched_items = found
        available = sum(int(item.get("quantity", 1)) for item in matched_items)
        quantity = self._parse_quantity(quantity_str, available)
        if quantity is None:
            return InnerWorldResult(message="数量格式错误，请输入正整数或 all。")
        if quantity > available:
            return InnerWorldResult(
                message=f"【{name}】数量不足，当前拥有 {available} 个。"
            )

        item_size = self._item_size(category, quantity)
        if world["used_space"] + item_size > world["max_capacity"]:
            return InnerWorldResult(
                message=(
                    f"内景地空间不足。需要 {item_size} 格，"
                    f"剩余 {world['max_capacity'] - world['used_space']} 格。"
                )
            )

        # 从纳戒扣除，优先扣除无品级或低品级可简单处理：按条目顺序扣除
        remaining_to_remove = quantity
        for item in matched_items:
            if remaining_to_remove <= 0:
                break
            item_qty = int(item.get("quantity", 1))
            remove_qty = min(remaining_to_remove, item_qty)
            pinji = item.get("pinji")
            await self.inventory_service.remove_item(
                user_id, category, name, remove_qty, pinji=pinji
            )
            self._add_to_world(world, category, name, remove_qty, pinji)
            remaining_to_remove -= remove_qty

        world["used_space"] += item_size
        world["last_update"] = int(time.time())
        self._set_world(user_id, world)

        return InnerWorldResult(
            success=True,
            category=category,
            name=name,
            quantity=quantity,
            item_size=item_size,
            used_space=world["used_space"],
            max_capacity=world["max_capacity"],
            message=f"成功将 {quantity} 个【{name}】存入内景地（{category}区），占用 {item_size} 格。",
        )

    def _add_to_world(
        self,
        world: dict[str, Any],
        category: str,
        name: str,
        quantity: int,
        pinji: int | None,
    ) -> None:
        """向内景地添加物品，按名称+品级合并。"""
        items: list[dict[str, Any]] = world.setdefault(category, [])
        for item in items:
            if item.get("name") == name and item.get("pinji") == pinji:
                item["quantity"] = int(item.get("quantity", 1)) + quantity
                item["last_update"] = int(time.time())
                return

        new_item: dict[str, Any] = {
            "name": name,
            "quantity": quantity,
            "store_time": int(time.time()),
        }
        if pinji is not None:
            new_item["pinji"] = pinji
        items.append(new_item)

    # ---------- 取出 ----------

    async def take(
        self, user_id: str, name: str, quantity_str: str
    ) -> InnerWorldResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return InnerWorldResult(player_not_found=True)

        world = await self.get_world(user_id)
        if world is None:
            return InnerWorldResult(
                not_open=True, message="你尚未开辟内景地空间，使用 #开辟内景地空间 开启。"
            )

        category, matched_items = self._find_in_world(world, name)
        if not matched_items:
            return InnerWorldResult(message=f"内景地中不存在【{name}】。")

        available = sum(int(item.get("quantity", 1)) for item in matched_items)
        quantity = self._parse_quantity(quantity_str, available)
        if quantity is None:
            return InnerWorldResult(message="数量格式错误，请输入正整数或 all。")
        if quantity > available:
            return InnerWorldResult(
                message=f"内景地中【{name}】数量不足，当前有 {available} 个。"
            )

        # 按存入时间先后取出
        matched_items.sort(key=lambda x: x.get("store_time", 0))
        released_space = 0
        remaining_to_take = quantity
        kept_items = []

        for item in matched_items:
            if remaining_to_take <= 0:
                kept_items.append(item)
                continue

            item_qty = int(item.get("quantity", 1))
            take_qty = min(remaining_to_take, item_qty)
            remaining_qty = item_qty - take_qty
            pinji = item.get("pinji")

            extras = {}
            if pinji is not None:
                extras["pinji"] = pinji
            await self.inventory_service.add_item(
                user_id, category, name, take_qty, **extras
            )

            released_space += self._item_size(category, item_qty) - self._item_size(
                category, remaining_qty
            )
            remaining_to_take -= take_qty

            if remaining_qty > 0:
                item["quantity"] = remaining_qty
                kept_items.append(item)

        world[category] = [
            item for item in world.get(category, [])
            if not (item.get("name") == name and item not in kept_items)
        ] + kept_items
        # 清理数量为 0 的条目
        world[category] = [item for item in world[category] if int(item.get("quantity", 1)) > 0]

        world["used_space"] = max(0, world["used_space"] - released_space)
        world["last_update"] = int(time.time())
        self._set_world(user_id, world)

        return InnerWorldResult(
            success=True,
            category=category,
            name=name,
            quantity=quantity,
            item_size=released_space,
            used_space=world["used_space"],
            max_capacity=world["max_capacity"],
            message=f"成功从内景地取出 {quantity} 个【{name}】，释放 {released_space} 格空间。",
        )

    # ---------- 升级 ----------

    async def upgrade(self, user_id: str) -> InnerWorldResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return InnerWorldResult(player_not_found=True)

        world = await self.get_world(user_id)
        if world is None:
            return InnerWorldResult(
                not_open=True, message="你尚未开辟内景地空间，使用 #开辟内景地空间 开启。"
            )

        cost = world["level"] * self.BASE_UPGRADE_COST
        if player.get("source_stones", 0) < cost:
            return InnerWorldResult(
                message=f"源石不足，升级需要 {cost:,} 源石，当前拥有 {player.get('source_stones', 0):,}。"
            )

        player["source_stones"] = player.get("source_stones", 0) - cost
        await self.player_service.save(user_id, player)

        world["level"] += 1
        world["max_capacity"] += self.CAPACITY_PER_LEVEL
        world["last_update"] = int(time.time())
        self._set_world(user_id, world)

        return InnerWorldResult(
            success=True,
            used_space=world["used_space"],
            max_capacity=world["max_capacity"],
            message=(
                f"内景地空间升级成功！等级 {world['level'] - 1} → {world['level']}，"
                f"容量 {world['max_capacity'] - self.CAPACITY_PER_LEVEL} → {world['max_capacity']} 格，"
                f"消耗 {cost:,} 源石。"
            ),
        )

    # ---------- 一键存入 ----------

    async def store_all(self, user_id: str) -> InnerWorldResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return InnerWorldResult(player_not_found=True)

        world = await self.get_world(user_id)
        if world is None:
            return InnerWorldResult(
                not_open=True, message="你尚未开辟内景地空间，使用 #开辟内景地空间 开启。"
            )

        inventory = await self.inventory_service.load_inventory(user_id)
        if inventory is None:
            return InnerWorldResult(message="无法读取纳戒。")

        total_stored = 0
        details: list[str] = []
        for category in ITEM_CATEGORIES:
            items = list(inventory.get(category, []))
            for item in items:
                name = item.get("name")
                qty = int(item.get("quantity", 1))
                pinji = item.get("pinji")
                item_size = self._item_size(category, qty)

                if world["used_space"] + item_size > world["max_capacity"]:
                    continue

                await self.inventory_service.remove_item(
                    user_id, category, name, qty, pinji=pinji
                )
                self._add_to_world(world, category, name, qty, pinji)
                world["used_space"] += item_size
                total_stored += qty
                details.append(f"{name}×{qty}")

        world["last_update"] = int(time.time())
        self._set_world(user_id, world)

        if total_stored == 0:
            return InnerWorldResult(message="没有可存入的物品，或空间已满。")

        return InnerWorldResult(
            success=True,
            stored_count=total_stored,
            used_space=world["used_space"],
            max_capacity=world["max_capacity"],
            message=(
                f"一键存入完成，共存入 {total_stored} 件物品。\n"
                f"当前容量：{world['used_space']}/{world['max_capacity']} 格\n"
                f"详情：{', '.join(details[:10])}"
                + ("..." if len(details) > 10 else "")
            ),
        )

    # ---------- 一键取出 ----------

    async def take_all(
        self, user_id: str, category_filter: str | None = None
    ) -> InnerWorldResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return InnerWorldResult(player_not_found=True)

        world = await self.get_world(user_id)
        if world is None:
            return InnerWorldResult(
                not_open=True, message="你尚未开辟内景地空间，使用 #开辟内景地空间 开启。"
            )

        categories = (
            [category_filter]
            if category_filter and category_filter in ITEM_CATEGORIES
            else ITEM_CATEGORIES
        )

        total_taken = 0
        details: list[str] = []
        for category in categories:
            items = list(world.get(category, []))
            if not items:
                continue
            for item in items:
                name = item.get("name")
                qty = int(item.get("quantity", 1))
                pinji = item.get("pinji")
                extras = {"pinji": pinji} if pinji is not None else {}
                await self.inventory_service.add_item(
                    user_id, category, name, qty, **extras
                )
                total_taken += qty
                details.append(f"{name}×{qty}")
            world[category] = []

        world["used_space"] = 0
        for category in ITEM_CATEGORIES:
            for item in world.get(category, []):
                world["used_space"] += self._item_size(
                    category, int(item.get("quantity", 1))
                )
        world["last_update"] = int(time.time())
        self._set_world(user_id, world)

        if total_taken == 0:
            return InnerWorldResult(message="内景地中没有可取出的物品。")

        return InnerWorldResult(
            success=True,
            taken_count=total_taken,
            used_space=world["used_space"],
            max_capacity=world["max_capacity"],
            message=(
                f"一键取出完成，共取出 {total_taken} 件物品。\n"
                f"当前容量：{world['used_space']}/{world['max_capacity']} 格\n"
                f"详情：{', '.join(details[:10])}"
                + ("..." if len(details) > 10 else "")
            ),
        )

    async def take_category(self, user_id: str, category: str) -> InnerWorldResult:
        if category not in ITEM_CATEGORIES:
            return InnerWorldResult(message=f"无效的物品类别：{category}。")
        return await self.take_all(user_id, category_filter=category)
