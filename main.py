import asyncio
import sys

# import logging
from src.services.logging_service import logger
from src.services.session_service import session_service
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

# # Setup logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler('game.log'),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger(__name__)


async def initialize_game_state() -> GameState:
    """
    Initialize a fresh GameState with all required fields.

    This represents the starting state before world initialization.
    All fields must be properly set to avoid downstream errors.

    Returns:
        GameState: Fresh game state with all fields initialized
    """
    logger.log_event("System", "Init", "Initializing fresh game state")

    # Create initial storyline (Phase 1 will populate this)
    initial_storyline = Storyline(nodes=[], current_phase="Intro")

    # Create initial narrative state
    initial_narrative = NarrativeState(
        title="The Lost Temple of Azurath",
        tagline="Adventurers seek an ancient, forgotten shrine.",
        story_arc_summary="The adventurers search for the lost temple of Azurath, facing trials and uncovering its secrets.",
        storyline=initial_storyline,
        narrative_entities={},
        major_factions=["The Cult of Azurath", "The Order of the Dawn"],
        narrative_tension=0.3,
        current_scene="The adventurers gather at the Rusty Dragon tavern",
    )

    # Create initial world state (Phase 1 will populate locations, NPCs, etc.)
    initial_world = WorldState(
        overview="A world of adventure and mystery.",
        regions=[],  # Populated by LoreBuilder
        cultures=[],  # Populated by LoreBuilder
        history=None,  # Populated by LoreBuilder
        important_npcs=[],  # Populated by LoreBuilder
        locations={},  # Populated by WorldEngine
        active_npcs={},  # Populated by WorldEngine
        global_time=0,
    )

    session_id = datetime.now().isoformat()

    # BUILD THE STATE DICT WITH ALL REQUIRED FIELDS
    # This is CRITICAL - missing any field will cause KeyError later
    state: GameState = {
        # User Input
        "user_prompt": "Begin the adventure!",
        # Settings & Configuration
        "setting": Setting(
            story_length=2000,
            story_arc_count=1,
            theme="Fantasy Exploration",
            player_concepts=["Rogue", "Wizard", "Fighter"],
            difficulty="Normal",
        ),
        # Game Data Structures
        "narrative": initial_narrative,
        "world": initial_world,
        "players": [],  # Populated by PlayerCreator
        "actions": [],  # Populated during gameplay
        "combat": None,  # Populated if combat starts
        # Rules & Mechanics
        "rules_context": RulesContext(
            active_rules=[],
            violations=[],
            clarifications_needed=[],
        ),
        # Metrics & State
        "emergence_metrics": EmergenceMetrics(
            player_agency=0.5,
            narrative_coherence=0.8,
            pacing_score=0.6,
            engagement_level=0.7,
        ),
        # Agent Outputs
        "director_directives": None,  # Populated by Director
        "messages": [],  # Populated by DungeonMaster
        # Metadata
        "metadata": {
            "session_id": session_id,
            "turn": 0,
            "started_at": datetime.now().isoformat(),
        },
        # Current Turn State (CRITICAL - orchestrator references these)
        "current_action": None,
        "last_outcome": None,
        "last_verdict": None,
        # Router Fields (CRITICAL - orchestrator uses these for routing)
        "response_type": "unknown",  # Set by dm.plan_response
        "__end__": False,  # Set by exit_check_node
        # Action Suggestions (populated by DungeonMaster)
        "action_suggestions": [],  # DM returns 2-3 suggested actions for player
    }

    logger.log_event("System", "Debug", f"GameState initialized: {session_id}", level="debug")
    return state


async def load_session(session_id: str) -> GameState:
    """
    Load a saved game session from checkpoint.

    Args:
        session_id: Session ID to load

    Returns:
        GameState: Loaded game state

    Raises:
        ValueError: If session not found
    """
    logger.log_event("System", "Load", f"Loading session: {session_id}")

    config = {"configurable": {"thread_id": session_id}}

    # Get the latest checkpoint for this session
    snapshot = await orchestrator_service.compiled_graph.aget_state(config)

    if not snapshot or not snapshot.values:
        raise ValueError(f"Session '{session_id}' not found or has no saved state")

    logger.log_event("System", "Load", f"Loaded session {session_id} at turn {snapshot.values.get('metadata', {}).get('turn', 0)}")
    return snapshot.values


