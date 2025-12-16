"""Tests for Phase 3: Gameplay Loop (Interactive Execution Stage).

Tests all 7 steps of the gameplay loop:
1. Player Action Generation
2. Action Validation & Rule Adjudication
3. Environment & Lore Update
4. Narrative Description & Dialogue
5. Director Oversight & Pacing
6. Event Recording & Memory Sync
7. Loop Iteration & Scene Transition
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.core.gameplay_phase import (
    ActionIntentType,
    ActionResolutionStatus,
    ActionOutcomeToken,
    RollResult,
    WorldStateChange,
    EventNode,
    SessionMemory,
    GameplayPhaseState,
    PacingMetrics,
    SceneTransitionTrigger,
)
from src.services.gameplay_executor import GameplayExecutor
from src.core.types import GameState, Setting, Player, DnDCharacterStats


class TestActionOutcomeToken:
    """Test action outcome tokens."""

    def test_token_creation(self):
        """Test creating an action outcome token."""
        roll = RollResult(
            dice_type="d20",
            rolls=[15],
            modifier=3,
            total=18,
            is_advantage=False,
            is_disadvantage=False
        )

        token = ActionOutcomeToken(
            action_id="act_001",
            performer_id="player_1",
            intent_type=ActionIntentType.ATTACK,
            status=ActionResolutionStatus.RESOLVED,
            primary_roll=roll,
            difficulty_class=10,
            meets_dc=True,
            mechanical_summary="Player attacks dragon",
            effectiveness=0.9,
            is_valid=True
        )

        assert token.action_id == "act_001"
        assert token.performer_id == "player_1"
        assert token.status == ActionResolutionStatus.RESOLVED
        assert token.meets_dc is True
        assert token.primary_roll.total == 18

    def test_critical_hit_detection(self):
        """Test detecting critical hits (roll of 20)."""
        roll = RollResult(
            dice_type="d20",
            rolls=[20],
            modifier=2,
            total=22
        )

        token = ActionOutcomeToken(
            action_id="act_002",
            performer_id="player_1",
            intent_type=ActionIntentType.ATTACK,
            status=ActionResolutionStatus.CRITICAL_HIT,
            primary_roll=roll,
            difficulty_class=10,
            meets_dc=True,
            mechanical_summary="CRITICAL HIT!",
            effectiveness=1.0,
            is_valid=True
        )

        assert token.status == ActionResolutionStatus.CRITICAL_HIT
        assert token.effectiveness == 1.0


class TestWorldStateChange:
    """Test world state changes."""

    def test_health_change(self):
        """Test recording a health change."""
        change = WorldStateChange(
            change_type="health",
            target_id="player_1",
            old_value=50,
            new_value=35,
            reason="Took 15 damage from fireball"
        )

        assert change.change_type == "health"
        assert change.old_value == 50
        assert change.new_value == 35
        assert "damage" in change.reason.lower()

    def test_inventory_change(self):
        """Test recording an inventory change."""
        change = WorldStateChange(
            change_type="inventory",
            target_id="player_1",
            old_value=["sword", "shield"],
            new_value=["sword", "shield", "magic_scroll"],
            reason="Found magic scroll on goblin"
        )

        assert change.change_type == "inventory"
        assert "magic_scroll" in change.new_value


class TestEventNode:
    """Test event recording."""

    def test_event_creation(self):
        """Test creating an event node."""
        token = ActionOutcomeToken(
            action_id="act_001",
            performer_id="player_1",
            intent_type=ActionIntentType.ATTACK,
            status=ActionResolutionStatus.RESOLVED,
            primary_roll=RollResult(
                dice_type="d20",
                rolls=[14],
                modifier=2,
                total=16
            ),
            difficulty_class=12,
            meets_dc=True,
            mechanical_summary="Attack hits",
            effectiveness=0.8,
            is_valid=True
        )

        event = EventNode(
            event_id="evt_1_1",
            turn_number=1,
            phase="action_resolution",
            performer_id="player_1",
            action_intent=ActionIntentType.ATTACK,
            outcome_token=token,
            scene_context="dungeon_chamber"
        )

        assert event.event_id == "evt_1_1"
        assert event.turn_number == 1
        assert event.outcome_token is not None


class TestSessionMemory:
    """Test dual-layer memory structure."""

    def test_memory_initialization(self):
        """Test creating session memory."""
        memory = SessionMemory(
            session_id="sess_001",
            campaign_id="camp_001"
        )

        assert memory.session_id == "sess_001"
        assert memory.campaign_id == "camp_001"
        assert len(memory.recent_events) == 0
        assert len(memory.campaign_chronicle) == 0

    def test_add_event_to_memory(self):
        """Test adding an event to memory."""
        memory = SessionMemory(
            session_id="sess_001",
            campaign_id="camp_001"
        )

        event = EventNode(
            event_id="evt_1_1",
            turn_number=1,
            phase="action_resolution",
            scene_context="dungeon"
        )

        memory.add_event(event)

        assert len(memory.recent_events) == 1
        assert len(memory.campaign_chronicle) == 1
        assert memory.recent_events[0].event_id == "evt_1_1"

    def test_recent_events_window(self):
        """Test that recent_events maintains a 20-event window."""
        memory = SessionMemory(
            session_id="sess_001",
            campaign_id="camp_001"
        )

        # Add 25 events
        for i in range(25):
            event = EventNode(
                event_id=f"evt_1_{i}",
                turn_number=1,
                phase="action_resolution",
                scene_context="dungeon"
            )
            memory.add_event(event)

        # recent_events should only keep last 20
        assert len(memory.recent_events) == 20
        # But campaign chronicle keeps all
        assert len(memory.campaign_chronicle) == 25

    def test_context_window_retrieval(self):
        """Test getting context window for LLM."""
        memory = SessionMemory(
            session_id="sess_001",
            campaign_id="camp_001"
        )

        for i in range(10):
            event = EventNode(
                event_id=f"evt_1_{i}",
                turn_number=1,
                phase="action_resolution",
                scene_context="dungeon"
            )
            memory.add_event(event)

        context = memory.get_context_window(lookback=5)
        assert len(context) == 5
        assert context[-1].event_id == "evt_1_9"


class TestPacingMetrics:
    """Test narrative pacing metrics."""

    def test_pacing_initialization(self):
        """Test creating pacing metrics."""
        pacing = PacingMetrics()

        assert pacing.turns_in_current_scene == 0
        assert 0.0 <= pacing.current_tension <= 1.0
        assert 0.0 <= pacing.player_agency_score <= 1.0

    def test_scene_transition_trigger(self):
        """Test when scene should transition based on turns."""
        pacing = PacingMetrics(max_turns_per_scene=5)
        pacing.turns_in_current_scene = 5

        assert pacing.should_transition_scene() is True

    def test_low_tension_scene_transition(self):
        """Test scene transition when tension drops too low."""
        pacing = PacingMetrics(max_turns_per_scene=20)
        pacing.turns_in_current_scene = 10
        pacing.current_tension = 0.1  # Very low

        assert pacing.should_transition_scene() is True

    def test_pacing_recommendations(self):
        """Test getting pacing recommendations."""
        pacing = PacingMetrics()

        pacing.current_tension = 0.9
        assert pacing.get_recommended_pacing() == "HIGH_INTENSITY"

        pacing.current_tension = 0.5
        assert pacing.get_recommended_pacing() == "NORMAL"

        pacing.current_tension = 0.1
        assert pacing.get_recommended_pacing() == "LOW_INTENSITY"


class TestGameplayPhaseState:
    """Test complete gameplay phase state."""

    def test_gameplay_state_creation(self):
        """Test creating gameplay state."""
        memory = SessionMemory(
            session_id="sess_001",
            campaign_id="camp_001"
        )
        state = GameplayPhaseState(
            session_memory=memory,
            turn_number=1
        )

        assert state.turn_number == 1
        assert state.session_memory.session_id == "sess_001"

    def test_log_event_in_state(self):
        """Test logging an event in gameplay state."""
        memory = SessionMemory(
            session_id="sess_001",
            campaign_id="camp_001"
        )
        state = GameplayPhaseState(
            session_memory=memory,
            turn_number=1
        )

        token = ActionOutcomeToken(
            action_id="act_001",
            performer_id="player_1",
            intent_type=ActionIntentType.ATTACK,
            status=ActionResolutionStatus.RESOLVED,
            primary_roll=RollResult(
                dice_type="d20",
                rolls=[14],
                modifier=2,
                total=16
            ),
            difficulty_class=12,
            meets_dc=True,
            mechanical_summary="Attack",
            effectiveness=0.8,
            is_valid=True
        )

        event = state.log_event(
            performer_id="player_1",
            action_intent=ActionIntentType.ATTACK,
            outcome_token=token,
            state_changes=[],
            npc_reactions={},
            scene_context="dungeon"
        )

        assert len(state.session_memory.recent_events) == 1
        assert event.performer_id == "player_1"


class TestGameplayExecutor:
    """Test the gameplay executor."""

    def test_executor_initialization(self):
        """Test initializing the gameplay executor."""
        executor = GameplayExecutor()
        assert executor.gameplay_state is None

    def test_initialize_gameplay_phase(self):
        """Test initializing Phase 3 state."""
        executor = GameplayExecutor()
        game_state = GameState(
            user_prompt="",
            setting=Setting(),
            narrative=None,
            world=None,
            players=[],
            actions=[],
            combat=None,
            rules_context=MagicMock(),
            emergence_metrics=MagicMock(),
            director_directives=None,
            messages=[],
            metadata={},
            current_action=None,
            last_outcome=None,
            last_verdict=None,
            response_type="unknown",
            __end__=False,
            action_suggestions=[]
        )

        state = executor.initialize_gameplay_phase(
            game_state,
            campaign_id="camp_001",
            session_id="sess_001"
        )

        assert state.session_memory.campaign_id == "camp_001"
        assert state.session_memory.session_id == "sess_001"
        assert state.turn_number == 0

    def test_classify_intent(self):
        """Test action intent classification."""
        executor = GameplayExecutor()

        assert executor._classify_intent("attack the goblin") == ActionIntentType.ATTACK
        assert executor._classify_intent("cast fireball spell") == ActionIntentType.CAST_SPELL
        assert executor._classify_intent("talk to the merchant") == ActionIntentType.DIALOGUE
        assert executor._classify_intent("search the room") == ActionIntentType.INVESTIGATE
        assert executor._classify_intent("move forward") == ActionIntentType.MOVE
        assert executor._classify_intent("block the attack") == ActionIntentType.DEFEND

    def test_generate_roll_for_intent(self):
        """Test generating D&D rolls."""
        executor = GameplayExecutor()

        game_state = GameState(
            user_prompt="",
            setting=Setting(),
            narrative=None,
            world=None,
            players=[
                Player(
                    id="player_1",
                    name="Hero",
                    class_name="Fighter",
                    race="Human",
                    background="Soldier",
                    level=1,
                    stats=DnDCharacterStats(
                        strength=15,
                        intelligence=10,
                        wisdom=12,
                        charisma=10
                    ),
                    backstory="A brave warrior",
                    motivation="Save the kingdom",
                    location_id="loc_1"
                )
            ],
            actions=[],
            combat=None,
            rules_context=MagicMock(),
            emergence_metrics=MagicMock(),
            director_directives=None,
            messages=[],
            metadata={},
            current_action=None,
            last_outcome=None,
            last_verdict=None,
            response_type="unknown",
            __end__=False,
            action_suggestions=[]
        )

        # Test attack roll (uses STR)
        roll = executor._generate_roll_for_intent(
            ActionIntentType.ATTACK,
            game_state,
            "player_1"
        )

        assert roll.dice_type == "d20"
        assert 1 <= roll.rolls[0] <= 20
        assert roll.modifier == 2  # (15-10)//2
        assert 3 <= roll.total <= 22

    def test_outcome_token_validation(self):
        """Test action outcome validation."""
        token = ActionOutcomeToken(
            action_id="act_001",
            performer_id="player_1",
            intent_type=ActionIntentType.ATTACK,
            status=ActionResolutionStatus.RESOLVED,
            primary_roll=RollResult(
                dice_type="d20",
                rolls=[15],
                modifier=3,
                total=18
            ),
            difficulty_class=10,
            meets_dc=True,
            mechanical_summary="Attack hits",
            effectiveness=0.9,
            is_valid=True
        )

        assert token.is_valid is True
        assert token.meets_dc is True
        assert len(token.rule_violations) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
