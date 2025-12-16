# Quick Start: Enhanced Initialization Phase

**Status**: Production-Ready ✅  
**Last Updated**: December 16, 2025  

---

## What You Get

✅ **3 collaboration services** for agent coordination  
✅ **Enhanced Story Architect** - Broadcasts narrative blueprints  
✅ **Enhanced Lore Builder** - Populates knowledge graph  
✅ **Enhanced DM** - Uses specialization for adaptive narration  
✅ **25+ tests** validating all components  
✅ **Zero breaking changes** - Fully backward compatible  

---

## 5-Minute Setup

### 1. Verify Installation

```bash
# Check files are present
ls -la src/services/agent_context_hub.py
ls -la src/services/knowledge_graph_service.py
ls -la src/core/agent_specialization.py

# Run tests
pytest tests/test_initialization_phase.py -v
```

### 2. Test Context Hub

```python
from src.services.agent_context_hub import AgentContextHub, AgentMessage, MessageType

hub = AgentContextHub()

# Create and broadcast a message
msg = AgentMessage(
    sender="Story Architect",
    message_type=MessageType.NARRATIVE_UPDATE,
    content={"title": "Test Campaign", "entities": 10}
)
hub.broadcast(msg)

# Verify
stats = hub.get_statistics()
print(f"Messages: {stats['total_messages']}")
print(f"Agents: {stats['active_agents']}")
```

### 3. Test Knowledge Graph

```python
from src.services.knowledge_graph_service import KnowledgeGraphService

graph = KnowledgeGraphService()

# Add entities
graph.add_entity("npc_hero", "character", {"name": "Hero", "race": "Human"})
graph.add_entity("loc_castle", "location", {"name": "Castle"})

# Add relation
graph.add_relation("npc_hero", "located_in", "loc_castle")

# Verify
report = graph.generate_consistency_report()
print(f"Entities: {report['total_entities']}")
print(f"Relations: {report['total_relations']}")
print(f"Consistency: {report['consistency_score']:.0%}")
```

### 4. Test Specialization

```python
from src.core.agent_specialization import SpecializationContext
from src.core.types import GameState

state = GameState(
    metadata={"turn": 0},
    setting=None,
    players=[],
    narrative=None,
    world=None
)

spec = SpecializationContext(state)
print(f"Phase: {spec.game_phase.value}")
print(f"Tension: {spec.tension_level:.0%}")

# Get DM guidance
guidance = spec.get_specialization_prompt("dungeon_master")
print(guidance)
```

### 5. Run Full Initialization

```python
import asyncio
from src.services.orchestrator_service import orchestrator_service
from src.core.types import GameState, Setting

async def main():
    # Setup
    setting = Setting(
        theme="Fantasy",
        tone="Dark",
        player_concepts=["Warrior", "Mage", "Rogue"],
        story_length=2000
    )
    
    state = GameState(
        setting=setting,
        metadata={
            "session_id": "test_game",
            "turn": 0,
            "timestamp": "2025-12-16T20:00:00Z"
        },
        players=[],
        narrative=None,
        world=None,
        messages=[]
    )
    
    # Initialize world
    final_state = await orchestrator_service.initialize_world(state)
    
    # Check results
    print(f"✅ Campaign: {final_state['narrative'].title}")
    print(f"✅ World: {final_state['world'].overview}")
    print(f"✅ Players: {len(final_state['players'])}")
    
    # Check collaboration data
    hub_stats = orchestrator_service.context_hub.get_statistics()
    print(f"✅ Hub messages: {hub_stats['total_messages']}")
    
    kg_report = orchestrator_service.knowledge_graph.generate_consistency_report()
    print(f"✅ Knowledge entities: {kg_report['total_entities']}")

asyncio.run(main())
```

---

## 3 Collaboration Patterns

### Pattern 1: Agent Context Hub
**What**: Central message bus for agent communication  
**Why**: Agents learn about each other's decisions  
**How**: Broadcast pattern with message history

