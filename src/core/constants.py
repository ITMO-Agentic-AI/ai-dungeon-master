from enum import Enum


class AgentType(str, Enum):
    STORY_ARCHITECT = "story_architect"
    DUNGEON_MASTER = "dungeon_master"
    PLAYER_PROXY = "player_proxy"
    WORLD_ENGINE = "world_engine"
    ACTION_RESOLVER = "action_resolver"
    DIRECTOR = "director"
    LORE_BUILDER = "lore_builder"
    RULE_JUDGE = "rule_judge"


class ActionType(str, Enum):
    MOVE = "move"
    ATTACK = "attack"
    CAST_SPELL = "cast_spell"
    USE_ITEM = "use_item"
    INTERACT = "interact"
    DIALOGUE = "dialogue"


class DiceType(str, Enum):
    D4 = "d4"
    D6 = "d6"
    D8 = "d8"
    D10 = "d10"
    D12 = "d12"
    D20 = "d20"
    D100 = "d100"
