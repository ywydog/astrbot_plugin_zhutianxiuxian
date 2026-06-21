import json
from pathlib import Path

import pytest

from src.data.exploration_data import ExplorationData
from src.services.exploration_service import ExplorationService
from src.services.player_service import PlayerService
from src.services.state_service import StateService


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    data_dir = tmp_path / "data"
    items_dir = data_dir / "items" / "副本"
    items_dir.mkdir(parents=True)

    secret_places = [
        {
            "id": 1,
            "name": "灵墟洞天",
            "Grade": "秘境",
            "Price": 1000,
            "shouyuan": 1,
            "experience": 0,
            "Best": [],
            "one": [{"name": "一品丹药"}],
            "two": [{"name": "二品丹药"}],
            "three": [{"name": "三品丹药"}],
            "four": [{"name": "四品丹药"}],
        },
        {
            "id": 2,
            "name": "永恒海",
            "Grade": "秘境",
            "Price": 5000,
            "shouyuan": 5,
            "experience": 0,
            "Best": [],
            "one": [],
            "two": [],
            "three": [],
            "four": [],
        },
    ]
    forbidden_areas = [
        {
            "id": 334,
            "name": "灭仙洞",
            "Grade": "禁地",
            "Price": 200000,
            "experience": 200000,
            "shouyuan": 10,
            "Best": [],
            "one": [],
            "two": [],
            "three": [],
            "four": [],
        }
    ]
    time_places = [
        {
            "id": 251,
            "name": "无欲天仙",
            "Grade": "限定*仙府",
            "Price": 700000,
            "Best": [],
            "one": [{"name": "十转神丹"}],
            "two": [{"name": "六阶玄元丹"}],
            "three": [{"name": "六阶淬体丹"}],
        }
    ]
    fairy_realms = [
        {
            "id": 100089,
            "name": "瑶池仙境",
            "Grade": "仙境",
            "Price": 75000,
            "shouyuan": 1,
            "Best": [],
            "one": [{"name": "仙晶"}],
            "two": [],
            "three": [],
        }
    ]

    (items_dir / "地点列表.json").write_text(
        json.dumps(secret_places, ensure_ascii=False), encoding="utf-8"
    )
    (items_dir / "禁地列表.json").write_text(
        json.dumps(forbidden_areas, ensure_ascii=False), encoding="utf-8"
    )
    (items_dir / "限定仙府.json").write_text(
        json.dumps(time_places, ensure_ascii=False), encoding="utf-8"
    )
    (items_dir / "仙境列表.json").write_text(
        json.dumps(fairy_realms, ensure_ascii=False), encoding="utf-8"
    )

    return data_dir


@pytest.fixture
def services(data_dir: Path):
    player_service = PlayerService(data_dir=data_dir)
    state_service = StateService(data_dir=data_dir)
    exploration_data = ExplorationData(data_dir=data_dir)
    exploration_service = ExplorationService(
        player_service=player_service,
        state_service=state_service,
        exploration_data=exploration_data,
    )
    return player_service, state_service, exploration_service


