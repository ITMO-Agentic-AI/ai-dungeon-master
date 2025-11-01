from typing import Any
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from src.core.types import GameState
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service


class PlayerProxyAgent(BaseAgent):
    def __init__(self):
        super().__init__("Player Proxy")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("simulate_action", self.simulate_action)
        graph.add_edge("__start__", "simulate_action")
        return graph

    async def simulate_action(self, state: GameState, runtime: Runtime) -> dict[str, Any]:
        return {}

    async def process(self, state: GameState, runtime: Runtime = None) -> dict[str, Any]:
        return await self.simulate_action(state, runtime)


graph = PlayerProxyAgent().compile()
