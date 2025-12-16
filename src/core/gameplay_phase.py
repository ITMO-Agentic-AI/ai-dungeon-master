"""Phase 3: Gameplay Loop - Interactive Execution Stage.

This module defines the structured gameplay loop that transforms player actions into
dynamic, reactive storytelling. Each turn follows a 7-step sequence combining autonomy,
rule adjudication, world evolution, and narrative description.

Step 1: Player Action Generation
Step 2: Action Validation & Rule Adjudication
Step 3: Environment & Lore Update
Step 4: Narrative Description & Dialogue
Step 5: Director Oversight & Pacing
Step 6: Event Recording & Memory Sync
Step 7: Loop Iteration & Scene Transition
"""

from typing import Any
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ActionIntentType(str, Enum):
    """Categories of player intent."""
    ATTACK = "attack"
    DEFEND = "defend"
    CAST_SPELL = "cast_spell"
    SKILL_CHECK = "skill_check"
    INTERACT = "interact"
    DIALOGUE = "dialogue"
    INVESTIGATE = "investigate"
    MOVE = "move"
    HELP = "help"
    DODGE = "dodge"
    COUNTER = "counter"
    UNKNOWN = "unknown"


class ActionResolutionStatus(str, Enum):
    """Status of action resolution."""
    PENDING = "pending"
    VALIDATED = "validated"
    RESOLVED = "resolved"
    FAILED = "failed"
    CRITICAL_HIT = "critical_hit"
    CRITICAL_FAIL = "critical_fail"


class RollResult(BaseModel):
    """Result of a single D&D roll."""
    dice_type: str = Field(description="e.g., 'd20', 'd12', 'd4'")
    rolls: list[int] = Field(description="Individual roll values")
    modifier: int = Field(default=0, description="Ability modifier or bonus")
    total: int = Field(description="Sum of rolls + modifier")
    is_advantage: bool = Field(default=False, description="Advantage/disadvantage applied")
    is_disadvantage: bool = Field(default=False, description="Disadvantage applied")


class ActionOutcomeToken(BaseModel):
    """Resolved mechanical outcome of an action."""
    action_id: str
    performer_id: str
    intent_type: ActionIntentType
    status: ActionResolutionStatus
    
    # Roll data
    primary_roll: RollResult | None = None
    secondary_rolls: list[RollResult] = Field(default_factory=list)
    
    # Mechanics
    difficulty_class: int | None = None
    meets_dc: bool | None = None
    damage_dealt: int = 0
    healing_received: int = 0
    
    # Narrative
    mechanical_summary: str = Field(description="Dry outcome summary")
    effectiveness: float = Field(description="0.0 (total fail) to 1.0 (critical success)")
    
    # Validation
    rule_violations: list[str] = Field(default_factory=list)
    is_valid: bool = True
    
    # Timestamp
    resolved_at: datetime = Field(default_factory=datetime.utcnow)


class WorldStateChange(BaseModel):
    """Single atomic change to world state."""
    change_type: str = Field(description="e.g., 'health', 'inventory', 'location', 'npc_attitude'")
    target_id: str = Field(description="Character, NPC, item, or location ID")
    old_value: Any
    new_value: Any
    reason: str = Field(description="Why this change occurred")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EventNode(BaseModel):
    """Canonical event record in the game chronicle."""
    event_id: str = Field(description="Unique identifier for this event")
    turn_number: int
    phase: str = Field(description="Which step of the loop (e.g., 'action', 'resolution', 'narration')")
    
    # What happened
    performer_id: str | None = None
    action_intent: ActionIntentType | None = None
    outcome_token: ActionOutcomeToken | None = None
    
    # State changes
    state_changes: list[WorldStateChange] = Field(default_factory=list)
    
    # Narrative context
    scene_context: str = Field(default="", description="Where/when this occurred")
    npc_reactions: dict[str, str] = Field(default_factory=dict, description="NPC ID -> reaction text")
    
    # Continuity
    triggered_by_event_id: str | None = None
    triggers_next_events: list[str] = Field(default_factory=list)
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SessionMemory(BaseModel):
    """Dual-layer memory structure for session and campaign continuity."""
    # Short-term: Current session
    session_id: str
    session_start: datetime
    current_turn: int = 0
    recent_events: list[EventNode] = Field(
        default_factory=list,
        description="Last 10-20 events for context window"
    )
    scene_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Current scene variables (lights on/off, door locked, etc.)"
    )
    
    # Long-term: Campaign continuity
    campaign_id: str
    campaign_chronicle: list[EventNode] = Field(
        default_factory=list,
        description="Complete record of all events this campaign"
    )
    character_development_log: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Character ID -> list of narrative/mechanical milestones"
    )
    
    def add_event(self, event: EventNode, preserve_history: bool = True) -> None:
        """Record an event in both short and long-term memory."""
        self.recent_events.append(event)
        # Keep only recent 20 in short-term window
        if len(self.recent_events) > 20:
            self.recent_events = self.recent_events[-20:]
        
        if preserve_history:
            self.campaign_chronicle.append(event)
    
    def get_context_window(self, lookback: int = 5) -> list[EventNode]:
        """Retrieve last N events for LLM context."""
        return self.recent_events[-lookback:] if self.recent_events else []


