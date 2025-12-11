import asyncio
import sys
import logging
import re
from datetime import datetime
from typing import Optional, List

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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def initialize_game_state() -> GameState:
    """
    Initialize a fresh GameState with all required fields.
    
    This represents the starting state before world initialization.
    All fields must be properly set to avoid downstream errors.
    
    Returns:
        GameState: Fresh game state with all fields initialized
    """
    logger.info("Initializing fresh game state")
    
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
    }
    
    logger.debug(f"GameState initialized with session_id: {session_id}")
    return state


def validate_game_state(state: GameState) -> bool:
    """
    Validate that GameState has all required fields.
    
    Args:
        state: GameState to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = [
        "user_prompt", "setting", "narrative", "world", "players",
        "actions", "combat", "rules_context", "emergence_metrics",
        "director_directives", "messages", "metadata",
        "current_action", "last_outcome", "last_verdict",
        "response_type", "__end__"
    ]
    
    for field in required_fields:
        if field not in state:
            logger.error(f"Missing required field in GameState: {field}")
            return False
    
    logger.debug("GameState validation passed")
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
        logger.warning("No world state to display")
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


def extract_action_suggestions(narrative: str) -> List[str]:
    """
    Extract action suggestions from DM's narrative.
    
    Looks for narrative prompts that suggest what the player might do:
    - Lines starting with: "A ", "You ", "Suddenly", "Before", "The ", "Something"
    - Lines ending with ellipsis (...)
    - Questions posed to the player
    - Sentences with action verbs: "lies", "emerges", "awaits", "notices", etc.
    
    Args:
        narrative: The DM's narrative text
        
    Returns:
        List of action suggestions extracted from the narrative
    """
    if not narrative:
        return []
    
    suggestions = []
    
    # Split into sentences
    sentences = re.split(r'(?<=[.!?])\s+', narrative)
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Look for action suggestion patterns
        prompt_starters = [
            "A ", "You ", "Suddenly", "Before", "The ", "Something",
            "Your", "A low", "A sudden", "A soft", "Behind",
            "Ahead", "To your", "You notice", "You realize", "You spot",
            "From", "Beyond", "Beneath"
        ]
        
        is_prompt = False
        for starter in prompt_starters:
            if sentence.startswith(starter) and len(sentence) > 10:
                is_prompt = True
                break
        
        # Also look for questions or uncertain phrases
        if '?' in sentence or '...' in sentence:
            is_prompt = True
        
        # Look for action-oriented sentences
        action_words = [
            "lies", "awaits", "emerges", "appears", "glints",
            "echoes", "beckons", "calls", "looms", "gleams",
            "stretches", "beckons", "waits", "stands", "sits",
            "moves", "shifts", "flickers", "shimmers"
        ]
        
        if any(word in sentence.lower() for word in action_words):
            is_prompt = True
        
        # Add if it's a good suggestion and not too short
        if is_prompt and len(sentence) > 15:
            # Remove markdown/formatting
            sentence = re.sub(r'\*\*', '', sentence)  # Remove bold
            sentence = re.sub(r'\*', '', sentence)    # Remove italics
            sentence = re.sub(r'>', '', sentence)     # Remove blockquotes
            suggestions.append(sentence)
    
    # Return up to 3 suggestions
    return suggestions[:3]


async def get_user_action(state: GameState, suggestions: Optional[List[str]] = None) -> Action:
    """
    Get player action from user input.
    
    IMPROVED: Shows action suggestions extracted from DM's narrative as hints.
    Player can use them as inspiration or write their own action.
    
    Args:
        state: Current GameState (for player info)
        suggestions: Optional list of action suggestions from narrative
        
    Returns:
        Action: The player's action
    """
    players = state.get("players", [])
    if not players:
        logger.error("No players in game state")
        raise RuntimeError("Cannot get action - no players")
    
    player = players[0]
    
    # Show suggestions if available
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
    
    if any(word in desc_lower for word in ["attack", "hit", "strike", "fight", "combat", "stab", "shoot"]):
        action_type = "attack"
    elif any(word in desc_lower for word in ["move", "go", "walk", "travel", "enter", "exit", "approach", "follow"]):
        action_type = "move"
    elif any(word in desc_lower for word in ["search", "investigate", "examine", "look", "check", "inspect", "observe"]):
        action_type = "investigate"
    elif any(word in desc_lower for word in ["talk", "speak", "say", "ask", "dialogue", "chat", "greet", "respond"]):
        action_type = "social"
    elif any(word in desc_lower for word in ["cast", "spell", "magic", "invoke"]):
        action_type = "magic"
    elif any(word in desc_lower for word in ["take", "grab", "pick", "use", "open", "drink", "eat"]):
        action_type = "interact"
    
    action = Action(
        player_id=player.id,
        type=action_type,
        description=description,
        timestamp=datetime.now().isoformat(),
        result=None,
    )
    
    logger.debug(f"Player action created: type={action_type}, description={description}")
    return action


async def run_game_loop() -> None:
    """
    Main game loop.
    
    Phases:
    1. Initialize game state
    2. Setup world (Phase 1)
    3. Main gameplay loop (Phase 2) - narrative-driven with embedded prompts
    4. Cleanup
    
    Raises:
        SystemExit: On critical failure
    """
    settings = get_settings()

    print("=" * 60)
    print("🎲 AI DUNGEON MASTER 🎲")
    print("=" * 60)
    
    model_display = (
        settings.custom_model_name 
        if settings.custom_model_enabled 
        else settings.model_name
    )
    print(f"Model: {model_display}")
    print(f"Temperature: {settings.model_temperature}")
    print("=" * 60)

    # Step 1: Initialize fresh game state
    logger.info("=" * 60)
    logger.info("STARTING NEW GAME")
    logger.info("=" * 60)
    
    state = await initialize_game_state()
    
    # Validate state
    if not validate_game_state(state):
        logger.error("Initial GameState validation failed")
        print("\n❌ Failed to initialize game (invalid state)")
        sys.exit(1)

    # Step 2: Run Phase 1 (World Initialization)
    print("\n🎲 Initializing game world...")
    print("This may take a moment as the AI creates your adventure...\n")
    
    logger.info("Starting Phase 1: World Initialization")
    
    try:
        state = await orchestrator_service.initialize_world(state)
    except Exception as e:
        logger.error(f"Phase 1 failed: {e}", exc_info=True)
        print(f"\n❌ Failed to initialize world: {e}")
        sys.exit(1)

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
        logger.warning("No players were created during world initialization")

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
        logger.warning("No DM messages generated during world initialization")

    print("\n" + "=" * 60)
    print("🏰 ADVENTURE BEGINS 🏰")
    print("=" * 60)
    print("\n(Type 'quit', 'exit', 'end', or 'q' to quit)\n")

    logger.info("Starting Phase 2: Gameplay Loop")


    # Step 3: Main game loop
    try:
        turn = 0
        max_turns = 1000  # Safety limit
        
        while turn < max_turns and not state.get("__end__", False):
            turn += 1
            state["metadata"]["turn"] = turn
            
            # Display current world state
            # display_world_state(state)  # Uncomment to show location details
            
            # Get player action
            try:
                # Extract action suggestions from previous narration
                suggestions = []
                messages = state.get("messages", [])
                if messages and turn > 1:  # Don't show suggestions on first turn
                    last_message = messages[-1]
                    content = (
                        last_message.content 
                        if hasattr(last_message, 'content') 
                        else str(last_message)
                    )
                    suggestions = extract_action_suggestions(content)
                
                action = await get_user_action(state, suggestions)
            except KeyboardInterrupt:
                logger.info("User interrupted during action input")
                break
            except Exception as e:
                logger.error(f"Failed to get user action: {e}")
                print(f"\n❌ Error getting action: {e}")
                continue
            
            # Check for exit keywords
            if action.description.lower() in ["quit", "exit", "end", "q"]:
                logger.info("Player requested to quit")
                print("\n👋 Thanks for playing!")
                break
            
            # Set state for orchestrator routing
            state["current_action"] = action
            state["response_type"] = "action"  # This must be set for routing!

            print("\n⚙️  Resolving action...")
            logger.debug(f"Turn {turn}: Executing {action.type} action")
            
            # Execute turn through orchestrator
            try:
                state = await orchestrator_service.execute_turn(state)
            except Exception as e:
                logger.error(f"Turn {turn} execution failed: {e}", exc_info=True)
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
                content = (
                    last_message.content 
                    if hasattr(last_message, 'content') 
                    else str(last_message)
                )
                print(f"\n{content}\n")
            else:
                logger.warning(f"No messages generated for turn {turn}")

        # End of game loop
        if turn >= max_turns:
            logger.warning(f"Reached maximum turns ({max_turns})")
            print(f"\n🛑 Reached maximum turns ({max_turns}). Session ended.")

    except KeyboardInterrupt:
        logger.info("Game interrupted by user (Ctrl+C)")
        print("\n\n👋 Session interrupted by user.")
    except Exception as e:
        logger.error(f"Unexpected error in game loop: {e}", exc_info=True)
        print(f"\n❌ Unexpected error: {e}")
    
    # Cleanup
    print("\n" + "=" * 60)
    print("Game session ended.")
    print(f"Total turns: {turn}")
    print("=" * 60)
    
    logger.info(f"Game ended after {turn} turns")


def main() -> None:
    """
    Main entry point for the application.
    
    Handles async execution and error management.
    """
    try:
        asyncio.run(run_game_loop())
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
        print("\nShutting down...")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Critical error in main: {e}", exc_info=True)
        print(f"\n❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
