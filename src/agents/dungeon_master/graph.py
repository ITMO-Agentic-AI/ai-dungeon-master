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

    async def narrate_initial(self, state: GameState) -> Dict[str, Any]:
        """
        Phase 6: The Initial Narrator.
        After the world is created and players are established,
        narrate the opening scene to set the mood and establish the initial setting.
        
        IMPROVED: Pure narrative prose with naturally embedded action suggestions.
        No placeholder lists visible to player.
        """
        narrative = state.get("narrative")
        setting = state.get("setting")
        world = state.get("world")
        players = state.get("players", [])

        if not narrative or not world or not players:
            return {"messages": [AIMessage(content="The world awaits...")]}

        # Get opening location
        starting_location = None
        if world and hasattr(world, 'locations') and world.locations:
            starting_location = list(world.locations.values())[0]

        player_names = ", ".join([p.name for p in players])
        theme = setting.theme if setting else "Unknown"

        # Build location context
        location_description = ""
        if starting_location and hasattr(starting_location, 'name') and hasattr(starting_location, 'description'):
            location_description = f"{starting_location.name}: {starting_location.description}"
        
        # Get NPC context
        npcs_present = []
        if starting_location and hasattr(starting_location, 'npc_ids') and starting_location.npc_ids:
            if world and hasattr(world, 'active_npcs'):
                npcs_present = [world.active_npcs.get(npc_id) for npc_id in starting_location.npc_ids[:2] if npc_id in world.active_npcs]
        
        npc_context = ""
        if npcs_present:
            npc_names = ", ".join([npc.base_data.name for npc in npcs_present if npc and hasattr(npc, 'base_data')])
            npc_context = f"NPCs present: {npc_names}"

        system_prompt = f"""You are the Dungeon Master for a {theme} campaign.
        
Craft an IMMERSIVE OPENING that plunges the players directly into the story - IN MEDIA RES.

CRITICAL RULES:
1. Start with vivid sensory details of the scene RIGHT NOW. What do the characters see, hear, feel?
2. Weave character names ({player_names}) naturally into descriptions so they feel present and relevant.
3. Build atmosphere and tension through subtle foreshadowing and environmental detail.
4. End with 3 natural narrative prompts for player action (NOT a numbered list, NOT a UI menu):
   Embed suggestions as narrative flow:
   - "A low sound echoes from..." or "You notice..." or "Before you lies..." or "Suddenly..."
   - Let each prompt be a sentence that flows naturally from the scene
   - Examples: "A sudden sound freezes you", "You spot something glinting", "The path ahead splits"
5. Use BOLD for key atmospheric details and > blockquotes for mysterious sounds/whispers/dialogue.
6. ABSOLUTELY NO section headers, tone statements, meta-commentary, or action menus. Pure narrative immersion.
7. Target length: 250-350 words.
8. After ending the narrative, DO NOT add any explanatory text, list format, or player guidance.
"""

        context_block = f"""Campaign: {narrative.title}
Theme: {theme}
Hook: {narrative.tagline}
Core: {narrative.story_arc_summary[:150]}

Characters: {player_names}
Setting: {location_description}
{npc_context}
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_block)
        ]

        response = await self.model.ainvoke(messages)
        return {"messages": [response]}

    async def narrate_outcome(self, state: GameState) -> Dict[str, Any]:
        """
        Phase 7b: The Narrator.
        Synthesizes the mechanical outcome into vivid prose.
        
        IMPROVED: Generates narrative with naturally embedded next-action prompts,
        not UI-style action menus.
        """
        outcome = state.get("last_outcome")
        directives = state.get("director_directives")
        action = state.get("current_action")

        if not outcome:
            return {"messages": [AIMessage(content="The world waits for your action.")]}

        # Get actor's location with safe None checking
        player_map = {p.id: p for p in state.get("players", [])}
        actor_location = "Unknown"
        if action and action.player_id in player_map:
            actor_loc_id = player_map[action.player_id].location_id
            world = state.get("world")
            if world and hasattr(world, 'locations'):
                location_obj = world.locations.get(actor_loc_id)
                if location_obj and hasattr(location_obj, 'description'):
                    actor_location = location_obj.description

        # Embed director guidance subtly
        tone_hint = ""
        if directives:
            tone_hint = f"Tone/mood to weave in subtly: {directives.narrative_focus}"

        system_prompt = f"""You are the Dungeon Master.

Narrate the IMMEDIATE CONSEQUENCE of the player's action in visceral, immersive prose.

CRITICAL RULES:
1. Show what happens as a direct result of their choice - make it FELT through sensory detail.
2. {tone_hint} (Weave the mood into word choice and pacing, NOT as explicit statements)
3. End with 2-3 natural narrative prompts for what might come next:
   - Embed as narrative flow: "A sound...", "You notice...", "Ahead lies...", "Something..."
   - Each prompt should be a complete narrative sentence, not a UI list item
   - Examples: "You realize the danger isn't behind—it's ahead...", "A sudden shape emerges..."
   - NEVER use numbered lists like "1. Attack" or "2. Search"
4. Use BOLD for sudden changes/revelations and > blockquotes for reactions or mysterious sounds.
5. Status: {'SUCCESS - the action had its intended effect' if outcome.success else 'FAILURE - unexpected consequences unfold'}.
6. Keep the momentum going. The next prompt should feel inevitable, not optional.
7. ABSOLUTELY NO action menu format. Pure narrative continuation only.
8. Target length: 150-250 words.
"""

        context_block = f"""Action: {action.description if action else 'Unknown'}
Outcome: {outcome.narrative_result}
Location: {actor_location}
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_block)
        ]

        response = await self.model.ainvoke(messages)
        return {"messages": [response]}

    async def plan_response(self, state: GameState) -> Dict[str, Any]:
        """
        Phase 7a: The Dungeon Master Planner.
        Receives the player's input (action or question) and decides the next step.
        Sets a flag ('response_type') in the state to guide routing.
        """
        # Get the latest message from the player
        messages = state.get("messages", [])
        player_input = ""
        if messages:
            # Assuming the last message is from the player
            player_input = messages[-1].content

        # Determine if it's an action, a question, or an exit command
        is_action = any(word in player_input.lower() for word in ["attack", "move", "cast", "use", "take", "open", "go", "examine", "investigate", "approach"])
        is_question = "?" in player_input or any(word in player_input.lower() for word in ["what", "where", "who", "why", "how", "tell me"])
        is_exit = any(word in player_input.lower() for word in ["quit", "exit", "goodbye", "end"])

        # Set the response type in the state
        response_type = "unknown"
        if is_action:
            response_type = "action"
        elif is_question:
            response_type = "question"
        elif is_exit:
            response_type = "exit"

        # Return the state update with the response type
        return {
            "response_type": response_type,
            "current_player_input": player_input
        }

    async def process(self, state: GameState) -> Dict[str, Any]:
        return await self.narrate_outcome(state)
