from typing import Literal, Dict, Any
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

# Import Types
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
        self.memory = MemorySaver() # Persist state between turns if needed
        
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
        Constructs the Master Graph connecting all sub-agents.
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
        
        # --- Gameplay Loop Nodes ---
        builder.add_node("action_resolver", self.resolver.resolve_action)
        builder.add_node("judge", self.judge.evaluate_turn)
        builder.add_node("director", self.director.direct_scene)
        builder.add_node("dungeon_master", self.dm.narrate_outcome)

        # ============================================================
        # 2. DEFINE ROUTING LOGIC
        # ============================================================

        def route_entry(state: GameState) -> Literal["story_architect", "action_resolver"]:
            """
            Determines if we are starting a new game or playing a turn.
            Checks if 'world.locations' exists to decide.
            """
            world = state.get("world")
            # If we have locations, the world is built -> Go to Game Loop
            if world and world.locations:
                return "action_resolver"
            # Otherwise -> Start Initialization
            return "story_architect"

        def route_judge(state: GameState) -> Literal["action_resolver", "director"]:
            """
            The Quality Assurance Loop.
            If the Judge flags the action/outcome as invalid, retry resolution.
            """
            verdict = state.get("last_verdict")
            if verdict and not verdict.is_valid:
                print(f" [!] Judge Rejected Turn: {verdict.feedback}. Retrying...")
                # We loop back to the resolver. 
                # (In a production app, you should inject the feedback into the context 
                # so the resolver knows why it failed).
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
        # After creation, we stop and wait for the user to trigger the first turn
        builder.add_edge("player_creator", END)

        # --- Game Loop Flow ---
        # 1. Resolver -> Judge
        builder.add_edge("action_resolver", "judge")
        
        # 2. Judge -> (Director OR Back to Resolver)
        builder.add_conditional_edges("judge", route_judge)
        
        # 3. Director -> DM
        builder.add_edge("director", "dungeon_master")
        
        # 4. DM -> End (Turn Complete)
        builder.add_edge("dungeon_master", END)

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
        
        # Ensure config has a thread_id for memory persistence
        if config is None:
            config = {"configurable": {"thread_id": "default_session"}}

        # Invoke the graph
        # The graph will automatically route based on the state provided
        final_state = await self.compiled_graph.ainvoke(state, config=config)
        return final_state

# Global instance
orchestrator_service = OrchestratorService()
