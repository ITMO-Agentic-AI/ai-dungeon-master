from typing import Any
import json
import logging
from langgraph.graph import StateGraph
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage

from src.core.types import GameState
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service
from src.core.gameplay_phase import ActionOutcomeToken, ActionIntentType

logger = logging.getLogger(__name__)

# FIX #14: Action-specific narration hints for variety
ACTION_NARRATION_HINTS = {
    ActionIntentType.ATTACK: "Describe the combat maneuver, weapon impact, and enemy reaction.",
    ActionIntentType.CAST_SPELL: "Describe magical energy, spell effects, and arcane outcomes.",
    ActionIntentType.INVESTIGATE: "Describe what the character discovers, notices, or learns.",
    ActionIntentType.DIALOGUE: "Describe the conversation, NPC reactions, and social dynamics.",
    ActionIntentType.MOVE: "Describe the movement, terrain, and arrival at destination.",
    ActionIntentType.DEFEND: "Describe defensive positioning, protection, and reaction.",
    ActionIntentType.STEALTH: "Describe sneaking, hiding, and avoiding detection.",
    ActionIntentType.SKILL_CHECK: "Describe the attempt, technique used, and result.",
}


class DungeonMasterAgent(BaseAgent):
    def __init__(self):
        super().__init__("Dungeon Master")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("narrate_outcome", self.narrate_outcome)
        graph.add_edge("__start__", "narrate_outcome")
        return graph

    async def narrate_initial(self, state: GameState) -> dict[str, Any]:
        """
        Phase 6: The Initial Narrator.
        After the world is created and players are established,
        narrate the opening scene to set the mood and establish the initial setting.

        IMPROVED: Pure narrative prose with naturally embedded action suggestions.
        Returns both narrative and explicit action suggestions.
        """
        narrative = state.get("narrative")
        setting = state.get("setting")
        world = state.get("world")
        players = state.get("players", [])

        if not narrative or not world or not players:
            return {
                "messages": [AIMessage(content="The world awaits...")],
                "action_suggestions": [
                    "Look around",
                    "Wait and listen",
                    "Ask for more information",
                ],
            }

        # Get opening location
        starting_location = None
        if world and hasattr(world, "locations") and world.locations:
            starting_location = list(world.locations.values())[0]

        player_names = ", ".join([p.name for p in players])
        theme = setting.theme if setting else "Unknown"

        # Build location context
        location_description = ""
        if (
            starting_location
            and hasattr(starting_location, "name")
            and hasattr(starting_location, "description")
        ):
            location_description = f"{starting_location.name}: {starting_location.description}"

        # Get NPC context
        npcs_present = []
        if (
            starting_location
            and hasattr(starting_location, "npc_ids")
            and starting_location.npc_ids
        ):
            if world and hasattr(world, "active_npcs"):
                npcs_present = [
                    world.active_npcs.get(npc_id)
                    for npc_id in starting_location.npc_ids[:2]
                    if npc_id in world.active_npcs
                ]

        npc_context = ""
        if npcs_present:
            npc_names = ", ".join(
                [npc.base_data.name for npc in npcs_present if npc and hasattr(npc, "base_data")]
            )
            npc_context = f"NPCs present: {npc_names}"

        system_prompt = f"""You are the Dungeon Master for a {theme} campaign.

Craft an IMMERSIVE OPENING that plunges the players directly into the story - IN MEDIA RES.

CRITICAL RULES:
1. Start with vivid sensory details of the scene RIGHT NOW. What do the characters see, hear, feel?
2. Weave character names ({player_names}) naturally into descriptions so they feel present and relevant.
3. Build atmosphere and tension through subtle foreshadowing and environmental detail.
4. Use BOLD for key atmospheric details and > blockquotes for mysterious sounds/whispers/dialogue.
5. ABSOLUTELY NO section headers, tone statements, meta-commentary, or action menus. Pure narrative immersion.
6. Target length: 250-350 words.

AFTER the narrative (on a new line), you MUST output a JSON block with action suggestions:

```json
{{
  "action_suggestions": [
    "Suggestion 1 - A specific action the player could take",
    "Suggestion 2 - Another viable action",
    "Suggestion 3 - A third option"
  ]
}}
```

Make suggestions concrete and action-oriented (e.g., "Talk to the stranger", "Search the desk", "Move toward the sound").
"""

        context_block = f"""Campaign: {narrative.title}
Theme: {theme}
Hook: {narrative.tagline}
Core: {narrative.story_arc_summary[:150]}

Characters: {player_names}
Setting: {location_description}
{npc_context}
        """

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=context_block)]

        logger.info("🎭 DM narrating initial scene...")
        response = await self.model.ainvoke(messages)

        # Extract narrative and suggestions
        content = response.content
        narrative_text, suggestions = self._extract_narrative_and_suggestions(content)

        return {"messages": [AIMessage(content=narrative_text)], "action_suggestions": suggestions}

    async def narrate_outcome(self, state: GameState) -> dict[str, Any]:
        """
        Phase 7b: The Narrator.
        Synthesizes the mechanical outcome into vivid prose.

        BACKWARD COMPATIBLE: Still accepts old signature for compatibility.
        Use narrate_outcome_with_tokens() for mechanical outcomes.
        """
        # Check if we have outcome tokens (new behavior)
        outcome_tokens = state.get("outcome_tokens")
        if outcome_tokens:
            return await self.narrate_outcome_with_tokens(state, outcome_tokens)
        
        # Fallback to old behavior for compatibility
        outcome = state.get("last_outcome")
        directives = state.get("director_directives")
        action = state.get("current_action")

        if not outcome:
            return {
                "messages": [AIMessage(content="The world waits for your action.")],
                "action_suggestions": ["Look around", "Listen carefully", "Wait"],
            }

        # Get actor's location with safe None checking
        player_map = {p.id: p for p in state.get("players", [])}
        actor_location = "Unknown"
        if action and action.player_id in player_map:
            actor_loc_id = player_map[action.player_id].location_id
            world = state.get("world")
            if world and hasattr(world, "locations"):
                location_obj = world.locations.get(actor_loc_id)
                if location_obj and hasattr(location_obj, "description"):
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
3. Use BOLD for sudden changes/revelations and > blockquotes for reactions or mysterious sounds.
4. Status: {'SUCCESS - the action had its intended effect' if outcome.success else 'FAILURE - unexpected consequences unfold'}.
5. Keep the momentum going. The next prompt should feel inevitable, not optional.
6. ABSOLUTELY NO action menu format. Pure narrative continuation only.
7. Target length: 150-250 words.

