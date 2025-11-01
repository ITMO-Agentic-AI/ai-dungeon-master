from typing import Any
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from src.core.types import GameState
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service


class RuleJudgeAgent(BaseAgent):
    def __init__(self):
        super().__init__("Rule Judge")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("validate_rules", self.validate_rules)
        graph.add_edge("__start__", "validate_rules")
        return graph

    async def validate_rules(self, state: GameState, runtime: Runtime) -> dict[str, Any]:
        return {}

    async def process(self, state: GameState, runtime: Runtime = None) -> dict[str, Any]:
        return await self.validate_rules(state, runtime)


graph = RuleJudgeAgent().compile()
