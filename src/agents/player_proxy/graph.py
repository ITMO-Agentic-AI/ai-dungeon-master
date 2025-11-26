from typing import Any, Dict, List
import uuid
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from src.core.types import GameState, Player, RPGStats
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service

# Helper for structured output
class CharacterBatch(BaseModel):
    characters: List[Player]

class PlayerCreatorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Player Creator")
        self.model = model_service.get_model()
        self.structured_llm = self.model.with_structured_output(CharacterBatch)

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("create_characters", self.create_characters)
        graph.add_edge("__start__", "create_characters")
        return graph

    async def create_characters(self, state: GameState) -> Dict[str, Any]:
        """
        Step 4: Player Proxy Initialization.
        Generates specific character sheets based on the 'Setting' concepts 
        and places them in the 'World'.
        """
        setting = state["setting"]
        narrative = state["narrative"]
        world = state["world"]
        
        # Determine a starting location (safe default: first location in the dict)
        # In a real scenario, Phase 3 should mark a 'starting_town'.
        start_loc_id = "unknown"
        if world.locations:
            start_loc_id = list(world.locations.keys())[0]

        # Construct the Prompt
        system_prompt = """You are an expert RPG Character Creator.
        Your goal is to generate balanced, interesting player characters (PCs) that fit the campaign theme.
        They must be ready for immediate gameplay."""

        user_prompt = f"""
        # Campaign Context
        Theme: {setting.theme}
        Story Hook: {narrative.tagline}
        Requested Archetypes: {', '.join(setting.player_concepts)}
        
        # Task
        Create {len(setting.player_concepts)} distinct Player Characters.
        For each character:
        1. Assign a Name and Class/Archetype.
        2. Generate standard D&D-style attributes (Str, Dex, etc.).
        3. Give them a starting Inventory (3-5 items).
        4. Write a 2-sentence Backstory tying them to the campaign hook.
        5. Assign 'max_hp' between 10 and 20.
        
        IMPORTANT: Set their 'location_id' to '{start_loc_id}'.
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])

        # Generate Characters
        chain = prompt | self.structured_llm
        result: CharacterBatch = await chain.ainvoke({})
        
        # Post-processing (ensure IDs are set if LLM missed them)
        final_players = []
        for char in result.characters:
            if not char.id:
                char.id = f"player_{uuid.uuid4().hex[:8]}"
            # Ensure consistency
            char.current_hp = char.max_hp
            char.location_id = start_loc_id
            final_players.append(char)

        return {"players": final_players}

    async def process(self, state: GameState) -> Dict[str, Any]:
        return await self.create_characters(state)
