import json
from pathlib import Path
from typing import Any


class ShopData:
    """洗劫商店数据加载器。"""

    def __init__(self, data_dir: Path):
        self.shops_file = data_dir / "items" / "shops.json"
        self._shops: list[dict[str, Any]] | None = None

    def _load(self) -> list[dict[str, Any]]:
        if not self.shops_file.exists():
            return []
        return json.loads(self.shops_file.read_text(encoding="utf-8"))

    @property
    def shops(self) -> list[dict[str, Any]]:
        if self._shops is None:
            self._shops = self._load()
        return self._shops

    def get(self, name: str) -> dict[str, Any] | None:
        """按名称获取商店。"""
        for shop in self.shops:
            if shop.get("name") == name:
                return shop
        return None

    def save(self, shops: list[dict[str, Any]]) -> None:
        """保存商店列表。"""
        self.shops_file.write_text(
            json.dumps(shops, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._shops = shops

    def reset(self) -> None:
        """重置缓存，下次读取重新加载。"""
        self._shops = None
