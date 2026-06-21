from dataclasses import dataclass

from src.data.item_data import ItemCatalog
from src.services.player_service import PlayerService


@dataclass
class GongfaListResult:
    """功法列表查询结果。"""

    player_not_found: bool = False
    learned: list[str] | None = None


@dataclass
class LearnGongfaResult:
    """学习功法结果。"""

    player_not_found: bool = False
    not_found: bool = False
    already_learned: bool = False
    success: bool = False
    name: str = ""
    type: str = ""


class GongfaService:
    """功法服务：查询、学习功法。"""

    GONGFA_FILE = "功法列表.json"

    def __init__(self, player_service: PlayerService, item_catalog: ItemCatalog):
        self.player_service = player_service
        self.item_catalog = item_catalog

    def _find_gongfa(self, name: str) -> dict | None:
        return self.item_catalog.find_item(name, self.GONGFA_FILE)

    async def list_learned(self, user_id: str) -> GongfaListResult:
        """查询玩家已学习的功法。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return GongfaListResult(player_not_found=True)

        learned = list(player.get("learned_gongfa", []))
        return GongfaListResult(learned=learned)

    async def learn(self, user_id: str, name: str) -> LearnGongfaResult:
        """学习功法（只要功法存在于图鉴即可学习）。"""
        player = await self.player_service.load(user_id)
        if player is None:
            return LearnGongfaResult(player_not_found=True)

        gongfa = self._find_gongfa(name)
        if gongfa is None:
            return LearnGongfaResult(not_found=True, name=name)

        learned: list[str] = player.setdefault("learned_gongfa", [])
        if name in learned:
            return LearnGongfaResult(already_learned=True, name=name)

        learned.append(name)
        await self.player_service.save(user_id, player)

        return LearnGongfaResult(
            success=True,
            name=name,
            type=gongfa.get("type", "未知"),
        )

    async def has_learned(self, user_id: str, name: str) -> bool:
        """检查玩家是否已学习某功法。"""
        result = await self.list_learned(user_id)
        if result.player_not_found or result.learned is None:
            return False
        return name in result.learned
