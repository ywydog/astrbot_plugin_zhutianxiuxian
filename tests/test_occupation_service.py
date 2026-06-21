from pathlib import Path

import pytest

from src.data.occupation_data import OccupationData
from src.services.inventory_service import InventoryService
from src.services.occupation_service import OccupationService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@pytest.fixture
def occupation_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    inventory_service = InventoryService(player_service=player_service)
    project_data_dir = Path(__file__).parent.parent / "data"
    occupation_data = OccupationData(data_dir=project_data_dir)
    return OccupationService(
        player_service=player_service,
        state_service=state_service,
        inventory_service=inventory_service,
        occupation_data=occupation_data,
        random_provider=lambda: 0.5,
    )


@pytest.mark.asyncio
async def test_get_info_player_not_found(occupation_service):
    result = await occupation_service.get_info("noone")
    assert result.player_not_found


@pytest.mark.asyncio
async def test_get_info_new_player(occupation_service):
    await occupation_service.player_service.create_player("u1")

    result = await occupation_service.get_info("u1")

    assert not result.player_not_found
    assert result.occupation == ""
    assert result.occupation_level == 1
    assert result.occupation_exp == 0
    assert result.secondary is None


@pytest.mark.asyncio
async def test_change_occupation_invalid(occupation_service):
    await occupation_service.player_service.create_player("u1")

    result = await occupation_service.change_occupation("u1", "不存在的职业")

    assert not result.success
    assert "没有" in result.reason


@pytest.mark.asyncio
async def test_change_occupation_same(occupation_service):
    await occupation_service.player_service.create_player("u1")
    player = await occupation_service.player_service.load("u1")
    player["occupation"] = "炼丹师"
    await occupation_service.player_service.save("u1", player)

    result = await occupation_service.change_occupation("u1", "炼丹师")

    assert not result.success
    assert "已经是" in result.reason


@pytest.mark.asyncio
async def test_change_occupation_no_cert(occupation_service):
    await occupation_service.player_service.create_player("u1")

    result = await occupation_service.change_occupation("u1", "炼丹师")

    assert not result.success
    assert "转职凭证" in result.reason


@pytest.mark.asyncio
async def test_change_occupation_level_restricted(occupation_service):
    await occupation_service.player_service.create_player("u1")
    await occupation_service.inventory_service.add_item("u1", "道具", "采矿师转职凭证", 1)

    result = await occupation_service.change_occupation("u1", "采矿师")

    assert not result.success
    assert "挖矿" in result.reason


@pytest.mark.asyncio
async def test_change_occupation_success(occupation_service):
    await occupation_service.player_service.create_player("u1")
    player = await occupation_service.player_service.load("u1")
    player["level_id"] = 17
    player["occupation"] = "采矿师"
    await occupation_service.player_service.save("u1", player)
    await occupation_service.inventory_service.add_item("u1", "道具", "炼丹师转职凭证", 1)

    result = await occupation_service.change_occupation("u1", "炼丹师")

    assert result.success
    assert result.occupation == "炼丹师"
    assert result.secondary_name == "采矿师"

    updated = await occupation_service.player_service.load("u1")
    assert updated["occupation"] == "炼丹师"
    assert updated["occupation_level"] == 1
    assert updated["occupation_exp"] == 0


@pytest.mark.asyncio
async def test_change_occupation_from_liehu_success(occupation_service):
    await occupation_service.player_service.create_player("u1")
    player = await occupation_service.player_service.load("u1")
    player["occupation"] = "猎户"
    await occupation_service.player_service.save("u1", player)

    result = await occupation_service.change_occupation_from_liehu("u1", "炼丹师")

    assert result.success
    assert result.occupation == "炼丹师"


@pytest.mark.asyncio
async def test_change_occupation_from_liehu_not_liehu(occupation_service):
    await occupation_service.player_service.create_player("u1")

    result = await occupation_service.change_occupation_from_liehu("u1", "炼丹师")

    assert not result.success
    assert "不是猎户" in result.reason


@pytest.mark.asyncio
async def test_swap_secondary_occupation_success(occupation_service):
    await occupation_service.player_service.create_player("u1")
    player = await occupation_service.player_service.load("u1")
    player["occupation"] = "炼丹师"
    player["occupation_level"] = 5
    player["occupation_exp"] = 30
    await occupation_service.player_service.save("u1", player)
    await occupation_service.state_service.set(
        "xiuxian:player:u1:fuzhi",
        {"职业名": "采矿师", "职业等级": 3, "职业经验": 10},
    )

    result = await occupation_service.swap_secondary_occupation("u1")

    assert result.success
    assert result.occupation == "采矿师"
    assert result.secondary_name == "炼丹师"

    updated = await occupation_service.player_service.load("u1")
    assert updated["occupation"] == "采矿师"
    assert updated["occupation_level"] == 3


@pytest.mark.asyncio
async def test_swap_secondary_occupation_no_secondary(occupation_service):
    await occupation_service.player_service.create_player("u1")

    result = await occupation_service.swap_secondary_occupation("u1")

    assert not result.success
    assert "还没有副职" in result.reason


@pytest.mark.asyncio
async def test_start_action_player_not_found(occupation_service):
    result = await occupation_service.start_action("noone", "采矿", 30)
    assert result.player_not_found


@pytest.mark.asyncio
async def test_start_action_unknown(occupation_service):
    await occupation_service.player_service.create_player("u1")

    result = await occupation_service.start_action("u1", "挖宝", 30)

    assert not result.success
    assert result.reason == "未知职业动作"


@pytest.mark.asyncio
async def test_start_action_wrong_occupation(occupation_service):
    await occupation_service.player_service.create_player("u1")
    player = await occupation_service.player_service.load("u1")
    player["spirit_stones"] = 500
    await occupation_service.player_service.save("u1", player)

    result = await occupation_service.start_action("u1", "采矿", 30)

    assert not result.success
    assert "挖矿许可证" in result.reason


