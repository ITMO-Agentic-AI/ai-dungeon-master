from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from langchain_core.messages import AIMessage

from src.core.types import GameState
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service

class DungeonMasterAgent(BaseAgent):
    def __init__(self):
        super().__init__("Dungeon Master")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        # This agent now has multiple functions, so we don't define a single graph here.
        # The main graph is defined in orchestrator_service.py.
        pass

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

        # Determine if it's an action or a question
        # This is a simple heuristic; you might want a more sophisticated classifier.
        is_action = any(word in player_input.lower() for word in ["attack", "move", "cast", "use", "take", "open", "go"])
        is_question = "?" in player_input or any(word in player_input.lower() for word in ["what", "where", "who", "why", "how", "tell me"])

        # Set the response type in the state
        response_type = "unknown"
        if is_action:
            response_type = "action"
        elif is_question:
            response_type = "question"

        # Return the state update with the response type
        return {
            "response_type": response_type,
            # You might also want to store the raw player input for later use
            "current_player_input": player_input
        }

    async def narrate_initial(self, state: GameState) -> Dict[str, Any]:
        """
        Phase 1: Initial Narration.
        Generates the opening scene description after world and players are created.
        """
        narrative = state.get("narrative")
        world = state.get("world")
        players = state.get("players", [])

        # Construct context
        context_block = f"""
        Campaign Title: {narrative.title}
        Story Hook: {narrative.tagline}
        Starting Location: {world.locations.get('start_location', 'Unknown') if world.locations else 'Not Set'}
        Players: {[p.name for p in players]}
        """

        system_prompt = """You are the Dungeon Master. 
        Describe the initial scene of the adventure vividly and immersively.
        
        Inputs to consider:
        1. Campaign Title and Hook.
        2. Current Location description.
        3. List of player characters.
        
        Format:
        - Use bold for key items or sudden events.
        - Use > blockquotes for NPC dialogue.
        - Keep it under 200 words.
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", f"Narrate the opening scene:\n{context_block}")
        ])

        response = await self.model.ainvoke(prompt)

        # Return this as a LangChain message to append to history
        return {
            "messages": [response]
        }

    async def narrate_outcome(self, state: GameState) -> Dict[str, Any]:
        """
        Phase 7b: The Narrator.
        Synthesizes the mechanical outcome + director instructions into prose.
        """
        # This function remains largely the same, but might need to handle different types of outcomes.
        outcome = state.get("last_outcome")
        directives = state.get("director_directives")
        # We might need to get the original player input for context
        player_input = state.get("current_player_input", "No input provided.")

        if not outcome:
            return {"messages": [AIMessage(content="The world waits for your action.")], "response_type": "unknown"}

        # --- Fix: Get actor's location ---
        player_map = {p.id: p for p in state['players']}
        actor_location = 'Unknown'
        # For simplicity, assume the first player is the actor for now
        if player_map:
            first_player_id = list(player_map.keys())[0]
            actor_loc_id = player_map[first_player_id].location_id
            actor_location = state['world'].locations.get(actor_loc_id, 'Unknown')
        # --- End Fix ---

        system_prompt = """You are the Dungeon Master.
        Describe the results of the player's action or answer their question vividly and immersively.

        Inputs to consider:
        1. Mechanical Outcome or Answer: What actually happened or what was found.
        2. Director's Note: Tone and focus (e.g., "Make it scary").
        3. World State: Use the location description and active NPCs.
        4. Original Player Input: To provide relevant context.

        Format:
        - Use bold for key items or sudden events.
        - Use > blockquotes for NPC dialogue.
        - Keep it under 200 words.
        """

        context_block = f"""
        Player Input: {player_input}
        Result: {outcome.narrative_result} (Success: {outcome.success})
        
        Director's Focus: {directives.narrative_focus if directives else 'Neutral'}
        Director's Note: {directives.next_beat if directives else 'Continue story'}
        
        Current Location: {actor_location}
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", f"Narrate this:\n{context_block}")
        ])

        response = await self.model.ainvoke(prompt)

        return {
            "messages": [response],
            # Clear the response type for the next turn
            "response_type": "unknown"
        }

    # Cleaned up process wrapper - Not needed for this agent since it has multiple functions
    # async def process(self, state: GameState) -> Dict[str, Any]:
    #     return await self.narrate_outcome(state)