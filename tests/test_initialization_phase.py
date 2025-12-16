"""Comprehensive tests for the enhanced initialization phase with collaboration services."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.orchestrator_service import OrchestratorService
from src.services.agent_context_hub import AgentContextHub, AgentMessage, MessageType
from src.services.knowledge_graph_service import KnowledgeGraphService
from src.core.agent_specialization import SpecializationContext, GamePhase
from src.core.types import GameState, Setting, NarrativeState, WorldState


@pytest.fixture
def orchestrator():
    """Create orchestrator instance for testing."""
    return OrchestratorService()


@pytest.fixture
def context_hub():
    """Create context hub instance."""
    return AgentContextHub()


@pytest.fixture
def knowledge_graph():
    """Create knowledge graph instance."""
    return KnowledgeGraphService()


@pytest.fixture
def test_setting():
    """Create test setting."""
    return Setting(
        theme="Fantasy",
        tone="Dark",
        player_concepts=["Brave Knight", "Wise Mage", "Cunning Rogue"],
        story_length=2000,
    )


@pytest.fixture
def initial_game_state(test_setting):
    """Create initial game state."""
    return GameState(
        setting=test_setting,
        metadata={
            "session_id": "test_session_123",
            "turn": 0,
            "timestamp": "2025-12-16T20:00:00Z",
        },
        players=[],
        narrative=None,
        world=None,
        messages=[],
    )


class TestAgentContextHub:
    """Test suite for AgentContextHub."""

    def test_hub_initialization(self, context_hub):
        """Test context hub initializes correctly."""
        assert context_hub is not None
        assert len(context_hub.message_queue) == 0
        assert len(context_hub.agent_memory) == 0

    def test_broadcast_message(self, context_hub):
        """Test broadcasting messages to hub."""
        message = AgentMessage(
            sender="Story Architect",
            message_type=MessageType.NARRATIVE_UPDATE,
            content={"title": "Test Campaign", "entities": 5},
        )

        context_hub.broadcast(message)

        assert len(context_hub.message_queue) == 1
        assert context_hub.message_queue[0].sender == "Story Architect"

    def test_get_context_for_agent(self, context_hub):
        """Test retrieving context for specific agent."""
        msg1 = AgentMessage(
            sender="Lore Builder",
            message_type=MessageType.WORLD_CHANGE,
            content={"regions": 3},
        )
        msg2 = AgentMessage(
            sender="World Engine",
            message_type=MessageType.WORLD_CHANGE,
            content={"locations": 9},
        )

        context_hub.broadcast(msg1)
        context_hub.broadcast(msg2)

        context = context_hub.get_context_for_agent("World Engine", limit=5)
        assert len(context) <= 5
        assert any(msg["sender"] == "Lore Builder" for msg in context)

    def test_get_lore_context(self, context_hub):
        """Test getting lore-specific context."""
        message = AgentMessage(
            sender="Lore Builder",
            message_type=MessageType.LORE_RESPONSE,
            content={"answer": "Dragons are powerful creatures"},
        )
        context_hub.broadcast(message)

        lore_ctx = context_hub.get_lore_context()
        assert "lore_updates" in lore_ctx
        assert "recent_changes" in lore_ctx
        assert len(lore_ctx["lore_updates"]) > 0

    def test_hub_statistics(self, context_hub):
        """Test hub statistics reporting."""
        for i in range(3):
            msg = AgentMessage(
                sender=f"Agent_{i}",
                message_type=MessageType.NARRATIVE_UPDATE,
                content={},
            )
            context_hub.broadcast(msg)

        stats = context_hub.get_statistics()
        assert stats["total_messages"] == 3
        assert stats["active_agents"] == 3
        assert "NARRATIVE_UPDATE" in stats["messages_by_type"]


class TestKnowledgeGraphService:
    """Test suite for KnowledgeGraphService."""

    def test_graph_initialization(self, knowledge_graph):
        """Test knowledge graph initializes correctly."""
        assert knowledge_graph is not None
        assert len(knowledge_graph.entities) == 0
        assert len(knowledge_graph.links) == 0

    def test_add_entity(self, knowledge_graph):
        """Test adding entities to graph."""
        knowledge_graph.add_entity(
            "loc_castle",
            "location",
            {"name": "Castle of Shadows", "danger": "High"},
        )

        assert "loc_castle" in knowledge_graph.entities
        assert knowledge_graph.entities["loc_castle"]["type"] == "location"

    def test_add_relation(self, knowledge_graph):
        """Test adding relationships between entities."""
        knowledge_graph.add_entity("char_hero", "character", {"name": "Hero"})
        knowledge_graph.add_entity("loc_castle", "location", {"name": "Castle"})

        knowledge_graph.add_relation(
            "char_hero",
            "located_in",
            "loc_castle",
            confidence=1.0,
            source_agent="World Engine",
        )

        assert len(knowledge_graph.links) == 1
        assert knowledge_graph.links[0].source == "char_hero"

    def test_get_connected_entities(self, knowledge_graph):
        """Test retrieving connected entities."""
        knowledge_graph.add_entity("char_hero", "character", {})
        knowledge_graph.add_entity("char_companion", "character", {})
        knowledge_graph.add_entity("item_sword", "item", {})

        knowledge_graph.add_relation("char_hero", "allies", "char_companion")
        knowledge_graph.add_relation("char_hero", "possesses", "item_sword")

        connected = knowledge_graph.get_connected("char_hero")
        assert len(connected) == 2
        assert "char_companion" in connected
        assert "item_sword" in connected

    def test_consistency_report(self, knowledge_graph):
        """Test generating consistency report."""
        # Add some entities and relations
        for i in range(5):
            knowledge_graph.add_entity(f"entity_{i}", "generic", {})
        for i in range(4):
            knowledge_graph.add_relation(f"entity_{i}", "relates_to", f"entity_{i+1}")

        report = knowledge_graph.generate_consistency_report()

        assert report["total_entities"] == 5
        assert report["total_relations"] == 4
        assert 0 <= report["consistency_score"] <= 1


class TestSpecializationContext:
    """Test suite for SpecializationContext."""

    def test_specialization_initialization(self, initial_game_state):
        """Test specialization context initializes with game state."""
        spec = SpecializationContext(initial_game_state)

        assert spec is not None
        assert spec.game_phase == GamePhase.SETUP
        assert 0 <= spec.tension_level <= 1
        assert 0 <= spec.player_engagement <= 1

    def test_game_phase_progression(self):
        """Test game phase determination based on turn count."""
        states = [
            ({"metadata": {"turn": 0}}, GamePhase.SETUP),
            ({"metadata": {"turn": 5}}, GamePhase.EXPLORATION),
            ({"metadata": {"turn": 15}}, GamePhase.CONFLICT),
            ({"metadata": {"turn": 25}}, GamePhase.CLIMAX),
            ({"metadata": {"turn": 35}}, GamePhase.RESOLUTION),
        ]

        for state, expected_phase in states:
            spec = SpecializationContext(state)
            assert spec.game_phase == expected_phase

    def test_specialization_prompt_generation(self, initial_game_state):
        """Test generating specialization prompts for agents."""
        spec = SpecializationContext(initial_game_state)

        dm_prompt = spec.get_specialization_prompt("dungeon_master")
        ar_prompt = spec.get_specialization_prompt("action_resolver")
        director_prompt = spec.get_specialization_prompt("director")

        assert dm_prompt is not None and len(dm_prompt) > 0
        assert ar_prompt is not None and len(ar_prompt) > 0
        assert director_prompt is not None and len(director_prompt) > 0

    def test_specialization_dict_export(self, initial_game_state):
        """Test exporting specialization context as dictionary."""
        spec = SpecializationContext(initial_game_state)
        spec_dict = spec.to_dict()

        assert "game_phase" in spec_dict
        assert "narrative_pace" in spec_dict
        assert "tension_level" in spec_dict
        assert "player_engagement" in spec_dict
        assert "discovery_state" in spec_dict


class TestOrchestratorIntegration:
    """Integration tests for orchestrator with collaboration services."""

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, orchestrator):
        """Test orchestrator initializes with all services."""
        assert orchestrator.context_hub is not None
        assert orchestrator.knowledge_graph is not None
        assert orchestrator.architect is not None
        assert orchestrator.lore_builder is not None
        assert orchestrator.world_engine is not None

    @pytest.mark.asyncio
    async def test_context_hub_in_state(self, orchestrator, initial_game_state):
        """Test context hub is properly passed through game state."""
        initial_game_state["_context_hub"] = orchestrator.context_hub
        initial_game_state["knowledge_graph"] = orchestrator.knowledge_graph

        assert initial_game_state["_context_hub"] is orchestrator.context_hub
        assert initial_game_state["knowledge_graph"] is orchestrator.knowledge_graph

    @pytest.mark.asyncio
    async def test_orchestrator_build_pipeline(self, orchestrator):
        """Test orchestrator can build the full pipeline."""
        await orchestrator.build_pipeline()
        assert orchestrator.compiled_graph is not None

    @pytest.mark.asyncio
    async def test_orchestrator_cleanup(self, orchestrator):
        """Test orchestrator cleanup procedure."""
        await orchestrator.build_pipeline()
        await orchestrator.cleanup()
        # Should not raise any exceptions


class TestMessageFlow:
    """Test message flow through collaboration services."""

    def test_narrative_message_flow(self, context_hub):
        """Test narrative update message flows correctly."""
        msg = AgentMessage(
            sender="Story Architect",
            message_type=MessageType.NARRATIVE_UPDATE,
            content={"title": "The Dark Tower", "entities": 12},
            target_agents=["Lore Builder", "Director"],
        )
        context_hub.broadcast(msg)

        latest = context_hub.get_latest_narrative_context()
        assert latest is not None
        assert latest["title"] == "The Dark Tower"

    def test_world_change_message_flow(self, context_hub):
        """Test world change message flows correctly."""
        msg = AgentMessage(
            sender="Lore Builder",
            message_type=MessageType.WORLD_CHANGE,
            content={"world_name": "Azeroth", "regions": 5},
        )
        context_hub.broadcast(msg)

        updates = context_hub.get_world_state_updates(limit=5)
        assert len(updates) > 0
        assert updates[0]["content"]["world_name"] == "Azeroth"

    def test_judge_verdict_message_flow(self, context_hub):
        """Test judge verdict message flows correctly."""
        msg = AgentMessage(
            sender="Rule Judge",
            message_type=MessageType.JUDGE_VERDICT,
            content={"valid": True, "note": "Action outcome is consistent"},
            requires_response=False,
        )
        context_hub.broadcast(msg)

        stats = context_hub.get_statistics()
        assert stats["messages_by_type"][MessageType.JUDGE_VERDICT.value] == 1


if __name__ == "__main__":
    # Run tests with: pytest tests/test_initialization_phase.py -v
    pytest.main([__file__, "-v"])
