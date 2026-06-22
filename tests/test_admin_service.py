import pytest

from src.services.admin_service import AdminService, ERAS
from src.services.player_service import PlayerService


@pytest.fixture
def admin_service(tmp_path):
    player_service = PlayerService(data_dir=tmp_path)
    return AdminService(player_service=player_service, data_dir=tmp_path)


@pytest.mark.asyncio
async def test_non_admin_denied(admin_service):
    await admin_service.player_service.create_player("user1")
    result = await admin_service.add_spirit_stones("not_admin", "user1", 100)
    assert not result.success
    assert result.not_admin


@pytest.mark.asyncio
async def test_add_admin(admin_service):
    result = await admin_service.add_admin("admin1")
    assert result.success
    assert "admin1" in result.message

    result2 = await admin_service.add_admin("admin1")
    assert not result2.success


@pytest.mark.asyncio
async def test_backup_and_restore(admin_service, tmp_path):
    await admin_service.player_service.create_player("user1")
    result = await admin_service.backup()
    assert result.success
    assert result.backup_path
    assert (tmp_path / "backups").exists()

    filename = result.backup_path.split("/")[-1]
    # 修改数据后恢复
    await admin_service.player_service.save("user1", {"id": "user1", "test": 1})
    restore_result = await admin_service.restore(filename)
    assert restore_result.success
    player = await admin_service.player_service.load("user1")
    assert player["id"] == "user1"
    assert "test" not in player


@pytest.mark.asyncio
async def test_add_spirit_stones(admin_service):
    await admin_service.add_admin("admin1")
    await admin_service.player_service.create_player("user1")
    result = await admin_service.add_spirit_stones("admin1", "user1", 500)
    assert result.success
    player = await admin_service.player_service.load("user1")
    assert player["spirit_stones"] == 10500


@pytest.mark.asyncio
async def test_add_source_stones(admin_service):
    await admin_service.add_admin("admin1")
    await admin_service.player_service.create_player("user1")
    result = await admin_service.add_source_stones("admin1", "user1", 200)
    assert result.success
    player = await admin_service.player_service.load("user1")
    assert player["source_stones"] == 200


@pytest.mark.asyncio
async def test_add_stones_player_not_found(admin_service):
    await admin_service.add_admin("admin1")
    result = await admin_service.add_spirit_stones("admin1", "ghost", 100)
    assert not result.success
    assert result.player_not_found


@pytest.mark.asyncio
async def test_ban_and_unban(admin_service):
    await admin_service.add_admin("admin1")
    await admin_service.player_service.create_player("user1")

    ban_result = await admin_service.ban("admin1", "user1")
    assert ban_result.success
    assert await admin_service.is_banned("user1")
    player = await admin_service.player_service.load("user1")
    assert player["banned"] is True

    unban_result = await admin_service.unban("admin1", "user1")
    assert unban_result.success
    assert not await admin_service.is_banned("user1")
    player = await admin_service.player_service.load("user1")
    assert player["banned"] is False


@pytest.mark.asyncio
async def test_set_era(admin_service):
    await admin_service.add_admin("admin1")
    result = await admin_service.set_era("admin1", "太古时代")
    assert result.success

    info = await admin_service.get_era_info()
    assert info.success
    assert info.data["name"] == "太古时代"
    assert info.data["index"] == 1


@pytest.mark.asyncio
async def test_set_era_unknown(admin_service):
    await admin_service.add_admin("admin1")
    result = await admin_service.set_era("admin1", "不存在的时代")
    assert not result.success


@pytest.mark.asyncio
async def test_next_era(admin_service):
    await admin_service.add_admin("admin1")
    await admin_service.set_era("admin1", "神话时代")
    result = await admin_service.next_era("admin1")
    assert result.success

    info = await admin_service.get_era_info()
    assert info.data["name"] == "太古时代"

    # 循环
    for _ in range(len(ERAS) - 1):
        await admin_service.next_era("admin1")
    info = await admin_service.get_era_info()
    assert info.data["name"] == "神话时代"


@pytest.mark.asyncio
async def test_toggle_auto_task(admin_service):
    await admin_service.player_service.create_player("user1")
    result = await admin_service.toggle_auto_task("user1", True)
    assert result.success
    assert "开启" in result.message

    status = await admin_service.get_auto_task_status("user1")
    assert status.data["enabled"] is True

    result2 = await admin_service.toggle_auto_task("user1", False)
    assert result2.success
    assert "关闭" in result2.message


@pytest.mark.asyncio
async def test_run_auto_daily_task(admin_service):
    await admin_service.player_service.create_player("user1")
    await admin_service.toggle_auto_task("user1", True)

    result = await admin_service.run_auto_daily_task("user1", today="2026-06-22")
    assert result.success
    player = await admin_service.player_service.load("user1")
    assert player["spirit_stones"] == 10100
    assert player["source_stones"] == 50
    assert player["exp"] == 201

    # 同一天再次执行失败
    result2 = await admin_service.run_auto_daily_task("user1", today="2026-06-22")
    assert not result2.success


@pytest.mark.asyncio
async def test_run_auto_task_not_enabled(admin_service):
    await admin_service.player_service.create_player("user1")
    result = await admin_service.run_auto_daily_task("user1", today="2026-06-22")
    assert not result.success
    assert "未开启" in result.message
