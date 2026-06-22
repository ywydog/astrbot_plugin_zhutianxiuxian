import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.constants.inventory import ITEM_CATEGORIES
from src.data.item_data import ItemCatalog
from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@dataclass
class ExchangeResult:
    """交易/求购操作结果。"""

    success: bool = False
    player_not_found: bool = False
    invalid_input: bool = False
    insufficient_funds: bool = False
    insufficient_items: bool = False
    item_not_found: bool = False
    listing_not_found: bool = False
    not_owner: bool = False
    self_trade: bool = False
    listings: list[dict[str, Any]] = field(default_factory=list)
    listing: dict[str, Any] | None = None
    message: str = ""


class ExchangeService:
    """交易行/求购版服务（简化版）：上架、查看、购买、下架、求购。"""

    DATA_FILE = "exchange/exchange.json"

    ITEM_CATEGORY_FILES = {
        "装备列表.json": "装备",
        "丹药列表.json": "丹药",
        "功法列表.json": "功法",
        "草药列表.json": "草药",
        "食材列表.json": "食材",
        "盒子列表.json": "盒子",
        "材料列表.json": "材料",
        "仙宠列表.json": "仙宠",
        "仙宠口粮列表.json": "仙宠口粮",
        "宝石.json": "宝石",
        "道具列表.json": "道具",
    }

    def __init__(
        self,
        player_service: PlayerService,
        inventory_service: InventoryService,
        data_dir: Path,
    ):
        self.player_service = player_service
        self.inventory_service = inventory_service
        self._file_path = data_dir / self.DATA_FILE
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._item_catalog = ItemCatalog(data_dir)

    def _load(self) -> list[dict[str, Any]]:
        if not self._file_path.exists():
            return []
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _save(self, data: list[dict[str, Any]]) -> None:
        self._file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _next_id(self, listings: list[dict[str, Any]]) -> int:
        if not listings:
            return 1
        return max(item.get("id", 0) for item in listings) + 1

    def _find_category_by_name(self, name: str) -> str | None:
        """按物品名称查找所属类别；优先查询物品目录，否则返回 None。"""
        for filename, category in self.ITEM_CATEGORY_FILES.items():
            if self._item_catalog.find_item(name, filename) is not None:
                return category
        return None

    async def _resolve_category(self, user_id: str, name: str) -> str | None:
        """先尝试从玩家纳戒中定位物品类别，再从全局物品目录查找。"""
        inventory = await self.inventory_service.load_inventory(user_id)
        if inventory is not None:
            for category in ITEM_CATEGORIES:
                for item in inventory.get(category, []):
                    if item.get("name") == name:
                        return category
        return self._find_category_by_name(name)

    async def create_sell_listing(
        self, user_id: str, name: str, quantity: int, price: int
    ) -> ExchangeResult:
        """#交易：玩家上架物品，以灵石出售。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return ExchangeResult(player_not_found=True)

        quantity = int(quantity)
        price = int(price)
        if quantity <= 0 or price <= 0:
            return ExchangeResult(
                invalid_input=True, message="数量与价格必须大于0。"
            )

        category = await self._resolve_category(user_id, name)
        if category is None:
            return ExchangeResult(item_not_found=True, message=f"未找到物品【{name}】。")

        if not await self.inventory_service.has_item(user_id, category, name, quantity):
            return ExchangeResult(
                insufficient_items=True, message=f"【{name}】数量不足。"
            )

        await self.inventory_service.remove_item(user_id, category, name, quantity)

        listings = self._load()
        listing = {
            "id": self._next_id(listings),
            "seller_id": user_id,
            "buyer_id": "",
            "name": name,
            "category": category,
            "quantity": quantity,
            "price": price,
            "type": "sell",
            "created_at": int(time.time()),
        }
        listings.append(listing)
        self._save(listings)

        return ExchangeResult(
            success=True,
            listing=listing,
            message=f"上架成功：【{name}】×{quantity}，售价 {price} 灵石。",
        )

    async def create_buy_request(
        self, user_id: str, name: str, quantity: int, price: int
    ) -> ExchangeResult:
        """#求购：玩家发布求购信息，预先扣除所需灵石。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return ExchangeResult(player_not_found=True)

        quantity = int(quantity)
        price = int(price)
        if quantity <= 0 or price <= 0:
            return ExchangeResult(
                invalid_input=True, message="数量与价格必须大于0。"
            )

        total = quantity * price
        if player.get("spirit_stones", 0) < total:
            return ExchangeResult(
                insufficient_funds=True, message=f"灵石不足，需要 {total} 灵石。"
            )

        category = self._find_category_by_name(name)
        if category is None:
            return ExchangeResult(item_not_found=True, message=f"未找到物品【{name}】。")

        await self.player_service.add_spirit_stones(user_id, -total)

        listings = self._load()
        listing = {
            "id": self._next_id(listings),
            "seller_id": "",
            "buyer_id": user_id,
            "name": name,
            "category": category,
            "quantity": quantity,
            "price": price,
            "type": "buy",
            "created_at": int(time.time()),
        }
        listings.append(listing)
        self._save(listings)

        return ExchangeResult(
            success=True,
            listing=listing,
            message=f"求购成功：【{name}】×{quantity}，单价 {price} 灵石。",
        )

    async def list_listings(self) -> ExchangeResult:
        """#查看交易：列出所有活跃挂单。"""
        listings = self._load()
        return ExchangeResult(
            success=True,
            listings=listings,
            message="交易列表已列出。",
        )

    def _find_listing(
        self, listings: list[dict[str, Any]], identifier: str
    ) -> tuple[int, dict[str, Any] | None]:
        """根据序号或物品名定位单个挂单，返回 (索引, 挂单)。"""
        try:
            index = int(identifier) - 1
            if 0 <= index < len(listings):
                return index, listings[index]
        except ValueError:
            pass

        for index, listing in enumerate(listings):
            if listing.get("name") == identifier:
                return index, listing
        return -1, None

    async def buy_item(
        self, user_id: str, identifier: str, quantity: int | None = None
    ) -> ExchangeResult:
        """#购买：按序号或物品名购买/接取挂单。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return ExchangeResult(player_not_found=True)

        listings = self._load()
        index, listing = self._find_listing(listings, identifier)
        if listing is None:
            return ExchangeResult(
                listing_not_found=True, message="未找到该交易。"
            )

        if user_id == listing.get("seller_id") or user_id == listing.get("buyer_id"):
            return ExchangeResult(self_trade=True, message="不能交易自己的挂单。")

        max_quantity = int(listing.get("quantity", 0))
        if quantity is None or quantity <= 0:
            quantity = max_quantity
        quantity = min(int(quantity), max_quantity)
        if quantity <= 0:
            return ExchangeResult(invalid_input=True, message="购买数量无效。")

        name = listing["name"]
        category = listing["category"]
        price = int(listing["price"])
        total = quantity * price

        if listing["type"] == "sell":
            if player.get("spirit_stones", 0) < total:
                return ExchangeResult(
                    insufficient_funds=True, message=f"灵石不足，需要 {total} 灵石。"
                )

            seller_id = listing["seller_id"]
            await self.player_service.add_spirit_stones(user_id, -total)
            await self.player_service.add_spirit_stones(seller_id, total)
            await self.inventory_service.add_item(user_id, category, name, quantity)

            msg = f"购买成功：花费 {total} 灵石购得【{name}】×{quantity}。"
        else:
            # 求购单：当前玩家作为卖家交付物品
            if not await self.inventory_service.has_item(user_id, category, name, quantity):
                return ExchangeResult(
                    insufficient_items=True, message=f"【{name}】数量不足。"
                )

            buyer_id = listing["buyer_id"]
            await self.inventory_service.remove_item(user_id, category, name, quantity)
            await self.inventory_service.add_item(buyer_id, category, name, quantity)
            await self.player_service.add_spirit_stones(user_id, total)

            msg = f"接取成功：交付【{name}】×{quantity}，获得 {total} 灵石。"

        remaining = max_quantity - quantity
        if remaining > 0:
            listing["quantity"] = remaining
        else:
            listings.pop(index)
        self._save(listings)

        return ExchangeResult(success=True, listing=listing, message=msg)

    async def remove_listing(self, user_id: str, name: str) -> ExchangeResult:
        """#下架：按物品名下架自己的挂单。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return ExchangeResult(player_not_found=True)

        listings = self._load()
        for index, listing in enumerate(listings):
            if listing.get("name") != name:
                continue
            if listing.get("seller_id") != user_id and listing.get("buyer_id") != user_id:
                continue

            if listing["type"] == "sell":
                await self.inventory_service.add_item(
                    user_id,
                    listing["category"],
                    listing["name"],
                    int(listing["quantity"]),
                )
                msg = f"下架成功：【{listing['name']}】已退回纳戒。"
            else:
                total = int(listing["quantity"]) * int(listing["price"])
                await self.player_service.add_spirit_stones(user_id, total)
                msg = f"取消成功：返还 {total} 灵石。"

            listings.pop(index)
            self._save(listings)
            return ExchangeResult(success=True, listing=listing, message=msg)

        return ExchangeResult(
            listing_not_found=True, message="你没有该物品的挂单。"
        )
