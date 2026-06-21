from pathlib import Path

import pytest

from src.services.state_service import StateService


@pytest.fixture
def state_service(tmp_path):
    return StateService(data_dir=tmp_path)


@pytest.mark.asyncio
async def test_get_set_delete(state_service, tmp_path):
    """状态服务应支持 get/set/delete。"""
    assert await state_service.get("player:123:cd") is None
    assert await state_service.get("player:123:cd", default=0) == 0

    await state_service.set("player:123:cd", "2026-06-21")
    assert await state_service.get("player:123:cd") == "2026-06-21"

    await state_service.delete("player:123:cd")
    assert await state_service.get("player:123:cd") is None

    state_file = tmp_path / "state" / "player_123_cd.json"
    assert not state_file.exists()
