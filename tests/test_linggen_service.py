from pathlib import Path

import pytest

from src.data.linggen_data import LinggenData
from src.services.inventory_service import InventoryService
from src.services.linggen_service import LinggenService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@pytest.fixture
def linggen_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    project_data_dir = Path(__file__).parent.parent / "data"
    linggen_data = LinggenData(data_dir=project_data_dir)
    return LinggenService(
        player_service=player_service,
        inventory_service=inventory_service,
        state_service=state_service,
        linggen_data=linggen_data,
    )


def _set_linggen(player_service, user_id, linggen):
    player = player_service._player_file(user_id)
    data = {}
    if player.exists():
        import json
        data = json.loads(player.read_text(encoding="utf-8"))
    data["linggen"] = linggen
    player.write_text(__import__("json").dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.mark.asyncio
async def test_get_info_player_not_found(linggen_service):
    result = await linggen_service.get_info("noone")
    assert result.player_not_found


@pytest.mark.asyncio
async def test_get_info_existing_player(linggen_service):
    await linggen_service.player_service.create_player("u1")

    result = await linggen_service.get_info("u1")

    assert not result.player_not_found
    assert "type" in result.linggen


@pytest.mark.asyncio
async def test_elysia_ritual_no_item(linggen_service):
    await linggen_service.player_service.create_player("u1")

    result = await linggen_service.start_elysia_ritual("u1")

    assert not result.player_not_found
    assert not result.prompt
    assert "往世乐土之章" in result.reason


@pytest.mark.asyncio
async def test_elysia_ritual_success(linggen_service):
    await linggen_service.player_service.create_player("u1")
    await linggen_service.inventory_service.add_item("u1", "道具", "往世乐土之章", 1)

    result = await linggen_service.start_elysia_ritual("u1")

    assert result.prompt
    assert "往世乐土" in result.prompt


@pytest.mark.asyncio
async def test_elysia_choice_invalid(linggen_service):
    await linggen_service.player_service.create_player("u1")

    result = await linggen_service.handle_elysia_choice("u1", "1")

    assert not result.success
    assert "闭合" in result.reason


@pytest.mark.asyncio
async def test_elysia_overwrite_success(linggen_service):
    await linggen_service.player_service.create_player("u1")
    await linggen_service.inventory_service.add_item("u1", "道具", "往世乐土之章", 1)
    await linggen_service.inventory_service.add_item("u1", "道具", "无瑕水晶花", 4)
    await linggen_service.inventory_service.add_item("u1", "道具", "誓约之证", 4)

    await linggen_service.start_elysia_ritual("u1")
    result = await linggen_service.handle_elysia_choice("u1", "1")

    assert result.success
    assert result.new_linggen["name"] == "爱莉希雅"


@pytest.mark.asyncio
async def test_elysia_overwrite_insufficient_materials(linggen_service):
    await linggen_service.player_service.create_player("u1")
    await linggen_service.inventory_service.add_item("u1", "道具", "往世乐土之章", 1)

    await linggen_service.start_elysia_ritual("u1")
    result = await linggen_service.handle_elysia_choice("u1", "1")

    assert not result.success
    assert "材料不足" in result.reason


@pytest.mark.asyncio
async def test_elysia_summon_count_success(linggen_service):
    await linggen_service.player_service.create_player("u1")
    await linggen_service.inventory_service.add_item("u1", "道具", "往世乐土之章", 3)

    await linggen_service.start_elysia_ritual("u1")
    choice = await linggen_service.handle_elysia_choice("u1", "2")
    assert choice.need_count_input

    count_result = await linggen_service.handle_elysia_count("u1", 2)
    assert count_result.success
    assert "召唤次数 +2" in count_result.message

    player = await linggen_service.player_service.load("u1")
    assert player["爱莉希雅召唤次数"] == 2


@pytest.mark.asyncio
async def test_zhenwo_awaken_success(linggen_service):
    await linggen_service.player_service.create_player("u1")
    player = await linggen_service.player_service.load("u1")
    player["mijing_level_id"] = 15
    player["linggen"] = {
        "name": "爱莉希雅",
        "type": "无瑕之人",
        "生命本源": 50,
        "eff": 1.2,
    }
    player["life_source"] = 150
    await linggen_service.player_service.save("u1", player)
    await linggen_service.inventory_service.add_item("u1", "道具", "往世乐土的记忆结晶", 5)
    await linggen_service.inventory_service.add_item("u1", "道具", "永恒的乐园之息", 5)

    result = await linggen_service.awaken_zhenwo("u1")

    assert result.success
    assert result.new_linggen["name"] == "人之律者·爱莉希雅"


@pytest.mark.asyncio
async def test_zhenwo_awaken_wrong_linggen(linggen_service):
    await linggen_service.player_service.create_player("u1")

    result = await linggen_service.awaken_zhenwo("u1")

    assert not result.success
    assert "只有无瑕之人" in result.reason


@pytest.mark.asyncio
async def test_liuying_awaken_success(linggen_service):
    await linggen_service.player_service.create_player("u1")
    player = await linggen_service.player_service.load("u1")
    player["mijing_level_id"] = 15
    player["linggen"] = {
        "name": "少女流萤",
        "type": "星铁",
        "生命本源": 0,
        "eff": 1.0,
    }
    player["life_source"] = 100
    await linggen_service.player_service.save("u1", player)
    await linggen_service.inventory_service.add_item("u1", "道具", "星核", 10)
    await linggen_service.inventory_service.add_item("u1", "道具", "命途碎片", 10)

    result = await linggen_service.awaken_liuying("u1")

    assert result.success
    assert result.new_linggen["name"] == "流萤·萨姆机甲"


@pytest.mark.asyncio
async def test_shengti_xiaocheng_success(linggen_service):
    await linggen_service.player_service.create_player("u1")
    player = await linggen_service.player_service.load("u1")
    player["mijing_level_id"] = 8
    player["linggen"] = {
        "name": "荒古圣体",
        "type": "圣体",
        "生命本源": 0,
        "eff": 1.0,
    }
    player["life_source"] = 100
    player["圣体秘境完成度"] = {
        "轮海": 60,
        "道宫": 60,
        "四极": 0,
        "化龙": 0,
    }
    await linggen_service.player_service.save("u1", player)

    result = await linggen_service.awaken_shengti("u1")

    assert result.success
    assert result.new_linggen["name"] == "小成·荒古圣体"


@pytest.mark.asyncio
async def test_shengti_dacheng_incomplete(linggen_service):
    await linggen_service.player_service.create_player("u1")
    player = await linggen_service.player_service.load("u1")
    player["mijing_level_id"] = 16
    player["linggen"] = {
        "name": "小成·荒古圣体",
        "type": "小成圣体",
        "生命本源": 150,
        "eff": 1.3,
    }
    player["life_source"] = 250
    player["圣体秘境完成度"] = {
        "轮海": 100,
        "道宫": 80,
        "四极": 100,
        "化龙": 100,
    }
    await linggen_service.player_service.save("u1", player)

    result = await linggen_service.awaken_shengti("u1")

    assert not result.success
    assert "100%圆满" in result.reason


@pytest.mark.asyncio
async def test_bati_xiaocheng_success(linggen_service):
    await linggen_service.player_service.create_player("u1")
    player = await linggen_service.player_service.load("u1")
    player["mijing_level_id"] = 8
    player["linggen"] = {
        "name": "苍天霸体",
        "type": "霸体",
        "生命本源": 0,
        "eff": 1.0,
    }
    player["life_source"] = 100
    await linggen_service.player_service.save("u1", player)
    await linggen_service.inventory_service.add_item("u1", "道具", "不灭霸血", 1)

    result = await linggen_service.awaken_bati("u1")

    assert result.success
    assert result.new_linggen["name"] == "小成·苍天霸体"


@pytest.mark.asyncio
async def test_bati_dacheng_missing_gongfa(linggen_service):
    await linggen_service.player_service.create_player("u1")
    player = await linggen_service.player_service.load("u1")
    player["mijing_level_id"] = 16
    player["linggen"] = {
        "name": "小成·苍天霸体",
        "type": "小成霸体",
        "生命本源": 100,
        "eff": 30,
    }
    player["life_source"] = 200
    await linggen_service.player_service.save("u1", player)

    result = await linggen_service.awaken_bati("u1")

    assert not result.success
    assert "霸拳真解" in result.reason


@pytest.mark.asyncio
async def test_yaoti_xiaocheng_success(linggen_service):
    await linggen_service.player_service.create_player("u1")
    player = await linggen_service.player_service.load("u1")
    player["mijing_level_id"] = 8
    player["linggen"] = {
        "name": "妖体",
        "type": "妖体",
        "生命本源": 0,
        "eff": 1.0,
    }
    player["life_source"] = 100
    await linggen_service.player_service.save("u1", player)
    await linggen_service.inventory_service.add_item("u1", "道具", "天妖真血", 1)

    result = await linggen_service.awaken_yaoti("u1")

    assert result.success
    assert result.new_linggen["name"] == "天妖王体"


@pytest.mark.asyncio
async def test_yaoti_dacheng_success(linggen_service):
    await linggen_service.player_service.create_player("u1")
    player = await linggen_service.player_service.load("u1")
    player["mijing_level_id"] = 16
    player["linggen"] = {
        "name": "天妖王体",
        "type": "小成妖体",
        "生命本源": 50,
        "eff": 2.2,
    }
    player["life_source"] = 150
    player["learned_gongfa"] = ["妖帝古经"]
    await linggen_service.player_service.save("u1", player)

    result = await linggen_service.awaken_yaoti("u1")

    assert result.success
    assert result.new_linggen["name"] == "天妖皇体"
