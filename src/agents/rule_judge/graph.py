# src/agents/rule_judge/graph.py

from typing import Any
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph

from src.core.types import GameState, JudgeVerdict
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service
from src.services.structured_output import get_structured_output
from src.tools.dnd_api_tools import (
    get_spell_info,
    get_equipment_info,
)


class JudgeAgent(BaseAgent):
    def __init__(self):
        super().__init__("Judge")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("evaluate_turn", self.evaluate_turn)
        graph.add_edge("__start__", "evaluate_turn")
        return graph

    async def evaluate_turn(self, state: GameState) -> dict[str, Any]:
        """
        Step 6: Quality Assurance / Judgment.
        Reviews the last action resolution for consistency and fun.
        Now uses D&D API tools for verification.
        """
        action = state.get("current_action")
        outcome = state.get("last_outcome")
        narrative = state.get("narrative")
        players = {p.id: p for p in state["players"]}

        if not action or not outcome:
            return {"last_verdict": None}

        actor = players.get(action.player_id)

        # --- API Checks ---
        api_checks = []
        correction_needed = False
        correction_suggestions = []

        if "cast" in action.description.lower() or "spell" in action.description.lower():
            import re

            spell_match = re.search(
                r"cast ['\"]?([^'\"]+?)['\"]?", action.description, re.IGNORECASE
            )
            if not spell_match:
                spell_match = re.search(
                    r"spell ['\"]?([^'\"]+?)['\"]?", action.description, re.IGNORECASE
                )

            if spell_match:
                spell_name = spell_match.group(1)
                try:
                    spell_info = await get_spell_info.ainvoke({"spell_name": spell_name})
                    if "error" in spell_info:
                        api_checks.append(
                            f"API Check: Spell '{spell_name}' not found in D&D database."
                        )
                        correction_needed = True
                        correction_suggestions.append(
                            f"The spell '{spell_name}' does not exist. Please choose a valid spell."
                        )
                    else:
                        api_checks.append(f"API Check: Spell '{spell_name}' verified.")
                except Exception as e:
                    api_checks.append(f"API Check: Failed to verify spell '{spell_name}': {e}")

        if "attack with" in action.description.lower() or "hit with" in action.description.lower():
            import re

            weapon_match = re.search(
                r"attack with ['\"]?([^'\"]+?)['\"]?", action.description, re.IGNORECASE
            )
            if not weapon_match:
                weapon_match = re.search(
                    r"hit with ['\"]?([^'\"]+?)['\"]?", action.description, re.IGNORECASE
                )

            if weapon_match:
                weapon_name = weapon_match.group(1)
                try:
                    weapon_info = await get_equipment_info.ainvoke({"equipment_name": weapon_name})
                    if "error" in weapon_info:
                        api_checks.append(
                            f"API Check: Weapon '{weapon_name}' not found in D&D database."
                        )
                        correction_needed = True
                        correction_suggestions.append(
                            f"The weapon '{weapon_name}' does not exist. Please choose a valid weapon."
                        )
                    else:
                        api_checks.append(f"API Check: Weapon '{weapon_name}' verified.")
                except Exception as e:
                    api_checks.append(f"API Check: Failed to verify weapon '{weapon_name}': {e}")

        if actor:
            class_name = actor.class_name
            if "cast" in action.description.lower() and class_name.lower() in ["fighter", "rogue"]:
                api_checks.append(f"Rule Check: Class '{class_name}' typically cannot cast spells.")
                correction_needed = True
                correction_suggestions.append(
                    f"Characters of class '{class_name}' usually cannot cast spells. Please reconsider the action or character build."
                )

        # --- LLM Evaluation ---
        context_str = f"""
        Campaign Tone: {state['setting'].theme}
        Current Scene: {narrative.current_scene}

        Player Action: {action.description} (Type: {action.type})
        Player Class: {actor.class_name if actor else 'Unknown'}
        Resolved Outcome: {outcome.narrative_result} (Success: {outcome.success})

        API Checks Performed:
        {chr(10).join(api_checks)}

        Correction Needed: {correction_needed}
        Suggested Corrections: {', '.join(correction_suggestions) if correction_suggestions else 'None'}
        """

        system_prompt = """You are the Arbiter and Judge of this D&D Roleplaying Game simulation.
        Your role is to evaluate the quality of the recent turn interaction.

        Criteria:
        1. Consistency: Does the outcome contradict established lore, physics, or D&D 5e rules (as verified by API checks)?
        2. Agency: Did the system ignore the player's intent?
        3. Safety: Is the content appropriate for the theme?
        4. Rule Adherence: Does the action align with the character's class, race, and abilities?

        If API checks flagged an issue or the outcome is nonsensical, hallucinations, or breaks the game, mark is_valid=False.
        Provide specific feedback in the 'feedback' field and a 'correction_suggestion' if applicable.
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Evaluate this turn:\n{context_str}"),
        ]

        verdict: JudgeVerdict = await get_structured_output(self.model, messages, JudgeVerdict)

        if correction_needed and verdict.is_valid:
            verdict.is_valid = False
            verdict.feedback += f" [API Discrepancy: {', '.join(correction_suggestions)}]"
            verdict.correction_suggestion = (
                ", ".join(correction_suggestions)
                if not verdict.correction_suggestion
                else verdict.correction_suggestion
                + f" [API Suggestion: {', '.join(correction_suggestions)}]"
            )

        return {"last_verdict": verdict}

    async def process(self, state: GameState) -> dict[str, Any]:
        return await self.evaluate_turn(state)
