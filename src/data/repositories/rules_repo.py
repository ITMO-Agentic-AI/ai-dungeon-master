from src.data.repositories.base import BaseRepository
from src.core.config import get_settings


class RulesRepository(BaseRepository):
    def __init__(self):
        settings = get_settings()
        super().__init__(f"{settings.data_path}/rules")

    async def get_rules(self) -> dict:
        return self._read_json("rules.json")

    async def save_rules(self, rules: dict) -> None:
        self._write_json("rules.json", rules)

    async def search_rule(self, query: str) -> list[dict]:
        return []
