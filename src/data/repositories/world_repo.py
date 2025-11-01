from src.data.repositories.base import BaseRepository
from src.core.types import WorldState
from src.core.config import get_settings


class WorldRepository(BaseRepository[WorldState]):
    def __init__(self):
        settings = get_settings()
        super().__init__(f"{settings.data_path}/world")

    async def get_state(self) -> WorldState:
        data = self._read_json("world_state.json")
        return WorldState(**data) if data else self._default_world_state()

    async def update_state(self, world_state: WorldState) -> None:
        self._write_json("world_state.json", world_state.model_dump())

    def _default_world_state(self) -> WorldState:
        return WorldState(
            current_location="tavern",
            time_of_day="evening",
            weather="clear",
            active_quests=[],
            world_events=[],
        )