@pytest.mark.asyncio
async def test_start_action_success(occupation_service):
    await occupation_service.player_service.create_player("u1")
    player = await occupation_service.player_service.load("u1")
    player["occupation"] = "采矿师"
    await occupation_service.player_service.save("u1", player)

    result = await occupation_service.start_action("u1", "采矿", 30, now=0)

    assert result.success
    assert result.action == "采矿"
    assert result.minutes == 30


@pytest.mark.asyncio
async def test_start_action_normalizes_minutes(occupation_service):
    await occupation_service.player_service.create_player("u1")
    player = await occupation_service.player_service.load("u1")
    player["occupation"] = "采药师"
    await occupation_service.player_service.save("u1", player)

    result = await occupation_service.start_action("u1", "采药", 40, now=0)

    assert result.success
    assert result.minutes == 30


@pytest.mark.asyncio
async def test_end_action_not_started(occupation_service):
    await occupation_service.player_service.create_player("u1")

    result = await occupation_service.end_action("u1", "采矿", now=100)

    assert not result.success
    assert "没有进行采矿" in result.reason


@pytest.mark.asyncio
async def test_end_action_mining_settlement(occupation_service):
    await occupation_service.player_service.create_player("u1")
    player = await occupation_service.player_service.load("u1")
    player["occupation"] = "采矿师"
    player["level_id"] = 20
    player["occupation_level"] = 10
    await occupation_service.player_service.save("u1", player)
    await occupation_service.start_action("u1", "采矿", 60, now=0)

    result = await occupation_service.end_action("u1", "采矿", now=3600)

    assert result.success
    assert result.action == "采矿"
    assert result.exp_gained > 0
    assert len(result.items) == 4


@pytest.mark.asyncio
async def test_craft_danfang_not_alchemist(occupation_service):
    await occupation_service.player_service.create_player("u1")

    result = await occupation_service.craft_danfang("u1", "凝血丹")

    assert not result.success
    assert "丹是上午炼的" in result.reason


@pytest.mark.asyncio
async def test_craft_danfang_not_found(occupation_service):
    await occupation_service.player_service.create_player("u1")
    player = await occupation_service.player_service.load("u1")
    player["occupation"] = "炼丹师"
    await occupation_service.player_service.save("u1", player)

    result = await occupation_service.craft_danfang("u1", "不存在的丹药")

    assert not result.success
    assert "世界上没有" in result.reason


@pytest.mark.asyncio
async def test_craft_danfang_insufficient_materials(occupation_service):
    await occupation_service.player_service.create_player("u1")
    player = await occupation_service.player_service.load("u1")
    player["occupation"] = "炼丹师"
    await occupation_service.player_service.save("u1", player)

    result = await occupation_service.craft_danfang("u1", "辟谷丹")

    assert not result.success
    assert "纳戒中拥有" in result.reason


@pytest.mark.asyncio
async def test_craft_danfang_success(occupation_service):
    await occupation_service.player_service.create_player("u1")
    player = await occupation_service.player_service.load("u1")
    player["occupation"] = "炼丹师"
    await occupation_service.player_service.save("u1", player)
    await occupation_service.inventory_service.add_item("u1", "草药", "万年凝血草", 10)
    await occupation_service.inventory_service.add_item("u1", "草药", "万年血精草", 10)

    result = await occupation_service.craft_danfang("u1", "辟谷丹", quantity=1)

    assert result.success
    assert result.name == "辟谷丹"
    assert result.quantity > 0


@pytest.mark.asyncio
async def test_craft_zhizuo_not_fushi(occupation_service):
    await occupation_service.player_service.create_player("u1")

    result = await occupation_service.craft_zhizuo("u1", "符笔")

    assert not result.success
    assert "符道玄奥" in result.reason


@pytest.mark.asyncio
async def test_craft_zhizuo_success(occupation_service):
    await occupation_service.player_service.create_player("u1")
    player = await occupation_service.player_service.load("u1")
    player["occupation"] = "符师"
    await occupation_service.player_service.save("u1", player)
    await occupation_service.inventory_service.add_item("u1", "道具", "灵兽毫毛", 10)
    await occupation_service.inventory_service.add_item("u1", "草药", "千年灵木", 10)

    result = await occupation_service.craft_zhizuo("u1", "符笔")

    assert result.success
    assert result.name == "符笔"


@pytest.mark.asyncio
async def test_craft_equipment_not_smith(occupation_service):
    await occupation_service.player_service.create_player("u1")

    result = await occupation_service.craft_equipment("u1", "【超维】天帝剑")

    assert not result.success
    assert "铜都不炼" in result.reason


@pytest.mark.asyncio
async def test_craft_equipment_success(occupation_service):
    await occupation_service.player_service.create_player("u1")
    player = await occupation_service.player_service.load("u1")
    player["occupation"] = "炼器师"
    player["occupation_level"] = 60
    await occupation_service.player_service.save("u1", player)
    await occupation_service.inventory_service.add_item("u1", "材料", "庚金", 10000000)
    await occupation_service.inventory_service.add_item("u1", "材料", "玄土", 10000000)
    await occupation_service.inventory_service.add_item("u1", "材料", "万维梵宇之石", 100)
    await occupation_service.inventory_service.add_item("u1", "材料", "超维位格碎片", 10)
    await occupation_service.inventory_service.add_item("u1", "材料", "天宇地宙石", 10)

    result = await occupation_service.craft_equipment("u1", "【超维】天帝剑")

    assert result.success
    assert result.name == "【超维】天帝剑"
    assert result.quality in ["劣", "普", "优", "精", "极", "绝", "顶"]
