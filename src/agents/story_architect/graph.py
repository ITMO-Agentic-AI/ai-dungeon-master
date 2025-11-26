from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field
from src.core.types import GameState, NarrativeState
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service

# Define the structured output for the LLM to ensure it fits our State
class CampaignBlueprint(BaseModel):
    title: str = Field(description="The campaign title")
    tagline: str = Field(description="A short, punchy tagline")
    overview: str = Field(description="The high-level story summary (Acts I-III)")
    key_beats: list[str] = Field(description="A list of 5-10 major plot points or quest milestones")
    factions: list[str] = Field(description="Names of 2-3 major antagonistic or allied groups")

class StoryArchitectAgent(BaseAgent):
    def __init__(self):
        super().__init__("Story Architect")
        self.model = model_service.get_model()
        # Enforce structured output so we don't get a raw string back
        self.structured_llm = self.model.with_structured_output(CampaignBlueprint)

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        # FIXED: Matches the method name defined below
        graph.add_node("plan_narrative", self.plan_narrative)
        graph.add_edge("__start__", "plan_narrative")
        return graph

    async def plan_narrative(self, state: GameState) -> Dict[str, Any]:
        """
        Step 1: High-Level Story & World Blueprint.
        """
        # FIXED: Access Pydantic fields using dot notation, not .get()
        setting = state["setting"]
        
        # Use default values if setting is empty (fallback)
        theme = getattr(setting, "theme", "High Fantasy")
        concepts = getattr(setting, "player_concepts", ["Heroes"])
        length = getattr(setting, "story_length", "short")

        system_prompt = """You are an expert AI Story Architect. 
        Create a high-level blueprint for a TTRPG campaign.
        Focus on the 'Big Picture': The inciting incident, the rising action, and the climax."""

        user_prompt = f"""
        Theme: {theme}
        Player Characters: {', '.join(concepts)}
        Target Length: {length} words equivalent
        
        Generate a campaign blueprint including:
        1. A Title and Tagline.
        2. An Overview (Act I, II, III).
        3. Key Story Beats (Specific milestones).
        4. Major Factions (Antagonists/Allies).
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])

        # Invoke model with structured output
        chain = prompt | self.structured_llm
        blueprint: CampaignBlueprint = await chain.ainvoke({})

        # Map the LLM output back to your NarrativeState
        new_narrative = NarrativeState(
            title=blueprint.title,
            tagline=blueprint.tagline,
            story_arc_summary=blueprint.overview,
            story_beats=blueprint.key_beats,
            major_factions=blueprint.factions,
            current_scene="start",
            narrative_tension=0.1
        )

        # Return the state update
        return {"narrative": new_narrative}

    # Cleaned up process wrapper
    async def process(self, state: GameState) -> Dict[str, Any]:
        return await self.plan_narrative(state)
