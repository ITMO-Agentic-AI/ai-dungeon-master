import asyncio
import sys
from datetime import datetime
from src.core.types import GameState, NarrativeState, WorldState, RulesContext, EmergenceMetrics, Storyline
from src.services.orchestrator_service import orchestrator_service
from src.agents.story_architect.graph import StoryArchitectAgent
from src.agents.dungeon_master.graph import DungeonMasterAgent
from src.agents.director.graph import DirectorAgent
from src.core.config import get_settings


async def initialize_game_state() -> GameState:
    # Create an initial, empty storyline
    initial_storyline = Storyline(nodes=[], current_phase="Intro")
    
    # Create initial narrative state using the new structure
    initial_narrative = NarrativeState(
        title="The Lost Temple of Azurath",
        tagline="Adventurers seek an ancient, forgotten shrine.",
        story_arc_summary="The adventurers search for the lost temple of Azurath, facing trials and uncovering its secrets.",
        storyline=initial_storyline, # Use the new storyline
        narrative_entities={}, # Start with no dynamic entities
        major_factions=["The Cult of Azurath", "The Order of the Dawn"],
        narrative_tension=0.3,
        current_scene="The adventurers gather at the Rusty Dragon tavern"
        # completed_beats is handled by storyline now
    )
    
    # Create initial world state using the new structure
    initial_world = WorldState(
        # Lore (Static)
        overview="A world of adventure and mystery.",
        regions=[], # Will be filled by LoreBuilder/WorldEngine
        cultures=[], # Will be filled by LoreBuilder
        history=None, # Will be filled by LoreBuilder
        important_npcs=[], # Will be filled by LoreBuilder
        # Simulation (Dynamic)
        locations={}, # Will be filled by WorldEngine
        active_npcs={}, # Will be filled by WorldEngine
        global_time=0 # Turn counter
    )

    # Initialize the GameState dictionary with the new structure
    return {
        "user_prompt": "Begin the adventure!",
        "setting": {
            "story_length": 2000,
            "story_arc_count": 1,
            "theme": "Fantasy Exploration",
            "player_concepts": ["Rogue", "Wizard", "Fighter"], # Example concepts
            "difficulty": "Normal"
        },
        "narrative": initial_narrative,
        "world": initial_world,
        "players": [], # Will be filled by PlayerCreator
        "actions": [], # Will be filled during gameplay
        "combat": None, # Will be filled if combat starts
        "rules_context": RulesContext(
            active_rules=[],
            violations=[],
            clarifications_needed=[]
        ),
        "emergence_metrics": EmergenceMetrics(
            player_agency=0.5,
            narrative_coherence=0.8,
            pacing_score=0.6,
            engagement_level=0.7
        ),
        "director_directives": None, # Will be filled by Director
        "messages": [], # Will be filled by DungeonMaster
        "metadata": {"session_id": datetime.now().isoformat(), "turn": 0},
        # Add fields potentially used by agents
        "current_action": None, # Will be filled by user input or simulation
        "last_outcome": None, # Will be filled by ActionResolver
        "last_verdict": None # Will be filled by RuleJudge
    }


async def run_game_loop():
    settings = get_settings()
    
    print("=" * 60)
    print("AI DUNGEON MASTER - Game Orchestrator")
    print("=" * 60)
    print(f"Model: {settings.model_name if not settings.custom_model_enabled else settings.custom_model_name}")
    print(f"Temperature: {settings.model_temperature}")
    print("=" * 60)
    
    # Note: The orchestrator service now manages agent registration internally
    # No need to manually register agents here anymore
    # story_architect = StoryArchitectAgent()
    # dungeon_master = DungeonMasterAgent()
    # director = DirectorAgent()
    #
    # orchestrator_service.register_agent("story_architect", story_architect)
    # orchestrator_service.register_agent("dungeon_master", dungeon_master)
    # orchestrator_service.register_agent("director", director)
    
    state = await initialize_game_state()
    
    print("\nInitializing game session...")
    print(f"Story Arc: {state['narrative'].title}") # Updated field name
    # Note: Initial location might be 'unknown' until WorldEngine runs
    print(f"Starting Location: {state['world'].get('current_location', 'Not Set Yet - Will be set by WorldEngine')}")
    print("\nStarting game loop... (Press Ctrl+C to exit)\n")
    
    try:
        turn = 0
        while True:
            turn += 1
            print(f"\n{'='*60}")
            print(f"TURN {turn}")
            print(f"{'='*60}\n")
            
            state = await orchestrator_service.execute_turn(state)
            
            if state.get("messages"):
                last_message = state["messages"][-1]
                # Assuming last_message is an AIMessage or similar with 'content'
                print(f"\nDungeon Master: {last_message.content}\n")
            
            await asyncio.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\nGame session ended by user.")
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
        traceback.print_exc() # Print the full traceback for debugging
        sys.exit(1)


if __name__ == "__main__":
    main()