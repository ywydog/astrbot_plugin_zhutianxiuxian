import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.services.inventory_service import InventoryService
from src.services.player_service import PlayerService


@dataclass
class DaolvResult:
    """道侣操作结果。"""

    success: bool = False
    player_not_found: bool = False
    target_not_found: bool = False
    self_action: bool = False
    already_partner: bool = False
    pending: bool = False
    no_relationship: bool = False
    item_not_enough: bool = False
    message: str = ""
    partner_id: str | None = None
    intimacy: int = 0


class DaolvService:
    """道侣系统服务：缔结道侣、赠送礼物、断绝姻缘、查询道侣。"""

    GIFT_ITEM_NAME = "百合花篮"
    GIFT_ITEM_CATEGORY = "道具"
    GIFT_INTIMACY = 60

    def __init__(
        self,
        player_service: PlayerService,
        inventory_service: InventoryService,
        data_dir: Path,
    ):
        self.player_service = player_service
        self.inventory_service = inventory_service
        self.daolv_dir = data_dir / "daolv"
        self.daolv_dir.mkdir(parents=True, exist_ok=True)
        self.daolv_file = self.daolv_dir / "daolv.json"
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.daolv_file.exists():
            return {"relationships": []}
        return json.loads(self.daolv_file.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.daolv_file.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _relationships(self) -> list[dict[str, Any]]:
        return self._data.setdefault("relationships", [])

    def _find_record(
        self,
        user_a: str,
        user_b: str,
        pending: bool | None = None,
    ) -> dict[str, Any] | None:
        """查找两人之间的关系记录；pending 为 None 时匹配任意状态。"""
        for record in self._relationships():
            a, b = record.get("user_id"), record.get("partner_id")
            match = (a == user_a and b == user_b) or (a == user_b and b == user_a)
            if not match:
                continue
            if pending is None or record.get("pending_proposal", False) == pending:
                return record
        return None

    def _has_partner(self, user_id: str) -> dict[str, Any] | None:
        """查找用户当前已缔结的道侣记录。"""
        for record in self._relationships():
            if record.get("pending_proposal", False):
                continue
            if record.get("user_id") == user_id or record.get("partner_id") == user_id:
                return record
        return None

    def _other_id(self, record: dict[str, Any], user_id: str) -> str:
        """给定关系记录，返回对方的 user_id。"""
        if record.get("user_id") == user_id:
            return record.get("partner_id", "")
        return record.get("user_id", "")

    async def propose(self, user_id: str, target_id: str) -> DaolvResult:
        """发起结为道侣请求。"""
        if user_id == target_id:
            return DaolvResult(self_action=True, message="不能对自己发起结为道侣")

        player = await self.player_service.load(user_id)
        if player is None:
            return DaolvResult(player_not_found=True, message="你还没有踏入仙途")

        if not await self.player_service.exists(target_id):
            return DaolvResult(target_not_found=True, message="对方尚未踏入仙途")

        existing = self._find_record(user_id, target_id)
        if existing is not None:
            if existing.get("pending_proposal", False):
                return DaolvResult(
                    pending=True,
                    message="你们之间已经有一道侣请求 pending",
                )
            return DaolvResult(already_partner=True, message="你们已经是道侣了")

        if self._has_partner(user_id) is not None:
            return DaolvResult(already_partner=True, message="你已经有道侣了")
        if self._has_partner(target_id) is not None:
            return DaolvResult(already_partner=True, message="对方已经有道侣了")

        record = {
            "user_id": user_id,
            "partner_id": target_id,
            "intimacy": 0,
            "created_at": time.time(),
            "pending_proposal": True,
        }
        self._relationships().append(record)
        self._save()
        return DaolvResult(
            success=True,
            pending=True,
            message=f"已向 {target_id} 发送道侣请求，等待对方回应",
            partner_id=target_id,
        )

    async def accept(self, user_id: str) -> DaolvResult:
        """同意最近的结为道侣请求（被请求方调用）。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return DaolvResult(player_not_found=True, message="你还没有踏入仙途")

        for record in self._relationships():
            if record.get("pending_proposal") and record.get("partner_id") == user_id:
                record["pending_proposal"] = False
                record["created_at"] = time.time()
                proposer = record.get("user_id")
                self._save()
                return DaolvResult(
                    success=True,
                    message=f"已同意 {proposer} 的道侣请求",
                    partner_id=proposer,
                    intimacy=record.get("intimacy", 0),
                )

        return DaolvResult(no_relationship=True, message="没有待处理的道侣请求")

    async def reject(self, user_id: str) -> DaolvResult:
        """拒绝最近的结为道侣请求（被请求方调用）。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return DaolvResult(player_not_found=True, message="你还没有踏入仙途")

        for record in self._relationships():
            if record.get("pending_proposal") and record.get("partner_id") == user_id:
                proposer = record.get("user_id")
                self._relationships().remove(record)
                self._save()
                return DaolvResult(
                    success=True,
                    message=f"已拒绝 {proposer} 的道侣请求",
                )

        return DaolvResult(no_relationship=True, message="没有待处理的道侣请求")

    async def get_my_daolv(self, user_id: str) -> DaolvResult:
        """查询当前道侣与亲密度。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return DaolvResult(player_not_found=True, message="你还没有踏入仙途")

        record = self._has_partner(user_id)
        if record is None:
            return DaolvResult(no_relationship=True, message="你还没有道侣")

        partner_id = self._other_id(record, user_id)
        intimacy = record.get("intimacy", 0)
        return DaolvResult(
            success=True,
            message=f"你的道侣是 {partner_id}，亲密度为 {intimacy}",
            partner_id=partner_id,
            intimacy=intimacy,
        )

    async def gift(self, user_id: str, target_id: str) -> DaolvResult:
        """赠送百合花篮，增加亲密度。"""
        if user_id == target_id:
            return DaolvResult(self_action=True, message="不能送给自己")

        player = await self.player_service.load(user_id)
        if player is None:
            return DaolvResult(player_not_found=True, message="你还没有踏入仙途")

        if not await self.player_service.exists(target_id):
            return DaolvResult(target_not_found=True, message="对方尚未踏入仙途")

        record = self._find_record(user_id, target_id, pending=False)
        if record is None:
            return DaolvResult(no_relationship=True, message="你们还不是道侣")

        count = await self.inventory_service.get_count(
            user_id, self.GIFT_ITEM_CATEGORY, self.GIFT_ITEM_NAME
        )
        if count < 1:
            return DaolvResult(
                item_not_enough=True,
                message=f"你没有[{self.GIFT_ITEM_NAME}]",
            )

        remove_result = await self.inventory_service.remove_item(
            user_id, self.GIFT_ITEM_CATEGORY, self.GIFT_ITEM_NAME, 1
        )
        if not remove_result.success:
            return DaolvResult(
                item_not_enough=True,
                message=f"你没有[{self.GIFT_ITEM_NAME}]",
            )

        record["intimacy"] = record.get("intimacy", 0) + self.GIFT_INTIMACY
        self._save()
        return DaolvResult(
            success=True,
            message=f"赠送成功，你们的亲密度增加了{self.GIFT_INTIMACY}",
            partner_id=target_id,
            intimacy=record["intimacy"],
        )

    async def breakup(self, user_id: str, target_id: str) -> DaolvResult:
        """与指定玩家断绝道侣关系（简化版：直接解除）。"""
        if user_id == target_id:
            return DaolvResult(self_action=True, message="不能和自己断绝姻缘")

        player = await self.player_service.load(user_id)
        if player is None:
            return DaolvResult(player_not_found=True, message="你还没有踏入仙途")

        if not await self.player_service.exists(target_id):
            return DaolvResult(target_not_found=True, message="对方尚未踏入仙途")

        record = self._find_record(user_id, target_id)
        if record is None:
            return DaolvResult(no_relationship=True, message="你们之间没有姻缘")

        self._relationships().remove(record)
        self._save()
        return DaolvResult(
            success=True,
            message=f"已断绝与 {target_id} 的姻缘",
        )
