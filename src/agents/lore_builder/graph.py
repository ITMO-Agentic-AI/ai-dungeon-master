from typing import Any, Dict, List
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field
from src.core.types import GameState, WorldState, Region, Culture, KeyNPC, WorldHistory
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service

# Structured Output Schema for the LLM
class WorldBible(BaseModel):
    world_name: str
    tone: str
    world_summary: str
    regions: List[Region]
    cultures: List[Culture]
    history: WorldHistory
    key_npcs: List[KeyNPC]


class LoreBuilderAgent(BaseAgent):
    def __init__(self):
        super().__init__("Lore Builder")
        self.model = model_service.get_model()
        # Enforce structured output to populate our WorldState directly
        self.structured_llm = self.model.with_structured_output(WorldBible)

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        # FIXED: Node name now matches the method name
        graph.add_node("build_lore", self.build_lore)
        graph.add_edge("__start__", "build_lore")
        return graph

    async def build_lore(self, state: GameState) -> Dict[str, Any]:
        """
        Step 2: Deep World-Building.
        Uses the 'narrative' blueprint from Phase 1 to generate concrete lore.
        """
        # Retrieve Phase 1 output
        narrative = state["narrative"]
        
        # Retrieve Setting info for context
        setting = state["setting"]

        system_prompt = """You are an expert World-Building AI. 
        Your task is to create a 'World Bible' that supports the provided Story Blueprint.
        The world must be game-ready, with distinct regions, conflicts, and NPCs that directly serve the plot."""

        user_prompt = f"""
        # Input Context
        Campaign Title: {narrative.title}
        Theme: {setting.theme}
        Story Summary: {narrative.story_arc_summary}
        Major Factions/Antagonists: {', '.join(narrative.major_factions)}
        
        # Requirement
        Generate a detailed World Bible containing:
        1. World Name & Tone.
        2. 3 Distinct Regions (Geographically diverse).
        3. 2 Major Cultures (Clashing values).
        4. A defining Historical Event (Myth).
        5. 2 Key NPCs per region (Total 6), with at least one tied to the Main Antagonist.
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])

        # Generate structured lore
        chain = prompt | self.structured_llm
        bible: WorldBible = await chain.ainvoke({})

        # Convert LLM output to WorldState
        new_world_state = WorldState(
            overview=f"{bible.world_name}: {bible.world_summary} (Tone: {bible.tone})",
            regions=bible.regions,
            cultures=bible.cultures,
            history=bible.history,
            important_npcs=bible.key_npcs
        )

        # Return state update (merges into GameState['world'])
        return {"world": new_world_state}

    async def process(self, state: GameState) -> Dict[str, Any]:
        return await self.build_lore(state)
