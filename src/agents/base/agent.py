from abc import ABC, abstractmethod
from typing import Any
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from src.core.types import GameState


class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.graph = None

    @abstractmethod
    def build_graph(self) -> StateGraph:
        pass

    @abstractmethod
    async def process(self, state: GameState, runtime: Runtime) -> dict[str, Any]:
        pass

    def compile(self):
        self.graph = self.build_graph().compile(name=self.name)
        return self.graph
