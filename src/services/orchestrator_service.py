from src.core.types import GameState


class OrchestratorService:
    def __init__(self):
        self.agents = {}

    def register_agent(self, agent_type: str, agent):
        self.agents[agent_type] = agent

    async def execute_turn(self, state: GameState) -> GameState:
        if "director" in self.agents:
            state = await self.agents["director"].process(state)

        if "story_architect" in self.agents:
            state = await self.agents["story_architect"].process(state)

        if "world_engine" in self.agents:
            state = await self.agents["world_engine"].process(state)

        if "action_resolver" in self.agents:
            state = await self.agents["action_resolver"].process(state)

        if "rule_judge" in self.agents:
            state = await self.agents["rule_judge"].process(state)

        if "dungeon_master" in self.agents:
            state = await self.agents["dungeon_master"].process(state)

        return state


orchestrator_service = OrchestratorService()
