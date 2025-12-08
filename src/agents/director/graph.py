from typing import Any, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph
from pydantic import BaseModel

from src.core.types import GameState, DirectorDirectives, NarrativeState
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service
from src.services.structured_output import get_structured_output


class DirectorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Director")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("direct_scene", self.direct_scene)
        graph.add_edge("__start__", "direct_scene")
        return graph

    async def direct_scene(self, state: GameState) -> Dict[str, Any]:
        """
        Phase 7a: The Director.
        Adjusts pacing and focus BEFORE the DM speaks.
        """
        narrative = state["narrative"]
        history = state.get("messages", [])
        # Calculate implied tension or just use the stored one
        current_tension = narrative.narrative_tension

        system_prompt = """You are the Narrative Director of an interactive story.
        Your goal is to manage pacing, tension, and plot progression.
        Do not generate story text; generate *directions* for the narrator."""

        user_prompt = f"""
        Current Arc: {narrative.story_arc_summary}
        Current Scene: {narrative.current_scene}
        Current Tension: {current_tension}
        Recent History Length: {len(history)} messages

        Analyze the state. Is the scene dragging? Is it too chaotic? 
        Provide directives to guide the next narration.
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        directives: DirectorDirectives = await get_structured_output(self.model, messages, DirectorDirectives)

        # Update the narrative state with new tension
        updated_narrative = narrative.model_copy(
            update={"narrative_tension": directives.tension_adjustment}
        )

        return {"director_directives": directives, "narrative": updated_narrative}

    async def process(self, state: GameState) -> Dict[str, Any]:
        return await self.direct_scene(state)
