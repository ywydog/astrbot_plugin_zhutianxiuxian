from pathlib import Path

import pytest

from src.data.tianjiao_data import TianjiaoData
from src.services.player_service import PlayerService
from src.services.state_service import StateService
from src.services.tianjiao_service import TianjiaoService


@pytest.fixture
def tianjiao_data():
    """测试使用项目自带的天骄数据。"""
    project_data_dir = Path(__file__).parent.parent / "data"
    return TianjiaoData(data_dir=project_data_dir)


@pytest.fixture
def service(tmp_path, tianjiao_data):
    player_service = PlayerService(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    return TianjiaoService(
        tianjiao_data=tianjiao_data,
        state_service=state_service,
        player_service=player_service,
    )


@pytest.mark.asyncio
async def test_tianjiao_data_loads_list(tianjiao_data):
    """天骄数据加载器应返回非空列表。"""
    tianjiaos = tianjiao_data.list_tianjiao()
    assert len(tianjiaos) > 0
    assert tianjiaos[0].get("名号") == "猪咪岁岁"


@pytest.mark.asyncio
async def test_tianjiao_data_find_by_name(tianjiao_data):
    """按名号查找天骄应返回对应数据。"""
    tianjiao = tianjiao_data.find_by_name("猪咪岁岁")
    assert tianjiao is not None
    assert tianjiao["境界"] == "无妄真劫境"


@pytest.mark.asyncio
async def test_tianjiao_data_find_not_exists(tianjiao_data):
    """查找不存在的天骄应返回 None。"""
    assert tianjiao_data.find_by_name("不存在的天骄") is None


@pytest.mark.asyncio
async def test_tianjiao_data_location_name(tianjiao_data):
    """位面 ID 应能正确映射为中文名称。"""
    assert tianjiao_data.get_location_name(0) == "凡间"
    assert tianjiao_data.get_location_name(2) == "遮天位面"
    assert tianjiao_data.get_location_name(999) == "未知位面(999)"


@pytest.mark.asyncio
async def test_service_list_tianjiao(service):
    """服务应能返回格式化的天骄列表。"""
    text = await service.list_tianjiao_text()
    assert "位面天骄列表" in text
    assert "猪咪岁岁" in text
    assert "凡间" in text


@pytest.mark.asyncio
async def test_service_status_initial(service):
    """未初始化时查询天骄状态应自动初始化为存活。"""
    text = await service.show_status_text("猪咪岁岁")
    assert "猪咪岁岁" in text
    assert "当前血量" in text
    assert "100%" in text
    assert "存活" in text


@pytest.mark.asyncio
async def test_service_status_all(service):
    """查询所有天骄状态应包含所有天骄。"""
    text = await service.show_all_status_text()
    assert "所有天骄状态" in text
    assert "猪咪岁岁" in text
    assert "金翅小鹏王" in text


@pytest.mark.asyncio
async def test_service_status_not_found(service):
    """查询不存在的天骄应返回未找到提示。"""
    text = await service.show_status_text("不存在")
    assert "未找到" in text


@pytest.mark.asyncio
async def test_service_challenge_missing_name(service):
    """未指定天骄名称讨伐应返回提示。"""
    result = await service.challenge("10086", "")
    assert result.error is True
    assert "请指定" in result.message


@pytest.mark.asyncio
async def test_service_challenge_not_found(service):
    """讨伐不存在的天骄应返回未找到提示。"""
    result = await service.challenge("10086", "不存在的天骄")
    assert result.error is True
    assert "未找到" in result.message


@pytest.mark.asyncio
async def test_service_challenge_level_too_low(service):
    """练气境界不足法身境时无法讨伐。"""
    await service.player_service.create_player("10086")
    result = await service.challenge("10086", "猪咪岁岁")
    assert result.error is True
    assert "法身境" in result.message


@pytest.mark.asyncio
async def test_service_challenge_wrong_location(service):
    """不在天骄所在位面时无法讨伐。"""
    player = await service.player_service.create_player("10086")
    player["level_id"] = 32
    player["power_place"] = 5
    await service.player_service.save("10086", player)

    result = await service.challenge("10086", "猪咪岁岁")
    assert result.error is True
    assert "不在" in result.message


@pytest.mark.asyncio
async def test_service_challenge_low_hp(service):
    """血量过低时无法讨伐。"""
    player = await service.player_service.create_player("10086")
    player["level_id"] = 32
    player["power_place"] = 0
    player["current_hp"] = 100
    player["hp_limit"] = 1000
    await service.player_service.save("10086", player)

    result = await service.challenge("10086", "猪咪岁岁")
    assert result.error is True
    assert "疗伤" in result.message


@pytest.mark.asyncio
async def test_service_challenge_success(service):
    """满足条件时讨伐应扣除天骄血量并奖励玩家。"""
    player = await service.player_service.create_player("10086")
    player["level_id"] = 32
    player["power_place"] = 0
    player["attack"] = 999999999
    player["defense"] = 999999999
    player["current_hp"] = 1000000000
    player["hp_limit"] = 1000000000
    player["crit_rate"] = 1.0
    player["crit_damage"] = 2.0
    player["learned_gongfa"] = []
    await service.player_service.save("10086", player)

    result = await service.challenge("10086", "猪咪岁岁")
    assert result.error is False
    assert "战胜" in result.message or "血量减少" in result.message

    status = await service.get_tianjiao_status("猪咪岁岁")
    assert status["currentHP"] < 100


@pytest.mark.asyncio
async def test_service_challenge_cooldown(service):
    """讨伐后应进入个人冷却。"""
    player = await service.player_service.create_player("10086")
    player["level_id"] = 32
    player["power_place"] = 0
    player["attack"] = 999999999
    player["defense"] = 999999999
    player["current_hp"] = 1000000000
    player["hp_limit"] = 1000000000
    player["crit_rate"] = 1.0
    player["crit_damage"] = 2.0
    player["learned_gongfa"] = []
    await service.player_service.save("10086", player)

    await service.challenge("10086", "猪咪岁岁")
    result = await service.challenge("10086", "猪咪岁岁")
    assert result.error is True
    assert "冷却" in result.message


@pytest.mark.asyncio
async def test_service_damage_rankings(service):
    """讨伐后应能查询到伤害贡献榜。"""
    player = await service.player_service.create_player("10086")
    player["level_id"] = 32
    player["power_place"] = 0
    player["attack"] = 999999999
    player["defense"] = 999999999
    player["current_hp"] = 1000000000
    player["hp_limit"] = 1000000000
    player["crit_rate"] = 1.0
    player["crit_damage"] = 2.0
    player["learned_gongfa"] = []
    await service.player_service.save("10086", player)

    await service.challenge("10086", "猪咪岁岁")
    rankings = await service.get_damage_rankings("猪咪岁岁")
    assert len(rankings) == 1
    assert rankings[0]["qq"] == "10086"


@pytest.mark.asyncio
async def test_service_damage_list_text(service):
    """#天骄贡献榜应返回格式化榜单。"""
    player = await service.player_service.create_player("10086")
    player["level_id"] = 32
    player["power_place"] = 0
    player["attack"] = 999999999
    player["defense"] = 999999999
    player["current_hp"] = 1000000000
    player["hp_limit"] = 1000000000
    player["crit_rate"] = 1.0
    player["crit_damage"] = 2.0
    player["learned_gongfa"] = []
    await service.player_service.save("10086", player)

    await service.challenge("10086", "猪咪岁岁")
    text = await service.show_damage_list_text("猪咪岁岁")
    assert "贡献榜" in text
    assert "10086" in text or "路人甲" in text
