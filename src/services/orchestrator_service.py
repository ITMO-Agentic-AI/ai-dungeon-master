# src/services/orchestrator_service.py

from typing import Literal, Dict, Any
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver

from src.core.types import GameState

# Import Agents - Corrected import path
from src.agents.story_architect.graph import StoryArchitectAgent
from src.agents.lore_builder.graph import LoreBuilderAgent
from src.agents.world_engine.graph import WorldEngineAgent

from src.agents.player_proxy.graph import PlayerProxyAgent  # Corrected import

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
        self.player_creator = PlayerProxyAgent() # Corrected instantiation

        self.resolver = ActionResolverAgent()
        self.judge = JudgeAgent()
        self.director = DirectorAgent()
        self.dm = DungeonMasterAgent()

    def build_pipeline(self):
        builder = StateGraph(GameState)

        # REGISTER NODES
        builder.add_node("story_architect", self.architect.plan_narrative)
        builder.add_node("lore_builder", self.lore_builder.build_lore)
        builder.add_node("world_engine", self.world_engine.process)  # 调用process因为world_engine内部有router判断
        builder.add_node("player_creator", self.player_creator.process)  # 调用process因为player_proxy内部有router判断

        builder.add_node("action_resolver", self.resolver.resolve_action)
        builder.add_node("judge", self.judge.evaluate_turn)
        builder.add_node("director", self.director.direct_scene)
        builder.add_node("dungeon_master", self.dm.narrate_outcome)

        # DEFINE ROUTING LOGIC
        def route_entry(state: GameState) -> Literal["story_architect", "action_resolver"]:
            world = state.get("world")
            if world and world.locations:
                return "action_resolver"
            return "story_architect"

        def route_judge(state: GameState) -> Literal["action_resolver", "director"]:
            verdict = state.get("last_verdict")
            if verdict and not verdict.is_valid:
                print(f" [!] Judge Rejected Turn: {verdict.feedback}. Retrying...")
                return "action_resolver"
            return "director"

        # DEFINE EDGES
        builder.add_conditional_edges(START, route_entry)

        builder.add_edge("story_architect", "lore_builder")
        builder.add_edge("lore_builder", "world_engine")
        builder.add_edge("world_engine", "player_creator")
        builder.add_edge("player_creator", END)

        builder.add_edge("action_resolver", "judge")
        builder.add_conditional_edges("judge", route_judge)
        builder.add_edge("director", "dungeon_master")
        builder.add_edge("dungeon_master", END)

        # COMPILE
        self.compiled_graph = builder.compile(checkpointer=self.memory)

    async def execute_turn(self, state: GameState, config: Dict[str, Any] = None) -> GameState:
        if not self.compiled_graph:
            self.build_pipeline()

        if config is None:
            config = {"configurable": {"thread_id": "default_session"}}

        final_state = await self.compiled_graph.ainvoke(state, config=config)
        return final_state

orchestrator_service = OrchestratorService()