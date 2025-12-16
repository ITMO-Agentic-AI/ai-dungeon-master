"""Agent Specialization Context - Dynamic adaptation of agent behavior based on game state."""

from enum import Enum
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class GamePhase(str, Enum):
    """Game phases for narrative structure."""

    SETUP = "setup"
    EXPLORATION = "exploration"
    CONFLICT = "conflict"
    CLIMAX = "climax"
    RESOLUTION = "resolution"


class NarrativePace(str, Enum):
    """Narrative pacing levels."""

    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"
    CLIMACTIC = "climactic"


class SpecializationContext:
    """Provides context about how agents should adapt their behavior."""

    def __init__(self, state: Any):
        """Initialize specialization context from game state.

        Args:
            state: GameState object
        """
        self.game_phase = self._determine_phase(state)
        self.narrative_pace = self._determine_pace(state)
        self.tension_level = self._calculate_tension(state)
        self.player_engagement = self._assess_engagement(state)
        self.discovery_state = self._analyze_discoveries(state)
        logger.debug(
            f"SpecializationContext: {self.game_phase.value} phase, "
            f"pace={self.narrative_pace.value}, tension={self.tension_level:.1%}"
        )

    def _determine_phase(self, state: Any) -> GamePhase:
        """Determine where we are in the story.

        Args:
            state: GameState object

        Returns:
            Current game phase
        """
        turn = state.get("metadata", {}).get("turn", 0)

        if turn < 3:
            return GamePhase.SETUP
        elif turn < 10:
            return GamePhase.EXPLORATION
        elif turn < 20:
            return GamePhase.CONFLICT
        elif turn < 30:
            return GamePhase.CLIMAX
        else:
            return GamePhase.RESOLUTION

    def _determine_pace(self, state: Any) -> NarrativePace:
        """Adjust pacing based on tension.

        Args:
            state: GameState object

        Returns:
            Appropriate narrative pace
        """
        tension = self._calculate_tension(state)

        if tension > 0.8:
            return NarrativePace.CLIMACTIC
        elif tension > 0.6:
            return NarrativePace.FAST
        elif tension > 0.3:
            return NarrativePace.NORMAL
        else:
            return NarrativePace.SLOW

    def _calculate_tension(self, state: Any) -> float:
        """Calculate narrative tension (0-1).

        Args:
            state: GameState object

        Returns:
            Tension level from 0 to 1
        """
        tension = 0.0

        # Tension increases with turn count
        turn = state.get("metadata", {}).get("turn", 0)
        tension += min(turn / 50, 0.3)

        # Player HP status
        players = state.get("players", [])
        if players:
            total_hp_ratio = 0
            for p in players:
                current_hp = getattr(p, "hp", 100)
                max_hp = getattr(p, "max_hp", 100)
                if max_hp > 0:
                    total_hp_ratio += current_hp / max_hp

            avg_hp_pct = total_hp_ratio / len(players)
            if avg_hp_pct < 0.3:
                tension += 0.3
            elif avg_hp_pct < 0.5:
                tension += 0.15

        # Recent combat/danger
        recent_outcomes = state.get("last_outcome")
        if recent_outcomes:
            outcome_str = str(recent_outcomes).lower()
            if any(
                word in outcome_str
                for word in ["danger", "combat", "attack", "enemy"]
            ):
                tension += 0.2

        return min(tension, 1.0)

    def _assess_engagement(self, state: Any) -> float:
        """Assess player engagement (0-1).

        Args:
            state: GameState object

        Returns:
            Engagement level from 0 to 1
        """
        # Could track: character deaths, choices made, dialogue length, etc.
        # For now, use default
        return 0.7

    def _analyze_discoveries(self, state: Any) -> Dict[str, bool]:
        """Track what player has discovered.

        Args:
            state: GameState object

        Returns:
            Dictionary of discoveries
        """
        discoveries = {
            "main_antagonist_known": False,
            "goal_known": False,
            "twist_discovered": False,
            "all_major_npcs_met": False,
        }
        # Populate from state if available
        # This could be enhanced with actual tracking
        return discoveries

    def get_specialization_prompt(self, agent_type: str) -> str:
        """Generate role adaptation prompt for agent.

        Args:
            agent_type: Type of agent (dungeon_master, action_resolver, etc.)

        Returns:
            Specialization guidance prompt
        """
        phase_guidance = self._get_phase_guidance()
        pace_guidance = self._get_pace_guidance()
        tension_guidance = self._get_tension_guidance()

        prompts = {
            "dungeon_master": f"""
You are narrating in the {self.game_phase.value} phase of the story.
Narrative pace should be {self.narrative_pace.value}.
Current tension level: {self.tension_level:.0%}

Adapt your narration:
- Phase {self.game_phase.value}: {phase_guidance}
- Pace {self.narrative_pace.value}: {pace_guidance}
- Tension: {tension_guidance}

Keep descriptions vivid but appropriate to the current moment.
""",
            "action_resolver": f"""
You are resolving actions in {self.game_phase.value} phase.
Consequences should match tension level: {self.tension_level:.0%}

Adjust difficulty and consequences:
- Low tension: More forgiving, exploratory outcomes
- High tension: Higher consequences, permanent effects
- Current tension: {self.tension_level:.0%}

Make rolls meaningful but fair.
""",
            "director": f"""
You are directing pacing in {self.game_phase.value} phase.
Player engagement: {self.player_engagement:.0%}

Recommendations:
- Discoveries made: {sum(self.discovery_state.values())}/4
- Suggest events matching the {self.game_phase.value} phase
- Maintain engagement at {self.player_engagement:.0%}
- Current tension: {tension_guidance}
""",
        }

        return prompts.get(agent_type, "")

    def _get_phase_guidance(self) -> str:
        """Get guidance for current game phase.

        Returns:
            Phase-specific guidance text
        """
        guidance = {
            GamePhase.SETUP: "Introduce world, NPCs, initial hooks. Build atmosphere and context.",
            GamePhase.EXPLORATION: "Encourage discovery. Present mysteries, secrets, and meaningful choices.",
            GamePhase.CONFLICT: "Escalate stakes. Make consequences matter. Show costs of actions.",
            GamePhase.CLIMAX: "Maximum tension. Important choices have permanent effects. Build to crescendo.",
            GamePhase.RESOLUTION: "Wrap up threads. Show consequences of all actions. Provide closure.",
        }
        return guidance.get(self.game_phase, "")

    def _get_pace_guidance(self) -> str:
        """Get guidance for narrative pace.

        Returns:
            Pace-specific guidance text
        """
        guidance = {
            NarrativePace.SLOW: "Detailed descriptions, long dialogue exchanges. Let players breathe and explore.",
            NarrativePace.NORMAL: "Balanced narration with good flow. Mix action and dialogue naturally.",
            NarrativePace.FAST: "Quick descriptions, rapid events, mounting pressure. Keep momentum.",
            NarrativePace.CLIMACTIC: "Intense action, critical moments, immediate consequences. No time to waste.",
        }
        return guidance.get(self.narrative_pace, "")

    def _get_tension_guidance(self) -> str:
        """Get guidance based on tension level.

        Returns:
            Tension-specific guidance text
        """
        if self.tension_level < 0.2:
            return "Low: Focus on exploration, character development, and world building"
        elif self.tension_level < 0.5:
            return "Moderate: Balance opportunity and danger. Most rolls matter."
        elif self.tension_level < 0.8:
            return "High: Most rolls have significant impact. Failures hurt."
        else:
            return "Critical: Every action is critical. Consequences are immediate and permanent."

    def to_dict(self) -> Dict[str, Any]:
        """Export context as dictionary.

        Returns:
            Dictionary representation of specialization context
        """
        return {
            "game_phase": self.game_phase.value,
            "narrative_pace": self.narrative_pace.value,
            "tension_level": self.tension_level,
            "player_engagement": self.player_engagement,
            "discovery_state": self.discovery_state,
        }
