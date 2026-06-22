import json
import shutil
import tarfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.services.player_service import PlayerService

ERAS = [
    {
        "name": "神话时代",
        "description": "天地初开，神灵显化。灵药遍地，异兽横行。大道法则清晰可见，凡人亦可感悟天道至理。",
    },
    {
        "name": "太古时代",
        "description": "神魔大战，万族并起。武道昌盛，血脉之力如江河奔涌。顶级修士可掌阴阳五行，移山填海。",
    },
    {
        "name": "天命时代",
        "description": "天命既明，规则既定。各族鼎立，宗门林立。灵气平稳有序，强者辈出。",
    },
    {
        "name": "末法时代",
        "description": "天道倾斜，灵气枯竭。规则崩坏，修行之途日渐艰难。仙路渐闭，凡人武道崛起。",
    },
    {
        "name": "绝灵时代",
        "description": "天地寂灭，灵气断绝。末法终结，万物归凡。曾经的修仙之道已成传说。",
    },
]

ERA_NAME_MAP = {era["name"]: i for i, era in enumerate(ERAS)}


@dataclass
class AdminResult:
    success: bool = False
    message: str = ""
    player_not_found: bool = False
    not_admin: bool = False
    backup_path: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class AdminService:
    """管理/备份/运营服务。"""

    def __init__(self, player_service: PlayerService, data_dir: Path):
        self.player_service = player_service
        self.data_dir = data_dir
        self.backup_dir = data_dir / "backups"
        self.admin_dir = data_dir / "admin"
        self.era_dir = data_dir / "era"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.admin_dir.mkdir(parents=True, exist_ok=True)
        self.era_dir.mkdir(parents=True, exist_ok=True)

    # ---------- 内部工具 ----------

    def _admin_file(self) -> Path:
        return self.admin_dir / "admin.json"

    def _era_file(self) -> Path:
        return self.era_dir / "era.json"

    def _load_json(self, file_path: Path, default: Any) -> Any:
        if not file_path.exists():
            return default
        return json.loads(file_path.read_text(encoding="utf-8"))

    def _save_json(self, file_path: Path, data: Any) -> None:
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_admin_config(self) -> dict[str, Any]:
        default = {"admins": [], "banned": [], "auto_tasks": {}}
        data = self._load_json(self._admin_file(), default)
        for key in default:
            data.setdefault(key, default[key])
        return data

    def _save_admin_config(self, data: dict[str, Any]) -> None:
        self._save_json(self._admin_file(), data)

    def _load_era(self) -> dict[str, Any]:
        default = {
            "name": ERAS[0]["name"],
            "index": 0,
            "description": ERAS[0]["description"],
        }
        data = self._load_json(self._era_file(), default)
        for key in default:
            data.setdefault(key, default[key])
        return data

    def _save_era(self, data: dict[str, Any]) -> None:
        self._save_json(self._era_file(), data)

    def _is_admin(self, user_id: str) -> bool:
        config = self._load_admin_config()
        return user_id in config.get("admins", [])

    def _check_admin(self, user_id: str) -> AdminResult | None:
        if not self._is_admin(user_id):
            return AdminResult(success=False, message="你没有管理员权限", not_admin=True)
        return None

    # ---------- 管理员管理 ----------

    async def add_admin(self, user_id: str) -> AdminResult:
        config = self._load_admin_config()
        admins = config.setdefault("admins", [])
        if user_id in admins:
            return AdminResult(success=False, message=f"{user_id} 已经是管理员")
        admins.append(user_id)
        self._save_admin_config(config)
        return AdminResult(success=True, message=f"已将 {user_id} 设为管理员")

    # ---------- 备份与恢复 ----------

    async def backup(self) -> AdminResult:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}.tar.gz"
        backup_path = self.backup_dir / backup_name
        try:
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(self.data_dir, arcname=self.data_dir.name)
            return AdminResult(
                success=True,
                message=f"备份成功：{backup_name}",
                backup_path=str(backup_path),
            )
        except Exception as e:
            return AdminResult(success=False, message=f"备份失败：{e}")

    async def restore(self, filename: str) -> AdminResult:
        backup_path = self.backup_dir / filename
        if not backup_path.exists():
            return AdminResult(success=False, message=f"备份文件不存在：{filename}")
        try:
            # 简单恢复：清空当前 data_dir（保留 backups 目录）后解压备份
            if self.data_dir.exists():
                for item in self.data_dir.iterdir():
                    if item.name == "backups":
                        continue
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(path=self.data_dir.parent)
            return AdminResult(success=True, message=f"已恢复备份：{filename}")
        except Exception as e:
            return AdminResult(success=False, message=f"恢复失败：{e}")

    # ---------- 管理员资源操作 ----------

    async def add_spirit_stones(self, admin_id: str, target_id: str, amount: int) -> AdminResult:
        check = self._check_admin(admin_id)
        if check:
            return check
        if amount <= 0:
            return AdminResult(success=False, message="数量必须大于 0")
        if not await self.player_service.exists(target_id):
            return AdminResult(success=False, message=f"玩家 {target_id} 不存在", player_not_found=True)
        await self.player_service.add_spirit_stones(target_id, amount)
        return AdminResult(success=True, message=f"已为 {target_id} 增加 {amount} 灵石")

    async def add_source_stones(self, admin_id: str, target_id: str, amount: int) -> AdminResult:
        check = self._check_admin(admin_id)
        if check:
            return check
        if amount <= 0:
            return AdminResult(success=False, message="数量必须大于 0")
        if not await self.player_service.exists(target_id):
            return AdminResult(success=False, message=f"玩家 {target_id} 不存在", player_not_found=True)
        await self.player_service.add_source_stones(target_id, amount)
        return AdminResult(success=True, message=f"已为 {target_id} 增加 {amount} 源石")

    # ---------- 封号管理 ----------

    async def ban(self, admin_id: str, target_id: str) -> AdminResult:
        check = self._check_admin(admin_id)
        if check:
            return check
        if not await self.player_service.exists(target_id):
            return AdminResult(success=False, message=f"玩家 {target_id} 不存在", player_not_found=True)
        config = self._load_admin_config()
        banned = config.setdefault("banned", [])
        if target_id in banned:
            return AdminResult(success=False, message=f"玩家 {target_id} 已被封号")
        banned.append(target_id)
        self._save_admin_config(config)
        player = await self.player_service.load(target_id)
        if player is not None:
            player["banned"] = True
            await self.player_service.save(target_id, player)
        return AdminResult(success=True, message=f"已封禁玩家 {target_id}")

    async def unban(self, admin_id: str, target_id: str) -> AdminResult:
        check = self._check_admin(admin_id)
        if check:
            return check
        config = self._load_admin_config()
        banned = config.setdefault("banned", [])
        if target_id not in banned:
            return AdminResult(success=False, message=f"玩家 {target_id} 未被封号")
        banned.remove(target_id)
        self._save_admin_config(config)
        player = await self.player_service.load(target_id)
        if player is not None:
            player["banned"] = False
            await self.player_service.save(target_id, player)
        return AdminResult(success=True, message=f"已解封玩家 {target_id}")

    async def is_banned(self, user_id: str) -> bool:
        config = self._load_admin_config()
        return user_id in config.get("banned", [])

    # ---------- 时代管理 ----------

    async def set_era(self, admin_id: str, era_name: str) -> AdminResult:
        check = self._check_admin(admin_id)
        if check:
            return check
        if era_name not in ERA_NAME_MAP:
            return AdminResult(
                success=False,
                message=f"未知时代：{era_name}，可选：{', '.join(ERA_NAME_MAP)}",
            )
        index = ERA_NAME_MAP[era_name]
        self._save_era(
            {
                "name": ERAS[index]["name"],
                "index": index,
                "description": ERAS[index]["description"],
            }
        )
        return AdminResult(success=True, message=f"已设置时代为 {era_name}")

    async def next_era(self, admin_id: str) -> AdminResult:
        check = self._check_admin(admin_id)
        if check:
            return check
        era = self._load_era()
        index = (era.get("index", 0) + 1) % len(ERAS)
        self._save_era(
            {
                "name": ERAS[index]["name"],
                "index": index,
                "description": ERAS[index]["description"],
            }
        )
        return AdminResult(success=True, message=f"已进入 {ERAS[index]['name']}")

    async def get_era_info(self) -> AdminResult:
        era = self._load_era()
        return AdminResult(
            success=True,
            message=f"当前时代：{era['name']}",
            data=era,
        )

    # ---------- 自动任务 ----------

    async def toggle_auto_task(self, user_id: str, enabled: bool) -> AdminResult:
        if not await self.player_service.exists(user_id):
            return AdminResult(success=False, message="玩家不存在", player_not_found=True)
        config = self._load_admin_config()
        auto_tasks = config.setdefault("auto_tasks", {})
        auto_tasks[user_id] = {
            "enabled": enabled,
            "last_run": auto_tasks.get(user_id, {}).get("last_run", ""),
        }
        self._save_admin_config(config)
        status = "开启" if enabled else "关闭"
        return AdminResult(success=True, message=f"自动任务已{status}")

    async def run_auto_daily_task(self, user_id: str, today: str | None = None) -> AdminResult:
        if not await self.player_service.exists(user_id):
            return AdminResult(success=False, message="玩家不存在", player_not_found=True)
        config = self._load_admin_config()
        auto_tasks = config.setdefault("auto_tasks", {})
        task_state = auto_tasks.setdefault(user_id, {"enabled": False, "last_run": ""})
        if not task_state.get("enabled", False):
            return AdminResult(success=False, message="自动任务未开启")

        if today is None:
            today = datetime.now().strftime("%Y-%m-%d")
        if task_state.get("last_run") == today:
            return AdminResult(success=False, message="今日自动任务已执行")

        await self.player_service.add_spirit_stones(user_id, 100)
        await self.player_service.add_source_stones(user_id, 50)
        await self.player_service.add_exp(user_id, 200)

        task_state["last_run"] = today
        self._save_admin_config(config)
        return AdminResult(
            success=True,
            message=f"自动任务完成，获得灵石*100、源石*50、修为*200",
            data={"last_run": today},
        )

    async def get_auto_task_status(self, user_id: str) -> AdminResult:
        config = self._load_admin_config()
        task_state = config.get("auto_tasks", {}).get(user_id, {"enabled": False, "last_run": ""})
        return AdminResult(
            success=True,
            message="自动任务状态",
            data=task_state,
        )
