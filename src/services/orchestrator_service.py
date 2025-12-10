from typing import Literal, Dict, Any
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from src.core.types import GameState

# Import Agents
from src.agents.story_architect.graph import StoryArchitectAgent
from src.agents.lore_builder.graph import LoreBuilderAgent
from src.agents.world_engine.graph import WorldEngineAgent
from src.agents.player_proxy.graph import PlayerCreatorAgent
from src.agents.action_resolver.graph import ActionResolverAgent
from src.agents.rule_judge.graph import JudgeAgent
from src.agents.director.graph import DirectorAgent
from src.agents.dungeon_master.graph import DungeonMasterAgent


class OrchestratorService:
    def __init__(self):
        self.workflow = None
        self.compiled_graph = None
        self.memory = MemorySaver()

        # Instantiate all agents
        self.architect = StoryArchitectAgent()
        self.lore_builder = LoreBuilderAgent()
        self.world_engine = WorldEngineAgent()
        self.player_creator = PlayerCreatorAgent()

        self.resolver = ActionResolverAgent()
        self.judge = JudgeAgent()
        self.director = DirectorAgent()
        self.dm = DungeonMasterAgent()

    def build_pipeline(self):
        """
        Constructs the Master Graph connecting all sub-agents according to the React pattern.
        """
        builder = StateGraph(GameState)

        # ============================================================
        # 1. REGISTER NODES
        # ============================================================

        # --- Initialization Phase Nodes ---
        builder.add_node("story_architect", self.architect.plan_narrative)
        builder.add_node("lore_builder", self.lore_builder.build_lore)
        builder.add_node("world_engine", self.world_engine.instantiate_world)
        builder.add_node("player_creator", self.player_creator.create_characters)
        # NEW: Initial DM Narration
        builder.add_node("initial_dm", self.dm.narrate_initial)

        # --- Gameplay Loop Nodes ---
        builder.add_node("dm_planner", self.dm.plan_response) # Central planner
        builder.add_node("action_resolver", self.resolver.resolve_action)
        builder.add_node("lore_builder_question", self.lore_builder.answer_question) # New node for questions
        builder.add_node("judge", self.judge.evaluate_turn)
        builder.add_node("director", self.director.direct_scene)
        builder.add_node("dm_outcome", self.dm.narrate_outcome) # Final narration

        # ============================================================
        # 2. DEFINE ROUTING LOGIC
        # ============================================================

        def route_entry(state: GameState) -> Literal["story_architect", "dm_planner"]:
            """
            Determines if we are starting a new game or playing a turn.
            Checks if 'world.locations' exists to decide.
            """
            world = state.get("world")
            # If we have locations, the world is built -> Go to Game Loop
            if world and world.locations:
                return "dm_planner"
            # Otherwise -> Start Initialization
            return "story_architect"

        def route_dm_plan(state: GameState) -> Literal["action_resolver", "lore_builder_question", "dm_outcome"]:
            """
            Routes the DM's plan based on whether it's an action or a question.
            This requires the DM Planner to set a flag in the state.
            """
            # Assume the DM Planner sets a field like 'response_type' in the state
            response_type = state.get("response_type", "unknown")

            if response_type == "action":
                return "action_resolver"
            elif response_type == "question":
                return "lore_builder_question"
            else:
                # If no clear type, default to final narration (might be a simple message)
                return "dm_outcome"

        def route_judge(state: GameState) -> Literal["action_resolver", "director"]:
            """
            The Quality Assurance Loop.
            If the Judge flags the action/outcome as invalid, retry resolution.
            """
            verdict = state.get("last_verdict")
            if verdict and not verdict.is_valid:
                print(f" [!] Judge Rejected Turn: {verdict.feedback}. Retrying...")
                # We loop back to the resolver.
                return "action_resolver"

            # If valid, proceed to Director
            return "director"

        # ============================================================
        # 3. DEFINE EDGES
        # ============================================================

        # --- Entry Point ---
        builder.add_conditional_edges(START, route_entry)

        # --- Initialization Flow (Linear) ---
        builder.add_edge("story_architect", "lore_builder")
        builder.add_edge("lore_builder", "world_engine")
        builder.add_edge("world_engine", "player_creator")
        # NEW: After player creation, generate initial narration
        builder.add_edge("player_creator", "initial_dm")
        # After initial narration, go to the main game loop
        builder.add_edge("initial_dm", "dm_planner") # Or END if you want to wait for user input first

        # --- Game Loop Flow ---
        # 1. DM Planner receives input and decides next step
        builder.add_node("dm_planner", self.dm.plan_response) # Already added above
        # 2. Route based on DM's decision
        builder.add_conditional_edges("dm_planner", route_dm_plan)

        # 3. For Actions: Resolver -> Judge -> Director -> DM Outcome
        builder.add_edge("action_resolver", "judge")
        builder.add_conditional_edges("judge", route_judge)
        builder.add_edge("director", "dm_outcome")

        # 4. For Questions: Lore Builder -> Director -> DM Outcome
        builder.add_edge("lore_builder_question", "director")
        builder.add_edge("director", "dm_outcome")

        # 5. DM Outcome returns to DM Planner for the next turn
        builder.add_edge("dm_outcome", "dm_planner")

        # 6. Define an end condition (e.g., if game over)
        # For now, we loop indefinitely until interrupted.
        # You could add a conditional edge from dm_outcome to END based on a game_over flag.

        # ============================================================
        # 4. COMPILE
        # ============================================================
        self.compiled_graph = builder.compile(checkpointer=self.memory)

    async def execute_turn(self, state: GameState, config: Dict[str, Any] = None) -> GameState:
        """
        The main entry point for the external application (FastAPI/CLI).
        """
        if not self.compiled_graph:
            self.build_pipeline()

        if config is None:
            config = {"configurable": {"thread_id": "default_session"}}

        # Invoke the graph
        final_state = await self.compiled_graph.ainvoke(state, config=config)
        return final_state

# Global instance
orchestrator_service = OrchestratorService()