```python
# Example: Story Architect broadcasts narrative
msg = AgentMessage(
    sender="Story Architect",
    message_type=MessageType.NARRATIVE_UPDATE,
    content={"title": "...", "overview": "..."},
    target_agents=["Lore Builder", "Director"]
)
hub.broadcast(msg)

# Example: Lore Builder consumes context
narrative = hub.get_latest_narrative_context()
```

### Pattern 2: Knowledge Graph
**What**: Semantic relationships between entities  
**Why**: World consistency validation  
**How**: Entity registration + relationship tracking

```python
# Example: Adding world entities
graph.add_entity("npc_warrior", "character", {...})
graph.add_entity("loc_tavern", "location", {...})

# Example: Creating relationships
graph.add_relation("npc_warrior", "located_in", "loc_tavern")

# Example: Validating consistency
report = graph.generate_consistency_report()
```

### Pattern 3: Agent Specialization
**What**: Dynamic behavior adaptation  
**Why**: Better narration for current game state  
**How**: Phase detection + guidance generation

```python
# Example: Get specialization context
spec = SpecializationContext(game_state)

# Example: Generate phase-aware guidance
dm_prompt = spec.get_specialization_prompt("dungeon_master")

# Example: Check current state
phase = spec.game_phase         # SETUP, EXPLORATION, CONFLICT, etc.
tension = spec.tension_level     # 0.0 - 1.0
pace = spec.narrative_pace       # SLOW, NORMAL, FAST, CLIMACTIC
```

---

## Integration Points

### In Orchestrator

```python
# Services are created
self.context_hub = AgentContextHub()
self.knowledge_graph = KnowledgeGraphService()

# Passed to all agents
state["_context_hub"] = self.context_hub
state["knowledge_graph"] = self.knowledge_graph
state["specialization"] = SpecializationContext(state)
```

### In Story Architect

```python
# Get context hub from state
context_hub = state.get("_context_hub")

# Broadcast narrative
if context_hub:
    message = AgentMessage(
        sender="Story Architect",
        message_type=MessageType.NARRATIVE_UPDATE,
        content={...}
    )
    context_hub.broadcast(message)
```

### In Lore Builder

```python
# Get context and knowledge graph
context_hub = state.get("_context_hub")
knowledge_graph = state.get("knowledge_graph")

# Consume narrative context
if context_hub:
    narrative_ctx = context_hub.get_latest_narrative_context()

# Update knowledge graph
if knowledge_graph:
    for region in regions:
        knowledge_graph.add_entity(f"region_{region.name}", "region", {...})
    
    for npc in npcs:
        knowledge_graph.add_entity(f"npc_{npc.name}", "npc", {...})
```

### In Dungeon Master

```python
# Get specialization context
specialization = state.get("specialization")

# Use in prompts
if specialization:
    phase_guidance = specialization.get_specialization_prompt("dungeon_master")
```

---

## Common Tasks

### Check Consistency

```python
report = orchestrator_service.knowledge_graph.generate_consistency_report()

if report['consistency_score'] < 0.8:
    print(f"Warnings: {report['issues']}")
else:
    print("World is consistent!")
```

### Get Communication History

```python
stats = orchestrator_service.context_hub.get_statistics()

print(f"Total messages: {stats['total_messages']}")
print(f"Messages by agent: {stats['messages_by_agent']}")
print(f"Messages by type: {stats['messages_by_type']}")
```

### Find Entity Relationships

```python
# Get all entities connected to a character
connected = graph.get_connected("npc_hero")

# Get relationship context
context = graph.get_entity_context("npc_hero")
print(context['connections'])

# Find path between entities
path = graph.find_path("npc_hero", "loc_castle", max_depth=3)
print(f"Path: {' -> '.join(path)}")
```

### Access Narration Guidance

