import copy
from dataclasses import dataclass, field
from typing import Any

from src.constants.inventory import (
    DEFAULT_INVENTORY,
    DEFAULT_SPIRIT_STONE_LIMIT,
    ITEM_CATEGORIES,
)
from src.services.player_service import PlayerService


@dataclass
class InventoryResult:
    """纳戒操作结果。"""

    player_not_found: bool = False
    success: bool = False
    category: str = ""
    name: str = ""
    quantity: int = 0
    remaining: int = 0
    message: str = ""


@dataclass
class InventoryViewResult:
    """纳戒查看结果。"""

    player_not_found: bool = False
    name: str = ""
    level: int = 1
    spirit_stones: int = 0
    spirit_stone_limit: int = 5000
    categories: dict[str, list[dict]] = field(default_factory=dict)


class InventoryService:
    """纳戒服务：管理玩家物品。"""

    def __init__(self, player_service: PlayerService):
        self.player_service = player_service

    @staticmethod
    def default_inventory() -> dict[str, Any]:
        """返回初始纳戒结构。"""
        return copy.deepcopy(DEFAULT_INVENTORY)

    async def load_inventory(self, user_id: str) -> dict[str, Any] | None:
        """加载玩家纳戒；若玩家不存在返回 None。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return None
        inventory = player.get("najie")
        if inventory is None:
            inventory = self.default_inventory()
            player["najie"] = inventory
            await self.player_service.save(user_id, player)
        return inventory

    async def view(self, user_id: str) -> InventoryViewResult:
        """查看纳戒。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return InventoryViewResult(player_not_found=True)

        inventory = player.get("najie")
        if inventory is None:
            inventory = self.default_inventory()
            player["najie"] = inventory
            await self.player_service.save(user_id, player)

        categories = {
            category: list(inventory.get(category, []))
            for category in ITEM_CATEGORIES
        }
        return InventoryViewResult(
            name=player.get("name", "无名"),
            level=int(inventory.get("level", 1)),
            spirit_stones=int(inventory.get("spirit_stones", 0)),
            spirit_stone_limit=int(
                inventory.get("spirit_stone_limit", DEFAULT_SPIRIT_STONE_LIMIT)
            ),
            categories=categories,
        )

    async def add_item(
        self,
        user_id: str,
        category: str,
        name: str,
        quantity: int = 1,
        **extra: Any,
    ) -> InventoryResult:
        """向纳戒添加物品。"""
        if category not in ITEM_CATEGORIES:
            return InventoryResult(
                category=category, name=name, quantity=quantity, message="未知物品类别"
            )

        player = await self.player_service.load(user_id)
        if player is None:
            return InventoryResult(player_not_found=True)

        inventory = player.setdefault("najie", self.default_inventory())
        items: list[dict] = inventory.setdefault(category, [])

        quantity = int(quantity)
        if quantity <= 0:
            return InventoryResult(
                category=category,
                name=name,
                quantity=quantity,
                message="添加数量必须大于0",
            )

        # 尝试合并同类可堆叠物品（无特殊属性差异时）
        merged = False
        if category in ("丹药", "道具", "草药", "食材", "盒子", "材料", "仙宠口粮"):
            for item in items:
                if item.get("name") == name:
                    item["quantity"] = int(item.get("quantity", 1)) + quantity
                    merged = True
                    break

        if not merged:
            new_item = {"name": name, "quantity": quantity, **extra}
            items.append(new_item)

        await self.player_service.save(user_id, player)

        return InventoryResult(
            success=True,
            category=category,
            name=name,
            quantity=quantity,
            remaining=next(
                (
                    int(item.get("quantity", quantity))
                    for item in items
                    if item.get("name") == name
                ),
                quantity,
            ),
        )

    async def remove_item(
        self,
        user_id: str,
        category: str,
        name: str,
        quantity: int = 1,
    ) -> InventoryResult:
        """从纳戒移除物品。"""
        if category not in ITEM_CATEGORIES:
            return InventoryResult(
                category=category, name=name, quantity=quantity, message="未知物品类别"
            )

        player = await self.player_service.load(user_id)
        if player is None:
            return InventoryResult(player_not_found=True)

        inventory = player.get("najie")
        if inventory is None:
            return InventoryResult(
                category=category,
                name=name,
                quantity=quantity,
                message="纳戒为空",
            )

        items: list[dict] = inventory.get(category, [])
        for item in items:
            if item.get("name") == name:
                current = int(item.get("quantity", 1))
                if current < quantity:
                    return InventoryResult(
                        category=category,
                        name=name,
                        quantity=quantity,
                        message="物品数量不足",
                    )

                remaining = current - quantity
                item["quantity"] = remaining
                if remaining <= 0:
                    items.remove(item)

                await self.player_service.save(user_id, player)
                return InventoryResult(
                    success=True,
                    category=category,
                    name=name,
                    quantity=quantity,
                    remaining=max(remaining, 0),
                )

        return InventoryResult(
            category=category,
            name=name,
            quantity=quantity,
            message="物品不存在",
        )

    async def has_item(
        self,
        user_id: str,
        category: str,
        name: str,
        quantity: int = 1,
    ) -> bool:
        """检查纳戒中是否拥有足够数量的物品。"""
        if category not in ITEM_CATEGORIES:
            return False

        inventory = await self.load_inventory(user_id)
        if inventory is None:
            return False

        for item in inventory.get(category, []):
            if item.get("name") == name and int(item.get("quantity", 1)) >= quantity:
                return True
        return False

    async def get_count(
        self,
        user_id: str,
        category: str,
        name: str,
    ) -> int:
        """获取纳戒中某物品数量。"""
        if category not in ITEM_CATEGORIES:
            return 0

        inventory = await self.load_inventory(user_id)
        if inventory is None:
            return 0

        return sum(
            int(item.get("quantity", 1))
            for item in inventory.get(category, [])
            if item.get("name") == name
        )
