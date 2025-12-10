from typing import Any, Dict
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field
from src.core.types import GameState, WorldState, Region, Culture, KeyNPC, WorldHistory
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service
from src.services.structured_output import get_structured_output
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


class WorldBible(BaseModel):
    world_name: str
    tone: str
    world_summary: str
    regions: list[Region]
    cultures: list[Culture]
    history: WorldHistory
    key_npcs: list[KeyNPC]


class LoreBuilderAgent(BaseAgent):
    def __init__(self):
        super().__init__("Lore Builder")
        self.model = model_service.get_model()

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

        setting = state["setting"]
        theme = setting.theme if hasattr(setting, 'theme') else setting.get('theme', 'Fantasy')

        system_prompt = """You are an expert World-Building AI. 
        Your task is to create a 'World Bible' that supports the provided Story Blueprint.
        The world must be game-ready, with distinct regions, conflicts, and NPCs that directly serve the plot."""

        user_prompt = f"""
        # Input Context
        Campaign Title: {narrative.title}
        Theme: {theme}
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

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        bible: WorldBible = await get_structured_output(
            self.model, messages, WorldBible
        )

        new_world_state = WorldState(
            overview=f"{bible.world_name}: {bible.world_summary} (Tone: {bible.tone})",
            regions=bible.regions,
            cultures=bible.cultures,
            history=bible.history,
            important_npcs=bible.key_npcs,
        )

        # Return state update (merges into GameState['world'])
        return {"world": new_world_state}

    async def answer_question(self, state: GameState) -> Dict[str, Any]:
        """
        Phase 4b: The Lore Master (Q&A).
        When a player asks a question during gameplay,
        consult the World Bible and respond in-character as an omniscient guide.
        """
        # Get player's question from current input
        messages = state.get("messages", [])
        player_question = ""
        if messages:
            # Assume the last message is the player's question
            player_question = messages[-1].content

        # Get world lore context
        world = state.get("world")
        world_overview = world.overview if world else "Unknown world"
        
        # Get relevant NPCs and regions
        npcs_info = ""
        if world and world.important_npcs:
            npcs_info = "\nKey NPCs:\n" + "\n".join(
                [f"- {npc.name}: {npc.description}" for npc in world.important_npcs[:3]]
            )
        
        regions_info = ""
        if world and world.regions:
            regions_info = "\nKey Regions:\n" + "\n".join(
                [f"- {region.name}: {region.description}" for region in world.regions[:3]]
            )

        system_prompt = """You are the Lore Keeper of this world.
        Answer player questions about the world, NPCs, history, and lore.
        
        Guidelines:
        - Stay in character as a knowledgeable guide
        - Reference the world lore and NPCs provided
        - Keep answers engaging but under 150 words
        - If asked about something not in the lore, improvise consistently with the world
        """

        context_block = f"""
        World Overview: {world_overview}
        {regions_info}
        {npcs_info}
        
        Player Question: {player_question}
        """

        messages_to_send = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Answer this question based on the world lore:\n{context_block}")
        ]

        response = await self.model.ainvoke(messages_to_send)

        return {"messages": [response]}

    async def process(self, state: GameState) -> dict[str, Any]:
        return await self.build_lore(state)
