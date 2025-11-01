from typing import Any
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from src.core.types import GameState
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service


class StoryArchitectAgent(BaseAgent):
    def __init__(self):
        super().__init__("Story Architect")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("plan_narrative", self.plan_narrative)
        graph.add_edge("__start__", "plan_narrative")
        return graph

    async def plan_narrative(self, state: GameState, runtime: Runtime) -> dict[str, Any]:
        narrative = state.get("narrative")
        players = state.get("players", [])

        prompt = f"""
Current Story Arc: {narrative.story_arc if narrative else "Unknown"}
Current Scene: {narrative.current_scene if narrative else "Unknown"}
Players: {len(players)}

Create the next narrative beat for the story.
"""

        response = await self.model.ainvoke(prompt)

        if narrative:
            narrative.story_beats.append(response.content)

        return {"narrative": narrative}

    async def process(self, state: GameState, runtime: Runtime = None) -> dict[str, Any]:
        return await self.plan_narrative(state, runtime)


graph = StoryArchitectAgent().compile()
