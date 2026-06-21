import json
from pathlib import Path


class OccupationData:
    """职业数据加载器。"""

    def __init__(self, data_dir: Path):
        self.occupation_dir = data_dir / "occupation"
        self._occupations: list[dict] | None = None
        self._experience: list[dict] | None = None
        self._recipes: dict[str, list[dict]] | None = None

    def _load(self, filename: str) -> list[dict]:
        file_path = self.occupation_dir / filename
        if not file_path.exists():
            return []
        return json.loads(file_path.read_text(encoding="utf-8"))

    @property
    def occupations(self) -> list[dict]:
        if self._occupations is None:
            self._occupations = self._load("职业列表.json")
        return self._occupations

    @property
    def experience(self) -> list[dict]:
        """职业经验等级表。"""
        if self._experience is None:
            self._experience = self._load("职业经验.json")
        return self._experience

    @property
    def recipes(self) -> dict[str, list[dict]]:
        """各类配方：炼丹、制符、装备图纸。"""
        if self._recipes is None:
            self._recipes = {
                "danfang": self._load("炼丹配方.json"),
                "zhizuo": self._load("制符列表.json"),
                "tuzhi": self._load("装备图纸.json"),
            }
        return self._recipes

    def get_occupation_name(self, occupation_id: int) -> str:
        for item in self.occupations:
            if item.get("id") == occupation_id:
                return item.get("name", "未知")
        return "未知"

    def find_occupation(self, name: str) -> dict | None:
        for item in self.occupations:
            if item.get("name") == name:
                return item
        return None

    def get_occupation_rate(self, level: int) -> float:
        """获取指定职业等级对应的 rate 加成。"""
        for item in self.experience:
            if item.get("id") == level:
                return float(item.get("rate", 0.1))
        return 0.1

    def get_occupation_exp_required(self, level: int) -> int:
        """获取指定职业等级升级所需经验。"""
        for item in self.experience:
            if item.get("id") == level:
                return int(item.get("experience", 100))
        return 100

    def find_recipe(self, recipe_type: str, name: str) -> dict | None:
        """按类型和名称查找配方。"""
        for recipe in self.recipes.get(recipe_type, []):
            if recipe.get("name") == name:
                return recipe
        return None
