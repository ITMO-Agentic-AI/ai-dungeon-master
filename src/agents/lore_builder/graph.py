from typing import Any
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from src.core.types import GameState
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service


class LoreBuilderAgent(BaseAgent):
    def __init__(self):
        super().__init__("Lore Builder")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("build_lore", self.build_lore)
        graph.add_edge("__start__", "build_lore")
        return graph

    async def build_lore(self, state: GameState, runtime: Runtime) -> dict[str, Any]:
        return {}

    async def process(self, state: GameState, runtime: Runtime = None) -> dict[str, Any]:
        return await self.build_lore(state, runtime)


graph = LoreBuilderAgent().compile()
