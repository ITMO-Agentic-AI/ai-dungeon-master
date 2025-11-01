from typing import Any
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from langchain_core.messages import AIMessage
from src.core.types import GameState
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service


class DungeonMasterAgent(BaseAgent):
    def __init__(self):
        super().__init__("Dungeon Master")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("narrate", self.narrate)
        graph.add_edge("__start__", "narrate")
        return graph

    async def narrate(self, state: GameState, runtime: Runtime) -> dict[str, Any]:
        narrative = state.get("narrative")
        world = state.get("world")
        players = state.get("players", [])
        actions = state.get("actions", [])

        context = f"""
Scene: {narrative.current_scene if narrative else "Unknown"}
Location: {world.current_location if world else "Unknown"}
Players: {", ".join(p.name for p in players)}
Recent Actions: {actions[-3:] if actions else "None"}

Narrate the scene to the players.
"""

        response = await self.model.ainvoke(context)

        return {"messages": [AIMessage(content=response.content, name="DungeonMaster")]}

    async def process(self, state: GameState, runtime: Runtime = None) -> dict[str, Any]:
        return await self.narrate(state, runtime)


graph = DungeonMasterAgent().compile()
