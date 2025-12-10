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
        """
        narrative = state.get("narrative")
        world = state.get("world")
        players = state.get("players", [])

        if not narrative or not world or not players:
            return {"messages": [AIMessage(content="The world awaits...")]}

        # Get opening location (usually the first location or a specific starting location)
        starting_location = None
        if world.locations:
            # Assume the first location is the starting point
            starting_location = list(world.locations.values())[0] if world.locations else None

        player_names = ", ".join([p.name for p in players])

        system_prompt = """You are the Dungeon Master.
        Craft an immersive opening narration that:
        1. Sets the tone and atmosphere of the campaign
        2. Introduces the setting and starting location
        3. Welcomes the players and their characters
        4. Creates intrigue and adventure hooks

        Format:
        - Use vivid, evocative language
        - Use bold for important details or atmosphere
        - Use > blockquotes for NPC greetings or ambient sounds
        - Keep it under 300 words to maintain pacing
        """

        location_description = ""
        if starting_location:
            location_description = f"\n\nStarting Location: {starting_location.name}\nDescription: {starting_location.description}"

        context_block = f"""Campaign Title: {narrative.title}
Theme: {narrative.theme}
Tone: {narrative.tone}

Player Characters: {player_names}

Opening Hook: {narrative.tagline}{location_description}
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Begin this campaign with an engaging opening narration:\n{context_block}")
        ]

        response = await self.model.ainvoke(messages)

        return {"messages": [response]}

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

    async def plan_response(self, state: GameState) -> Dict[str, Any]:
        """
        Phase 7a: The Dungeon Master Planner.
        Receives the player's input (action or question) and decides the next step.
        Sets a flag ('response_type') in the state to guide routing.
        """
        # Get the latest message from the player (assuming it's the last one)
        messages = state.get("messages", [])
        player_input = ""
        if messages:
            # Assuming the last message is from the player
            player_input = messages[-1].content

        # Determine if it's an action, a question, or an exit command
        is_action = any(word in player_input.lower() for word in ["attack", "move", "cast", "use", "take", "open", "go"])
        is_question = "?" in player_input or any(word in player_input.lower() for word in ["what", "where", "who", "why", "how", "tell me"])
        is_exit = any(word in player_input.lower() for word in ["quit", "exit", "goodbye"])

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
