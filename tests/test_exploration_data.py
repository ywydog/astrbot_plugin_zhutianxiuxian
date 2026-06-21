import json
from pathlib import Path

import pytest

from src.data.exploration_data import ExplorationData


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
            "one": [],
            "two": [],
            "three": [],
            "four": [],
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
            "one": [],
            "two": [],
            "three": [],
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
            "one": [],
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


class TestExplorationData:
    def test_load_secret_places(self, data_dir: Path) -> None:
        data = ExplorationData(data_dir)
        places = data.get_secret_places()
        assert len(places) == 2
        assert places[0]["name"] == "灵墟洞天"

    def test_find_secret_place(self, data_dir: Path) -> None:
        data = ExplorationData(data_dir)
        place = data.find_secret_place("永恒海")
        assert place is not None
        assert place["Price"] == 5000

    def test_find_secret_place_not_found(self, data_dir: Path) -> None:
        data = ExplorationData(data_dir)
        assert data.find_secret_place("不存在的秘境") is None

    def test_load_forbidden_areas(self, data_dir: Path) -> None:
        data = ExplorationData(data_dir)
        areas = data.get_forbidden_areas()
        assert len(areas) == 1
        assert areas[0]["name"] == "灭仙洞"

    def test_find_forbidden_area(self, data_dir: Path) -> None:
        data = ExplorationData(data_dir)
        area = data.find_forbidden_area("灭仙洞")
        assert area is not None
        assert area["experience"] == 200000

    def test_load_time_places(self, data_dir: Path) -> None:
        data = ExplorationData(data_dir)
        places = data.get_time_places()
        assert len(places) == 1
        assert places[0]["name"] == "无欲天仙"

    def test_load_fairy_realms(self, data_dir: Path) -> None:
        data = ExplorationData(data_dir)
        realms = data.get_fairy_realms()
        assert len(realms) == 1
        assert realms[0]["name"] == "瑶池仙境"

    def test_find_place_across_all(self, data_dir: Path) -> None:
        data = ExplorationData(data_dir)
        assert data.find_place("灵墟洞天")["Grade"] == "秘境"
        assert data.find_place("灭仙洞")["Grade"] == "禁地"
        assert data.find_place("无欲天仙")["Grade"] == "限定*仙府"
        assert data.find_place("瑶池仙境")["Grade"] == "仙境"
        assert data.find_place("不存在") is None
