from datetime import datetime
from src.data.repositories.base import BaseRepository
from src.core.config import get_settings


class LogsRepository(BaseRepository):
    def __init__(self):
        settings = get_settings()
        super().__init__(settings.logs_path)

    async def log_action(self, action: dict) -> None:
        timestamp = datetime.now().isoformat()
        log_file = f"actions_{datetime.now().strftime('%Y%m%d')}.json"

        logs = self._read_json(log_file)
        if "actions" not in logs:
            logs["actions"] = []

        logs["actions"].append({"timestamp": timestamp, **action})

        self._write_json(log_file, logs)

    async def log_narrative(self, narrative: dict) -> None:
        timestamp = datetime.now().isoformat()
        log_file = f"narrative_{datetime.now().strftime('%Y%m%d')}.json"

        logs = self._read_json(log_file)
        if "events" not in logs:
            logs["events"] = []

        logs["events"].append({"timestamp": timestamp, **narrative})

        self._write_json(log_file, logs)