async def select_or_create_session() -> tuple[GameState, bool]:
    """
    Display session selection menu and return chosen session.

    Returns:
        tuple: (GameState, is_new_session)
    """
    print("\n" + "=" * 60)
    print("🎲 AI DUNGEON MASTER - SESSION MANAGER 🎲")
    print("=" * 60)

    # List existing sessions
    sessions = session_service.list_sessions(status_filter="active")

    if sessions:
        print("\n📚 Saved Sessions:")
        print()
        for i, session in enumerate(sessions[:10], 1):  # Show max 10
            created = session.created_at[:10]  # Just the date
            last_played = session.last_played[:10]
            print(f"  {i}. {session.title}")
            print(f"     Turn {session.turn_count} | Created: {created} | Last: {last_played}")
            print(f"     ID: {session.session_id}")
            print()

        print("  N. Start New Game")
        print("  Q. Quit")
        print()
        choice = input("Select option (1-{}, N, Q): ".format(len(sessions[:10]))).strip().upper()

        if choice == "Q":
            print("\n👋 Goodbye!")
            sys.exit(0)
        elif choice == "N":
            # Create new session
            return await initialize_game_state(), True
        else:
            # Try to load selected session
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(sessions[:10]):
                    selected = sessions[idx]
                    state = await load_session(selected.session_id)
                    return state, False
                else:
                    print("❌ Invalid selection. Starting new game.")
                    return await initialize_game_state(), True
            except (ValueError, Exception) as e:
                logger.log_event("System", "Error", f"Failed to load session: {e}", level="error")
                print(f"❌ Failed to load session: {e}")
                print("Starting new game instead...")
                return await initialize_game_state(), True
    else:
        print("\n📝 No saved sessions found.")
        print("\nStarting new game...")
        return await initialize_game_state(), True


