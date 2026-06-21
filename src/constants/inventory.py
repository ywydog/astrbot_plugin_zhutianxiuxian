from typing import Any


ITEM_CATEGORIES = [
    "装备",
    "丹药",
    "道具",
    "功法",
    "草药",
    "食材",
    "盒子",
    "材料",
    "仙宠",
    "仙宠口粮",
    "宝石",
]

DEFAULT_SPIRIT_STONE_LIMIT = 5000


def default_inventory() -> dict[str, Any]:
    """返回初始纳戒结构。"""
    inventory: dict[str, Any] = {
        "level": 1,
        "spirit_stone_limit": DEFAULT_SPIRIT_STONE_LIMIT,
        "spirit_stones": 0,
    }
    for category in ITEM_CATEGORIES:
        inventory[category] = []
    return inventory


DEFAULT_INVENTORY = default_inventory()
