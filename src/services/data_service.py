from src.core.types import Player, WorldState
from src.data.repositories.player_repo import PlayerRepository
from src.data.repositories.world_repo import WorldRepository


class DataService:
    def __init__(self):
        self.player_repo = PlayerRepository()
        self.world_repo = WorldRepository()

    async def get_player(self, player_id: str) -> Player | None:
        return await self.player_repo.get(player_id)

    async def save_player(self, player: Player) -> None:
        await self.player_repo.save(player)

    async def list_players(self) -> list[Player]:
        return await self.player_repo.list_all()

    async def get_world_state(self) -> WorldState:
        return await self.world_repo.get_state()

    async def update_world_state(self, world_state: WorldState) -> None:
        await self.world_repo.update_state(world_state)


data_service = DataService()
