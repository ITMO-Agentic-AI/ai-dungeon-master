from typing import Any, Dict
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from pydantic import BaseModel

from src.core.types import GameState, JudgeVerdict, EvaluationMetrics
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service

class JudgeAgent(BaseAgent):
    def __init__(self):
        super().__init__("Judge")
        self.model = model_service.get_model()
        self.structured_llm = self.model.with_structured_output(JudgeVerdict)

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("evaluate_turn", self.evaluate_turn)
        graph.add_edge("__start__", "evaluate_turn")
        return graph

    async def evaluate_turn(self, state: GameState) -> Dict[str, Any]:
        """
        Step 6: Quality Assurance / Judgment.
        Reviews the last action resolution for consistency and fun.
        """
        action = state.get("current_action")
        outcome = state.get("last_outcome")
        narrative = state.get("narrative")
        
        if not action or not outcome:
            return {"last_verdict": None}

        # Construct Context
        context_str = f"""
        Campaign Tone: {state['setting'].theme}
        Current Scene: {narrative.current_scene}
        
        Player Action: {action.description} (Type: {action.type})
        Resolved Outcome: {outcome.narrative_result} (Success: {outcome.success})
        """

        system_prompt = """You are the Arbiter and Judge of this Roleplaying Game simulation.
        Your role is to evaluate the quality of the recent turn interaction.
        
        Criteria:
        1. Consistency: Does the outcome contradict established lore or physics?
        2. Agency: Did the system ignore the player's intent?
        3. Safety: Is the content appropriate for the theme?
        
        If the outcome is nonsensical, hallucinations, or breaks the game, mark is_valid=False.
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", f"Evaluate this turn:\n{context_str}")
        ])

        # Invoke LLM
        verdict: JudgeVerdict = await (prompt | self.structured_llm).ainvoke({})

        return {"last_verdict": verdict}

    async def process(self, state: GameState) -> Dict[str, Any]:
        return await self.evaluate_turn(state)
