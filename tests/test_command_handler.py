from dataclasses import dataclass, field
from pathlib import Path

import pytest

from src.data.boss_data import BossData
from src.data.exploration_data import ExplorationData
from src.data.item_data import ItemCatalog
from src.data.level_data import LevelData
from src.data.linggen_data import LinggenData
from src.data.occupation_data import OccupationData
from src.data.tianjiao_data import TianjiaoData
from src.services.battle_service import BattleService
from src.services.boss_service import BossService
from src.services.exploration_service import ExplorationService
from src.services.gongfa_service import GongfaService
from src.services.inventory_service import InventoryService
from src.services.lifespan_service import LifespanService
from src.services.linggen_service import LinggenService
from src.services.occupation_service import OccupationService
from src.services.player_service import PlayerService
from src.services.ranking_service import RankingService
from src.services.state_service import StateService
from src.services.checkin_service import CheckinService
from src.services.breakthrough_service import BreakthroughService
from src.services.cultivation_service import CultivationService
from src.services.tianjiao_service import TianjiaoService
from src.services.yuanshen_service import YuanshenService
from src.handlers.command_handler import XiuxianCommandHandler


@dataclass
class FakeAdapter:
    """测试用消息适配器，记录回复内容。"""

    user_id: str
    group_id: str | None = None
    at_users: list[str] = field(default_factory=list)
    replies: list[str] = field(default_factory=list)

    async def get_user_id(self) -> str:
        return self.user_id

    async def get_group_id(self) -> str | None:
        return self.group_id

    async def get_at_users(self) -> list[str]:
        return self.at_users

    async def reply_text(self, text: str) -> None:
        self.replies.append(text)


