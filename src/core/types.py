from typing import TypedDict, Annotated, List, Dict, Optional, Any
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage
import operator
import uuid

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


# --- NEW: DnD-Specific Stats ---
class DnDCharacterStats(BaseModel):
    # Ability Scores
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    # Derived Stats (Examples - calculated based on class/level/abilities)
    armor_class: int = 10
    initiative: int = 0
    speed: int = 30
    max_hit_points: int = 10
    current_hit_points: int = 10
    temporary_hit_points: int = 0
    hit_dice: str = "1d8"
    hit_dice_remaining: int = 1

    # Saving Throws (Example fields - typically tied to class/abilities)
    saving_throw_strength: int = 0
    saving_throw_dexterity: int = 0
    saving_throw_constitution: int = 0
    saving_throw_intelligence: int = 0
    saving_throw_wisdom: int = 0
    saving_throw_charisma: int = 0

    # Skills (Example - typically tied to class/abilities/proficiencies)
    skills: Dict[str, int] = Field(default_factory=dict) # {"Perception": +5, ...}

    # Spellcasting (Examples)
    spell_save_dc: int = 0
    spell_attack_bonus: int = 0

    # Proficiency Bonus
    proficiency_bonus: int = 2 # Level 1 default


# --- NEW: SVO and Storyteller Structures ---
class SVOEvent(BaseModel):
    subject: str # Who or what performs the action
    verb: str    # The action itself (e.g., "attacks", "discovers", "destroys")
    object: str  # What is affected by the action (e.g., "the dragon", "the secret", "the village")


class PlotNode(BaseModel):
    id: str
    title: str
    description: str
    svo_event: SVOEvent
    follows_node: Optional[str] = None # ID of the previous node
    leads_to_node: Optional[str] = None # ID of the next node
    required_entities: List[str] = Field(default_factory=list) # Entities needed for this beat
    resulting_entities: List[str] = Field(default_factory=list) # Entities created/changed by this beat
    tags: List[str] = Field(default_factory=list) # e.g., "setup", "climax", "resolution"


class NarrativeEntity(BaseModel):
    id: str
    name: str
    type: str # e.g., "character", "location", "item", "concept"
    core_description: str
    mutable_attributes: Dict[str, Any] = Field(default_factory=dict) # e.g., {"health": 50, "location": "room1"}
    relationships: Dict[str, List[str]] = Field(default_factory=dict) # e.g., {"allies": ["npc_john"], "possesses": ["item_sword"]}


class Storyline(BaseModel):
    nodes: List[PlotNode] = Field(default_factory=list)
    current_phase: str = "Act I"


# --- Updated Player Model ---
class Player(BaseModel):
    id: str
    name: str
    class_name: str # D&D Class (e.g., 'Fighter', 'Wizard')
    race: str       # D&D Race (e.g., 'Human', 'Elf')
    background: str # D&D Background (e.g., 'Acolyte', 'Outlander')
    level: int = 1
    stats: DnDCharacterStats # Use the new DnD stats

    # Narrative Hooks
    backstory: str = Field(description="Short history relative to the campaign setting")
    motivation: str = Field(description="Why they are adventuring")
    location_id: str = Field(description="ID of the location where they start")

    # State
    is_active: bool = True
    conditions: List[str] = Field(default_factory=list)


# --- Updated Action Model ---
class Action(BaseModel):
    player_id: str
    type: str # Changed from 'action_type' to match agent code
    description: str
    timestamp: str
    result: str | None = None


class CombatState(BaseModel):
    active: bool
    initiative_order: list[str]
    current_turn: str
    round_number: int


class NarrativeState(BaseModel):
    title: str = ""
    tagline: str = ""
    story_arc_summary: str = Field(description="High-level summary of the entire campaign")
    # Use the new Storyline structure
    storyline: Storyline = Field(default_factory=Storyline)
    # Use the new NarrativeEntity structure
    narrative_entities: Dict[str, NarrativeEntity] = Field(default_factory=dict)
    major_factions: List[str] = Field(default_factory=list)
    narrative_tension: float = 0.0
    current_scene: str = "intro"
    # completed_beats can be derived from storyline.nodes if needed


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


# --- Updated WorldState Model ---
class WorldState(BaseModel):
    # Lore (Static)
    overview: str = ""
    regions: List[Region] = Field(default_factory=list)
    cultures: List[Culture] = Field(default_factory=list)
    history: Optional[WorldHistory] = None
    # Added field for initial entities
    important_npcs: List[KeyNPC] = Field(default_factory=list)

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


# --- Updated CampaignBlueprint for StoryArchitect ---
class CampaignBlueprint(BaseModel):
    title: str = Field(description="The campaign title")
    tagline: str = Field(description="A short, punchy tagline")
    overview: str = Field(description="The high-level story summary (Acts I-III)")
    storyline: Storyline = Field(default_factory=Storyline, description="The structured sequence of key plot points using SVO events.")
    initial_entities: List[NarrativeEntity] = Field(default_factory=list, description="Initial Narrative Entities and their starting states.")


class GameState(TypedDict):
    user_prompt: str
    setting: Setting
    narrative: NarrativeState
    world: WorldState
    # 增加operator.add防止角色相互覆盖
    players: Annotated[List[Player], operator.add]

    actions: List[Action]
    combat: CombatState | None
    rules_context: RulesContext
    emergence_metrics: EmergenceMetrics
    director_directives: Optional[DirectorDirectives]
    messages: Annotated[list[BaseMessage], add_messages]
    metadata: dict
    # Add fields potentially used by agents
    current_action: Optional[Action]
    last_outcome: Optional[dict] # Or specific outcome type if defined
    last_verdict: Optional[JudgeVerdict]
    response_type: str # Added for DM Planner routing