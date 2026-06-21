import json
from pathlib import Path
from typing import Any


class ShituData:
    """师徒关系数据加载器。"""

    def __init__(self, data_dir: Path):
        self.shitu_dir = data_dir / "shitu"
        self.shitu_dir.mkdir(parents=True, exist_ok=True)
        self.shitu_file = self.shitu_dir / "shitu.json"
        if not self.shitu_file.exists():
            self.shitu_file.write_text("[]", encoding="utf-8")
        self._records: list[dict[str, Any]] | None = None

    def _load(self) -> list[dict[str, Any]]:
        if not self.shitu_file.exists():
            return []
        return json.loads(self.shitu_file.read_text(encoding="utf-8"))

    @property
    def records(self) -> list[dict[str, Any]]:
        if self._records is None:
            self._records = self._load()
        return self._records

    def get_by_master(self, user_id: str) -> dict[str, Any] | None:
        """根据师傅 ID 获取师徒记录。"""
        for record in self.records:
            if record.get("master") == user_id:
                return record
        return None

    def get_by_apprentice(self, user_id: str) -> dict[str, Any] | None:
        """根据徒弟 ID 获取师徒记录。"""
        for record in self.records:
            if record.get("apprentice") == user_id:
                return record
        return None

    def add_master(self, user_id: str) -> dict[str, Any]:
        """为玩家创建一条师傅记录。"""
        record = {
            "master": user_id,
            "recruiting": 0,
            "apprentice": "",
            "task_stage": 0,
            "renwu1": 0,
            "renwu2": 0,
            "renwu3": 0,
            "boss_hp": 100000000,
            "graduated_apprentices": [],
        }
        self.records.append(record)
        self.save(self.records)
        return record

    def ensure_master_record(self, user_id: str) -> dict[str, Any]:
        """确保玩家存在师傅记录。"""
        record = self.get_by_master(user_id)
        if record is None:
            record = self.add_master(user_id)
        return record

    def save(self, records: list[dict[str, Any]]) -> None:
        """保存全部师徒记录。"""
        self.shitu_file.write_text(
            json.dumps(records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._records = records

    def reset(self) -> None:
        """重置缓存，下次读取重新加载。"""
        self._records = None


class ShituShopData:
    """师徒积分商城数据加载器。"""

    def __init__(self, data_dir: Path):
        self.shop_file = data_dir / "items" / "shitujifen.json"
        self._items: list[dict[str, Any]] | None = None

    def _load(self) -> list[dict[str, Any]]:
        if not self.shop_file.exists():
            return []
        return json.loads(self.shop_file.read_text(encoding="utf-8"))

    @property
    def items(self) -> list[dict[str, Any]]:
        if self._items is None:
            self._items = self._load()
        return self._items

    def get(self, name: str) -> dict[str, Any] | None:
        """按名称获取商品。"""
        for item in self.items:
            if item.get("name") == name:
                return item
        return None

    def reset(self) -> None:
        """重置缓存。"""
        self._items = None
