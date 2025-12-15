"""
Chainlit chat interface for AI Dungeon Master.

Provides a web-based chat UI for playing the D&D game, with session
management and persistent game state.
"""

import asyncio
from datetime import datetime
from typing import Optional

import chainlit as cl
from chainlit.input_widget import Select

from src.core.types import GameState, Action
from src.services.orchestrator_service import orchestrator_service
from src.services.session_service import session_service
from src.services.logging_service import logger


@cl.on_chat_end
async def on_chat_end():
    """Cleanup when chat session ends."""
    try:
        await orchestrator_service.cleanup()
        logger.log_event("System", "Cleanup", "Orchestrator resources cleaned up")
    except Exception as e:
        logger.log_event("System", "Error", f"Cleanup error: {e}", level="error")


async def initialize_game_state() -> GameState:
    """
    Initialize a fresh GameState with all required fields.
    
    This is identical to the function in main.py.
    
    Returns:
        GameState: Fresh game state with all fields initialized
    """
    from src.core.types import (
        NarrativeState,
        WorldState,
        RulesContext,
        EmergenceMetrics,
        Storyline,
        Setting,
    )

    logger.log_event("System", "Init", "Initializing fresh game state")

    initial_storyline = Storyline(nodes=[], current_phase="Intro")

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

    initial_world = WorldState(
        overview="A world of adventure and mystery.",
        regions=[],
        cultures=[],
        history=None,
        important_npcs=[],
        locations={},
        active_npcs={},
        global_time=0,
    )

    session_id = datetime.now().isoformat()

    state: GameState = {
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
        "players": [],
        "actions": [],
        "combat": None,
        "rules_context": RulesContext(
            active_rules=[],
            violations=[],
            clarifications_needed=[],
        ),
        "emergence_metrics": EmergenceMetrics(
            player_agency=0.5,
            narrative_coherence=0.8,
            pacing_score=0.6,
            engagement_level=0.7,
        ),
        "director_directives": None,
        "messages": [],
        "metadata": {
            "session_id": session_id,
            "turn": 0,
            "started_at": datetime.now().isoformat(),
        },
        "current_action": None,
        "last_outcome": None,
        "last_verdict": None,
        "response_type": "unknown",
        "__end__": False,
        "action_suggestions": [],
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

    # Ensure graph is compiled
    if not orchestrator_service.compiled_graph:
        await orchestrator_service.build_pipeline()

    config = {"configurable": {"thread_id": session_id}}

    try:
        snapshot = await orchestrator_service.compiled_graph.aget_state(config)

        if not snapshot or not snapshot.values:
            raise ValueError(f"Session '{session_id}' not found or has no saved state")

        logger.log_event(
            "System",
            "Load",
            f"Loaded session {session_id} at turn {snapshot.values.get('metadata', {}).get('turn', 0)}",
        )
        return snapshot.values
    except Exception as e:
        logger.log_event("System", "Error", f"Failed to load session state: {e}", level="error")
        raise ValueError(f"Could not load session '{session_id}': {e}") from e


@cl.on_chat_start
async def start():
    """Initialize the chat session with session selection."""
    await cl.Message(
        content="# 🎲 Welcome to AI Dungeon Master! 🎲\n\nInitializing game system...",
        author="System",
    ).send()

    # Build the orchestrator graph
    try:
        await orchestrator_service.build_pipeline()
        logger.log_event("System", "Init", "Orchestrator pipeline built")
    except Exception as e:
        logger.log_event("System", "Error", f"Failed to build pipeline: {e}", level="error")
        await cl.Message(
            content=f"❌ Failed to initialize game system: {e}", author="System"
        ).send()
        return

    # Get saved sessions
    sessions = session_service.list_sessions(status_filter="active", limit=10)

    # Create session selection
    if sessions:
        session_options = [
            {"label": f"{s.title} (Turn {s.turn_count})", "value": s.session_id}
            for s in sessions
        ]
        session_options.append({"label": "🆕 Start New Game", "value": "NEW"})

        res = await cl.AskActionMessage(
            content="Would you like to continue a saved game or start new?",
            actions=[
                cl.Action(name=opt["value"], value=opt["value"], label=opt["label"], payload={})
                for opt in session_options
            ],
        ).send()

        if res and res.get("value") == "NEW":
            # Start new game
            await start_new_game()
        elif res and res.get("value"):
            # Load existing game
            await load_existing_game(res.get("value"))
        else:
            # Default to new game
            await start_new_game()
    else:
        # No saved games, start new
        await cl.Message(content="No saved games found. Starting new adventure!").send()
        await start_new_game()


async def start_new_game():
    """Initialize a new game session."""
    msg = cl.Message(content="🎲 Creating new adventure...", author="System")
    await msg.send()

    try:
        # Initialize state
        state = await initialize_game_state()

        # Run Phase 1 (World Initialization)
        await msg.stream_token("\n\n🌍 Building the world...")
        state = await orchestrator_service.initialize_world(state)

        # Save session metadata
        session_id = state["metadata"]["session_id"]
        session_title = state.get("narrative", {}).title or "Untitled Campaign"
        session_service.create_session(session_id, session_title)

        # Store in user session
        cl.user_session.set("game_state", state)
        cl.user_session.set("session_id", session_id)

        # Display world intro
        narrative = state.get("narrative")
        players = state.get("players", [])

        intro = f"\n\n# ✅ World Created!\n\n"
        intro += f"## 📖 {narrative.title}\n\n"
        intro += f"*{narrative.tagline}*\n\n"

        if players:
            intro += "### 👥 Your Characters:\n\n"
            for player in players:
                intro += f"- **{player.name}** - {player.race} {player.class_name}\n"
                intro += f"  - _{player.motivation}_\n"

        await msg.stream_token(intro)

        # Display initial DM narration
        messages = state.get("messages", [])
        if messages:
            dm_content = "\n\n---\n\n## 📜 Dungeon Master\n\n"
            for game_msg in messages:
                content = getattr(game_msg, "content", str(game_msg))
                dm_content += f"{content}\n\n"
            await msg.stream_token(dm_content)

        # Show action suggestions
        suggestions = state.get("action_suggestions", [])
        if suggestions:
            await msg.stream_token("\n\n💡 **What might you do?**\n\n")
            for i, suggestion in enumerate(suggestions, 1):
                await msg.stream_token(f"{i}. {suggestion}\n")

        await msg.update()

        logger.log_event("System", "Init", f"New game started: {session_id}")

    except Exception as e:
        logger.log_event("System", "Error", f"Failed to start new game: {e}", level="error")
        await cl.Message(content=f"❌ Failed to initialize game: {e}", author="System").send()


async def load_existing_game(session_id: str):
    """Load an existing game session."""
    msg = cl.Message(content=f"📂 Loading session...", author="System")
    await msg.send()

    try:
        state = await load_session(session_id)

        # Store in user session
        cl.user_session.set("game_state", state)
        cl.user_session.set("session_id", session_id)

        # Display session info
        narrative = state.get("narrative")
        turn = state.get("metadata", {}).get("turn", 0)

        content = f"\n\n# ✅ Session Loaded!\n\n"
        content += f"## 📖 {narrative.title if narrative else 'Campaign'}\n\n"
        content += f"**Turn:** {turn}\n\n"
        content += "Ready to continue your adventure!\n"

        await msg.stream_token(content)
        await msg.update()

        logger.log_event("System", "Load", f"Loaded session: {session_id}")

    except Exception as e:
        logger.log_event("System", "Error", f"Failed to load session: {e}", level="error")
        await cl.Message(content=f"❌ Failed to load session: {e}", author="System").send()
        # Fall back to new game
        await start_new_game()


@cl.on_message
async def handle_message(message: cl.Message):
    """Handle player actions and route through orchestrator."""
    state: Optional[GameState] = cl.user_session.get("game_state")
    session_id: Optional[str] = cl.user_session.get("session_id")

    if not state or not session_id:
        await cl.Message(
            content="❌ No active game session. Please restart.", author="System"
        ).send()
        return

    # Check for exit commands
    if message.content.lower().strip() in ["quit", "exit", "end", "q"]:
        await cl.Message(content="👋 Thanks for playing! Session saved.", author="System").send()
        return

    # Create action from user input
    players = state.get("players", [])
    if not players:
        await cl.Message(content="❌ No player character found.", author="System").send()
        return

    player = players[0]

    # Classify action type
    action_type = "other"
    desc_lower = message.content.lower()

    if any(word in desc_lower for word in ["attack", "hit", "strike", "fight"]):
        action_type = "attack"
    elif any(word in desc_lower for word in ["move", "go", "walk", "travel"]):
        action_type = "move"
    elif any(word in desc_lower for word in ["search", "investigate", "examine", "look"]):
        action_type = "investigate"
    elif any(word in desc_lower for word in ["talk", "speak", "say", "ask"]):
        action_type = "social"
    elif any(word in desc_lower for word in ["cast", "spell", "magic"]):
        action_type = "magic"
    elif any(word in desc_lower for word in ["take", "grab", "pick", "use"]):
        action_type = "interact"

    action = Action(
        player_id=player.id,
        type=action_type,
        description=message.content,
        timestamp=datetime.now().isoformat(),
        result=None,
    )

    logger.log_event("Player", "Action", f"{action.description} ({action.type})")

    # Update state for orchestrator routing
    # CRITICAL: Always reset response_type to ensure proper routing
    state["current_action"] = action
    state["response_type"] = "action"
    
    # Clear previous turn data to prevent stale routing
    state["last_outcome"] = None
    state["last_verdict"] = None

    # Execute turn
    msg = cl.Message(content="⚙️ Resolving action...", author="Dungeon Master")
    await msg.send()

    try:
        state = await orchestrator_service.execute_turn(state)

        # Update turn counter
        turn = state.get("metadata", {}).get("turn", 0) + 1
        state["metadata"]["turn"] = turn

        # Save session
        session_service.update_session(session_id, turn)
        cl.user_session.set("game_state", state)

        # Display DM response
        messages = state.get("messages", [])
        if messages:
            last_message = messages[-1]
            dm_content = getattr(last_message, "content", str(last_message))

            await msg.stream_token(f"\n\n{dm_content}")

            # Show action suggestions
            suggestions = state.get("action_suggestions", [])
            if suggestions:
                await msg.stream_token("\n\n---\n\n💡 **What might you do?**\n\n")
                for i, suggestion in enumerate(suggestions, 1):
                    await msg.stream_token(f"{i}. {suggestion}\n")

            await msg.update()

        logger.log_event("DM", "Response", f"Turn {turn} completed")

    except Exception as e:
        logger.log_event("System", "Error", f"Turn execution failed: {e}", level="error")
        await msg.stream_token(f"\n\n❌ Error: {e}")
        await msg.update()


if __name__ == "__main__":
    # This is handled by the chainlit CLI
    pass
