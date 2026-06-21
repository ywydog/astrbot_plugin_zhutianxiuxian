from pathlib import Path

import pytest

from src.data.level_data import LevelData
from src.services.player_service import PlayerService
from src.services.yuanshen_service import YuanshenService


@pytest.fixture
def yuanshen_deps(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    project_data_dir = tmp_path / "data"
    project_data_dir.mkdir(parents=True, exist_ok=True)
    # 复制一份元神境界数据到临时目录
    source = (
        Path(__file__).parent.parent / "data" / "levels" / "元神境界.json"
    )
    if source.exists():
        (project_data_dir / "levels").mkdir(parents=True, exist_ok=True)
        (project_data_dir / "levels" / "元神境界.json").write_text(
            source.read_text(encoding="utf-8"), encoding="utf-8"
        )
    level_data = LevelData(data_dir=project_data_dir)
    yuanshen_service = YuanshenService(
        player_service=player_service,
        level_data=level_data,
    )
    return yuanshen_service, player_service, level_data


@pytest.fixture
def yuanshen_service(yuanshen_deps):
    return yuanshen_deps[0]


@pytest.fixture
def player_service(yuanshen_deps):
    return yuanshen_deps[1]


def _make_player(pid, **kwargs):
    return {
        "id": pid,
        "name": kwargs.get("name", f"道友{pid}"),
        "yuanshen": kwargs.get("yuanshen", 0),
        "yuanshen_limit": kwargs.get("yuanshen_limit", 0),
        "yuanshenlevel_id": kwargs.get("yuanshenlevel_id"),
        "shenshi": kwargs.get("shenshi", 0),
        "neijingdi": kwargs.get("neijingdi", 0),
        "ninglian_count": kwargs.get("ninglian_count", 1),
        "mijing_level_id": kwargs.get("mijing_level_id", 1),
        "xiangu_level_id": kwargs.get("xiangu_level_id", 1),
        "level_id": kwargs.get("level_id", 1),
        "physique_id": kwargs.get("physique_id", 1),
        "daoshang": kwargs.get("daoshang", 0),
        "exp": kwargs.get("exp", 0),
        "blood_qi": kwargs.get("blood_qi", 0),
    }


@pytest.mark.asyncio
async def test_get_status_not_condensed(yuanshen_service, player_service):
    await player_service.save("p1", _make_player("p1", yuanshen=1000))

    result = await yuanshen_service.get_status("p1")

    assert result.not_condensed is True
    assert result.yuanshen == 1000


@pytest.mark.asyncio
async def test_get_status_condensed(yuanshen_service, player_service):
    await player_service.save("p1", _make_player("p1", yuanshenlevel_id=2))

    result = await yuanshen_service.get_status("p1")

    assert result.level_id == 2
    assert result.level_name == "王者/真神级元神"


@pytest.mark.asyncio
async def test_condense_first_time(yuanshen_service, player_service):
    await player_service.save(
        "p1", _make_player("p1", yuanshen=20_000_000, yuanshenlevel_id=None)
    )

    result = await yuanshen_service.condense("p1")

    assert result.success is True
    assert result.level_id == 0
    player = await player_service.load("p1")
    assert player["yuanshenlevel_id"] == 0
    assert player["yuanshen"] == 5_000_000


@pytest.mark.asyncio
async def test_condense_insufficient_yuanshen(yuanshen_service, player_service):
    await player_service.save("p1", _make_player("p1", yuanshen=1000))

    result = await yuanshen_service.condense("p1")

    assert result.insufficient_yuanshen is True


@pytest.mark.asyncio
async def test_condense_upgrade_requires_mijing(yuanshen_service, player_service):
    await player_service.save(
        "p1",
        _make_player(
            "p1",
            yuanshen=100_000_000,
            yuanshenlevel_id=5,
            mijing_level_id=12,
            xiangu_level_id=1,
        ),
    )

    result = await yuanshen_service.condense("p1")

    assert result.insufficient_mijing is True
    assert result.required_mijing_level == 15


@pytest.mark.asyncio
async def test_condense_upgrade_requires_xiangu(yuanshen_service, player_service):
    await player_service.save(
        "p1",
        _make_player(
            "p1",
            yuanshen=100_000_000,
            yuanshenlevel_id=5,
            mijing_level_id=20,
            xiangu_level_id=10,
        ),
    )

    result = await yuanshen_service.condense("p1")

    assert result.insufficient_xiangu is True
    assert result.required_xiangu_level == 13


@pytest.mark.asyncio
async def test_open_neijing_not_condensed(yuanshen_service, player_service):
    await player_service.save("p1", _make_player("p1"))

    result = await yuanshen_service.open_neijing("p1")

    assert result.not_condensed is True


@pytest.mark.asyncio
async def test_open_neijing_already_open(yuanshen_service, player_service):
    await player_service.save(
        "p1", _make_player("p1", yuanshenlevel_id=1, neijingdi=1, yuanshen=1_000_000_000)
    )

    result = await yuanshen_service.open_neijing("p1")

    assert result.already_open is True


@pytest.mark.asyncio
async def test_open_neijing_insufficient_yuanshen(yuanshen_service, player_service):
    await player_service.save(
        "p1", _make_player("p1", yuanshenlevel_id=1, yuanshen=0)
    )

    result = await yuanshen_service.open_neijing("p1")

    assert result.insufficient_yuanshen is True


@pytest.mark.asyncio
async def test_enter_neijing_not_open(yuanshen_service, player_service):
    await player_service.save("p1", _make_player("p1", neijingdi=0))

    result = await yuanshen_service.enter_neijing("p1")

    assert result.not_open is True


@pytest.mark.asyncio
async def test_enter_neijing_success(yuanshen_service, player_service):
    await player_service.save(
        "p1",
        _make_player(
            "p1",
            neijingdi=1,
            mijing_level_id=2,
            xiangu_level_id=2,
            level_id=3,
            physique_id=2,
            exp=0,
            blood_qi=0,
            shenshi=0,
            daoshang=1.0,
        ),
    )

    result = await yuanshen_service.enter_neijing("p1")

    assert result.success is True
    assert result.exp_gained > 0
    assert result.daoshang_reduced > 0
    player = await player_service.load("p1")
    assert player["neijingdi"] == 0
    assert player["exp"] == result.exp_gained


@pytest.mark.asyncio
async def test_neijing_batch_not_condensed(yuanshen_service, player_service):
    await player_service.save("p1", _make_player("p1"))

    result = await yuanshen_service.neijing_batch("p1", 5)

    assert result.not_condensed is True


@pytest.mark.asyncio
async def test_neijing_batch_limited_to_50(yuanshen_service, player_service):
    await player_service.save(
        "p1",
        _make_player(
            "p1",
            yuanshenlevel_id=1,
            yuanshen=1_000_000_000,
            mijing_level_id=1,
            xiangu_level_id=1,
        ),
    )

    result = await yuanshen_service.neijing_batch("p1", 100)

    assert result.planned == 50
