# src/agents/player_proxy/graph.py

import uuid
import operator
from typing import Any, Dict, List, Literal, Annotated, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.types import Send
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from src.core.types import GameState, Player, DnDCharacterStats
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service
from src.services.structured_output import get_structured_output # Assuming this utility exists


# Character input structure
class PlayerGenInput(BaseModel):
    name: str = Field(default="Unknown", description="Character name")
    class_name: str = Field(default="Adventurer", description="Class name e.g. Warrior")
    race: str = Field(default="Human")
    background: str = Field(default="Unknown")
    motivation: str = Field(default="To explore")
    backstory: str = Field(default="A mysterious traveler.")
    location_id: str = Field(default="unknown")

    # stats
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    max_hit_points: int = 10
    current_hit_points: int = 10
    armor_class: int = 10

    # **No id field here, set as optional, because LLM-generated IDs are too hard to control,
    # so generate ID directly in code**
    id: Optional[str] = Field(default=None)


class PlayerProxyAgent(BaseAgent):
    """
    Phase 1:
    - Parallel Character Creation
    - Use Send API to generate multiple D&D 5e character sheets simultaneously
    Phase 3:
    - Gameplay Loop
    - Simulate player actions based on environment and memory
    """

    def __init__(self):
        super().__init__("Player Proxy")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("create_single_character", self.create_single_character)
        graph.add_node("simulate_action", self.simulate_action)

        # NEW: Add the specific update method for gameplay
        graph.add_node("update_players", self.update_players)

        graph.add_conditional_edges("__start__", self.route_step)

        graph.add_edge("create_single_character", END)
        graph.add_edge("simulate_action", END)
        graph.add_edge("update_players", END) # NEW: Edge for player update

        return graph

    # Routing logic (Map Step Router)
    def route_step(self, state: GameState):
        """
        Check current state:
        - If no players -> Start parallel creation (return Send list)
        - If players exist -> Enter gameplay loop (return "simulate_action")
        """
        players = state.get("players", [])

        # If the players list is empty, need to initialize character generation
        if not players:
            # Get setting (read from State)
            setting = state.get("setting")
            narrative = state.get("narrative")
            world = state.get("world")

            # Get concepts logic
            concepts = ["Warrior", "Mage", "Rogue"]  # Default value
            if isinstance(setting, dict):
                concepts = setting.get("player_concepts", concepts)
            elif hasattr(setting, "player_concepts"):
                concepts = setting.player_concepts

            story_hook = "A generic adventure"
            if isinstance(narrative, dict):
                story_hook = narrative.get("tagline", story_hook)
            elif hasattr(narrative, "tagline"):
                story_hook = narrative.tagline

            locations = {}
            if isinstance(world, dict):
                locations = world.get("locations", {})
            elif hasattr(world, "locations"):
                locations = world.locations

            return [
                Send(
                    "create_single_character",
                    {"concept": concept, "story_hook": story_hook, "locations": locations},
                )
                for concept in concepts
            ]

        # NEW LOGIC: Check if it's an update request (e.g., triggered by orchestrator after Judge)
        outcome = state.get("last_outcome")
        if outcome:
            # If there's an outcome from an action affecting players, route to update
            return "update_players"

        return "simulate_action"

    async def create_single_character(self, state: dict) -> Dict[str, Any]:
        """Worker node for parallel character creation.
        Receives a payload dict from Send, not the full GameState.
        """
        concept = state.get("concept")
        hook = state.get("story_hook")
        locations = state.get("locations")

        # Determine initial location ID
        start_loc_id = "unknown_location"
        if locations:
            # Take the ID of the first available location
            start_loc_id = list(locations.keys())[0]

        # Construct Prompt
        system_prompt = """You are an expert D&D 5e Character Creator.
        Your goal is to generate a valid JSON object for a player character."""

        user_prompt = f"""
        # Context
        Campaign Hook: {hook}
        Target Archetype: {concept}

        # Task
        Create a character profile inside a "character" object.

        # REQUIREMENTS (Use EXACT lowercase keys):
        1. "name": Character name.
        2. "class_name": Use "{concept}".
        3. "race": Character race.
        4. "background": Character background.
        5. "motivation": One short sentence.
        6. "backstory": Two sentences connecting to hook.
        7. "location_id": Set exactly to "{start_loc_id}".

        # STATS (Integers only):
        - "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"
        - "max_hit_points", "current_hit_points", "armor_class"

        IMPORTANT: Do NOT nest stats. Keep JSON flat.
        """

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        gen_data = await get_structured_output(self.model, messages, PlayerGenInput)

        # Generate ID using Python code here, it's more effective than LLM
        final_id = gen_data.id if gen_data.id else f"player_{uuid.uuid4().hex[:8]}"

        # Construct Player object (src.core.types.Player)
        # Manually assemble Stats nested object
        stats_obj = DnDCharacterStats(
            strength=gen_data.strength,
            dexterity=gen_data.dexterity,
            constitution=gen_data.constitution,
            intelligence=gen_data.intelligence,
            wisdom=gen_data.wisdom,
            charisma=gen_data.charisma,
            max_hit_points=gen_data.max_hit_points,
            current_hit_points=gen_data.current_hit_points,
            armor_class=gen_data.armor_class,
        )

        final_player = Player(
            id=final_id,
            name=gen_data.name,
            class_name=gen_data.class_name,  # Use processed class name
            race=gen_data.race,
            background=gen_data.background,
            motivation=gen_data.motivation,
            backstory=gen_data.backstory,
            location_id=start_loc_id,
            stats=stats_obj,  # Pass in the assembled object
        )

        # *Return result, because types.py defines players as Annotated[List, add]
        # So this returned list will be automatically appended to the total list, not overwritten
        return {"players": [final_player]}

    # NEW: Specific method for updating player sheets based on action outcomes during gameplay
    async def update_players(self, state: GameState) -> Dict[str, Any]:
        """
        Phase 2d: Update Player Sheets based on action outcome during gameplay.
        Modifies player character sheets (HP, inventory, conditions, etc.) based on the result of an action.
        """
        print("--- [Player Proxy] Updating Player Sheets (Gameplay) ---")

        # Get the outcome of the action
        outcome = state.get("last_outcome")
        # Get the current list of players
        players = state.get("players", [])

        # Example logic: If the action involved taking damage, update the player's HP
        # This is a placeholder; you would implement specific logic based on the outcome
        # For example, update inventory, apply conditions, etc.
        if outcome and hasattr(outcome, 'stat_changes'):
            for change in outcome.stat_changes:
                for player in players:
                    if player.id == change.target_id:
                        if change.stat_name == "hp":
                            # Assuming player has stats object
                            player.stats.current_hit_points = change.new_value
                            # Also update the player's current_hp if it's a separate field
                            player.current_hp = player.stats.current_hit_points
                            print(f"  Updated {player.name}'s HP to {player.stats.current_hit_points}")

        # Return the potentially updated players list
        # For now, just return the existing list unless modified by the logic above
        return {"players": players}


    # Phase 3: Gameplay Loop
    async def simulate_action(self, state: GameState, runtime: Runtime = None) -> dict[str, Any]:
        # Read world state (compatible with Pydantic object access)
        world = state.get("world")
        if world:
            time_val = getattr(world, "global_time", 0)
            if isinstance(world, dict):
                time_val = world.get("global_time", 0)
            context_desc = f"Turn {time_val}. "
        else:
            context_desc = "Unknown environment."

        # Read character sheet
        players = state.get("players", [])
        if not players:
            return {"messages": []}

        # Temporarily simulate only the first player, or the active player
        active_player = players[0]

        # Compatible attribute reading for Dict and Pydantic objects
        if isinstance(active_player, dict):
            p_name = active_player.get("name", "Unknown")
            p_class = active_player.get("class_name", "Unknown")
            p_race = active_player.get("race", "Unknown")
            p_bg = active_player.get("background", "Unknown")
            p_backstory = active_player.get("backstory", "")
        else:
            p_name = getattr(active_player, "name", "Unknown")
            p_class = getattr(active_player, "class_name", "Unknown")
            p_race = getattr(active_player, "race", "Unknown")
            p_bg = getattr(active_player, "background", "Unknown")
            p_backstory = getattr(active_player, "backstory", "")

        # Read memory (Messages)
        messages = state.get("messages", [])
        recent_msgs = messages[-5:]
        history_text = ""
        for msg in recent_msgs:
            # Compatible with different types of Message objects
            m_type = getattr(msg, "type", "unknown")
            if isinstance(msg, dict):
                m_type = msg.get("type", "unknown")

            m_content = getattr(msg, "content", str(msg))
            if isinstance(msg, dict):
                m_content = msg.get("content", "")

            history_text += f"[{m_type}]: {m_content}\n"

        if not history_text:
            history_text = "[System]: The adventure begins."

        # Construct Prompt
        prompt = (
            f"Roleplay Instructions:\n"
            f"You are {p_name}, a Level 1 {p_class}.\n"
            f"Race: {p_race}. Background: {p_bg}.\n"
            f"Personality/Backstory: {p_backstory}\n\n"
            f"Current Situation: {context_desc}\n"
            f"Recent History:\n{history_text}\n\n"
            f"Task: Based on your character, describe what you do next in ONE vivid sentence.\n"
            f"Focus on action and intent. Do not dictate the outcome."
        )

        # Call model (text output)
        try:
            response = await self.model.ainvoke(prompt)
            action_text = (
                response.content if hasattr(response, "content") else str(response)
            ).strip()
        except Exception as e:
            action_text = f"{p_name} hesitates, unsure what to do. (Error: {e})"

        # Return result
        new_message = {"type": "human", "name": p_name, "content": action_text}

        return {"messages": [new_message]}

    async def process(self, state: GameState, runtime: Runtime = None) -> dict[str, Any]:
        """Process method required by BaseAgent."""
        if not self.graph:
            self.compile()
        return await self.graph.ainvoke(state)

# Optional: Compile the graph if needed elsewhere
# graph = PlayerProxyAgent().build_graph().compile()