class PacingMetrics(BaseModel):
    """Real-time tracking of narrative pacing and rhythm."""
    turns_in_current_scene: int = 0
    max_turns_per_scene: int = 10
    
    # Tension tracking
    base_tension: float = 0.5
    current_tension: float = 0.5
    tension_trajectory: list[float] = Field(default_factory=list)
    
    # Engagement
    player_agency_score: float = 0.5  # 0.0 = no choices, 1.0 = full agency
    outcome_unpredictability: float = 0.5  # 0.0 = deterministic, 1.0 = random
    
    # Scene metrics
    combat_turns: int = 0
    dialogue_turns: int = 0
    exploration_turns: int = 0
    
    def should_transition_scene(self) -> bool:
        """Determine if scene should end based on pacing."""
        return (
            self.turns_in_current_scene >= self.max_turns_per_scene
            or (self.turns_in_current_scene > 5 and self.current_tension < 0.2)
        )
    
    def get_recommended_pacing(self) -> str:
        """Suggest pacing adjustment to Director."""
        if self.current_tension > 0.8:
            return "HIGH_INTENSITY"
        elif self.current_tension > 0.6:
            return "ESCALATING"
        elif self.current_tension > 0.4:
            return "NORMAL"
        elif self.current_tension > 0.2:
            return "DESCENDING"
        else:
            return "LOW_INTENSITY"


class SceneTransitionTrigger(BaseModel):
    """Condition that triggers scene or beat transition."""
    trigger_type: str = Field(description="e.g., 'victory', 'failure', 'resolution', 'time_limit'")
    condition_met: bool
    reason: str
    next_scene_id: str | None = None
    fallback_scene_id: str | None = None


class GameplayPhaseState(BaseModel):
    """Complete snapshot of Phase 3 state (extends GameState during gameplay)."""
    # Memories and logs
    session_memory: SessionMemory
    
    # Current turn state
    turn_number: int
    player_actions: list[dict] = Field(
        default_factory=list,
        description="Actions taken this turn"
    )
    outcome_tokens: list[ActionOutcomeToken] = Field(default_factory=list)
    world_state_deltas: list[WorldStateChange] = Field(default_factory=list)
    
    # Pacing & narrative flow
    pacing: PacingMetrics = Field(default_factory=PacingMetrics)
    scene_transitions: list[SceneTransitionTrigger] = Field(default_factory=list)
    
    # Current DM directives (from Director Agent)
    dm_directives: dict[str, Any] = Field(
        default_factory=dict,
        description="Tone, emphasis, next beat, NPC cues from Director"
    )
    
    def log_event(
        self,
        performer_id: str | None,
        action_intent: ActionIntentType,
        outcome_token: ActionOutcomeToken | None,
        state_changes: list[WorldStateChange],
        npc_reactions: dict[str, str],
        scene_context: str
    ) -> EventNode:
        """Create and record a new event in the chronicle."""
        event = EventNode(
            event_id=f"evt_{self.turn_number}_{len(self.session_memory.recent_events)}",
            turn_number=self.turn_number,
            phase="gameplay",
            performer_id=performer_id,
            action_intent=action_intent,
            outcome_token=outcome_token,
            state_changes=state_changes,
            scene_context=scene_context,
            npc_reactions=npc_reactions
        )
        self.session_memory.add_event(event)
        return event