AFTER the narrative (on a new line), you MUST output a JSON block with action suggestions:

```json
{{
  "action_suggestions": [
    "Suggestion 1 - A specific action the player could take next",
    "Suggestion 2 - Another viable action",
    "Suggestion 3 - A third option"
  ]
}}
```

Make suggestions concrete and action-oriented (e.g., "Pursue the fleeing figure", "Examine the symbol", "Ask for help").
Suggestions should flow naturally from the narrative and provide clear next steps.
"""

        context_block = f"""Action: {action.description if action else 'Unknown'}
Outcome: {outcome.narrative_result}
Location: {actor_location}
        """

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=context_block)]

        logger.debug("🎭 DM narrating action outcome...")
        response = await self.model.ainvoke(messages)

        # Extract narrative and suggestions
        content = response.content
        narrative_text, suggestions = self._extract_narrative_and_suggestions(content)

        return {"messages": [AIMessage(content=narrative_text)], "action_suggestions": suggestions}

    async def narrate_outcome_with_tokens(
        self,
        state: GameState,
        outcome_tokens: list[ActionOutcomeToken]
    ) -> dict[str, Any]:
        """
        FIX #2 & #3 & #14: Narrate outcome using mechanical tokens with action-specific context.
        
        This is the PRIMARY narration method - receives dice rolls and outcomes
        and narrates based on mechanical results AND action type for variety.
        
        Args:
            state: Current GameState
            outcome_tokens: List of ActionOutcomeToken with dice rolls and results
            
        Returns:
            Dict with narrative message and action suggestions
        """
        action = state.get("current_action")
        directives = state.get("director_directives", {})
        world_changes = state.get("last_world_changes", [])

        if not outcome_tokens or not action:
            return {
                "messages": [AIMessage(content="The world waits for your action.")],
                "action_suggestions": ["Look around", "Listen carefully", "Wait"],
            }

        # Build outcome-aware context from outcome tokens
        token = outcome_tokens[0]  # Use first outcome (single player for now)
        
        # Build mechanical context
        roll_total = token.primary_roll.total if token.primary_roll else 0
        dc = token.difficulty_class
        is_success = token.meets_dc
        damage = getattr(token, "damage_dealt", 0)
        effectiveness = token.effectiveness

        # FIX #14: Get action-specific narration hint for variety
        action_hint = ACTION_NARRATION_HINTS.get(
            token.intent_type,
            "Describe what happens as a result of this specific action."
        )
        
        # Get action type as string
        action_type_str = token.intent_type.value if hasattr(token.intent_type, 'value') else str(token.intent_type)

        # Get location
        player_map = {p.id: p for p in state.get("players", [])}
        actor_location = "Unknown"
        if action.player_id in player_map:
            actor_loc_id = player_map[action.player_id].location_id
            world = state.get("world")
            if world and hasattr(world, "locations"):
                location_obj = world.locations.get(actor_loc_id)
                if location_obj and hasattr(location_obj, "description"):
                    actor_location = location_obj.description

        tone_hint = ""
        if directives:
            tone_hint = f"Tone/mood to weave in subtly: {directives.get('narrative_focus', 'ongoing')}"

        # FIX #14: Enhanced prompt with action-specific emphasis
        system_prompt = f"""You are the Dungeon Master.

Narrate the IMMEDIATE CONSEQUENCE of the player's SPECIFIC action in visceral, immersive prose.