class TestExplorationService:
    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_secret_place_player_not_found(self, services) -> None:
        _, _, svc = services
        result = await svc.start_secret_place("user1", "灵墟洞天", now=0)
        assert result.player_not_found
        assert not result.success

    @pytest.mark.asyncio
    async def test_secret_place_not_found(self, services) -> None:
        player_service, _, svc = services
        await player_service.create_player("user1")
        result = await svc.start_secret_place("user1", "不存在", now=0)
        assert not result.success
        assert "未知" in result.reason or "不存在" in result.reason

    @pytest.mark.asyncio
    async def test_secret_place_insufficient_resources(self, services) -> None:
        player_service, _, svc = services
        await player_service.create_player("user1")
        player = await player_service.load("user1")
        player["spirit_stones"] = 100
        player["shouyuan"] = 1
        await player_service.save("user1", player)

        result = await svc.start_secret_place("user1", "灵墟洞天", now=0)
        assert not result.success
        assert "灵石" in result.reason

    @pytest.mark.asyncio
    async def test_secret_place_success(self, services) -> None:
        player_service, state_service, svc = services
        await player_service.create_player("user1")
        player = await player_service.load("user1")
        player["spirit_stones"] = 100000
        player["shouyuan"] = 100
        await player_service.save("user1", player)

        result = await svc.start_secret_place("user1", "灵墟洞天", now=0)
        assert result.success
        assert "灵墟洞天" in result.message

        player = await player_service.load("user1")
        assert player["spirit_stones"] == 99000
        assert player["shouyuan"] == 99

        action = await state_service.get("xiuxian:player:user1:action")
        assert action is not None
        assert action["action"] == "秘境历练"

    @pytest.mark.asyncio
    async def test_forbidden_area_level_requirement(self, services) -> None:
        player_service, _, svc = services
        await player_service.create_player("user1")
        player = await player_service.load("user1")
        player["level_id"] = 1
        player["spirit_stones"] = 1000000
        player["exp"] = 1000000
        player["shouyuan"] = 100
        await player_service.save("user1", player)

        result = await svc.start_forbidden_area("user1", "灭仙洞", now=0)
        assert not result.success
        assert "化神" in result.reason

    @pytest.mark.asyncio
    async def test_forbidden_area_success(self, services) -> None:
        player_service, state_service, svc = services
        await player_service.create_player("user1")
        player = await player_service.load("user1")
        player["level_id"] = 22
        player["spirit_stones"] = 1000000
        player["exp"] = 1000000
        player["blood_qi"] = 1000000
        player["shouyuan"] = 100
        await player_service.save("user1", player)

        result = await svc.start_forbidden_area("user1", "灭仙洞", now=0)
        assert result.success
        assert "灭仙洞" in result.message

        player = await player_service.load("user1")
        assert player["exp"] == 800000
        assert player["spirit_stones"] == 800000

    @pytest.mark.asyncio
    async def test_time_place_success(self, services) -> None:
        player_service, state_service, svc = services
        await player_service.create_player("user1")
        player = await player_service.load("user1")
        player["level_id"] = 21
        player["spirit_stones"] = 1000000
        player["exp"] = 200000
        player["shouyuan"] = 100
        await player_service.save("user1", player)

        result = await svc.start_time_place("user1", now=0)
        assert result.success
        assert "仙府" in result.message

        player = await player_service.load("user1")
        assert player["exp"] == 100000
        assert player["spirit_stones"] < 1000000

    @pytest.mark.asyncio
    async def test_fairy_realm_level_requirement(self, services) -> None:
        player_service, _, svc = services
        await player_service.create_player("user1")
        player = await player_service.load("user1")
        player["level_id"] = 1
        player["spirit_stones"] = 1000000
        player["shouyuan"] = 100
        await player_service.save("user1", player)

        result = await svc.start_fairy_realm("user1", "瑶池仙境", now=0)
        assert not result.success
        assert "成仙" in result.reason

    @pytest.mark.asyncio
    async def test_fairy_realm_success(self, services) -> None:
        player_service, state_service, svc = services
        await player_service.create_player("user1")
        player = await player_service.load("user1")
        player["level_id"] = 42
        player["spirit_stones"] = 1000000
        player["shouyuan"] = 100
        await player_service.save("user1", player)

        result = await svc.start_fairy_realm("user1", "瑶池仙境", now=0)
        assert result.success
        assert "瑶池仙境" in result.message

        action = await state_service.get("xiuxian:player:user1:action")
        assert action is not None
        assert action["action"] == "镇守仙境"

    @pytest.mark.asyncio
    async def test_give_up(self, services) -> None:
        player_service, state_service, svc = services
        await player_service.create_player("user1")
        player = await player_service.load("user1")
        player["spirit_stones"] = 100000
        player["shouyuan"] = 100
        await player_service.save("user1", player)

        await svc.start_secret_place("user1", "灵墟洞天", now=0)
        result = await svc.give_up("user1", now=0)
        assert result.success
        assert "逃离" in result.message

        action = await state_service.get("xiuxian:player:user1:action")
        assert action is None

    @pytest.mark.asyncio
    async def test_drop_text(self, services) -> None:
        _, _, svc = services
        text = await svc.get_drop_text("灵墟洞天")
        assert "灵墟洞天" in text
        assert "一品丹药" in text

    @pytest.mark.asyncio
    async def test_busy_action(self, services) -> None:
        player_service, _, svc = services
        await player_service.create_player("user1")
        player = await player_service.load("user1")
        player["spirit_stones"] = 1000000
        player["shouyuan"] = 100
        await player_service.save("user1", player)

        await svc.start_secret_place("user1", "灵墟洞天", now=0)
        result = await svc.start_secret_place("user1", "灵墟洞天", now=0)
        assert not result.success
        assert "正在" in result.reason
