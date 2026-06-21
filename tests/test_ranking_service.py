import pytest

from src.services.player_service import PlayerService
from src.services.ranking_service import RankingService


@pytest.fixture
def ranking_deps(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    ranking_service = RankingService(player_service=player_service, data_dir=tmp_path)
    return ranking_service, player_service


@pytest.fixture
def ranking_service(ranking_deps):
    return ranking_deps[0]


@pytest.fixture
def player_service(ranking_deps):
    return ranking_deps[1]


def _make_player(pid, **kwargs):
    player = {
        "id": pid,
        "name": kwargs.get("name", f"道友{pid}"),
        "level_id": kwargs.get("level_id", 1),
        "exp": kwargs.get("exp", 0),
        "spirit_stones": kwargs.get("spirit_stones", 0),
        "modao_value": kwargs.get("modao_value", 0),
        "attack_bonus": kwargs.get("attack_bonus", 0),
        "defense_bonus": kwargs.get("defense_bonus", 0),
        "hp_bonus": kwargs.get("hp_bonus", 0),
    }
    return player


@pytest.mark.asyncio
async def test_modao_ranking(ranking_service, player_service):
    await player_service.save("p1", _make_player("p1", modao_value=100))
    await player_service.save("p2", _make_player("p2", modao_value=300))
    await player_service.save("p3", _make_player("p3", modao_value=200))

    result = await ranking_service.get_modao_ranking(limit=2)

    assert len(result) == 2
    assert result[0]["user_id"] == "p2"
    assert result[0]["score"] == 300
    assert result[1]["user_id"] == "p3"


@pytest.mark.asyncio
async def test_enhance_ranking(ranking_service, player_service):
    await player_service.save(
        "p1", _make_player("p1", attack_bonus=10, defense_bonus=20, hp_bonus=30)
    )
    await player_service.save(
        "p2", _make_player("p2", attack_bonus=100, defense_bonus=50, hp_bonus=25)
    )

    result = await ranking_service.get_enhance_ranking(limit=10)

    assert len(result) == 2
    assert result[0]["user_id"] == "p2"
    assert result[0]["score"] == 175
    assert result[1]["score"] == 60


@pytest.mark.asyncio
async def test_exp_ranking(ranking_service, player_service):
    await player_service.save("p1", _make_player("p1", exp=1000))
    await player_service.save("p2", _make_player("p2", exp=5000))

    result = await ranking_service.get_exp_ranking(limit=10)

    assert result[0]["user_id"] == "p2"
    assert result[0]["score"] == 5000


@pytest.mark.asyncio
async def test_spirit_stones_ranking(ranking_service, player_service):
    await player_service.save("p1", _make_player("p1", spirit_stones=999))
    await player_service.save("p2", _make_player("p2", spirit_stones=10000))

    result = await ranking_service.get_spirit_stones_ranking(limit=10)

    assert result[0]["user_id"] == "p2"
    assert result[0]["score"] == 10000


@pytest.mark.asyncio
async def test_ranking_empty(ranking_service):
    result = await ranking_service.get_modao_ranking(limit=10)
    assert result == []


@pytest.mark.asyncio
async def test_ranking_limit(ranking_service, player_service):
    for i in range(5):
        await player_service.save(f"p{i}", _make_player(f"p{i}", modao_value=i))

    result = await ranking_service.get_modao_ranking(limit=3)

    assert len(result) == 3
    assert result[0]["user_id"] == "p4"
