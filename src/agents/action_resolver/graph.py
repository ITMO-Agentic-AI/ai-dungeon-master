from typing import Any
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from src.core.types import GameState
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service


class ActionResolverAgent(BaseAgent):
    def __init__(self):
        super().__init__("Action Resolver")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("resolve_action", self.resolve_action)
        graph.add_edge("__start__", "resolve_action")
        return graph

    async def resolve_action(self, state: GameState, runtime: Runtime) -> dict[str, Any]:
        return {}

    async def process(self, state: GameState, runtime: Runtime = None) -> dict[str, Any]:
        return await self.resolve_action(state, runtime)


graph = ActionResolverAgent().compile()
