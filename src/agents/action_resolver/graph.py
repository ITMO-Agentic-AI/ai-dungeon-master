from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph

from src.core.types import GameState, ActionOutcome
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service
from src.services.structured_output import get_structured_output


class ActionResolverAgent(BaseAgent):
    def __init__(self):
        super().__init__("Action Resolver")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("resolve_action", self.resolve_action)
        graph.add_edge("__start__", "resolve_action")
        return graph

    async def resolve_action(self, state: GameState) -> dict[str, Any]:
        """
        Step 5: Action Resolution.
        Evaluates a player's intent against the world state and mechanics.
        """
        action = state.get("current_action")
        world = state["world"]
        players = {p.id: p for p in state["players"]}

        if not action:
            return {
                "last_outcome": ActionOutcome(success=False, narrative_result="No action provided.")
            }

        actor = players.get(action.player_id)
        current_loc = world.locations.get(actor.location_id) if actor else None

        context_str = f"""
        Actor: {actor.name} ({actor.class_name}, HP: {actor.stats.current_hit_points}/{actor.stats.max_hit_points})
        Location: {current_loc.name if current_loc else 'Unknown'} - {current_loc.description if current_loc else ''}
        Visible NPCs: {', '.join(current_loc.npc_ids) if current_loc else 'None'}
        Action Type: {action.type}
        Action Description: "{action.description}"
        """

        system_prompt = """You are an expert RPG Game Master and Rules Engine.
        Resolve the player's action based on logical consequences and dramatic flair.

        Rules:
        1. 'move' actions generally succeed if the location is connected.
        2. 'attack' actions resolve based on a simple simulation (assume standard difficulty).
        3. 'investigate' reveals clues present in the location.

        Output the result using the structure provided.
        - For damage, use 'stat_changes' with 'hp'.
        - For movement, set 'new_location_id'.
        - Provide a 'narrative_result' describing the scene.
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Resolve this situation:\n{context_str}"),
        ]

        outcome: ActionOutcome = await get_structured_output(self.model, messages, ActionOutcome)

        # updated_players = []
        player_map = {p.id: p for p in state["players"]}

        for change in outcome.stat_changes:
            if change.target_id in player_map:
                p = player_map[change.target_id]
                if change.stat_name == "hp":
                    p.stats.current_hit_points = change.new_value  # Update stats object

        if outcome.new_location_id and outcome.new_location_id in world.locations:
            player_map[action.player_id].location_id = outcome.new_location_id

        final_player_list = list(player_map.values())

        return {
            "last_outcome": outcome,
            "players": final_player_list,
        }

    async def process(self, state: GameState) -> dict[str, Any]:
        return await self.resolve_action(state)
