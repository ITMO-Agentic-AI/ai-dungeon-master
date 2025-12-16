from typing import Any
from langgraph.graph import StateGraph
from src.core.types import GameState, NarrativeState, CampaignBlueprint
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service
from src.services.structured_output import get_structured_output
from src.services.agent_context_hub import AgentMessage, MessageType
from langchain_core.messages import SystemMessage, HumanMessage
import logging

logger = logging.getLogger(__name__)


class StoryArchitectAgent(BaseAgent):
    def __init__(self):
        super().__init__("Story Architect")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("plan_narrative", self.plan_narrative)
        graph.add_edge("__start__", "plan_narrative")
        return graph

    async def plan_narrative(self, state: GameState) -> dict[str, Any]:
        """
        Step 1: High-Level Story & World Blueprint using Storyteller principles.
        Generates a structured storyline with SVO events and initial narrative entities.
        """
        setting = state["setting"]
        theme = setting.theme if hasattr(setting, "theme") else setting.get("theme", "Fantasy")
        player_concepts = (
            setting.player_concepts
            if hasattr(setting, "player_concepts")
            else setting.get("player_concepts", [])
        )
        story_length = (
            setting.story_length
            if hasattr(setting, "story_length")
            else setting.get("story_length", 2000)
        )

        # Get context hub for broadcasting messages
        context_hub = state.get("_context_hub")

        system_prompt = """You are an expert AI Story Architect using the STORYTELLER framework.
        Create a high-level campaign blueprint ensuring narrative coherence and logical consistency.
        Structure the story using Subject-Verb-Object (SVO) events for key beats (PlotNodes).
        Define initial Narrative Entities (Characters, Locations, Items) and their starting states/relationships.

        CRITICAL: When specifying relationships for entities, ALWAYS use lists even for single values.
        Example: "located_in": ["location_id"] NOT "located_in": "location_id"
        Example: "allies": ["char_1", "char_2"] NOT "allies": "char_1"
        
        Make the narrative engaging, with clear hooks that will drive player decisions.
        Ensure thematic consistency throughout the story arc.
        """

        # Use raw string to avoid f-string format specifier issues with JSON examples
        user_prompt = f"""
        Theme: {theme}
        Player Characters: {', '.join(player_concepts)}
        Target Length: {story_length} words equivalent

        Generate a campaign blueprint including:
        1. A Title and Tagline that capture the essence.
        2. An Overview (Act I, II, III) with clear story progression.
        3. A structured Storyline with 5-10 PlotNodes.
           Each PlotNode must have:
           - An ID (e.g., "beat_01", "beat_02").
           - A Title and Description.
           - An SVOEvent (Subject, Verb, Object).
           - Logical connections (follows_node, leads_to_node).
           - Tags (e.g., 'setup', 'conflict', 'climax', 'resolution').
        4. Initial Narrative Entities (e.g., 3-5 major characters, key locations, important items).
           Each Entity must have:
           - An ID (e.g., "char_main_hero", "loc_castle", "item_sword").
           - A Name and Type (character, location, item).
           - A core description.
           - Initial mutable attributes as a dictionary with string keys and values.
           - Relationships with other entities (IMPORTANT: ALL relationship values MUST be LISTS, even for single values).
             Valid relationship examples:
             - "allies": ["char_companion1", "char_companion2"]
             - "located_in": ["loc_starting_town"]
             - "possesses": ["item_magical_key"]
             - "enemy_of": ["char_dark_lord"]

           REMEMBER: located_in, possesses, owned_by, and ALL other relationships must map to LISTS.
           Example: Do NOT use "located_in": "loc_castle", instead use "located_in": ["loc_castle"]

        Focus on creating a logically connected sequence of events and well-defined initial entities.
        """

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        logger.info("📖 Story Architect generating campaign blueprint...")
        blueprint: CampaignBlueprint = await get_structured_output(
            self.model, messages, CampaignBlueprint
        )
        logger.info(f"✅ Campaign created: {blueprint.title}")

        # DEFENSIVE: Post-process relationships to ensure all values are lists
        for entity in blueprint.initial_entities:
            if entity.relationships:
                cleaned_relationships = {}
                for key, value in entity.relationships.items():
                    if isinstance(value, list):
                        cleaned_relationships[key] = value
                    elif isinstance(value, str):
                        # Convert string to single-item list
                        cleaned_relationships[key] = [value]
                    else:
                        # Handle other types by converting to string first
                        cleaned_relationships[key] = [str(value)]
                entity.relationships = cleaned_relationships

        new_narrative = NarrativeState(
            title=blueprint.title,
            tagline=blueprint.tagline,
            story_arc_summary=blueprint.overview,
            storyline=blueprint.storyline,
            narrative_entities={entity.id: entity for entity in blueprint.initial_entities},
            current_scene="start",
            narrative_tension=0.1,
        )

        # Broadcast narrative update to context hub
        if context_hub:
            message = AgentMessage(
                sender="Story Architect",
                message_type=MessageType.NARRATIVE_UPDATE,
                content={
                    "title": blueprint.title,
                    "tagline": blueprint.tagline,
                    "overview": blueprint.overview,
                    "num_entities": len(blueprint.initial_entities),
                    "num_plot_nodes": len(blueprint.storyline),
                },
                target_agents=["Lore Builder", "Director"],
            )
            context_hub.broadcast(message)
            logger.debug(f"✓ Broadcast narrative update to context hub")

        return {"narrative": new_narrative, "_context_hub": context_hub}

    async def process(self, state: GameState) -> dict[str, Any]:
        return await self.plan_narrative(state)
