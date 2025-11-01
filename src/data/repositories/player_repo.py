from src.data.repositories.base import BaseRepository
from src.core.types import Player
from src.core.config import get_settings


class PlayerRepository(BaseRepository[Player]):
    def __init__(self):
        settings = get_settings()
        super().__init__(f"{settings.data_path}/players")

    async def get(self, player_id: str) -> Player | None:
        data = self._read_json(f"{player_id}.json")
        return Player(**data) if data else None

    async def save(self, player: Player) -> None:
        self._write_json(f"{player.id}.json", player.model_dump())

    async def list_all(self) -> list[Player]:
        players = []
        for file in self.data_dir.glob("*.json"):
            data = self._read_json(file.name)
            players.append(Player(**data))
        return players

    async def delete(self, player_id: str) -> bool:
        filepath = self.data_dir / f"{player_id}.json"
        if filepath.exists():
            filepath.unlink()
            return True
        return False
