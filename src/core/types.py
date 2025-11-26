from typing import TypedDict, Annotated, List, Dict, Optional, Any
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class Setting(BaseModel):
    story_length: int = 2000
    story_arc_count: int = 3
    theme: str = "D&D Adventure"
    player_concepts: List[str] = Field(default_factory=lambda: ["Adventurers"])
    difficulty: str = "Normal"


class KeyNPC(BaseModel):
    name: str
    role: str = Field(description="Role in society or story (e.g., 'High Priest', 'Rebel Leader')")
    region: str = Field(description="The region where this NPC is primarily located")
    motivation: str
    connection_to_plot: str = Field(description="How this NPC relates to the main story arcs")


class Region(BaseModel):
    name: str
    description: str
    dominant_factions: List[str]
    key_landmarks: List[str] = Field(description="Notable locations within this region")
    environmental_hook: str = Field(description="Unique feature (e.g., 'Always raining', 'Floating islands')")


class Culture(BaseModel):
    name: str
    values: List[str]
    social_structure: str
    conflicts: str = Field(description="Major conflicts with other groups or internal struggles")


class WorldHistory(BaseModel):
    major_event: str = Field(description="A myth or legend that shapes the current era")
    unresolved_mystery: str = Field(description="A prophecy or secret for the players to discover")


class RPGStats(BaseModel):
    strength: int = 10
    dexterity: int = 10
    intelligence: int = 10
    charisma: int = 10
    constitution: int = 10
    wisdom: int = 10


class Player(BaseModel):
    id: str
    name: str
    archetype: str = Field(description="Class or Role (e.g., 'Rogue', 'Technomancer')")
    level: int = 1
    stats: RPGStats
    current_hp: int
    max_hp: int
    inventory: List[str] = Field(default_factory=list)
    
    # Narrative Hooks
    backstory: str = Field(description="Short history relative to the campaign setting")
    motivation: str = Field(description="Why they are adventuring")
    location_id: str = Field(description="ID of the location where they start")
    
    # State
    is_active: bool = True


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


class WorldDescription(BaseModel):
    world_overview: str
    regions: str
    cultures: str
    backstory: str
    key_NPCs: list[str]
    connectivity: str


class NarrativeState(BaseModel):
    title: str = ""
    tagline: str = ""
    story_arc_summary: str = Field(description="High-level summary of the entire campaign")
    story_beats: List[str] = Field(description="Key plot points or milestones")
    major_factions: List[str] = Field(description="Key groups or antagonists introduced")
    narrative_tension: float = 0.0
    current_scene: str = "intro"
    completed_beats: List[str] = Field(default_factory=list)


class LocationNode(BaseModel):
    id: str = Field(description="Unique ID (e.g., 'loc_village_square')")
    name: str
    region_name: str = Field(description="The parent region this location belongs to")
    description: str = Field(description="Immersive description for the player")
    connected_ids: List[str] = Field(default_factory=list, description="IDs of locations accessible from here")
    npc_ids: List[str] = Field(default_factory=list, description="IDs of NPCs currently here")
    clues: List[str] = Field(default_factory=list, description="Discoverable info or items")


class ActiveNPC(BaseModel):
    id: str
    base_data: KeyNPC  # Reference to the static Lore data
    current_location_id: str
    status: str = "alive"
    current_activity: str = "idle"


class EvaluationMetrics(BaseModel):
    narrative_consistency: float = Field(description="Score 0.0-1.0. Does this fit previous lore?")
    player_agency: float = Field(description="Score 0.0-1.0. Did the player's choice matter?")
    rule_adherence: float = Field(description="Score 0.0-1.0. Did the mechanics work correctly?")
    safety_score: float = Field(description="Score 0.0-1.0. Is the content appropriate?")
    feedback: str = Field(description="Constructive feedback for the system/DM")


class JudgeVerdict(BaseModel):
    is_valid: bool = Field(description="If False, the last action/outcome should be regenerated")
    metrics: EvaluationMetrics
    correction_suggestion: Optional[str] = Field(description="How to fix the error if invalid")


class DirectorDirectives(BaseModel):
    narrative_focus: str = Field(description="What the DM should emphasize (e.g., 'Horror', 'Discovery')")
    tension_adjustment: float = Field(description="New tension level (0.0 to 1.0)")
    next_beat: str = Field(description="The specific plot point to steer towards")
    npc_instructions: List[str] = Field(default_factory=list, description="Specific cues for NPCs")


class WorldState(BaseModel):
    # Lore (Static)
    overview: str = ""
    regions: List[Region] = Field(default_factory=list)
    cultures: List[Culture] = Field(default_factory=list)
    history: Optional[WorldHistory] = None
    
    # Simulation (Dynamic)
    locations: Dict[str, LocationNode] = Field(default_factory=dict)
    active_npcs: Dict[str, ActiveNPC] = Field(default_factory=dict)
    global_time: int = 0  # Turn counter
    
    def get_location(self, loc_id: str) -> Optional[LocationNode]:
        return self.locations.get(loc_id)


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
    user_prompt: str
    setting: Setting
    narrative: NarrativeState
    world: WorldState
    players: List[Player]
    actions: List[Action]
    combat: CombatState | None
    rules_context: RulesContext
    emergence_metrics: EmergenceMetrics
    director_directives: Optional[DirectorDirectives]
    messages: Annotated[list[BaseMessage], add_messages]
    metadata: dict  