def validate_game_state(state: GameState) -> bool:
    """
    Validate that GameState has all required fields.

    Args:
        state: GameState to validate

    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = [
        "user_prompt",
        "setting",
        "narrative",
        "world",
        "players",
        "actions",
        "combat",
        "rules_context",
        "emergence_metrics",
        "director_directives",
        "messages",
        "metadata",
        "current_action",
        "last_outcome",
        "last_verdict",
        "response_type",
        "__end__",
        "action_suggestions",
    ]

    for field in required_fields:
        if field not in state:
            logger.log_event("System", "Error", f"Missing required field: {field}", level="error")
            return False

    logger.log_event("System", "Debug", "GameState validation passed")
    return True


def display_world_state(state: GameState) -> None:
    """
    Display the current world state to the player.

    Shows location, NPCs, exits, and player status.

    Args:
        state: Current GameState
    """
    players = state.get("players", [])
    if not players:
        return

    player = players[0]
    world = state.get("world")

    if not world:
        logger.log_event("System", "Warning", "No world state to display", level="warning")
        return

    # Get player's current location
    location = world.locations.get(player.location_id) if world.locations else None

    print("\n" + "=" * 60)
    print(f"📍 LOCATION: {location.name if location else 'Unknown'}")
    print("=" * 60)

    if location:
        print(f"\n{location.description}")

        # Show NPCs
        if location.npc_ids:
            npcs = [world.active_npcs.get(npc_id) for npc_id in location.npc_ids]
            npc_names = [npc.base_data.name for npc in npcs if npc]
            if npc_names:
                print(f"\n👥 NPCs here: {', '.join(npc_names)}")

        # Show exits
        if location.connected_ids:
            exits = []
            for loc_id in location.connected_ids:
                exit_loc = world.locations.get(loc_id)
                if exit_loc:
                    exits.append(exit_loc.name)
            if exits:
                print(f"\n🚪 Exits: {', '.join(exits)}")

        # Show clues
        if location.clues:
            print(f"\n🔍 Clues: {', '.join(location.clues[:2])}")

    # Show player stats
    print(f"\n👤 {player.name} ({player.race} {player.class_name}, Level {player.level})")
    print(f"❤️  HP: {player.stats.current_hit_points}/{player.stats.max_hit_points}")
    print(f"⚔️  AC: {player.stats.armor_class}")
    print("=" * 60)


async def get_user_action(state: GameState) -> Action:
    """
    Get player action from user input.

    Shows action suggestions from DM (if available) and accepts player input.
    Player can use suggestions as-is or write their own action.

    Args:
        state: Current GameState (for player info and suggestions)

    Returns:
        Action: The player's action
    """
    players = state.get("players", [])
    if not players:
        logger.log_event("System", "Error", "No players in game state", level="error")
        raise RuntimeError("Cannot get action - no players")

    player = players[0]

    # Show action suggestions from DM (if available)
    suggestions = state.get("action_suggestions", [])
    if suggestions and len(suggestions) > 0:
        print("\n💡 What might you do?")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"   {i}. {suggestion}")
        print()

    print("", end="")
    description = input("> ").strip()

    if not description:
        description = "look around and wait for what happens next"

    # Classify action type based on keywords
    action_type = "other"
    desc_lower = description.lower()

    if any(
        word in desc_lower
        for word in ["attack", "hit", "strike", "fight", "combat", "stab", "shoot"]
    ):
        action_type = "attack"
    elif any(
        word in desc_lower
        for word in ["move", "go", "walk", "travel", "enter", "exit", "approach", "follow"]
    ):
        action_type = "move"
    elif any(
        word in desc_lower
        for word in ["search", "investigate", "examine", "look", "check", "inspect", "observe"]
    ):
        action_type = "investigate"
    elif any(
        word in desc_lower
        for word in ["talk", "speak", "say", "ask", "dialogue", "chat", "greet", "respond"]
    ):
        action_type = "social"
    elif any(word in desc_lower for word in ["cast", "spell", "magic", "invoke"]):
        action_type = "magic"
    elif any(
        word in desc_lower for word in ["take", "grab", "pick", "use", "open", "drink", "eat"]
    ):
        action_type = "interact"

    action = Action(
        player_id=player.id,
        type=action_type,
        description=description,
        timestamp=datetime.now().isoformat(),
        result=None,
    )

    logger.log_event("Player", "Action", f"{action.description} ({action.type})")
    return action


async def run_game_loop() -> None:
    """
    Main game loop.

    Phases:
    1. Initialize game state
    2. Setup world (Phase 1)
    3. Main gameplay loop (Phase 2) - with DM-provided action suggestions
    4. Cleanup

    Raises:
        SystemExit: On critical failure
    """
    settings = get_settings()

    print("=" * 60)
    print("🎲 AI DUNGEON MASTER 🎲")
    print("=" * 60)

    model_display = (
        settings.custom_model_name if settings.custom_model_enabled else settings.model_name
    )
    print(f"Model: {model_display}")
    print(f"Temperature: {settings.model_temperature}")
    print("=" * 60)

    # Step 1: Select or load session
    state, is_new_session = await select_or_create_session()

    if not is_new_session:
        # Loaded existing session
        print("\n" + "=" * 60)
        print("📂 SESSION LOADED")
        print("=" * 60)
        
        narrative = state.get("narrative")
        if narrative:
            print(f"\n📖 Campaign: {narrative.title}")
        
        turn = state.get("metadata", {}).get("turn", 0)
        print(f"🔄 Resuming at turn {turn}")
        
        # Skip world initialization - go straight to gameplay
        print("\n" + "=" * 60)
        print("🏰 ADVENTURE CONTINUES 🏰")
        print("=" * 60)
        print("\n(Type 'quit', 'exit', 'end', or 'q' to quit)\n")
        
        # Jump to game loop
        turn = state.get("metadata", {}).get("turn", 0)
    else:
        # New session - run full initialization
        print("=" * 60)
        logger.log_event("System", "Start", "STARTING NEW GAME")
        print("=" * 60)

        # Validate state
        if not validate_game_state(state):
            logger.log_event("System", "Error", "Initial GameState validation failed", level="error")
            print("\n❌ Failed to initialize game (invalid state)")
            sys.exit(1)

        # Step 2: Run Phase 1 (World Initialization)
        print("\n🎲 Initializing game world...")
        print("This may take a moment as the AI creates your adventure...\n")

        logger.log_event("System", "Phase 1", "Starting World Initialization")

        try:
            state = await orchestrator_service.initialize_world(state)

            world = state.get("world")  # new add
            if world:
                logger.log_event(
                    "World",
                    "Created",
                    f"World '{state['narrative'].title}' created with {len(world.regions)} regions.",
                )

        except Exception as e:
            logger.log_event("System", "Error", f"Phase 1 Failed: {e}", level="error")
            print(f"\n❌ Failed to initialize world: {e}")
            sys.exit(1)

        # Save new session metadata
        session_id = state["metadata"]["session_id"]
        session_title = state.get("narrative", {}).title or "Untitled Campaign"
        session_service.create_session(session_id, session_title)
        logger.log_event("System", "Session", f"Created session: {session_id}")

        # Display initialized world
        print("\n✅ World Created!")
        narrative = state.get("narrative")
        if narrative:
            print(f"\n📖 Campaign: {narrative.title}")
            print(f"📝 {narrative.tagline}")

        players = state.get("players", [])
        if players:
            print("\n👥 Your Characters:")
            seen_ids = set()
            for player in players:
                pid = getattr(player, "id", None)
                if pid is not None and pid in seen_ids:
                    continue
                if pid is not None:
                    seen_ids.add(pid)

                print(f"  • {player.name} - {player.race} {player.class_name}")
                print(f"    {player.motivation}")
        else:
            logger.log_event(
                "System",
                "Warning",
                "No players were created during world initialization",
                level="warning",
            )

        # ✅ Show initial DM narration produced during Phase 1
        messages = state.get("messages", [])
        if messages:
            print("\n" + "=" * 60)
            print("📜 DUNGEON MASTER")
            print("=" * 60)
            for msg in messages:
                content = getattr(msg, "content", str(msg))
                print(f"\n{content}")
        else:
            logger.log_event(
                "System",
                "Warning",
                "No DM messages generated during world initialization",
                level="warning",
            )

        print("\n" + "=" * 60)
        print("🏰 ADVENTURE BEGINS 🏰")
        print("=" * 60)
        print("\n(Type 'quit', 'exit', 'end', or 'q' to quit)\n")

        logger.log_event("System", "Phase 2", "Starting Gameplay Loop")
        turn = 0

    # Step 3: Main game loop
    try:
        max_turns = 1000  # Safety limit
        session_id = state["metadata"]["session_id"]

        while turn < max_turns and not state.get("__end__", False):
            turn += 1
            state["metadata"]["turn"] = turn

            # Display current world state
            # display_world_state(state)  # Uncomment to show location details

            # Get player action
            try:
                action = await get_user_action(state)
            except KeyboardInterrupt:
                logger.log_event("User interrupted during action input")
                break
            except Exception as e:
                logger.log_event(
                    "System", "Error", f"Failed to get user action: {e}", level="error"
                )
                print(f"\n❌ Error getting action: {e}")
                continue

            # Check for exit keywords
            if action.description.lower() in ["quit", "exit", "end", "q"]:
                logger.log_event("System", "Info", "Player requested to quit")
                print("\n👋 Thanks for playing!")
                break

            # Set state for orchestrator routing
            # CRITICAL: Always reset response_type to ensure proper routing
            state["current_action"] = action
            state["response_type"] = "action"  # This must be set for routing!
            
            # Clear previous turn data to prevent stale routing
            state["last_outcome"] = None
            state["last_verdict"] = None

            print("\n⚙️  Resolving action...")
            logger.log_event(
                "System", "Debug", f"Turn {turn}: Executing {action.type} action", level="debug"
            )

            # Execute turn through orchestrator
            try:
                state = await orchestrator_service.execute_turn(state)
                
                # Save session metadata after successful turn
                session_service.update_session(session_id, turn)
                logger.log_event("System", "Debug", f"Saved session metadata for turn {turn}", level="debug")
            except Exception as e:
                logger.log_event(
                    "System", "Error", f"Turn {turn} execution failed: {e}", level="error"
                )
                print(f"\n❌ Error during turn: {e}")
                continue

            # Display DM narrative
            messages = state.get("messages", [])
            if messages:
                last_message = messages[-1]
                print("\n" + "=" * 60)
                print("📜 DUNGEON MASTER")
                print("=" * 60)

                # Extract message content
                content = getattr(last_message, "content", str(last_message))
                logger.log_event("DM", "Narrative", content)
            else:
                logger.log_event(
                    "System", "Warning", f"No DM message for turn {turn}", level="warning"
                )

        # End of game loop
        if turn >= max_turns:
            logger.log_event(
                "System", "Warning", f"Reached maximum turns ({max_turns})", level="warning"
            )
            print(f"\n🛑 Reached maximum turns ({max_turns}). Session ended.")

    except KeyboardInterrupt:
        logger.log_event("System", "Info", "Game interrupted by user (Ctrl+C)")
        print("\n\n👋 Session interrupted by user.")
    except Exception as e:
        logger.log_event("System", "Error", f"Unexpected error in gameloop: {e}", level="error")
        print(f"\n❌ Unexpected error: {e}")

    # Cleanup
    print("\n" + "=" * 60)
    print("Game session ended.")
    print(f"Total turns: {turn}")
    print("=" * 60)

    logger.log_event("System", "End", f"Game ended after {turn} turns")


def main() -> None:
    """
    Main entry point for the application.

    Handles async execution and error management.
    """
    try:
        asyncio.run(run_game_loop())
    except KeyboardInterrupt:
        logger.log_event("System", "Info", "Application shutdown requested")
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        logger.log_event("System", "Critical", f"Critical error in main: {e}", level="error")
        print(f"\n❌ Critical error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
