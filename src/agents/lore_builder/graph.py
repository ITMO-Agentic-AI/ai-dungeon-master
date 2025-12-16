from typing import Any
from langgraph.graph import StateGraph
from pydantic import BaseModel
from src.core.types import GameState, WorldState, Region, Culture, KeyNPC, WorldHistory
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service
from src.services.structured_output import get_structured_output
from src.services.agent_context_hub import AgentMessage, MessageType
from langchain_core.messages import SystemMessage, HumanMessage
import logging

logger = logging.getLogger(__name__)


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

    async def build_lore(self, state: GameState) -> dict[str, Any]:
        """
        Step 2: Deep World-Building.
        Uses the 'narrative' blueprint from Phase 1 to generate concrete lore.
        """
        # Retrieve Phase 1 output
        narrative = state["narrative"]
        setting = state["setting"]
        context_hub = state.get("_context_hub")
        knowledge_graph = state.get("knowledge_graph")

        # FIXED: theme is in Setting, not NarrativeState
        theme = setting.theme

        # Get narrative context from hub
        narrative_context = ""
        if context_hub:
            latest_narrative = context_hub.get_latest_narrative_context()
            if latest_narrative:
                narrative_context = (
                    f"\n\nStory Context from Architect: "
                    f"{latest_narrative.get('title', 'Untitled')} - "
                    f"{latest_narrative.get('overview', '')[:200]}"
                )

        system_prompt = """You are an expert World-Building AI.
        Your task is to create a 'World Bible' that supports the provided Story Blueprint.
        The world must be game-ready, with distinct regions, conflicts, and NPCs that directly serve the plot.
        Ensure the world feels cohesive, with cultures and locations deeply interconnected.

        CRITICAL REQUIREMENT: For each Culture object, you MUST provide ALL of these fields:
        - name: The culture's name (string)
        - values: List of core values (array of strings, e.g., ["honor", "family", "arcane magic"])
        - social_structure: REQUIRED - Description of how society is organized (string, e.g., "Hierarchical monarchy with noble bloodlines", "Guild-based councils", "Tribal elders with shamanic traditions")
        - conflicts: String describing major conflicts or internal struggles
        """

        user_prompt = f"""# Input Context
        Campaign Title: {narrative.title}
        Theme: {theme}
        Story Summary: {narrative.story_arc_summary}
        Major Factions/Antagonists: {', '.join(narrative.major_factions)}{narrative_context}

        # Requirement
        Generate a detailed World Bible containing:
        1. World Name & Tone - Must be distinctive and match the theme.
        2. 3 Distinct Regions (Geographically diverse).
           Each region should feel unique and interconnected.
        3. 2 Major Cultures (Clashing values and beliefs).
           CRITICAL: For EACH culture, you MUST provide:
           - name: Culture name (e.g., "Stoneborn Dwarves", "Sunfire Elves")
           - values: Array of core values (e.g., ["craftsmanship", "tradition", "ancestor honor"])
           - social_structure: How their society is organized - DO NOT OMIT THIS FIELD 
             Examples: "Monarchical dynasty with appointed nobles", "Guild-based apprenticeship system", "Tribal councils with shamanic authority", "Meritocratic warrior society"
           - conflicts: String describing what they fight about internally and externally
        4. A defining Historical Event (Myth) - An event that shapes the current world.
        5. 2 Key NPCs per region (Total 6), with at least one tied to the Main Antagonist.
           NPCs should have clear motivations and connections to other NPCs.
        """

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        logger.info("🌍 Lore Builder generating world bible...")
        bible: WorldBible = await get_structured_output(self.model, messages, WorldBible)
        logger.info(f"✅ World created: {bible.world_name}")

        new_world_state = WorldState(
            overview=f"{bible.world_name}: {bible.world_summary} (Tone: {bible.tone})",
            regions=bible.regions,
            cultures=bible.cultures,
            history=bible.history,
            important_npcs=bible.key_npcs,
        )

        # Update knowledge graph with world entities
        if knowledge_graph:
            # Add regions
            for region in bible.regions:
                knowledge_graph.add_entity(
                    f"region_{region.name.lower()}",
                    "region",
                    {"name": region.name, "description": region.description},
                )

            # Add cultures
            for culture in bible.cultures:
                culture_id = f"culture_{culture.name.lower()}"
                knowledge_graph.add_entity(
                    culture_id, "culture", culture.model_dump()
                )

            # Add NPCs
            for npc in bible.key_npcs:
                npc_id = f"npc_{npc.name.lower()}"
                knowledge_graph.add_entity(npc_id, "npc", npc.model_dump())

                # Add location relationship if available
                if hasattr(npc, "region") and npc.region:
                    region_id = f"region_{npc.region.lower()}"
                    knowledge_graph.add_relation(
                        npc_id, "located_in", region_id, source_agent="Lore Builder"
                    )

            logger.debug(
                f"✓ Knowledge graph updated with "
                f"{len(bible.regions)} regions, "
                f"{len(bible.cultures)} cultures, "
                f"{len(bible.key_npcs)} NPCs"
            )

        # Broadcast world update to context hub
        if context_hub:
            message = AgentMessage(
                sender="Lore Builder",
                message_type=MessageType.WORLD_CHANGE,
                content={
                    "world_name": bible.world_name,
                    "tone": bible.tone,
                    "num_regions": len(bible.regions),
                    "num_cultures": len(bible.cultures),
                    "num_npcs": len(bible.key_npcs),
                    "description": bible.world_summary[:100],
                },
                target_agents=["World Engine", "Director", "Dungeon Master"],
            )
            context_hub.broadcast(message)
            logger.debug("✓ Broadcast world update to context hub")

        # Return state update (merges into GameState['world'])
        return {
            "world": new_world_state,
            "knowledge_graph": knowledge_graph,
            "_context_hub": context_hub,
        }

    async def answer_question(self, state: GameState) -> dict[str, Any]:
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
                [f"- {npc.name}: {npc.role}" for npc in world.important_npcs[:3]]
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
        - Make connections between different world elements when relevant
        """

        context_block = f"""
        World Overview: {world_overview}
        {regions_info}
        {npcs_info}

        Player Question: {player_question}
        """

        messages_to_send = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Answer this question based on the world lore:\n{context_block}"
            ),
        ]

        response = await self.model.ainvoke(messages_to_send)

        # Broadcast lore query response
        context_hub = state.get("_context_hub")
        if context_hub:
            message = AgentMessage(
                sender="Lore Builder",
                message_type=MessageType.LORE_RESPONSE,
                content={
                    "question": player_question,
                    "response_preview": str(response.content)[:100],
                },
                target_agents=["Dungeon Master", "Director"],
            )
            context_hub.broadcast(message)

        return {"messages": [response], "_context_hub": context_hub}

    async def process(self, state: GameState) -> dict[str, Any]:
        return await self.build_lore(state)
