# src/agents/dungeon_master/graph.py

from typing import Any, Dict
from langgraph.graph import StateGraph
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage

from src.core.types import GameState
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service


class DungeonMasterAgent(BaseAgent):
    def __init__(self):
        super().__init__("Dungeon Master")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("narrate_outcome", self.narrate_outcome)
        graph.add_edge("__start__", "narrate_outcome")
        return graph

    async def narrate_outcome(self, state: GameState) -> Dict[str, Any]:
        """
        Phase 7b: The Narrator.
        Synthesizes the mechanical outcome + director instructions into prose.
        """
        outcome = state.get("last_outcome")
        directives = state.get("director_directives")
        action = state.get("current_action")

        if not outcome:
            return {"messages": [AIMessage(content="The world waits for your action.")]}

        # --- Fix: Get actor's location ---
        player_map = {p.id: p for p in state["players"]}
        actor_location = "Unknown"
        if action and action.player_id in player_map:
            actor_loc_id = player_map[action.player_id].location_id
            actor_location = state["world"].locations.get(actor_loc_id, "Unknown")
        # --- End Fix ---

        system_prompt = """You are the Dungeon Master.
        Describe the results of the player's action vividly and immersively.

        Inputs to consider:
        1. Mechanical Outcome: What actually happened (Success/Failure).
        2. Director's Note: Tone and focus (e.g., "Make it scary").
        3. World State: Use the location description and active NPCs.

        Format:
        - Use bold for key items or sudden events.
        - Use > blockquotes for NPC dialogue.
        - Keep it under 200 words.
        """

        context_block = f"""
        Player Action: {action.description}
        Result: {outcome.narrative_result} (Success: {outcome.success})

        Director's Focus: {directives.narrative_focus if directives else 'Neutral'}
        Director's Note: {directives.next_beat if directives else 'Continue story'}

        Current Location: {actor_location} # Use the fixed location
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Narrate this:\n{context_block}")
        ]

        response = await self.model.ainvoke(messages)

        return {"messages": [response]}

    async def process(self, state: GameState) -> Dict[str, Any]:
        return await self.narrate_outcome(state)
