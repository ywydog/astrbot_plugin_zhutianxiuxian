import pytest

from src.services.lifespan_service import LifespanService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@pytest.fixture
def lifespan_deps(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    state_service = StateService(data_dir=tmp_path)
    lifespan_service = LifespanService(
        player_service=player_service,
        state_service=state_service,
    )
    return lifespan_service, player_service, state_service


@pytest.fixture
def lifespan_service(lifespan_deps):
    return lifespan_deps[0]


@pytest.fixture
def player_service(lifespan_deps):
    return lifespan_deps[1]


@pytest.fixture
def state_service(lifespan_deps):
    return lifespan_deps[2]


def _make_player(pid, **kwargs):
    return {
        "id": pid,
        "name": kwargs.get("name", f"道友{pid}"),
        "level_id": kwargs.get("level_id", 1),
        "shouyuan": kwargs.get("shouyuan", 1000),
        "linggen": kwargs.get("linggen", {"type": "金"}),
    }


@pytest.mark.asyncio
async def test_get_lifespan_for_existing_player(lifespan_service, player_service):
    await player_service.save("p1", _make_player("p1", shouyuan=500))

    lifespan = await lifespan_service.get_lifespan("p1")

    assert lifespan == 500


@pytest.mark.asyncio
async def test_get_lifespan_for_missing_player(lifespan_service):
    assert await lifespan_service.get_lifespan("notfound") is None


@pytest.mark.asyncio
async def test_reduce_lifespan_task_normal_level(lifespan_service, player_service):
    await player_service.save("p1", _make_player("p1", level_id=42, shouyuan=2000))

    result = await lifespan_service.reduce_lifespan_task()

    assert result.processed == 1
    player = await player_service.load("p1")
    assert player["shouyuan"] == 1000


@pytest.mark.asyncio
async def test_reduce_lifespan_task_low_level_uses_fixed_amount(
    lifespan_service, player_service
):
    await player_service.save("p1", _make_player("p1", level_id=10, shouyuan=100))

    await lifespan_service.reduce_lifespan_task()

    player = await player_service.load("p1")
    assert player["shouyuan"] == 80


@pytest.mark.asyncio
async def test_reduce_lifespan_task_high_level_gets_half(lifespan_service, player_service):
    await player_service.save("p1", _make_player("p1", level_id=51, shouyuan=2000))

    await lifespan_service.reduce_lifespan_task()

    player = await player_service.load("p1")
    assert player["shouyuan"] == 1500


@pytest.mark.asyncio
async def test_reduce_lifespan_task_special_body_ratio(lifespan_service, player_service):
    await player_service.save(
        "p1", _make_player("p1", level_id=42, shouyuan=2000, linggen={"type": "圣体道胎"})
    )

    await lifespan_service.reduce_lifespan_task()

    player = await player_service.load("p1")
    assert player["shouyuan"] == 1700


@pytest.mark.asyncio
async def test_reduce_lifespan_task_skips_gm(lifespan_service, player_service):
    await player_service.save("p1", _make_player("p1", name="GM测试", shouyuan=1000))

    result = await lifespan_service.reduce_lifespan_task()

    assert result.processed == 0
    assert result.skipped_gm == 1
    player = await player_service.load("p1")
    assert player["shouyuan"] == 1000


@pytest.mark.asyncio
async def test_reduce_lifespan_task_skips_sealed(lifespan_service, player_service, state_service):
    await player_service.save("p1", _make_player("p1", shouyuan=1000))
    await state_service.set("xiuxian:player:p1:action", {"action": "神源封印"})

    result = await lifespan_service.reduce_lifespan_task()

    assert result.processed == 0
    assert result.skipped_sealed == 1
    player = await player_service.load("p1")
    assert player["shouyuan"] == 1000


@pytest.mark.asyncio
async def test_reduce_lifespan_manual_uses_manual_rules(lifespan_service, player_service):
    await player_service.save("p1", _make_player("p1", level_id=10, shouyuan=1000))

    await lifespan_service.reduce_lifespan_manual(1000)

    player = await player_service.load("p1")
    assert player["shouyuan"] == 900


@pytest.mark.asyncio
async def test_reduce_lifespan_manual_yuancheng_ratio(lifespan_service, player_service):
    await player_service.save(
        "p1", _make_player("p1", level_id=42, shouyuan=2000, linggen={"type": "圆环之理"})
    )

    await lifespan_service.reduce_lifespan_manual(1000)

    player = await player_service.load("p1")
    assert player["shouyuan"] == 1900


@pytest.mark.asyncio
async def test_reduce_lifespan_never_negative(lifespan_service, player_service):
    await player_service.save("p1", _make_player("p1", level_id=42, shouyuan=100))

    await lifespan_service.reduce_lifespan_task()

    player = await player_service.load("p1")
    assert player["shouyuan"] == 0


@pytest.mark.asyncio
async def test_reduce_lifespan_counts_high_level_and_special_body(
    lifespan_service, player_service
):
    await player_service.save("p1", _make_player("p1", level_id=51, shouyuan=2000))
    await player_service.save(
        "p2", _make_player("p2", level_id=42, shouyuan=2000, linggen={"type": "神体"})
    )

    result = await lifespan_service.reduce_lifespan_task()

    assert result.processed == 2
    assert result.high_level_count == 1
    assert result.special_body_count == 1
