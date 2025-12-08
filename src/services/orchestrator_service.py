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
        self.initialization_graph = None
        self.gameplay_graph = None
        self.memory = MemorySaver()

        self.architect = StoryArchitectAgent()
        self.lore_builder = LoreBuilderAgent()
        self.world_engine = WorldEngineAgent()
        self.player_creator = PlayerProxyAgent()

        self.resolver = ActionResolverAgent()
        self.judge = JudgeAgent()
        self.director = DirectorAgent()
        self.dm = DungeonMasterAgent()

    def build_initialization_graph(self):
        builder = StateGraph(GameState)
        
        builder.add_node("story_architect", self.architect.plan_narrative)
        builder.add_node("lore_builder", self.lore_builder.build_lore)
        builder.add_node("world_engine", self.world_engine.build_graph().compile())
        builder.add_node("player_creator", self.player_creator.build_graph().compile())
        
        builder.add_edge(START, "story_architect")
        builder.add_edge("story_architect", "lore_builder")
        builder.add_edge("lore_builder", "world_engine")
        builder.add_edge("world_engine", "player_creator")
        builder.add_edge("player_creator", END)
        
        self.initialization_graph = builder.compile()

    def build_gameplay_graph(self):
        builder = StateGraph(GameState)
        
        builder.add_node("action_resolver", self.resolver.resolve_action)
        builder.add_node("judge", self.judge.evaluate_turn)
        builder.add_node("director", self.director.direct_scene)
        builder.add_node("dungeon_master", self.dm.narrate_outcome)
        
        def route_judge(state: GameState) -> Literal["action_resolver", "director"]:
            verdict = state.get("last_verdict")
            if verdict and not verdict.is_valid:
                print(f"[!] Judge rejected action: {verdict.correction_suggestion}")
                return "action_resolver"
            return "director"
        
        builder.add_edge(START, "action_resolver")
        builder.add_edge("action_resolver", "judge")
        builder.add_conditional_edges("judge", route_judge)
        builder.add_edge("director", "dungeon_master")
        builder.add_edge("dungeon_master", END)
        
        self.gameplay_graph = builder.compile()

    async def initialize_world(self, state: GameState) -> GameState:
        if not self.initialization_graph:
            self.build_initialization_graph()
        return await self.initialization_graph.ainvoke(state)

    async def execute_turn(self, state: GameState) -> GameState:
        if not self.gameplay_graph:
            self.build_gameplay_graph()
        return await self.gameplay_graph.ainvoke(state)


orchestrator_service = OrchestratorService()
