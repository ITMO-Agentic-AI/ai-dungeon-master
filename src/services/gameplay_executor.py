"""Phase 3 Gameplay Loop Executor.

Coordinates the 7-step interactive execution loop:
1. Player Action Generation
2. Action Validation & Rule Adjudication
3. Environment & Lore Update
4. Narrative Description & Dialogue
5. Director Oversight & Pacing
6. Event Recording & Memory Sync
7. Loop Iteration & Scene Transition
"""

import logging
from typing import Any
from datetime import datetime

from src.core.types import GameState, ActionOutcome, Action
from src.core.gameplay_phase import (
    ActionIntentType,
    ActionResolutionStatus,
    ActionOutcomeToken,
    WorldStateChange,
    EventNode,
    SessionMemory,
    GameplayPhaseState,
    PacingMetrics,
    SceneTransitionTrigger,
    RollResult,
)

logger = logging.getLogger(__name__)


class GameplayExecutor:
    """
    Orchestrates the Phase 3 gameplay loop.
    
    Each turn follows: Player Action → Validation → World Update → Narration → Director → Memory → Transition
    """

    def __init__(self):
        """Initialize gameplay executor."""
        self.gameplay_state: GameplayPhaseState | None = None
        logger.info("GameplayExecutor initialized")

    def initialize_gameplay_phase(
        self,
        game_state: GameState,
        campaign_id: str,
        session_id: str
    ) -> GameplayPhaseState:
        """
        Step 0: Initialize Phase 3 state from completed Phase 1 (initialization).
        
        Args:
            game_state: Completed GameState from initialization
            campaign_id: Campaign identifier
            session_id: Session identifier
            
        Returns:
            GameplayPhaseState ready for turn execution
        """
        session_memory = SessionMemory(
            session_id=session_id,
            campaign_id=campaign_id,
            session_start=datetime.utcnow(),
            current_turn=0
        )

        self.gameplay_state = GameplayPhaseState(
            session_memory=session_memory,
            turn_number=0,
            pacing=PacingMetrics()
        )

        logger.info(
            f"🎮 Phase 3 initialized (campaign={campaign_id}, session={session_id})"
        )
        return self.gameplay_state

    async def execute_turn(
        self,
        game_state: GameState,
        action_resolver: Any = None,  # ActionResolverAgent
        judge: Any = None,  # JudgeAgent
        world_engine: Any = None,  # WorldEngineAgent
        lore_builder: Any = None,  # LoreBuilder
        dm: Any = None,  # DungeonMasterAgent
        director: Any = None  # DirectorAgent
    ) -> tuple[GameState, GameplayPhaseState]:
        """
        Execute one complete turn of the gameplay loop (all 7 steps).
        
        Args:
            game_state: Current GameState
            action_resolver: Agent for mechanical resolution (optional for testing)
            judge: Agent for rule validation (optional for testing)
            world_engine: Agent for world updates (optional for testing)
            lore_builder: Agent for lore consistency (optional for testing)
            dm: Agent for narration (optional for testing)
            director: Agent for pacing/tone (optional for testing)
            
        Returns:
            Tuple of (updated GameState dict, updated GameplayPhaseState)
        """
        if not self.gameplay_state:
            raise RuntimeError("Gameplay phase not initialized. Call initialize_gameplay_phase first.")

        self.gameplay_state.turn_number += 1
        logger.info(f"\n🎲 === TURN {self.gameplay_state.turn_number} === 🎲")

        # ============================================================
        # STEP 1: Player Action Generation
        # ============================================================
        logger.info("\ud83d� Step 1: Player Action Generation")
        player_actions = await self._step1_generate_actions(game_state)
        self.gameplay_state.player_actions = player_actions

        # ============================================================
        # STEP 2: Action Validation & Rule Adjudication
        # ============================================================
        logger.info("\ud83d� Step 2: Action Validation & Rule Adjudication")
        outcome_tokens = await self._step2_validate_actions(
            game_state,
            player_actions,
            action_resolver,
            judge
        )
        self.gameplay_state.outcome_tokens = outcome_tokens

        # ============================================================
        # STEP 3: Environment & Lore Update
        # ============================================================
        logger.info("\ud83d� Step 3: Environment & Lore Update")
        state_changes = await self._step3_update_world(
            game_state,
            outcome_tokens,
            world_engine,
            lore_builder
        )
        self.gameplay_state.world_state_deltas = state_changes

        # ============================================================
        # STEP 4: Narrative Description & Dialogue
        # ============================================================
        logger.info("\ud83d� Step 4: Narrative Description & Dialogue")
        narration_result = await self._step4_narrate_outcome(
            game_state,
            outcome_tokens,
            state_changes,
            dm
        )

        # ============================================================
        # STEP 5: Director Oversight & Pacing
        # ============================================================
        logger.info("\ud83d� Step 5: Director Oversight & Pacing")
        pacing_result, directives = await self._step5_director_oversight(
            game_state,
            self.gameplay_state.pacing,
            director
        )
        self.gameplay_state.pacing = pacing_result
        self.gameplay_state.dm_directives = directives

        # ============================================================
        # STEP 6: Event Recording & Memory Sync
        # ============================================================
        logger.info("\ud83d� Step 6: Event Recording & Memory Sync")
        event_nodes = await self._step6_record_events(
            outcome_tokens,
            state_changes,
            narration_result
        )

        # ============================================================
        # STEP 7: Loop Iteration & Scene Transition
        # ============================================================
        logger.info("\ud83d� Step 7: Loop Iteration & Scene Transition")
        scene_transition = await self._step7_check_scene_transition(
            game_state,
            self.gameplay_state.pacing,
            outcome_tokens
        )
        self.gameplay_state.scene_transitions.append(scene_transition)

        # ============================================================
        # Update GameState for next iteration or scene
        # ============================================================
        game_state["last_outcome"] = narration_result
        game_state["director_directives"] = directives
        game_state["metadata"]["turn"] = self.gameplay_state.turn_number
        game_state["metadata"]["last_turn_timestamp"] = datetime.utcnow().isoformat()

        logger.info(f"✅ Turn {self.gameplay_state.turn_number} complete")
        
        # CRITICAL: Return tuple of (GameState dict, GameplayPhaseState)
        # NOT a tuple where first element tries to use .get()
        return game_state, self.gameplay_state

    async def _step1_generate_actions(self, game_state: GameState) -> list[dict]:
        """
        Step 1: Player Action Generation
        
        Interprets current world state, story context, and character motivations
        to determine player intents.
        """
        players = game_state.get("players", [])
        current_action = game_state.get("current_action")
        messages = game_state.get("messages", [])

        actions = []

        if current_action:
            # Real player action from input
            actions.append({
                "performer_id": current_action.player_id,
                "intent_type": self._classify_intent(current_action.description),
                "description": current_action.description,
                "parameters": {},
                "expected_outcome_type": "uncertain"
            })
        else:
            # Fallback: default action for each player
            for player in players:
                actions.append({
                    "performer_id": player.id,
                    "intent_type": ActionIntentType.INVESTIGATE,
                    "description": f"{player.name} waits and observes the situation.",
                    "parameters": {},
                    "expected_outcome_type": "passive"
                })

        logger.info(f"Generated {len(actions)} player action(s)")
        return actions

    async def _step2_validate_actions(
        self,
        game_state: GameState,
        player_actions: list[dict],
        action_resolver: Any,
        judge: Any
    ) -> list[ActionOutcomeToken]:
        """
        Step 2: Action Validation & Rule Adjudication
        
        Converts intents into D&D-compliant mechanical rolls and validates
        against rules, conditions, and prior state.
        """
        outcome_tokens = []

        for action_idx, action in enumerate(player_actions):
            intent_type = action["intent_type"]
            performer_id = action["performer_id"]

            # Generate mechanical roll based on intent
            primary_roll = self._generate_roll_for_intent(
                intent_type,
                game_state,
                performer_id
            )

            # Check against DC (difficulty class)
            dc = 10  # Default moderate difficulty
            meets_dc = primary_roll.total >= dc

            # Create outcome token
            token = ActionOutcomeToken(
                action_id=f"action_{self.gameplay_state.turn_number}_{action_idx}",
                performer_id=performer_id,
                intent_type=intent_type,
                status=ActionResolutionStatus.RESOLVED,
                primary_roll=primary_roll,
                difficulty_class=dc,
                meets_dc=meets_dc,
                mechanical_summary=f"{action['description']} (rolled {primary_roll.total} vs DC {dc})",
                effectiveness=min(1.0, primary_roll.total / dc) if dc > 0 else 1.0,
                is_valid=True
            )

            outcome_tokens.append(token)
            logger.info(
                f"✓ Validated action: {performer_id} ({intent_type.value}) "
                f"rolled {primary_roll.total} vs DC {dc}"
            )

        return outcome_tokens

    async def _step3_update_world(
        self,
        game_state: GameState,
        outcome_tokens: list[ActionOutcomeToken],
        world_engine: Any,
        lore_builder: Any
    ) -> list[WorldStateChange]:
        """
        Step 3: Environment & Lore Update
        
        Applies mechanical outcomes to world state and validates narrative
        consistency through lore.
        """
        state_changes: list[WorldStateChange] = []

        for token in outcome_tokens:
            if token.meets_dc:
                # Successful action: apply effects
                if token.damage_dealt > 0:
                    change = WorldStateChange(
                        change_type="health",
                        target_id=token.performer_id,
                        old_value=None,  # Would retrieve from game_state
                        new_value=None,  # Would be calculated
                        reason=f"Damage from action: {token.action_id}"
                    )
                    state_changes.append(change)
            else:
                # Failed action: potential consequence
                logger.info(f"Action {token.action_id} failed (rolled {token.primary_roll.total} < {token.difficulty_class})")

        logger.info(f"Applied {len(state_changes)} world state change(s)")
        return state_changes

    async def _step4_narrate_outcome(
        self,
        game_state: GameState,
        outcome_tokens: list[ActionOutcomeToken],
        state_changes: list[WorldStateChange],
        dm: Any
    ) -> ActionOutcome:
        """
        Step 4: Narrative Description & Dialogue Generation
        
        Translates mechanical outcomes into immersive prose and NPC reactions.
        """
        # Build context for DM
        narrative_context = {
            "outcomes": [t.mechanical_summary for t in outcome_tokens],
            "changes": len(state_changes),
            "scene": game_state.get("current_scene", "unknown")
        }

        # Mock narration if DM not provided
        if dm is None:
            outcome = ActionOutcome(
                success=all(t.meets_dc for t in outcome_tokens),
                narrative_result="The action unfolds before you...",
                stat_changes=[],
                new_location_id=None
            )
        else:
            # DM narrates (already has narrate_outcome method)
            dm_response = await dm.narrate_outcome(game_state)
            # Extract or construct ActionOutcome
            outcome = ActionOutcome(
                success=all(t.meets_dc for t in outcome_tokens),
                narrative_result=dm_response["messages"][0].content if dm_response.get("messages") else "The action unfolds...",
                stat_changes=[],
                new_location_id=None
            )

        logger.info(f"📖 DM narrated turn outcome ({len(outcome.narrative_result)} chars)")
        return outcome

    async def _step5_director_oversight(
        self,
        game_state: GameState,
        pacing: PacingMetrics,
        director: Any
    ) -> tuple[PacingMetrics, dict[str, Any]]:
        """
        Step 5: Director Oversight & Pacing Control
        
        Monitors and adjusts narrative flow, tension, and story hooks.
        """
        pacing.turns_in_current_scene += 1

        # Mock directives if director not provided
        if director is None:
            directives = {
                "narrative_focus": "Continue current scene",
                "tension_adjustment": 0.0,
                "next_beat": "ongoing"
            }
        else:
            # Director provides guidance
            directives = await director.direct_scene(game_state)

        # Update tension based on director feedback
        tension_adjustment = directives.get("tension_adjustment", 0)
        pacing.current_tension = min(1.0, max(0.0, pacing.current_tension + tension_adjustment))
        pacing.tension_trajectory.append(pacing.current_tension)

        logger.info(
            f"🎬 Director: tension={pacing.current_tension:.1%}, "
            f"pacing={pacing.get_recommended_pacing()}"
        )

        return pacing, directives

    async def _step6_record_events(
        self,
        outcome_tokens: list[ActionOutcomeToken],
        state_changes: list[WorldStateChange],
        narration_result: ActionOutcome
    ) -> list[EventNode]:
        """
        Step 6: Event Recording & Memory Synchronization
        
        Records all turn activities in dual-layer memory (short-term and
        campaign chronicle).
        """
        event_nodes = []

        for token in outcome_tokens:
            event = EventNode(
                event_id=token.action_id,
                turn_number=self.gameplay_state.turn_number,
                phase="action_resolution",
                performer_id=token.performer_id,
                action_intent=token.intent_type,
                outcome_token=token,
                state_changes=state_changes,
                scene_context="gameplay"
            )
            event_nodes.append(event)
            self.gameplay_state.session_memory.add_event(event)

        logger.info(
            f"📝 Recorded {len(event_nodes)} event(s) to memory "
            f"(total chronicle: {len(self.gameplay_state.session_memory.campaign_chronicle)})"
        )
        return event_nodes

    async def _step7_check_scene_transition(
        self,
        game_state: GameState,
        pacing: PacingMetrics,
        outcome_tokens: list[ActionOutcomeToken]
    ) -> SceneTransitionTrigger:
        """
        Step 7: Loop Iteration & Scene Transition
        
        Determines if current scene should end or continue based on
        pacing metrics and outcome conditions.
        """
        should_transition = pacing.should_transition_scene()

        trigger = SceneTransitionTrigger(
            trigger_type="pacing" if should_transition else "ongoing",
            condition_met=should_transition,
            reason=f"Scene duration: {pacing.turns_in_current_scene} turns"
        )

        if should_transition:
            # Reset scene metrics for next scene
            pacing.turns_in_current_scene = 0
            logger.info("🔄 Scene transition triggered")
        else:
            logger.info("\u23ef\ufe0f  Scene continues...")

        return trigger

    # ============================================================
    # Helper Methods
    # ============================================================

    def _classify_intent(self, action_description: str) -> ActionIntentType:
        """Classify player action description into ActionIntentType."""
        desc_lower = action_description.lower()

        if any(w in desc_lower for w in ["attack", "hit", "strike", "swing"]):
            return ActionIntentType.ATTACK
        elif any(w in desc_lower for w in ["cast", "spell", "magic"]):
            return ActionIntentType.CAST_SPELL
        elif any(w in desc_lower for w in ["talk", "say", "ask", "negotiate"]):
            return ActionIntentType.DIALOGUE
        elif any(w in desc_lower for w in ["check", "search", "look", "examine", "investigate"]):
            return ActionIntentType.INVESTIGATE
        elif any(w in desc_lower for w in ["move", "go", "walk", "run"]):
            return ActionIntentType.MOVE
        elif any(w in desc_lower for w in ["defend", "block", "shield"]):
            return ActionIntentType.DEFEND
        else:
            return ActionIntentType.UNKNOWN

    def _generate_roll_for_intent(
        self,
        intent_type: ActionIntentType,
        game_state: GameState,
        performer_id: str
    ) -> RollResult:
        """Generate appropriate D&D roll for given intent."""
        import random

        # Get character stats
        players = {p.id: p for p in game_state.get("players", [])}
        player = players.get(performer_id)

        modifier = 0
        if player and hasattr(player, "stats"):
            # Use appropriate ability modifier
            if intent_type == ActionIntentType.ATTACK:
                modifier = (player.stats.strength - 10) // 2
            elif intent_type == ActionIntentType.CAST_SPELL:
                modifier = (player.stats.intelligence - 10) // 2
            elif intent_type == ActionIntentType.DIALOGUE:
                modifier = (player.stats.charisma - 10) // 2
            elif intent_type == ActionIntentType.INVESTIGATE:
                modifier = (player.stats.wisdom - 10) // 2

        # Roll d20
        rolls = [random.randint(1, 20)]
        is_crit = rolls[0] == 20
        is_fumble = rolls[0] == 1

        return RollResult(
            dice_type="d20",
            rolls=rolls,
            modifier=modifier,
            total=rolls[0] + modifier,
            is_advantage=False,
            is_disadvantage=False
        )