** PLAYER ACTION:**
- Action Type: {action_type_str}
- What They Did: "{action.description}"
- Narration Focus: {action_hint}

** MECHANICAL OUTCOME:**
- Roll: {roll_total} vs DC {dc}
- Result: {'SUCCESS - The action achieves its intended effect' if is_success else 'FAILURE - The action does not succeed as intended'}
- Effectiveness: {effectiveness:.0%}
- Damage Dealt: {damage} HP (if applicable)

CRITICAL RULES:
1. Narrate SPECIFICALLY what happens when the player "{action.description}".
2. {'Show how their action SUCCEEDS and what it achieves' if is_success else 'Show how their action FAILS and what goes wrong'}.
3. Make it FELT through sensory detail - match the action type.
4. {tone_hint}
5. Use BOLD for sudden changes/revelations and > blockquotes for reactions or mysterious sounds.
6. Keep the momentum going. The next action should feel inevitable.
7. ABSOLUTELY NO action menu format. Pure narrative continuation only.
8. Target length: 150-250 words.

AFTER the narrative (on a new line), you MUST output a JSON block with action suggestions:

```json
{{
  "action_suggestions": [
    "Suggestion 1 - A specific action the player could take next",
    "Suggestion 2 - Another viable action",
    "Suggestion 3 - A third option"
  ]
}}
```

Make suggestions concrete, action-oriented, and contextual to what just happened.
The narration MUST vary based on the action type (combat vs magic vs investigation vs dialogue).
"""

        # FIX #14: Enhanced context block with action emphasis
        context_block = f"""PLAYER ACTION:
  Type: {action_type_str}
  Description: "{action.description}"
  
MECHANICAL RESULT:
  Dice Roll: {token.mechanical_summary}
  Outcome: {'SUCCESS - Action achieves its goal' if token.meets_dc else 'FAILURE - Action does not succeed'}
  Effectiveness: {effectiveness:.0%}
  Damage: {damage} HP
  
SETTING:
  Location: {actor_location}
  World Changes: {len(world_changes)} state change(s) applied
  
NARRATE: Describe specifically and vividly what happens when the player {action.description}.
The narration MUST be different based on whether they attacked, cast a spell, investigated, talked, etc.
        """

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=context_block)]

        logger.info(
            f"🎬 DM narrating {action_type_str}: roll {roll_total} vs DC {dc} ({'SUCCESS' if is_success else 'FAILURE'})"
        )
        response = await self.model.ainvoke(messages)

        # Extract narrative and suggestions
        content = response.content
        narrative_text, suggestions = self._extract_narrative_and_suggestions(content)

        return {"messages": [AIMessage(content=narrative_text)], "action_suggestions": suggestions}

    def _extract_narrative_and_suggestions(self, content: str) -> tuple[str, list[str]]:
        """
        Extract narrative text and action suggestions from LLM response.

        Expected format:
        [Narrative text...]

        ```json
        {
          "action_suggestions": ["Suggestion 1", "Suggestion 2", "Suggestion 3"]
        }
        ```

        Args:
            content: Full response from LLM

        Returns:
            Tuple of (narrative_text, suggestions_list)
        """
        default_suggestions = ["Look around", "Wait", "Ask for clarification"]

        try:
            # Find JSON block
            if "```json" in content:
                start = content.find("```json") + len("```json")
                end = content.find("```", start)
                if end > start:
                    json_str = content[start:end].strip()
                    json_data = json.loads(json_str)
                    suggestions = json_data.get("action_suggestions", default_suggestions)

                    # Extract narrative (everything before JSON block)
                    narrative = content[: content.find("```json")].strip()

                    return narrative, suggestions
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse suggestions JSON: {e}")

        # Fallback: return full content as narrative with defaults
        return content, default_suggestions

    async def plan_response(self, state: GameState) -> dict[str, Any]:
        """
        Phase 7a: The Dungeon Master Planner.
        Receives the player's input (action or question) and decides the next step.
        Sets a flag ('response_type') in the state to guide routing.
        """
        # Check if response_type is already set (e.g., from Chainlit interface)
        existing_response_type = state.get("response_type")
        if existing_response_type and existing_response_type != "unknown":
            # Response type already determined by caller, use it
            return {"response_type": existing_response_type}
        
        # Get the latest message from the player
        messages = state.get("messages", [])
        player_input = ""
        if messages:
            # Assuming the last message is from the player
            player_input = messages[-1].content

        # Determine if it's an action, a question, or an exit command
        is_action = any(
            word in player_input.lower()
            for word in [
                "attack",
                "move",
                "cast",
                "use",
                "take",
                "open",
                "go",
                "examine",
                "investigate",
                "approach",
            ]
        )
        is_question = "?" in player_input or any(
            word in player_input.lower()
            for word in ["what", "where", "who", "why", "how", "tell me"]
        )
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
        return {"response_type": response_type, "current_player_input": player_input}

    async def process(self, state: GameState) -> dict[str, Any]:
        return await self.narrate_outcome(state)
