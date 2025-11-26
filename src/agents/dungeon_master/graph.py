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
        # DM returns pure text (Markdown), so no structured output needed here,
        # unless you want to separate 'speech' from 'narration'.

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
        
        # Fallback if previous steps failed
        if not outcome:
            return {"messages": [AIMessage(content="The world waits for your action.")]}

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

        # Construct context
        context_block = f"""
        Player Action: {action.description}
        Result: {outcome.narrative_result} (Success: {outcome.success})
        
        Director's Focus: {directives.narrative_focus if directives else 'Neutral'}
        Director's Note: {directives.next_beat if directives else 'Continue story'}
        
        Current Location: {state['world'].locations.get(action.player_id, 'Unknown')}
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", f"Narrate this:\n{context_block}")
        ])

        response = await self.model.ainvoke(prompt)
        
        # We return this as a LangChain message to append to history
        return {
            "messages": [response]
        }

    async def process(self, state: GameState) -> Dict[str, Any]:
        return await self.narrate_outcome(state)
