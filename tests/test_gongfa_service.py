from pathlib import Path

import pytest

from src.data.item_data import ItemCatalog
from src.services.gongfa_service import GongfaService
from src.services.player_service import PlayerService


@pytest.fixture
def gongfa_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    project_data_dir = Path(__file__).parent.parent / "data"
    item_catalog = ItemCatalog(data_dir=project_data_dir)
    return GongfaService(
        player_service=player_service,
        item_catalog=item_catalog,
    )


@pytest.mark.asyncio
async def test_list_learned_for_new_player(gongfa_service):
    """新玩家尚未学习任何功法。"""
    await gongfa_service.player_service.create_player("u1")

    result = await gongfa_service.list_learned("u1")

    assert not result.player_not_found
    assert result.learned == []


@pytest.mark.asyncio
async def test_learn_gongfa_success(gongfa_service):
    """学习已存在的功法应成功。"""
    await gongfa_service.player_service.create_player("u1")

    result = await gongfa_service.learn("u1", "维宙星灭诀")

    assert result.success
    assert result.name == "维宙星灭诀"

    learned = await gongfa_service.list_learned("u1")
    assert learned.learned == ["维宙星灭诀"]


@pytest.mark.asyncio
async def test_learn_gongfa_not_found(gongfa_service):
    """学习不存在的功法应返回 not_found。"""
    await gongfa_service.player_service.create_player("u1")

    result = await gongfa_service.learn("u1", "不存在的功法")

    assert result.not_found
    assert not result.success


@pytest.mark.asyncio
async def test_learn_gongfa_already_learned(gongfa_service):
    """重复学习同一功法应返回 already_learned。"""
    await gongfa_service.player_service.create_player("u1")
    await gongfa_service.learn("u1", "维宙星灭诀")

    result = await gongfa_service.learn("u1", "维宙星灭诀")

    assert result.already_learned
    assert not result.success


@pytest.mark.asyncio
async def test_has_learned(gongfa_service):
    """has_learned 应正确反映学习状态。"""
    await gongfa_service.player_service.create_player("u1")
    assert not await gongfa_service.has_learned("u1", "维宙星灭诀")

    await gongfa_service.learn("u1", "维宙星灭诀")
    assert await gongfa_service.has_learned("u1", "维宙星灭诀")


@pytest.mark.asyncio
async def test_learn_gongfa_player_not_found(gongfa_service):
    """未创建角色时学习功法应返回 player_not_found。"""
    result = await gongfa_service.learn("noone", "维宙星灭诀")

    assert result.player_not_found
    assert not result.success
