import json
from pathlib import Path


class ExplorationData:
    """探索副本数据加载器，管理秘境、禁地、仙府、仙境等地点数据。"""

    FILE_MAP = {
        "secret_place": "副本/地点列表.json",
        "forbidden_area": "副本/禁地列表.json",
        "time_place": "副本/限定仙府.json",
        "fairy_realm": "副本/仙境列表.json",
        "zhetian": "副本/遮天宇宙列表.json",
        "xiajie": "副本/下界八域列表.json",
        "jiutianshidi": "副本/九天十地.json",
        "jiehai": "副本/界海列表.json",
        "shangcang": "副本/上苍之上列表.json",
        "time_river": "副本/时间长河列表.json",
        "guild_secret": "副本/宗门秘境.json",
    }

    def __init__(self, data_dir: Path):
        self.items_dir = data_dir / "items"
        self._cache: dict[str, list[dict]] = {}

    def _load(self, filename: str) -> list[dict]:
        file_path = self.items_dir / filename
        if not file_path.exists():
            return []
        return json.loads(file_path.read_text(encoding="utf-8"))

    def _get(self, key: str) -> list[dict]:
        if key not in self._cache:
            self._cache[key] = self._load(self.FILE_MAP[key])
        return self._cache[key]

    def get_secret_places(self) -> list[dict]:
        """获取秘境地点列表。"""
        return self._get("secret_place")

    def get_forbidden_areas(self) -> list[dict]:
        """获取禁地地点列表。"""
        return self._get("forbidden_area")

    def get_time_places(self) -> list[dict]:
        """获取限定仙府列表。"""
        return self._get("time_place")

    def get_fairy_realms(self) -> list[dict]:
        """获取仙境列表。"""
        return self._get("fairy_realm")

    def get_zhetian_places(self) -> list[dict]:
        """获取遮天位面地点列表。"""
        return self._get("zhetian")

    def get_xiajie_places(self) -> list[dict]:
        """获取下界八域地点列表。"""
        return self._get("xiajie")

    def get_jiutianshidi_places(self) -> list[dict]:
        """获取九天十地地点列表。"""
        return self._get("jiutianshidi")

    def get_jiehai_places(self) -> list[dict]:
        """获取界海地点列表。"""
        return self._get("jiehai")

    def get_shangcang_places(self) -> list[dict]:
        """获取上苍之上地点列表。"""
        return self._get("shangcang")

    def get_time_river_places(self) -> list[dict]:
        """获取时间长河地点列表。"""
        return self._get("time_river")

    def get_guild_secrets(self) -> list[dict]:
        """获取宗门秘境列表。"""
        return self._get("guild_secret")

    def _find_in(self, places: list[dict], name: str) -> dict | None:
        for place in places:
            if place.get("name") == name:
                return place
        return None

    def find_secret_place(self, name: str) -> dict | None:
        return self._find_in(self.get_secret_places(), name)

    def find_forbidden_area(self, name: str) -> dict | None:
        return self._find_in(self.get_forbidden_areas(), name)

    def find_time_place(self, name: str) -> dict | None:
        return self._find_in(self.get_time_places(), name)

    def find_fairy_realm(self, name: str) -> dict | None:
        return self._find_in(self.get_fairy_realms(), name)

    def find_zhetian_place(self, name: str) -> dict | None:
        return self._find_in(self.get_zhetian_places(), name)

    def find_xiajie_place(self, name: str) -> dict | None:
        return self._find_in(self.get_xiajie_places(), name)

    def find_jiutianshidi_place(self, name: str) -> dict | None:
        return self._find_in(self.get_jiutianshidi_places(), name)

    def find_jiehai_place(self, name: str) -> dict | None:
        return self._find_in(self.get_jiehai_places(), name)

    def find_shangcang_place(self, name: str) -> dict | None:
        return self._find_in(self.get_shangcang_places(), name)

    def find_time_river_place(self, name: str) -> dict | None:
        return self._find_in(self.get_time_river_places(), name)

    def find_guild_secret(self, name: str) -> dict | None:
        return self._find_in(self.get_guild_secrets(), name)

    def find_place(self, name: str) -> dict | None:
        """在所有探索地点中按名称查找。"""
        getters = [
            self.find_secret_place,
            self.find_forbidden_area,
            self.find_time_place,
            self.find_fairy_realm,
            self.find_zhetian_place,
            self.find_xiajie_place,
            self.find_jiutianshidi_place,
            self.find_jiehai_place,
            self.find_shangcang_place,
            self.find_time_river_place,
            self.find_guild_secret,
        ]
        for getter in getters:
            place = getter(name)
            if place is not None:
                return place
        return None
