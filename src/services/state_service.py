import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class StateService:
    """
    玩家状态/CD 服务，用于替代原插件中的 Redis 临时状态。
    当前使用文件存储；生产环境可切换为 Redis 后端。
    """

    def __init__(self, data_dir: Path):
        self.state_dir = data_dir / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, key: str) -> Path:
        # 将 key 中的特殊字符替换，保证可作为文件名
        safe_key = key.replace(":", "_").replace("/", "_")
        return self.state_dir / f"{safe_key}.json"

    async def get(self, key: str, default: Any = None) -> Any:
        file_path = self._file_path(key)
        if not file_path.exists():
            return default
        return json.loads(file_path.read_text(encoding="utf-8"))

    async def set(self, key: str, value: Any) -> None:
        file_path = self._file_path(key)
        file_path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    async def delete(self, key: str) -> None:
        file_path = self._file_path(key)
        if file_path.exists():
            file_path.unlink()

    @staticmethod
    def today_str() -> str:
        """返回当前日期字符串，用于每日签到等按天重置的逻辑。"""
        return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
