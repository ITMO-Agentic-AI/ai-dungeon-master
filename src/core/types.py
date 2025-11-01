from typing import TypedDict, Annotated
from pydantic import BaseModel
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class Player(BaseModel):
    id: str
    name: str
    class_type: str
    level: int
    stats: dict
    inventory: list[str]
    current_hp: int
    max_hp: int


class Location(BaseModel):
    id: str
    name: str
    description: str
    npcs: list[str]
    connections: list[str]


class Action(BaseModel):
    player_id: str
    action_type: str
    description: str
    timestamp: str
    result: str | None = None


class CombatState(BaseModel):
    active: bool
    initiative_order: list[str]
    current_turn: str
    round_number: int


class WorldState(BaseModel):
    current_location: str
    time_of_day: str
    weather: str
    active_quests: list[str]
    world_events: list[str]


class NarrativeState(BaseModel):
    story_arc: str
    current_scene: str
    story_beats: list[str]
    narrative_tension: float
    completed_beats: list[str]


class RulesContext(BaseModel):
    active_rules: list[str]
    violations: list[str]
    clarifications_needed: list[str]


class EmergenceMetrics(BaseModel):
    player_agency: float
    narrative_coherence: float
    pacing_score: float
    engagement_level: float


class GameState(TypedDict):
    narrative: NarrativeState
    world: WorldState
    players: list[Player]
    actions: list[Action]
    combat: CombatState | None
    rules_context: RulesContext
    emergence_metrics: EmergenceMetrics
    messages: Annotated[list[BaseMessage], add_messages]
    metadata: dict
