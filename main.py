import asyncio
import sys
from datetime import datetime
from src.core.types import GameState, NarrativeState, WorldState, RulesContext, EmergenceMetrics
from src.services.orchestrator_service import orchestrator_service
from src.agents.story_architect.graph import StoryArchitectAgent
from src.agents.dungeon_master.graph import DungeonMasterAgent
from src.agents.director.graph import DirectorAgent
from src.core.config import get_settings


async def initialize_game_state() -> GameState:
    return GameState(
        narrative=NarrativeState(
            story_arc="The Lost Temple of Azurath",
            current_scene="The adventurers gather at the Rusty Dragon tavern",
            story_beats=[],
            narrative_tension=0.3,
            completed_beats=[]
        ),
        world=WorldState(
            current_location="tavern",
            time_of_day="evening",
            weather="clear",
            active_quests=["Find the Lost Temple"],
            world_events=[]
        ),
        players=[],
        actions=[],
        combat=None,
        rules_context=RulesContext(
            active_rules=[],
            violations=[],
            clarifications_needed=[]
        ),
        emergence_metrics=EmergenceMetrics(
            player_agency=0.5,
            narrative_coherence=0.8,
            pacing_score=0.6,
            engagement_level=0.7
        ),
        messages=[],
        metadata={"session_id": datetime.now().isoformat(), "turn": 0}
    )


async def run_game_loop():
    settings = get_settings()
    
    print("=" * 60)
    print("AI DUNGEON MASTER - Game Orchestrator")
    print("=" * 60)
    print(f"Model: {settings.model_name if not settings.custom_model_enabled else settings.custom_model_name}")
    print(f"Temperature: {settings.model_temperature}")
    print("=" * 60)
    
    story_architect = StoryArchitectAgent()
    dungeon_master = DungeonMasterAgent()
    director = DirectorAgent()
    
    orchestrator_service.register_agent("story_architect", story_architect)
    orchestrator_service.register_agent("dungeon_master", dungeon_master)
    orchestrator_service.register_agent("director", director)
    
    state = await initialize_game_state()
    
    print("\nInitializing game session...")
    print(f"Story Arc: {state['narrative'].story_arc}")
    print(f"Starting Location: {state['world'].current_location}")
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
                print(f"\n{last_message.name}: {last_message.content}\n")
            
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
        sys.exit(1)


if __name__ == "__main__":
    main()
