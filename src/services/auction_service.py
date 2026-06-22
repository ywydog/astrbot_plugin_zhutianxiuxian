import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@dataclass
class AuctionResult:
    success: bool = False
    player_not_found: bool = False
    no_auction: bool = False
    has_auction: bool = False
    invalid_input: bool = False
    insufficient_funds: bool = False
    insufficient_items: bool = False
    self_bid: bool = False
    cooldown: bool = False
    cooldown_seconds: int = 0
    auction: dict[str, Any] | None = None
    message: str = ""


class AuctionService:
    """玩家拍卖行服务（简化版）：上架、查看、竞价、结算。"""

    DATA_FILE = "auction/auction.json"
    COOLDOWN_SECONDS = 24 * 3600
    MIN_BID_INCREASE = 1.1

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

    def _load(self) -> dict[str, Any]:
        if not self._file_path.exists():
            return {}
        return json.loads(self._file_path.read_text(encoding="utf-8"))

    def _save(self, data: dict[str, Any]) -> None:
        self._file_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    async def create_auction(
        self,
        user_id: str,
        name: str,
        start_price: int,
        quantity: int,
        group_id: str = "",
    ) -> AuctionResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return AuctionResult(player_not_found=True)

        data = self._load()
        if data.get("auction"):
            return AuctionResult(has_auction=True, message="已有拍卖正在进行。")

        now = int(time.time())
        last = data.get("last_auction", {}).get(user_id, 0)
        if now - last < self.COOLDOWN_SECONDS:
            remain = self.COOLDOWN_SECONDS - (now - last)
            return AuctionResult(
                cooldown=True,
                cooldown_seconds=remain,
                message=f"每24小时可上架一次，还需等待 {remain // 3600} 小时。",
            )

        if start_price <= 0 or quantity <= 0:
            return AuctionResult(
                invalid_input=True, message="起拍价与数量必须大于0。"
            )

        # 查找物品并确定类别
        inventory = await self.inventory_service.load_inventory(user_id)
        if inventory is None:
            return AuctionResult(insufficient_items=True, message="纳戒为空。")

        item_info = None
        category = ""
        for cat in [
            "装备", "丹药", "功法", "道具", "草药", "材料", "食材", "盒子"
        ]:
            for item in inventory.get(cat, []):
                if item.get("name") == name:
                    item_info = item
                    category = cat
                    break
            if item_info:
                break

        if item_info is None:
            return AuctionResult(
                insufficient_items=True, message=f"你没有【{name}】。"
            )

        if await self.inventory_service.get_count(user_id, category, name) < quantity:
            return AuctionResult(
                insufficient_items=True, message=f"{name} 数量不足。"
            )

        await self.inventory_service.remove_item(user_id, category, name, quantity)

        auction = {
            "seller_id": user_id,
            "seller_name": player.get("name", user_id),
            "name": name,
            "category": category,
            "quantity": quantity,
            "start_price": start_price,
            "last_price": start_price,
            "last_bidder_id": "",
            "last_bidder_name": "",
            "last_bid_time": now,
            "group_ids": [group_id] if group_id else [],
            "start_time": now,
        }

        data["auction"] = auction
        data.setdefault("last_auction", {})[user_id] = now
        self._save(data)

        return AuctionResult(
            success=True,
            auction=auction,
            message=f"开始拍卖【{name}】×{quantity}，起拍价 {start_price} 灵石。",
        )

    async def get_auction(self) -> AuctionResult:
        data = self._load()
        auction = data.get("auction")
        if not auction:
            return AuctionResult(no_auction=True, message="目前没有拍卖正在进行。")
        return AuctionResult(success=True, auction=auction)

    async def bid(
        self, user_id: str, price: int | None = None
    ) -> AuctionResult:
        player = await self.player_service.load(user_id)
        if player is None:
            return AuctionResult(player_not_found=True)

        data = self._load()
        auction = data.get("auction")
        if not auction:
            return AuctionResult(no_auction=True, message="没有拍卖正在进行。")

        if user_id == auction["seller_id"]:
            return AuctionResult(self_bid=True, message="禁止自娱自乐。")

        if user_id == auction["last_bidder_id"]:
            return AuctionResult(self_bid=True, message="你已是最高出价者。")

        last_price = int(auction["last_price"])
        min_price = int(last_price * self.MIN_BID_INCREASE)
        if price is None or price <= 0:
            price = min_price

        if price < min_price:
            return AuctionResult(
                invalid_input=True,
                message=f"最新价 {last_price}，每次加价不少于10%（至少 {min_price}）。",
            )

        if player.get("spirit_stones", 0) < price:
            return AuctionResult(insufficient_funds=True, message="灵石不足。")

        # 退还上一轮出价者灵石（如果有）
        prev_bidder = auction.get("last_bidder_id")
        if prev_bidder:
            await self.player_service.add_spirit_stones(
                prev_bidder, int(auction["last_price"])
            )

        # 扣除当前出价者灵石
        await self.player_service.add_spirit_stones(user_id, -price)

        auction["last_price"] = price
        auction["last_bidder_id"] = user_id
        auction["last_bidder_name"] = player.get("name", user_id)
        auction["last_bid_time"] = int(time.time())
        self._save(data)

        return AuctionResult(
            success=True,
            auction=auction,
            message=f"{player.get('name', user_id)} 出价 {price} 灵石。",
        )

    async def settle(self) -> AuctionResult:
        """结算当前拍卖：将物品交给最高出价者，灵石交给卖家。"""
        data = self._load()
        auction = data.get("auction")
        if not auction:
            return AuctionResult(no_auction=True)

        seller_id = auction["seller_id"]
        bidder_id = auction.get("last_bidder_id")
        price = int(auction["last_price"])
        name = auction["name"]
        category = auction["category"]
        quantity = int(auction["quantity"])

        if bidder_id:
            # 卖家获得灵石
            await self.player_service.add_spirit_stones(seller_id, price)
            # 出价者获得物品
            await self.inventory_service.add_item(
                bidder_id, category, name, quantity
            )
            msg = (
                f"拍卖结束！{auction.get('last_bidder_name', bidder_id)} "
                f"以 {price} 灵石拍得【{name}】×{quantity}。"
            )
        else:
            # 流拍，物品退回
            await self.inventory_service.add_item(
                seller_id, category, name, quantity
            )
            msg = f"拍卖结束，【{name}】×{quantity} 流拍退回。"

        del data["auction"]
        self._save(data)
        return AuctionResult(success=True, message=msg)
