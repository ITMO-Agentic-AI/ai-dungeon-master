from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field
from src.core.types import GameState, NarrativeState, CampaignBlueprint
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service

class StoryArchitectAgent(BaseAgent):
    def __init__(self):
        super().__init__("Story Architect")
        self.model = model_service.get_model()
        self.structured_llm = self.model.with_structured_output(CampaignBlueprint)

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("plan_narrative", self.plan_narrative)
        graph.add_edge("__start__", "plan_narrative")
        return graph

    async def plan_narrative(self, state: GameState) -> Dict[str, Any]:
        """
        Step 1: High-Level Story & World Blueprint using Storyteller principles.
        Generates a structured storyline with SVO events and initial narrative entities.
        """
        setting = state["setting"]

        system_prompt = """You are an expert AI Story Architect using the STORYTELLER framework.
        Create a high-level campaign blueprint ensuring narrative coherence and logical consistency.
        Structure the story using Subject-Verb-Object (SVO) events for key beats (PlotNodes).
        Define initial Narrative Entities (Characters, Locations, Items) and their starting states/relationships."""

        user_prompt = f"""
        Theme: {setting.theme}
        Player Characters: {', '.join(setting.player_concepts)}
        Target Length: {setting.story_length} words equivalent

        Generate a campaign blueprint including:
        1. A Title and Tagline.
        2. An Overview (Act I, II, III).
        3. A structured Storyline with 5-10 PlotNodes.
           Each PlotNode must have:
           - An ID (e.g., beat_01, beat_02).
           - A Title and Description.
           - An SVOEvent (Subject, Verb, Object).
           - Logical connections (follows_node, leads_to_node).
           - Tags (e.g., 'setup', 'conflict', 'climax', 'resolution').
        4. Initial Narrative Entities (e.g., 3-5 major characters, key locations, important items).
           Each Entity must have:
           - An ID.
           - A Name and Type (character, location, item).
           - A core description.
           - Initial mutable attributes (e.g., location, health, status).
           - Relationships with other entities (e.g., 'ally_of', 'located_in', 'possessed_by').
        Focus on creating a logically connected sequence of events and well-defined initial entities.
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])

        chain = prompt | self.structured_llm
        blueprint: CampaignBlueprint = await chain.ainvoke({})

        new_narrative = NarrativeState(
            title=blueprint.title,
            tagline=blueprint.tagline,
            story_arc_summary=blueprint.overview,
            storyline=blueprint.storyline,
            narrative_entities={entity.id: entity for entity in blueprint.initial_entities},
            current_scene="start",
            narrative_tension=0.1
        )

        return {"narrative": new_narrative}

    async def process(self, state: GameState) -> Dict[str, Any]:
        return await self.plan_narrative(state)