```python
spec = SpecializationContext(state)

# Get current state
print(f"Game Phase: {spec.game_phase.value}")
print(f"Narrative Pace: {spec.narrative_pace.value}")
print(f"Tension Level: {spec.tension_level:.0%}")
print(f"Engagement: {spec.player_engagement:.0%}")

# Get guidance for agent
guidance = spec.get_specialization_prompt("dungeon_master")
print(guidance)
```

---

## Testing

### Run All Tests

```bash
pytest tests/test_initialization_phase.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_initialization_phase.py::TestAgentContextHub -v
pytest tests/test_initialization_phase.py::TestKnowledgeGraphService -v
pytest tests/test_initialization_phase.py::TestSpecializationContext -v
```

### Run Single Test

```bash
pytest tests/test_initialization_phase.py::TestAgentContextHub::test_broadcast_message -v
```

### Coverage Report

```bash
pytest tests/test_initialization_phase.py --cov=src/services --cov=src/core
```

---

## Troubleshooting

### Messages Not Broadcasting

```python
# Verify hub is initialized
assert orchestrator_service.context_hub is not None

# Check message queue
queue = orchestrator_service.context_hub.message_queue
print(f"Queue length: {len(queue)}")

# Verify message format
msg = AgentMessage(
    sender="AgentName",
    message_type=MessageType.NARRATIVE_UPDATE,
    content={...}
)
print(msg.to_dict())
```

### Knowledge Graph Empty

```python
# Verify Lore Builder is populating graph
report = graph.generate_consistency_report()
print(f"Entities: {report['total_entities']}")
print(f"Relations: {report['total_relations']}")

# Check if regions were added
regions = graph.get_entities_by_type("region")
print(f"Regions: {regions}")

# Check imports
assert graph.import_from_dict is not None
```

### Specialization Not Adapting

```python
# Verify context was created
spec = state.get("specialization")
assert spec is not None

# Check phase calculation
print(f"Turn: {state['metadata']['turn']}")
print(f"Phase: {spec.game_phase.value}")

# Check tension calculation
print(f"Tension: {spec.tension_level}")
```

---

## Performance Tips

1. **Context Hub**: Clear history periodically for long sessions
   ```python
   if len(hub.message_queue) > 1000:
       hub.clear_history()
   ```

2. **Knowledge Graph**: Use `max_depth` limit for pathfinding
   ```python
   path = graph.find_path(start, end, max_depth=3)  # Not unlimited
   ```

3. **Specialization**: Cache context if checking repeatedly
   ```python
   spec = SpecializationContext(state)  # Create once
   guidance_1 = spec.get_specialization_prompt("dungeon_master")
   guidance_2 = spec.get_specialization_prompt("director")
   ```

---

## Next Steps

1. ✅ Run tests: `pytest tests/test_initialization_phase.py -v`
2. ✅ Initialize world: Follow "Run Full Initialization" above
3. ✅ Play a game: Use `orchestrator.execute_turn(state)`
4. ✅ Monitor output: Check hub statistics and knowledge graph
5. ✅ Iterate: Use consistency reports to improve world

---

## Files Reference

| File | Purpose | Lines |
|------|---------|-------|
| `src/services/agent_context_hub.py` | Message bus | 220 |
| `src/services/knowledge_graph_service.py` | Semantic relationships | 310 |
| `src/core/agent_specialization.py` | Dynamic adaptation | 260 |
| `tests/test_initialization_phase.py` | Comprehensive tests | 360 |
| `src/services/orchestrator_service.py` | Enhanced (modified) | +450 |
| `src/agents/story_architect/graph.py` | Enhanced (modified) | +35 |
| `src/agents/lore_builder/graph.py` | Enhanced (modified) | +55 |
| `src/agents/dungeon_master/graph.py` | Enhanced (modified) | +60 |

---

## Success Indicators
✅ All tests passing  
✅ Context hub messages flowing  
✅ Knowledge graph populated  
✅ World consistency >80%  
✅ Specialization context active  
✅ No performance regressions  

---

**Ready to play!** 💎
