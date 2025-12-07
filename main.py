import asyncio
import sys
from datetime import datetime
from src.core.types import (
    GameState,
    NarrativeState,
    WorldState,
    RulesContext,
    EmergenceMetrics,
    Storyline,
    Action,
    Setting,
)
from src.services.orchestrator_service import orchestrator_service
from src.core.config import get_settings


async def initialize_game_state() -> GameState:
    # Create an initial, empty storyline
    initial_storyline = Storyline(nodes=[], current_phase="Intro")

    # Create initial narrative state using the new structure
    initial_narrative = NarrativeState(
        title="The Lost Temple of Azurath",
        tagline="Adventurers seek an ancient, forgotten shrine.",
        story_arc_summary="The adventurers search for the lost temple of Azurath, facing trials and uncovering its secrets.",
        storyline=initial_storyline,  # Use the new storyline
        narrative_entities={},  # Start with no dynamic entities
        major_factions=["The Cult of Azurath", "The Order of the Dawn"],
        narrative_tension=0.3,
        current_scene="The adventurers gather at the Rusty Dragon tavern",
        # completed_beats is handled by storyline now
    )

    # Create initial world state using the new structure
    initial_world = WorldState(
        # Lore (Static)
        overview="A world of adventure and mystery.",
        regions=[],  # Will be filled by LoreBuilder/WorldEngine
        cultures=[],  # Will be filled by LoreBuilder
        history=None,  # Will be filled by LoreBuilder
        important_npcs=[],  # Will be filled by LoreBuilder
        # Simulation (Dynamic)
        locations={},  # Will be filled by WorldEngine
        active_npcs={},  # Will be filled by WorldEngine
        global_time=0,  # Turn counter
    )

    # Initialize the GameState dictionary with the new structure
    return {
        "user_prompt": "Begin the adventure!",
        "setting": Setting(
            story_length=2000,
            story_arc_count=1,
            theme="Fantasy Exploration",
            player_concepts=["Rogue", "Wizard", "Fighter"],
            difficulty="Normal",
        ),
        "narrative": initial_narrative,
        "world": initial_world,
        "players": [],  # Will be filled by PlayerCreator
        "actions": [],  # Will be filled during gameplay
        "combat": None,  # Will be filled if combat starts
        "rules_context": RulesContext(active_rules=[], violations=[], clarifications_needed=[]),
        "emergence_metrics": EmergenceMetrics(
            player_agency=0.5, narrative_coherence=0.8, pacing_score=0.6, engagement_level=0.7
        ),
        "director_directives": None,  # Will be filled by Director
        "messages": [],  # Will be filled by DungeonMaster
        "metadata": {"session_id": datetime.now().isoformat(), "turn": 0},
        # Add fields potentially used by agents
        "current_action": None,  # Will be filled by user input or simulation
        "last_outcome": None,  # Will be filled by ActionResolver
        "last_verdict": None,  # Will be filled by RuleJudge
    }


def display_world_state(state: GameState):
    if not state["players"]:
        return

    player = state["players"][0]
    world = state["world"]
    location = world.locations.get(player.location_id) if hasattr(world, 'locations') else None
    
    print("\n" + "=" * 60)
    print(f"📍 LOCATION: {location.name if location else 'Unknown'}")
    print("=" * 60)
    
    if location:
        print(f"\n{location.description}")
        
        if location.npc_ids:
            npcs = [state["world"].active_npcs.get(npc_id) for npc_id in location.npc_ids]
            npc_names = [npc.base_data.name for npc in npcs if npc]
            if npc_names:
                print(f"\n👥 NPCs here: {', '.join(npc_names)}")
        
        if location.connected_ids:
            exits = []
            for loc_id in location.connected_ids:
                exit_loc = world.locations.get(loc_id)
                if exit_loc:
                    exits.append(exit_loc.name)
            if exits:
                print(f"\n🚪 Exits: {', '.join(exits)}")
        
        if location.clues:
            print(f"\n🔍 Clues: {', '.join(location.clues[:2])}")
    
    print(f"\n👤 {player.name} ({player.race} {player.class_name}, Level {player.level})")
    print(f"❤️  HP: {player.stats.current_hit_points}/{player.stats.max_hit_points}")
    print(f"⚔️  AC: {player.stats.armor_class}")
    print("=" * 60)


async def get_user_action(state: GameState) -> Action:
    player = state["players"][0]
    
    print("\nWhat do you do?")
    print("(Type your action, e.g., 'attack the goblin', 'search the room', 'move to the forest')")
    description = input("> ").strip()
    
    if not description:
        description = "look around"
    
    action_type = "other"
    desc_lower = description.lower()
    if any(word in desc_lower for word in ["attack", "hit", "strike", "fight"]):
        action_type = "attack"
    elif any(word in desc_lower for word in ["move", "go", "walk", "travel"]):
        action_type = "move"
    elif any(word in desc_lower for word in ["search", "investigate", "examine", "look"]):
        action_type = "investigate"
    elif any(word in desc_lower for word in ["talk", "speak", "say", "ask"]):
        action_type = "social"
    
    return Action(
        player_id=player.id,
        type=action_type,
        description=description,
        timestamp=datetime.now().isoformat()
    )


async def run_game_loop():
    settings = get_settings()

    print("=" * 60)
    print("AI DUNGEON MASTER")
    print("=" * 60)
    
    model_display = settings.custom_model_name if settings.custom_model_enabled else settings.model_name
    print(f"Model: {model_display}")
    print(f"Temperature: {settings.model_temperature}")

    print("=" * 60)

    state = await initialize_game_state()

    print("\n🎲 Initializing game world...")
    print("This may take a moment as the AI creates your adventure...\n")
    
    state = await orchestrator_service.initialize_world(state)

    print("\n✅ World Created!")
    print(f"\n📖 Campaign: {state['narrative'].title}")
    print(f"📝 {state['narrative'].tagline}")
    
    if state["players"]:
        print("\n👥 Your Characters:")
        for player in state["players"]:
            print(f"  • {player.name} - {player.race} {player.class_name}")
            print(f"    {player.motivation}")
    
    print("\n" + "=" * 60)
    print("ADVENTURE BEGINS")
    print("=" * 60)
    print("\n(Type 'quit' or press Ctrl+C to exit)\n")

    try:
        turn = 0
        while True:
            turn += 1
            state["metadata"]["turn"] = turn
            
            display_world_state(state)
            
            action = await get_user_action(state)
            if action.description.lower() in ["quit", "exit", "q"]:
                break
            
            state["current_action"] = action

            print("\n⚙️  Resolving action...")
            state = await orchestrator_service.execute_turn(state)

            if state.get("messages"):
                last_message = state["messages"][-1]
                print("\n" + "=" * 60)
                print("📜 DUNGEON MASTER")
                print("=" * 60)
                print(f"\n{last_message.content}\n")

    except KeyboardInterrupt:
        print("\n")
    
    print("\n" + "=" * 60)
    print("Game session ended.")
    print(f"Total turns: {turn}")
    print("=" * 60)


def main():
    try:
        asyncio.run(run_game_loop())
    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        print(f"\nError occurred: {e}")
        import traceback

        traceback.print_exc()  # Print the full traceback for debugging
        sys.exit(1)


if __name__ == "__main__":
    main()
