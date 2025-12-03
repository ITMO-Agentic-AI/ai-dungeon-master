# src/agents/player_proxy/graph.py

from typing import Any, Dict, List
import uuid
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field

from src.core.types import GameState, Player, DnDCharacterStats
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service

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

        start_loc_id = "unknown"
        if world.locations:
            start_loc_id = list(world.locations.keys())[0]

        system_prompt = """You are an expert D&D 5e Character Creator.
        Your goal is to generate balanced, interesting player characters (PCs) that fit the campaign theme.
        They must be ready for immediate gameplay with full D&D 5e stats."""

        user_prompt = f"""
        # Campaign Context
        Theme: {setting.theme}
        Story Hook: {narrative.tagline}
        Requested Archetypes: {', '.join(setting.player_concepts)}

        # Task
        Create {len(setting.player_concepts)} distinct Player Characters for D&D 5e.
        For each character:
        1. Assign a Name, D&D Class (e.g., Fighter, Wizard), Race (e.g., Human, Elf), and Background (e.g., Acolyte).
        2. Generate D&D 5e attributes (Str, Dex, Con, Int, Wis, Cha). Use standard array or point buy method.
        3. Calculate derived stats: HP (based on class and Con), AC (based on class/armor), Initiative (Dex mod), Proficiency Bonus (based on level=1).
        4. Assign a starting Inventory (3-5 items).
        5. Write a 2-sentence Backstory tying them to the campaign hook.
        6. Calculate saving throws and skills based on class and stats.

        IMPORTANT: Set their 'location_id' to '{start_loc_id}'.
        Use the provided JSON schema for output.
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])

        chain = prompt | self.structured_llm
        result: CharacterBatch = await chain.ainvoke({})

        final_players = []
        for char in result.characters:
            if not char.id:
                char.id = f"player_{uuid.uuid4().hex[:8]}"

            # Calculate HP if not set by LLM
            if char.stats.max_hit_points == 10 and char.class_name:
                con_mod = (char.stats.constitution - 10) // 2
                base_hp = 8
                if char.class_name.lower() in ["barbarian"]:
                    base_hp = 12
                elif char.class_name.lower() in ["fighter", "paladin", "ranger"]:
                    base_hp = 10
                char.stats.max_hit_points = base_hp + con_mod
                char.stats.current_hit_points = char.stats.max_hit_points

            char.location_id = start_loc_id
            final_players.append(char)

        return {"players": final_players}

    async def process(self, state: GameState) -> Dict[str, Any]:
        return await self.create_characters(state)