@pytest.fixture
def handler(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    checkin_service = CheckinService(
        player_service=player_service,
        state_service=state_service,
        today_provider=lambda: "2026-06-21",
    )
    # 测试使用项目自带的境界数据
    project_data_dir = Path(__file__).parent.parent / "data"
    level_data = LevelData(data_dir=project_data_dir)
    occupation_data = OccupationData(data_dir=project_data_dir)
    item_catalog = ItemCatalog(data_dir=project_data_dir)
    tianjiao_data = TianjiaoData(data_dir=project_data_dir)
    breakthrough_service = BreakthroughService(
        player_service=player_service,
        level_data=level_data,
    )
    cultivation_service = CultivationService(
        player_service=player_service,
        state_service=state_service,
    )
    tianjiao_service = TianjiaoService(
        tianjiao_data=tianjiao_data,
        state_service=state_service,
        player_service=player_service,
    )
    exploration_data = ExplorationData(data_dir=project_data_dir)
    exploration_service = ExplorationService(
        player_service=player_service,
        state_service=state_service,
        exploration_data=exploration_data,
    )
    battle_service = BattleService(
        player_service=player_service,
        level_data=level_data,
        state_service=state_service,
        data_dir=tmp_path,
    )
    (tmp_path / "boss_config.json").write_text(
        '{"qualified_level": 3}', encoding="utf-8"
    )
    boss_data = BossData(data_dir=tmp_path)
    boss_service = BossService(
        battle_service=battle_service,
        player_service=player_service,
        state_service=state_service,
        boss_data=boss_data,
        data_dir=tmp_path,
    )
    ranking_service = RankingService(
        player_service=player_service,
        data_dir=tmp_path,
    )
    lifespan_service = LifespanService(
        player_service=player_service,
        state_service=state_service,
    )
    yuanshen_service = YuanshenService(
        player_service=player_service,
        level_data=level_data,
        state_service=state_service,
    )
    inventory_service = InventoryService(
        player_service=player_service,
    )
    gongfa_service = GongfaService(
        player_service=player_service,
        item_catalog=item_catalog,
    )
    occupation_service = OccupationService(
        player_service=player_service,
        state_service=state_service,
        inventory_service=inventory_service,
        occupation_data=occupation_data,
    )
    linggen_data = LinggenData(data_dir=project_data_dir)
    linggen_service = LinggenService(
        player_service=player_service,
        inventory_service=inventory_service,
        state_service=state_service,
        linggen_data=linggen_data,
    )
    return XiuxianCommandHandler(
        player_service=player_service,
        checkin_service=checkin_service,
        level_data=level_data,
        breakthrough_service=breakthrough_service,
        cultivation_service=cultivation_service,
        occupation_data=occupation_data,
        item_catalog=item_catalog,
        tianjiao_service=tianjiao_service,
        exploration_service=exploration_service,
        exploration_data=exploration_data,
        battle_service=battle_service,
        boss_service=boss_service,
        boss_data=boss_data,
        ranking_service=ranking_service,
        lifespan_service=lifespan_service,
        yuanshen_service=yuanshen_service,
        inventory_service=inventory_service,
        gongfa_service=gongfa_service,
        occupation_service=occupation_service,
        linggen_service=linggen_service,
        master_ids={"master"},
    )


@pytest.mark.asyncio
async def test_start_cultivation_creates_player(handler):
    """收到 #踏入仙途 应为新玩家创建存档并回复欢迎信息。"""
    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#踏入仙途")

    assert await handler.player_service.exists("10086")
    assert len(adapter.replies) == 1
    assert "踏入仙途" in adapter.replies[0]


@pytest.mark.asyncio
async def test_start_cultivation_for_existing_player(handler):
    """已有玩家再次发送 #踏入仙途 应提示已存在。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#踏入仙途")

    assert len(adapter.replies) == 1
    assert "已踏上仙途" in adapter.replies[0]


@pytest.mark.asyncio
async def test_unknown_command_is_ignored(handler):
    """未知指令不应产生回复。"""
    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#不存在的指令")

    assert len(adapter.replies) == 0


@pytest.mark.asyncio
async def test_show_player_info_for_existing(handler):
    """已有玩家发送 #我的练气 应显示角色信息。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#我的练气")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "路人甲" in reply
    assert "凡人" in reply
    assert "灵石" in reply


@pytest.mark.asyncio
async def test_show_player_info_for_newbie(handler):
    """未创建角色时发送 #我的练气 应提示先踏入仙途。"""
    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#我的练气")

    assert len(adapter.replies) == 1
    assert "踏入仙途" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_physique_info_for_existing(handler):
    """已有玩家发送 #我的炼体 应显示炼体信息。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#我的炼体")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "路人甲" in reply
    assert "莽夫" in reply


@pytest.mark.asyncio
async def test_show_physique_info_for_newbie(handler):
    """未创建角色时发送 #我的炼体 应提示先踏入仙途。"""
    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#我的炼体")

    assert len(adapter.replies) == 1
    assert "踏入仙途" in adapter.replies[0]


@pytest.mark.asyncio
async def test_checkin_for_existing_player(handler):
    """已有玩家发送 #修仙签到 应签到成功并显示奖励。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#修仙签到")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "签到成功" in reply
    assert "连续签到" in reply
    assert "灵石" in reply


@pytest.mark.asyncio
async def test_checkin_for_newbie(handler):
    """未创建角色时发送 #修仙签到 应提示先踏入仙途。"""
    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#修仙签到")

    assert len(adapter.replies) == 1
    assert "踏入仙途" in adapter.replies[0]


@pytest.mark.asyncio
async def test_checkin_twice_same_day(handler):
    """同一天重复签到应提示已签到。"""
    await handler.player_service.create_player("10086")
    await handler.handle(FakeAdapter(user_id="10086"), "#修仙签到")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#修仙签到")

    assert len(adapter.replies) == 1
    assert "今日已签到" in adapter.replies[0]


@pytest.mark.asyncio
async def test_breakthrough_succeeds(handler):
    """修为足够时 #突破 应成功。"""
    player = await handler.player_service.create_player("10086")
    player["exp"] = 999999
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#突破")

    assert len(adapter.replies) == 1
    assert "突破成功" in adapter.replies[0]

    player = await handler.player_service.load("10086")
    assert player["level_id"] == 2


@pytest.mark.asyncio
async def test_breakthrough_fails_without_exp(handler):
    """修为不足时 #突破 应提示修为不足。"""
    player = await handler.player_service.create_player("10086")
    player["exp"] = 0
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#突破")

    assert len(adapter.replies) == 1
    assert "修为不足" in adapter.replies[0]


@pytest.mark.asyncio
async def test_physique_breakthrough_succeeds(handler):
    """血气足够时 #破体 应成功。"""
    player = await handler.player_service.create_player("10086")
    player["blood_qi"] = 999999
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#破体")

    assert len(adapter.replies) == 1
    assert "破体成功" in adapter.replies[0]

    player = await handler.player_service.load("10086")
    assert player["physique_id"] == 2


@pytest.mark.asyncio
async def test_physique_breakthrough_fails_without_blood_qi(handler):
    """血气不足时 #破体 应提示血气不足。"""
    player = await handler.player_service.create_player("10086")
    player["blood_qi"] = 0
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#破体")

    assert len(adapter.replies) == 1
    assert "血气不足" in adapter.replies[0]


@pytest.mark.asyncio
async def test_set_sex_succeeds_once(handler):
    """#设置性别 应成功且只能设置一次。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#设置性别 男")

    assert len(adapter.replies) == 1
    assert "设置" in adapter.replies[0]

    player = await handler.player_service.load("10086")
    assert player["sex"] == 2

    adapter2 = FakeAdapter(user_id="10086")
    await handler.handle(adapter2, "#设置性别 女")
    assert len(adapter2.replies) == 1
    assert "仅可" in adapter2.replies[0]


@pytest.mark.asyncio
async def test_set_sex_invalid_format(handler):
    """#设置性别 参数错误时应提示格式。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#设置性别 未知")

    assert len(adapter.replies) == 1
    assert "格式" in adapter.replies[0]


@pytest.mark.asyncio
async def test_rename_succeeds(handler):
    """#改名 应消耗灵石并修改名称。"""
    player = await handler.player_service.create_player("10086")
    player["spirit_stones"] = 2000
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#改名 青云子")

    assert len(adapter.replies) == 1
    assert "改名成功" in adapter.replies[0]

    player = await handler.player_service.load("10086")
    assert player["name"] == "青云子"
    assert player["spirit_stones"] == 1000


@pytest.mark.asyncio
async def test_rename_too_long(handler):
    """#改名 名称过长应拒绝。"""
    player = await handler.player_service.create_player("10086")
    player["spirit_stones"] = 2000
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#改名 这是一个超过八个字的名字")

    assert len(adapter.replies) == 1
    assert "最多" in adapter.replies[0]


@pytest.mark.asyncio
async def test_rename_insufficient_spirit_stones(handler):
    """#改名 灵石不足应拒绝。"""
    player = await handler.player_service.create_player("10086")
    player["spirit_stones"] = 500
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#改名 青云子")

    assert len(adapter.replies) == 1
    assert "灵石" in adapter.replies[0]


@pytest.mark.asyncio
async def test_set_motto_succeeds(handler):
    """#设置道宣 应修改宣言。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#设置道宣 修仙问道，长生不灭")

    assert len(adapter.replies) == 1
    assert "道宣" in adapter.replies[0]

    player = await handler.player_service.load("10086")
    assert player["motto"] == "修仙问道，长生不灭"


@pytest.mark.asyncio
async def test_set_motto_too_long(handler):
    """#设置道宣 内容过长应拒绝。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    long_text = "道" * 51
    await handler.handle(adapter, f"#设置道宣 {long_text}")

    assert len(adapter.replies) == 1
    assert "最多" in adapter.replies[0]


@pytest.mark.asyncio
async def test_seclusion_command_dispatched(handler):
    """#闭关 应被正确分发并回复。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#闭关60分钟")

    assert len(adapter.replies) == 1
    assert "闭关" in adapter.replies[0]


@pytest.mark.asyncio
async def test_hunt_command_dispatched(handler):
    """#降妖 应被正确分发并回复。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#降妖60分钟")

    assert len(adapter.replies) == 1
    assert "降妖" in adapter.replies[0]


@pytest.mark.asyncio
async def test_end_seclusion_without_session(handler):
    """未闭关时 #出关 应提示不在闭关中。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#出关")

    assert len(adapter.replies) == 1
    assert "不在闭关中" in adapter.replies[0]


@pytest.mark.asyncio
async def test_end_hunt_without_session(handler):
    """未降妖时 #降妖归来 应提示不在降妖中。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#降妖归来")

    assert len(adapter.replies) == 1
    assert "不在降妖中" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_full_info(handler):
    """#我的 应显示完整角色信息。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#我的")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "路人甲" in reply
    assert "境界" in reply
    assert "灵根" in reply
    assert "道宣" in reply


@pytest.mark.asyncio
async def test_lucky_breakthrough_succeeds(handler):
    """#幸运突破 应消耗灵石并升级。"""
    player = await handler.player_service.create_player("10086")
    player["exp"] = 999999
    player["spirit_stones"] = 1000
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#幸运突破")

    assert len(adapter.replies) == 1
    assert "幸运突破成功" in adapter.replies[0]

    player = await handler.player_service.load("10086")
    assert player["level_id"] == 2
    assert player["spirit_stones"] == 500


@pytest.mark.asyncio
async def test_lucky_physique_breakthrough_succeeds(handler):
    """#幸运破体 应消耗灵石并升级。"""
    player = await handler.player_service.create_player("10086")
    player["blood_qi"] = 999999
    player["spirit_stones"] = 1000
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#幸运破体")

    assert len(adapter.replies) == 1
    assert "幸运破体成功" in adapter.replies[0]

    player = await handler.player_service.load("10086")
    assert player["physique_id"] == 2
    assert player["spirit_stones"] == 500


@pytest.mark.asyncio
async def test_show_help(handler):
    """#修仙帮助 应返回支持的指令列表。"""
    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#修仙帮助")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "修仙指令列表" in reply
    assert "#踏入仙途" in reply
    assert "#一键突破" in reply


@pytest.mark.asyncio
async def test_refresh_info_for_existing_player(handler):
    """#刷新信息 应为已有玩家补全字段并回复。"""
    player = await handler.player_service.create_player("10086")
    # 删除部分字段模拟旧存档
    player.pop("physique_id", None)
    player.pop("current_hp", None)
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#刷新信息")

    assert len(adapter.replies) == 1
    assert "信息刷新完成" in adapter.replies[0]

    refreshed = await handler.player_service.load("10086")
    assert refreshed["physique_id"] == 1
    assert refreshed["current_hp"] == 8000


@pytest.mark.asyncio
async def test_refresh_info_for_newbie(handler):
    """未创建角色时 #刷新信息 应提示先踏入仙途。"""
    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#刷新信息")

    assert len(adapter.replies) == 1
    assert "踏入仙途" in adapter.replies[0]


@pytest.mark.asyncio
async def test_refresh_info_no_changes(handler):
    """字段完整时 #刷新信息 应提示无需刷新。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#刷新信息")

    assert len(adapter.replies) == 1
    assert "无需刷新" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_status_idle(handler):
    """#修仙状态 在无动作时应显示空闲。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#修仙状态")

    assert len(adapter.replies) == 1
    assert "空闲" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_status_in_seclusion(handler):
    """#修仙状态 在闭关时应显示剩余时间。"""
    await handler.player_service.create_player("10086")
    await handler.cultivation_service.start_seclusion("10086", 60)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#修仙状态")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "闭关" in reply
    assert "剩余时间" in reply


@pytest.mark.asyncio
async def test_show_status_for_newbie(handler):
    """未创建角色时 #修仙状态 应提示先踏入仙途。"""
    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#修仙状态")

    assert len(adapter.replies) == 1
    assert "踏入仙途" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_cultivation_levels(handler):
    """#练气境界 应返回境界列表。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#练气境界")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "练气境界表" in reply
    assert "凡人" in reply


@pytest.mark.asyncio
async def test_show_physique_levels(handler):
    """#炼体境界 应返回境界列表。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#炼体境界")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "炼体境界表" in reply
    assert "莽夫" in reply


@pytest.mark.asyncio
async def test_show_mijing_levels(handler):
    """#秘境体系 应返回秘境列表。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#秘境体系")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "秘境体系" in reply
    assert "轮海秘境" in reply


@pytest.mark.asyncio
async def test_show_xiangu_levels(handler):
    """#仙古今世法 应返回仙古列表及极境信息。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#仙古今世法")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "仙古今世法" in reply
    assert "搬血境" in reply
    assert "极境" in reply


@pytest.mark.asyncio
async def test_show_occupation_levels(handler):
    """#职业等级 应返回职业列表。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#职业等级")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "职业列表" in reply
    assert "炼丹师" in reply


@pytest.mark.asyncio
async def test_show_equipment_catalog(handler):
    """#装备楼 应返回装备列表。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#装备楼")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "装备楼" in reply
    assert "烂铁匕首" in reply


@pytest.mark.asyncio
async def test_show_pill_catalog(handler):
    """#丹药楼 应返回丹药列表。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#丹药楼")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "丹药楼" in reply
    assert "凝血丹" in reply


@pytest.mark.asyncio
async def test_show_gongfa_catalog(handler):
    """#功法楼 应返回功法列表。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#功法楼")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "功法楼" in reply
    assert "维宙星灭诀" in reply


@pytest.mark.asyncio
async def test_show_gem_catalog(handler):
    """#宝石楼 应返回宝石列表。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#宝石楼")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "宝石楼" in reply
    assert "生命宝石" in reply


@pytest.mark.asyncio
async def test_show_tianjiao_list(handler):
    """#天骄列表 应返回位面天骄列表。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#天骄列表")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "位面天骄列表" in reply
    assert "猪咪岁岁" in reply


@pytest.mark.asyncio
async def test_show_tianjiao_status(handler):
    """#天骄状态 应返回指定天骄状态。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#天骄状态 猪咪岁岁")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "猪咪岁岁" in reply
    assert "当前血量" in reply


@pytest.mark.asyncio
async def test_show_tianjiao_status_all(handler):
    """#天骄状态 不带名称时应返回所有天骄状态。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#天骄状态")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "所有天骄状态" in reply
    assert "猪咪岁岁" in reply


@pytest.mark.asyncio
async def test_challenge_tianjiao_missing_name(handler):
    """#讨伐天骄 未指定名称时应提示。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#讨伐天骄")

    assert len(adapter.replies) == 1
    assert "请指定" in adapter.replies[0]


@pytest.mark.asyncio
async def test_challenge_tianjiao_level_too_low(handler):
    """练气境界不足时讨伐天骄应拒绝。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#讨伐天骄 猪咪岁岁")

    assert len(adapter.replies) == 1
    assert "法身境" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_tianjiao_damage_list(handler):
    """#天骄贡献榜 应返回贡献榜。"""
    player = await handler.player_service.create_player("10086")
    player["level_id"] = 32
    player["power_place"] = 0
    player["attack"] = 999999999
    player["defense"] = 999999999
    player["current_hp"] = 1000000000
    player["hp_limit"] = 1000000000
    player["crit_rate"] = 1.0
    player["crit_damage"] = 2.0
    player["learned_gongfa"] = []
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#讨伐天骄 猪咪岁岁")

    adapter2 = FakeAdapter(user_id="10086")
    await handler.handle(adapter2, "#天骄贡献榜 猪咪岁岁")

    assert len(adapter2.replies) == 1
    reply = adapter2.replies[0]
    assert "贡献榜" in reply


@pytest.mark.asyncio
async def test_auto_breakthrough_succeeds(handler):
    """#一键突破 应连续升级并在资源不足时停止。"""
    player = await handler.player_service.create_player("10086")
    player["exp"] = 500
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#一键突破")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "一键突破完成" in reply
    assert "1" in reply

    player = await handler.player_service.load("10086")
    assert player["level_id"] == 2


@pytest.mark.asyncio
async def test_auto_breakthrough_fails_without_exp(handler):
    """#一键突破 资源不足时应提示失败原因。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#一键突破")

    assert len(adapter.replies) == 1
    assert "一键突破失败" in adapter.replies[0]


@pytest.mark.asyncio
async def test_auto_physique_breakthrough_succeeds(handler):
    """#一键破体 应连续升级并在资源不足时停止。"""
    player = await handler.player_service.create_player("10086")
    player["blood_qi"] = 500
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#一键破体")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "一键破体完成" in reply

    player = await handler.player_service.load("10086")
    assert player["physique_id"] == 2


@pytest.mark.asyncio
async def test_rob_requires_at_target(handler):
    """#打劫 未 @ 目标时应提示。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#打劫")

    assert len(adapter.replies) == 1
    assert "@" in adapter.replies[0]


@pytest.mark.asyncio
async def test_rob_success(handler):
    """#打劫 @目标 应发起战斗并结算。"""
    a = await handler.player_service.create_player("10086")
    a["level_id"] = 2
    a["current_hp"] = 20000
    a["spirit_stones"] = 50000
    await handler.player_service.save("10086", a)
    b = await handler.player_service.create_player("20000")
    b["current_hp"] = 20000
    b["spirit_stones"] = 100000
    await handler.player_service.save("20000", b)

    adapter = FakeAdapter(user_id="10086", at_users=["20000"])
    await handler.handle(adapter, "#打劫")

    assert len(adapter.replies) == 1
    assert "击败" in adapter.replies[0]


@pytest.mark.asyncio
async def test_duel_requires_at_target(handler):
    """#比武 未 @ 目标时应提示。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#比武")

    assert len(adapter.replies) == 1
    assert "@" in adapter.replies[0]


@pytest.mark.asyncio
async def test_duel_success(handler):
    """#比武 @目标 应发起战斗并结算。"""
    a = await handler.player_service.create_player("10086")
    a["level_id"] = 2
    a["current_hp"] = 10000
    await handler.player_service.save("10086", a)
    b = await handler.player_service.create_player("20000")
    b["current_hp"] = 4000
    await handler.player_service.save("20000", b)

    adapter = FakeAdapter(user_id="10086", at_users=["20000"])
    await handler.handle(adapter, "#比武")

    assert len(adapter.replies) == 1
    assert "击败" in adapter.replies[0]


async def _make_qualified_player(handler, user_id):
    player = await handler.player_service.create_player(user_id)
    player["level_id"] = 3
    player["current_hp"] = 100000
    return player


@pytest.mark.asyncio
async def test_init_boss_with_qualified_players(handler):
    """有达标玩家时 #开启妖王 应成功开启。"""
    await handler.player_service.save(
        "p0", await _make_qualified_player(handler, "p0")
    )

    adapter = FakeAdapter(user_id="admin")
    await handler.handle(adapter, "#开启妖王")

    assert len(adapter.replies) == 1
    assert "妖王已开启" in adapter.replies[0]
    assert "血量" in adapter.replies[0]


@pytest.mark.asyncio
async def test_init_boss_without_qualified_players(handler):
    """无达标玩家时 #开启妖王 应提示失败。"""
    adapter = FakeAdapter(user_id="admin")
    await handler.handle(adapter, "#开启妖王")

    assert len(adapter.replies) == 1
    assert "没有" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_boss_status_when_alive(handler):
    """妖王开启后 #妖王状态 应显示血量与奖励。"""
    await handler.player_service.save(
        "p0", await _make_qualified_player(handler, "p0")
    )
    init_result = await handler.boss_service.initialize_boss()
    assert init_result.success, f"初始化失败: {init_result.reason}"

    adapter = FakeAdapter(user_id="admin")
    await handler.handle(adapter, "#妖王状态")

    assert len(adapter.replies) == 1
    assert "妖王状态" in adapter.replies[0]
    assert "血量" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_boss_status_when_not_alive(handler):
    """妖王未开启时 #妖王状态 应提示。"""
    adapter = FakeAdapter(user_id="admin")
    await handler.handle(adapter, "#妖王状态")

    assert len(adapter.replies) == 1
    assert "未开启" in adapter.replies[0]


@pytest.mark.asyncio
async def test_challenge_boss_success(handler):
    """达标玩家 #讨伐妖王 应记录伤害。"""
    await handler.player_service.save(
        "p0", await _make_qualified_player(handler, "p0")
    )
    await handler.player_service.save(
        "p1", await _make_qualified_player(handler, "p1")
    )
    await handler.boss_service.initialize_boss()

    adapter = FakeAdapter(user_id="p1")
    await handler.handle(adapter, "#讨伐妖王")

    assert len(adapter.replies) == 1
    assert "妖王" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_boss_damage_list(handler):
    """挑战后 #妖王贡献榜 应返回排名。"""
    await handler.player_service.save(
        "p0", await _make_qualified_player(handler, "p0")
    )
    await handler.player_service.save(
        "p1", await _make_qualified_player(handler, "p1")
    )
    await handler.boss_service.initialize_boss()
    await handler.boss_service.challenge("p1")

    adapter = FakeAdapter(user_id="p1")
    await handler.handle(adapter, "#妖王贡献榜")

    assert len(adapter.replies) == 1
    assert "贡献排行榜" in adapter.replies[0]


@pytest.mark.asyncio
async def test_close_boss(handler):
    """#关闭妖王 应清除妖王状态。"""
    await handler.player_service.save(
        "p0", await _make_qualified_player(handler, "p0")
    )
    await handler.boss_service.initialize_boss()

    adapter = FakeAdapter(user_id="admin")
    await handler.handle(adapter, "#关闭妖王")

    assert len(adapter.replies) == 1
    assert "关闭" in adapter.replies[0]
    status = await handler.boss_service.get_status()
    assert status["alive"] is False


@pytest.mark.asyncio
async def test_show_modao_ranking(handler):
    """#魔道榜 应按魔道值排序返回。"""
    p1 = await handler.player_service.create_player("p1")
    p1["modao_value"] = 100
    await handler.player_service.save("p1", p1)
    p2 = await handler.player_service.create_player("p2")
    p2["modao_value"] = 999
    await handler.player_service.save("p2", p2)

    adapter = FakeAdapter(user_id="admin")
    await handler.handle(adapter, "#魔道榜")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "魔道榜" in reply
    assert "第 1 名" in reply


@pytest.mark.asyncio
async def test_show_exp_ranking(handler):
    """#天榜 应按修为排序返回。"""
    p1 = await handler.player_service.create_player("p1")
    p1["exp"] = 100
    await handler.player_service.save("p1", p1)
    p2 = await handler.player_service.create_player("p2")
    p2["exp"] = 99999
    await handler.player_service.save("p2", p2)

    adapter = FakeAdapter(user_id="admin")
    await handler.handle(adapter, "#天榜")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "天榜" in reply
    assert "第 1 名" in reply


@pytest.mark.asyncio
async def test_show_empty_ranking(handler):
    """无玩家时排行榜应提示暂无数据。"""
    adapter = FakeAdapter(user_id="admin")
    await handler.handle(adapter, "#灵榜")

    assert len(adapter.replies) == 1
    assert "暂无数据" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_lifespan_for_existing_player(handler):
    """#查看寿元 应显示当前寿元。"""
    player = await handler.player_service.create_player("10086")
    player["shouyuan"] = 666
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#查看寿元")

    assert len(adapter.replies) == 1
    assert "寿元" in adapter.replies[0]
    assert "666" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_lifespan_for_newbie(handler):
    """未创建角色时 #查看寿元 应提示先踏入仙途。"""
    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#查看寿元")

    assert len(adapter.replies) == 1
    assert "踏入仙途" in adapter.replies[0]


@pytest.mark.asyncio
async def test_reduce_lifespan_manual_requires_master(handler):
    """非主人执行 #执行寿元流逝 应被拒绝。"""
    adapter = FakeAdapter(user_id="normal")
    await handler.handle(adapter, "#执行寿元流逝")

    assert len(adapter.replies) == 1
    assert "主人" in adapter.replies[0]


@pytest.mark.asyncio
async def test_reduce_lifespan_manual_by_master(handler):
    """主人执行 #执行寿元流逝 应减少所有玩家寿元。"""
    player = await handler.player_service.create_player("p1")
    player["shouyuan"] = 1000
    await handler.player_service.save("p1", player)

    adapter = FakeAdapter(user_id="master")
    await handler.handle(adapter, "#执行寿元流逝")

    assert len(adapter.replies) == 1
    assert "寿元流逝执行完成" in adapter.replies[0]
    assert "处理玩家总数：1" in adapter.replies[0]

    player = await handler.player_service.load("p1")
    assert player["shouyuan"] < 1000


@pytest.mark.asyncio
async def test_reduce_lifespan_manual_with_custom_amount(handler):
    """主人执行 #执行寿元流逝500 应按指定数量减少寿元。"""
    player = await handler.player_service.create_player("p1")
    player["shouyuan"] = 1000
    player["level_id"] = 42
    await handler.player_service.save("p1", player)

    adapter = FakeAdapter(user_id="master")
    await handler.handle(adapter, "#执行寿元流逝500")

    assert len(adapter.replies) == 1
    assert "寿元流逝执行完成" in adapter.replies[0]

    player = await handler.player_service.load("p1")
    assert player["shouyuan"] == 500


@pytest.mark.asyncio
async def test_reduce_lifespan_manual_invalid_amount(handler):
    """#执行寿元流逝 后跟无效数字应提示格式。"""
    adapter = FakeAdapter(user_id="master")
    await handler.handle(adapter, "#执行寿元流逝abc")

    assert len(adapter.replies) == 1
    assert "有效" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_yuanshen_for_newbie(handler):
    """未创建角色时 #我的元神 应提示先踏入仙途。"""
    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#我的元神")

    assert len(adapter.replies) == 1
    assert "踏入仙途" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_yuanshen_not_condensed(handler):
    """#我的元神 对未凝练玩家应显示未凝练状态。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#我的元神")

    assert len(adapter.replies) == 1
    assert "未凝练" in adapter.replies[0]


@pytest.mark.asyncio
async def test_condense_yuanshen_insufficient(handler):
    """元神不足时 #凝练元神 应提示不足。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#凝练元神")

    assert len(adapter.replies) == 1
    assert "不足" in adapter.replies[0]


@pytest.mark.asyncio
async def test_condense_yuanshen_success(handler):
    """元神足够时 #凝练元神 应成功凝练。"""
    player = await handler.player_service.create_player("10086")
    player["yuanshen"] = 20_000_000
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#凝练元神")

    assert len(adapter.replies) == 1
    assert "成功凝练" in adapter.replies[0]


@pytest.mark.asyncio
async def test_open_neijing_not_condensed(handler):
    """未凝练元神时 #开启内景地 应提示。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#开启内景地")

    assert len(adapter.replies) == 1
    assert "未凝练" in adapter.replies[0]


@pytest.mark.asyncio
async def test_enter_neijing_not_open(handler):
    """内景地未开启时 #进入内景地 应提示。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#进入内景地")

    assert len(adapter.replies) == 1
    assert "未开" in adapter.replies[0]


@pytest.mark.asyncio
async def test_neijing_batch_invalid_format(handler):
    """#内景地修炼 格式错误应提示。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#内景地修炼abc")

    assert len(adapter.replies) == 1
    assert "格式" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_inventory_for_newbie(handler):
    """未创建角色时 #我的纳戒 应提示创建角色。"""
    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#我的纳戒")

    assert len(adapter.replies) == 1
    assert "踏入仙途" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_inventory_empty(handler):
    """新玩家 #我的纳戒 应显示空纳戒。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#纳戒")

    assert len(adapter.replies) == 1
    assert "纳戒" in adapter.replies[0]
    assert "空空如也" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_inventory_with_items(handler):
    """纳戒有物品时应按分类显示。"""
    await handler.player_service.create_player("10086")
    await handler.inventory_service.add_item("10086", "丹药", "聚气丹", 5)
    await handler.inventory_service.add_item("10086", "装备", "铁剑")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#我的纳戒")

    assert len(adapter.replies) == 1
    text = adapter.replies[0]
    assert "丹药" in text
    assert "聚气丹" in text
    assert "装备" in text
    assert "铁剑" in text


@pytest.mark.asyncio
async def test_show_gongfa_for_newbie(handler):
    """未创建角色时 #我的功法 应提示创建角色。"""
    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#我的功法")

    assert len(adapter.replies) == 1
    assert "踏入仙途" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_gongfa_empty(handler):
    """新玩家 #我的功法 应显示未学习功法。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#我的功法")

    assert len(adapter.replies) == 1
    assert "尚未学习" in adapter.replies[0]


@pytest.mark.asyncio
async def test_show_gongfa_with_learned(handler):
    """#我的功法 应显示已学习的功法。"""
    await handler.player_service.create_player("10086")
    await handler.gongfa_service.learn("10086", "维宙星灭诀")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#我的功法")

    assert len(adapter.replies) == 1
    assert "维宙星灭诀" in adapter.replies[0]


@pytest.mark.asyncio
async def test_learn_gongfa_missing_name(handler):
    """#学习功法 未指定名称时应提示格式。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#学习功法")

    assert len(adapter.replies) == 1
    assert "格式" in adapter.replies[0]


@pytest.mark.asyncio
async def test_learn_gongfa_not_found(handler):
    """#学习功法 指定不存在功法时应提示。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#学习功法 不存在的功法")

    assert len(adapter.replies) == 1
    assert "不存在" in adapter.replies[0]


@pytest.mark.asyncio
async def test_learn_gongfa_success(handler):
    """#学习功法 应成功学习并保存。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#学习功法 维宙星灭诀")

    assert len(adapter.replies) == 1
    assert "学习成功" in adapter.replies[0]
    assert await handler.gongfa_service.has_learned("10086", "维宙星灭诀")


@pytest.mark.asyncio
async def test_learn_gongfa_already_learned(handler):
    """重复学习同一功法应提示已学习。"""
    await handler.player_service.create_player("10086")
    await handler.gongfa_service.learn("10086", "维宙星灭诀")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "#学习功法 维宙星灭诀")

    assert len(adapter.replies) == 1
    assert "已学习" in adapter.replies[0]


@pytest.mark.asyncio
async def test_cultivate_yuanshen_with_gongfa_not_condensed(handler):
    """未凝练元神时使用功法修炼应提示。"""
    await handler.player_service.create_player("10086")

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "以前字秘修炼元神")

    assert len(adapter.replies) == 1
    assert "未凝练" in adapter.replies[0]


@pytest.mark.asyncio
async def test_cultivate_yuanshen_with_gongfa_not_learned(handler):
    """未学习功法时使用该功法修炼应提示。"""
    player = await handler.player_service.create_player("10086")
    player["yuanshenlevel_id"] = 0
    player["yuanshen_limit"] = 1000
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "以前字秘修炼元神")

    assert len(adapter.replies) == 1
    assert "尚未学习" in adapter.replies[0]


@pytest.mark.asyncio
async def test_cultivate_yuanshen_with_gongfa_success(handler):
    """已学习功法且凝练元神时修炼应恢复元神。"""
    player = await handler.player_service.create_player("10086")
    player["yuanshenlevel_id"] = 0
    player["yuanshen"] = 100
    player["yuanshen_limit"] = 1000
    player["learned_gongfa"] = ["前字秘"]
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "以前字秘修炼元神")

    assert len(adapter.replies) == 1
    reply = adapter.replies[0]
    assert "修炼元神" in reply
    assert "当前元神" in reply

    player = await handler.player_service.load("10086")
    assert player["yuanshen"] > 100


@pytest.mark.asyncio
async def test_cultivate_yuanshen_with_unknown_gongfa(handler):
    """使用不能修炼元神的功法时应提示。"""
    player = await handler.player_service.create_player("10086")
    player["yuanshenlevel_id"] = 0
    player["yuanshen_limit"] = 1000
    await handler.player_service.save("10086", player)

    adapter = FakeAdapter(user_id="10086")
    await handler.handle(adapter, "以维宙星灭诀修炼元神")

    assert len(adapter.replies) == 1
    assert "并非" in adapter.replies[0]
