from typing import Literal, Any
import logging
from pathlib import Path

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from src.core.types import GameState

# Import Agents - Use the ACTUAL agent classes
from src.agents.story_architect.graph import StoryArchitectAgent
from src.agents.lore_builder.graph import LoreBuilderAgent
from src.agents.world_engine.graph import WorldEngineAgent
from src.agents.player_proxy.graph import PlayerProxyAgent  # NOTE: This is the actual class
from src.agents.action_resolver.graph import ActionResolverAgent
from src.agents.rule_judge.graph import JudgeAgent
from src.agents.director.graph import DirectorAgent
from src.agents.dungeon_master.graph import DungeonMasterAgent

# Import collaboration services
from src.services.agent_context_hub import AgentContextHub
from src.services.knowledge_graph_service import KnowledgeGraphService
from src.services.gameplay_executor import GameplayExecutor
from src.core.agent_specialization import SpecializationContext

logger = logging.getLogger(__name__)


class OrchestratorService:
    """
    Central orchestrator for the AI Dungeon Master MAS.

    **CRITICAL**: This orchestrator integrates with agents that have their own internal LangGraphs.

    **IMPORTANT**: Collaboration services (context_hub, knowledge_graph) are NOT stored in GameState
    because GameState is serialized with msgpack for checkpointing. These are managed directly in the
    orchestrator and passed as function arguments to agents.

    Phase 1: Setup Pipeline (returns to caller on completion)
    - StoryArchitectAgent.plan_narrative() -> generates narrative blueprint
    - LoreBuilderAgent.build_lore() -> generates world lore
    - WorldEngineAgent.instantiate_world() -> creates locations and NPCs
    - PlayerProxyAgent.process() -> USES INTERNAL SEND() for parallel character creation
    - DungeonMasterAgent.narrate_initial() -> initial narration
    - phase1_complete -> END (exits setup phase)

    Phase 2: Gameplay Loop (called from main.py each turn)
    - DungeonMasterAgent.plan_response() -> decides next action
    - ActionResolverAgent.resolve_action() -> handles player action
    - JudgeAgent.evaluate_turn() -> validates outcomes
    - WorldEngineAgent.update_world() -> updates world state
    - PlayerProxyAgent.update_players() -> updates player state
    - DirectorAgent.direct_scene() -> narrative pacing
    - DungeonMasterAgent.narrate_outcome() -> narrate results
    - turn_complete -> END (exits single turn)
    
    Phase 3: Gameplay Executor (comprehensive turn orchestration)
    - Uses GameplayExecutor to coordinate all 7 steps of the turn
    - Handles player actions, resolution, world updates, narration, etc.
    - Returns complete GameplayPhaseState with memory and pacing
    """

    def __init__(self):
        """Initialize orchestrator with all agent instances and memory."""
        self.workflow = None
        self.compiled_graph = None

        # Store database path for async initialization
        self.db_path = Path("src/data/storage/sessions.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # AsyncSqliteSaver context manager and checkpointer
        self._checkpointer_cm = None  # Store context manager
        self.memory = MemorySaver()  # Temporary default until async setup

        self._retry_count = 0
        self._max_retry_attempts = 2

        # Instantiate all agents
        self.architect = StoryArchitectAgent()
        self.lore_builder = LoreBuilderAgent()
        self.world_engine = WorldEngineAgent()
        # CRITICAL: Use PlayerProxyAgent, not PlayerCreatorAgent
        self.player_proxy = PlayerProxyAgent()

        self.resolver = ActionResolverAgent()
        self.judge = JudgeAgent()
        self.director = DirectorAgent()
        self.dm = DungeonMasterAgent()

        # Initialize collaboration services (NOT IN GameState - managed here)
        self.context_hub = AgentContextHub()
        self.knowledge_graph = KnowledgeGraphService()
        
        # Initialize Phase 3 executor
        self.gameplay_executor = GameplayExecutor()

        logger.info("OrchestratorService initialized with all agents and collaboration services")

    async def build_pipeline(self) -> None:
        """
        Constructs the Master Graph connecting all agents.

        **CRITICAL FIX**: Graph now has two separate flows:
        - Phase 1: Setup pipeline that exits after narrate_initial
        - Phase 2: Gameplay loop that runs ONE TURN and exits

        Phase 2 now has explicit turn completion that returns to main.py,
        preventing infinite recursion within a single ainvoke() call.
        """
        # Initialize AsyncSqliteSaver for persistent checkpoint storage
        if self._checkpointer_cm is None:
            self._checkpointer_cm = AsyncSqliteSaver.from_conn_string(str(self.db_path))
            self.memory = await self._checkpointer_cm.__aenter__()
            logger.info(f"AsyncSqliteSaver initialized with database: {self.db_path}")

        try:
            builder = StateGraph(GameState)

            # ============================================================
            # 1. REGISTER NODES
            # ============================================================

            # --- Phase 1: Initialization Pipeline ---
            builder.add_node("story_architect", self.architect.plan_narrative)
            builder.add_node("lore_builder", self.lore_builder.build_lore)
            builder.add_node("world_engine", self.world_engine.instantiate_world)

            # CRITICAL FIX: PlayerProxyAgent has process() method that handles parallel creation
            # Its internal graph uses Send() to create characters in parallel
            builder.add_node("player_creator", self.player_proxy.run_initialization)

            builder.add_node("initial_dm", self.dm.narrate_initial)

            # --- Phase 2: Single-Turn Gameplay ---
            builder.add_node("dm_planner", self.dm.plan_response)
            builder.add_node("action_resolver", self.resolver.resolve_action)
            builder.add_node("lore_builder_question", self.lore_builder.answer_question)
            builder.add_node("judge", self.judge.evaluate_turn)
            builder.add_node("world_engine_update", self.world_engine.update_world)
            builder.add_node("player_creator_update", self.player_proxy.update_players)
            builder.add_node("director", self.director.direct_scene)
            builder.add_node("dm_outcome", self.dm.narrate_outcome)
            builder.add_node("exit_check", self._exit_check_node)

            logger.debug("Registered all graph nodes")

            # ============================================================
            # 2. DEFINE ROUTING LOGIC
            # ============================================================

            def route_entry(state: GameState) -> Literal["story_architect", "dm_planner"]:
                """
                Route entry point: either start setup or jump to gameplay.
                Check if world is already initialized (locations populated).
                """
                world = state.get("world")

                # If world has locations, we're resuming or in gameplay
                if world and world.locations and len(world.regions) > 0:
                    logger.debug("Routing to dm_planner (world already initialized)")
                    return "dm_planner"

                # Otherwise start from beginning
                logger.debug("Routing to story_architect (new game)")
                return "story_architect"

            def route_dm_plan(
                state: GameState,
            ) -> Literal["action_resolver", "lore_builder_question", "exit_check"]:
                """
                Route DM's plan based on response_type.
                DM must set: state["response_type"] to one of:
                - "action": player performed an action
                - "question": player asked a question
                - "exit": player wants to quit
                """
                response_type = state.get("response_type", "unknown")

                if not response_type:
                    logger.warning("DM response_type not set, defaulting to exit_check")
                    return "exit_check"

                response_type_lower = str(response_type).lower().strip()

                if response_type_lower == "action":
                    logger.debug("DM plan routed to action_resolver")
                    return "action_resolver"
                elif response_type_lower == "question":
                    logger.debug("DM plan routed to lore_builder_question")
                    return "lore_builder_question"
                elif response_type_lower == "exit":
                    logger.debug("DM plan routed to exit_check")
                    return "exit_check"
                else:
                    logger.warning(
                        f"Unknown response_type: {response_type}. Routing to exit_check."
                    )
                    return "exit_check"

            def route_judge(state: GameState) -> Literal["action_resolver", "world_engine_update"]:
                """
                Quality Assurance routing - Judge evaluates outcome.
                If invalid and retries remaining, loop back to resolver.
                Otherwise proceed to state updates.
                """
                verdict = state.get("last_verdict")
                retry_count = state.get("_retry_count", 0)

                # Valid verdict: proceed
                if verdict and verdict.is_valid:
                    logger.debug("Judge verdict valid. Proceeding to world_engine_update.")
                    state["_retry_count"] = 0
                    return "world_engine_update"

                # Invalid verdict with retries remaining: retry resolution
                if verdict and not verdict.is_valid and retry_count < self._max_retry_attempts:
                    retry_count += 1
                    state["_retry_count"] = retry_count
                    logger.warning(
                        f"Judge rejected turn (attempt {retry_count}/{self._max_retry_attempts}). "
                        f"Feedback: {verdict.correction_suggestion}"
                    )
                    return "action_resolver"

                # Max retries exceeded: proceed anyway
                if retry_count >= self._max_retry_attempts:
                    logger.warning(
                        f"Max retry attempts ({self._max_retry_attempts}) reached. Proceeding anyway."
                    )
                    state["_retry_count"] = 0
                    return "world_engine_update"

                # No verdict: proceed to update
                logger.debug("No judge verdict. Proceeding to world_engine_update.")
                return "world_engine_update"

            # ============================================================
            # 3. DEFINE EDGES
            # ============================================================

            # --- Entry Point ---
            builder.add_conditional_edges(START, route_entry)

            # --- Phase 1: Setup Pipeline (Linear Flow) -> EXIT ---
            builder.add_edge("story_architect", "lore_builder")
            builder.add_edge("lore_builder", "world_engine")
            builder.add_edge("world_engine", "player_creator")
            builder.add_edge("player_creator", "initial_dm")
            builder.add_edge("initial_dm", END)

            # --- Phase 2: Single-Turn Gameplay ---
            builder.add_conditional_edges("dm_planner", route_dm_plan)

            # Action resolution path: Action -> Judge -> Update path
            builder.add_edge("action_resolver", "judge")
            builder.add_conditional_edges("judge", route_judge)

            # Update path: World -> Players -> Director -> Outcome -> END
            builder.add_edge("world_engine_update", "player_creator_update")
            builder.add_edge("player_creator_update", "director")
            builder.add_edge("director", "dm_outcome")

            # Question resolution path: Question -> Director -> Outcome -> END
            builder.add_edge("lore_builder_question", "director")
            builder.add_edge("director", "dm_outcome")

            # Return to next turn
            builder.add_edge("dm_outcome", END)

            # Exit path
            builder.add_edge("exit_check", END)

            logger.debug("All graph edges defined")

            # ============================================================
            # 4. COMPILE GRAPH
            # ============================================================
            self.compiled_graph = builder.compile(checkpointer=self.memory)
            logger.info("Graph compiled successfully")

        except Exception as e:
            logger.error(f"Failed to build pipeline: {e}", exc_info=True)
            raise RuntimeError(f"Graph building failed: {e}") from e

    async def cleanup(self) -> None:
        """Cleanup resources, especially the AsyncSqliteSaver connection."""
        if self._checkpointer_cm is not None:
            try:
                await self._checkpointer_cm.__aexit__(None, None, None)
                logger.info("AsyncSqliteSaver connection closed")
            except Exception as e:
                logger.warning(f"Error closing AsyncSqliteSaver: {e}")
            finally:
                self._checkpointer_cm = None
                self.memory = MemorySaver()  # Fallback to in-memory

    async def initialize_world(self, state: GameState) -> GameState:
        """
        Phase 1: Initialize the world through the setup pipeline.

        Flow:
        1. StoryArchitectAgent creates narrative blueprint
        2. LoreBuilderAgent creates world lore
        3. WorldEngineAgent creates locations and NPCs
        4. PlayerProxyAgent.process() creates characters IN PARALLEL (via Send API)
        5. DungeonMasterAgent provides initial narration
        6. Graph exits and returns state

        Args:
            state: Initial GameState

        Returns:
            GameState after setup completion

        Raises:
            RuntimeError: If initialization fails
        """
        # Force clean old map
        self.workflow = None
        self.compiled_graph = None

        if not self.compiled_graph:
            logger.debug("Graph not compiled. Building pipeline...")
            await self.build_pipeline()

        session_id = state["metadata"].get("session_id", "default_session")
        config = {"configurable": {"thread_id": session_id}}

        logger.info(f"Starting world initialization (session: {session_id})")
        logger.info(
            "Phase 1: Story Architect -> Lore Builder -> World Engine -> Player Creator (PARALLEL) -> Initial DM -> Complete"
        )

        # Prepare state - reset for clean Phase 1
        clean_state = state.copy()
        clean_state["last_outcome"] = None
        clean_state["players"] = []
        clean_state["response_type"] = "unknown"

        try:
            # Run graph WITHOUT passing services to GameState
            final_state = await self.compiled_graph.ainvoke(clean_state, config=config)
            logger.info("World initialization completed successfully")

            # Log what was created
            players = final_state.get("players", [])
            narrative = final_state.get("narrative")
            world = final_state.get("world")

            logger.info(f"Created: {len(players)} characters")
            if narrative:
                logger.info(f"Campaign: {narrative.title}")
            if world:
                logger.info(
                    f"World has {len(world.locations)} locations and {len(world.active_npcs)} NPCs"
                )

            # Log collaboration hub statistics
            hub_stats = self.context_hub.get_statistics()
            logger.info(
                f"Context Hub: {hub_stats['total_messages']} messages, "
                f"{hub_stats['active_agents']} active agents"
            )
            kg_report = self.knowledge_graph.generate_consistency_report()
            logger.info(
                f"Knowledge Graph: {kg_report['total_entities']} entities, "
                f"{kg_report['total_relations']} relations, "
                f"consistency={kg_report['consistency_score']:.0%}"
            )
            
            # Initialize Phase 3 gameplay executor
            campaign_id = state["metadata"].get("campaign_id", "campaign_001")
            self.gameplay_executor.initialize_gameplay_phase(
                final_state,
                campaign_id,
                session_id
            )
            logger.info("Phase 3 Gameplay Executor initialized")

            return final_state

        except Exception as e:
            logger.error(f"World initialization failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize world: {e}") from e

    async def execute_turn(
        self, state: GameState, config: dict[str, Any] | None = None
    ) -> tuple[GameState, Any]:
        """
        Phase 2/3: Execute a single game turn using comprehensive gameplay loop.

        This executes all 7 steps of the gameplay loop:
        1. Player Action Generation
        2. Action Validation & Rule Adjudication
        3. Environment & Lore Update
        4. Narrative Description & Dialogue
        5. Director Oversight & Pacing
        6. Event Recording & Memory Sync
        7. Loop Iteration & Scene Transition

        Args:
            state: Current GameState
            config: Optional LangGraph config (session ID, etc.)

        Returns:
            Tuple of (updated GameState, GameplayPhaseState)

        Raises:
            RuntimeError: If turn execution fails
        """
        if not self.compiled_graph:
            logger.debug("Graph not compiled. Building pipeline...")
            await self.build_pipeline()

        session_id = state["metadata"].get("session_id", "default_session")
        turn = state["metadata"].get("turn", 0)

        if config is None:
            config = {"configurable": {"thread_id": session_id}}

        logger.info(f"Executing turn {turn} (session: {session_id})")

        try:
            # Use GameplayExecutor for comprehensive turn orchestration
            updated_state, gameplay_state = await self.gameplay_executor.execute_turn(
                state,
                self.resolver,
                self.judge,
                self.world_engine,
                self.lore_builder,
                self.dm,
                self.director
            )
            logger.debug(f"Turn {turn} completed successfully")
            return updated_state, gameplay_state

        except Exception as e:
            logger.error(f"Turn {turn} execution failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to execute turn: {e}") from e

    def _exit_check_node(self, state: GameState) -> GameState:
        """
        Check if the game should exit based on recent messages.

        Looks for exit keywords in the last message from the state.
        Sets state["__end__"] = True if exit is detected.

        Args:
            state: Current GameState

        Returns:
            Updated GameState
        """
        exit_keywords = ["quit", "exit", "end", "goodbye", "bye"]

        messages = state.get("messages", [])
        if messages:
            # Get the last message content
            last_msg = messages[-1]
            msg_content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
            msg_lower = msg_content.lower()

            # Check for exit keywords
            if any(keyword in msg_lower for keyword in exit_keywords):
                logger.info("Exit command detected. Ending game.")
                state["__end__"] = True

        return state


# Global singleton instance
orchestrator_service = OrchestratorService()
