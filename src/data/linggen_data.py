import json
from pathlib import Path
from typing import Any


class LinggenData:
    """灵根觉醒数据加载器。"""

    def __init__(self, data_dir: Path):
        self.linggen_dir = data_dir / "linggen"
        self._paths: dict[str, dict[str, Any]] | None = None

    def _load(self) -> dict[str, dict[str, Any]]:
        file_path = self.linggen_dir / "awakening_paths.json"
        if not file_path.exists():
            return {}
        return json.loads(file_path.read_text(encoding="utf-8"))

    @property
    def paths(self) -> dict[str, dict[str, Any]]:
        if self._paths is None:
            self._paths = self._load()
        return self._paths

    def get_path(self, key: str) -> dict[str, Any] | None:
        return self.paths.get(key)
