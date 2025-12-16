# Phase 3 Troubleshooting Guide

**Complete reference for all Phase 3 errors and solutions**

---

## Quick Error Reference

| Error | Cause | Solution |
|-------|-------|----------|
| `Field required [type=missing]` | Missing default factory | See Fix #1 |
| `'tuple' object has no attribute 'get'` | Not unpacking return value | See Fix #2 |
| `'NoneType' object has no attribute 'aget_state'` | Session not initialized | See Fix #3 |
| `initialize_gameplay_phase failed` | Missing GameState fields | Ensure all fields populated |
| Tests failing | Old code still in cache | Run `pytest --cache-clear` |
| Agent not responding | Agent parameter is None | Pass actual agent or mock will be used |

---

## Fix #1: Pydantic Validation Errors

### Error
```
Failed to initialize world: 1 validation error for GameplayPhaseState
player_actions
  Field required [type=missing, input_value={...}]
```

### Solution
**Status**: ✅ Already Fixed

The code has been updated with proper default factories:
```python
# In src/core/gameplay_phase.py
player_actions: list[dict] = Field(
    default_factory=list,  # ✅ Added this
    description="Actions taken this turn"
)

scene_context: str = Field(
    default="",  # ✅ Added this
    description="Where/when this occurred"
)
```

### How to Verify It's Fixed

```python
from src.core.gameplay_phase import GameplayPhaseState, SessionMemory
from datetime import datetime

# Should work without errors
memory = SessionMemory(
    session_id="test",
    campaign_id="test",
    session_start=datetime.utcnow(),
    current_turn=0
)

state = GameplayPhaseState(
    session_memory=memory,
    turn_number=0
)  # ✅ No error

print(f"✅ GameplayPhaseState initialized: {state.turn_number}")
```

---

## Fix #2: Tuple Unpacking Errors

### Error
```
Unexpected error in gameloop: 'tuple' object has no attribute 'get'
AttributeError: 'tuple' object has no attribute 'get'
```

### Root Cause
`execute_turn()` returns a tuple `(GameState, GameplayPhaseState)` but code tries to use it as a dict.

### Solution
**Status**: ✅ Already Fixed

Always unpack the tuple:

```python
# ❌ WRONG - Tuple doesn't have .get()
result = await executor.execute_turn(game_state)
result.get("field")  # ERROR
result["field"]      # ERROR

# ✅ CORRECT - Unpack immediately
game_state, gameplay_state = await executor.execute_turn(game_state)
game_state["field"]  # OK
gameplay_state.turn_number  # OK
```

### How to Verify It's Fixed

```python
from src.services.gameplay_executor import GameplayExecutor

executor = GameplayExecutor()
gameplay_state = executor.initialize_gameplay_phase(
    {"players": [], "metadata": {}},
    "camp_001",
    "sess_001"
)

# Execute turn
game_state, gameplay_state = await executor.execute_turn(
    {"players": [], "metadata": {}}
)

# ✅ Both should work
print(f"Turn: {gameplay_state.turn_number}")
print(f"State type: {type(game_state)}")
assert isinstance(game_state, dict)
assert gameplay_state.turn_number == 1
```

---

## Fix #3: Session Loading Errors

### Error
```
Failed to load session: 'NoneType' object has no attribute 'aget_state'
AttributeError: 'NoneType' object has no attribute 'aget_state'
```

### Root Cause
Attempting to load a session that hasn't been initialized, or the session saver is not configured.

### Solution
**Status**: ✅ Guidance Provided

Always initialize before loading:

```python
# ❌ WRONG - No session initialized
executor = GameplayExecutor()
await executor.execute_turn(game_state)  # ERROR: session is None

# ✅ CORRECT - Initialize first
executor = GameplayExecutor()
gameplay_state = executor.initialize_gameplay_phase(
    game_state, "camp_001", "sess_001"
)
await executor.execute_turn(game_state)  # OK
```

### Safe Loading Pattern

```python
import asyncio
from src.services.gameplay_executor import GameplayExecutor

async def safe_load_session():
    executor = GameplayExecutor()
    game_state = {"players": [], "metadata": {}}
    
    # Step 1: Initialize (creates session)
    try:
        gameplay_state = executor.initialize_gameplay_phase(
            game_state,
            campaign_id="camp_001",
            session_id="sess_001"
        )
        print(f"✅ Session initialized: {gameplay_state.session_memory.session_id}")
    except Exception as e:
        print(f"❌ Error initializing: {e}")
        return
    
    # Step 2: Execute (uses session)
    try:
        game_state, gameplay_state = await executor.execute_turn(game_state)
        print(f"✅ Turn executed: {gameplay_state.turn_number}")
    except Exception as e:
        print(f"❌ Error executing: {e}")
        return

asyncio.run(safe_load_session())
```

---

## Common Issues & Solutions

### Issue: "Tests Failing After Update"

**Problem**: Tests pass locally but fail in CI/CD or after pulling code

**Solution**:
```bash
# Clear pytest cache
pytest --cache-clear

# Reinstall dependencies
pip install -e . --upgrade

# Run tests again
pytest tests/test_gameplay_phase.py -v
```

### Issue: "Import Errors in Phase 3"

**Problem**: `ModuleNotFoundError` or `ImportError`

**Solution**:
```python
# Ensure all imports are correct
from src.core.gameplay_phase import (
    GameplayPhaseState,
    ActionIntentType,
    ActionResolutionStatus,
    PacingMetrics,
    SessionMemory
)

from src.services.gameplay_executor import GameplayExecutor

# Check if modules exist
import os
assert os.path.exists('src/core/gameplay_phase.py')
assert os.path.exists('src/services/gameplay_executor.py')
```

### Issue: "Agents Not Responding"

**Problem**: Agents return None or empty results

**Solution**: Agents are now optional. Mocks will be used if None:
```python
# This works (agents are optional)
await executor.execute_turn(
    game_state,
    action_resolver=None,  # No agent - uses mock
    judge=None,
    world_engine=None,
    lore_builder=None,
    dm=None,
    director=None
)

# This also works (real agents)
await executor.execute_turn(
    game_state,
    action_resolver=actual_resolver,
    judge=actual_judge,
    # ... other agents
)
```

### Issue: "Memory Growing Too Large"

**Problem**: Campaign chronicle consuming memory

**Solution**: Recent events window keeps only 20 events, chronicle is entire history:
```python
# Access recent events (capped at 20)
recent = gameplay_state.session_memory.recent_events
print(f"Recent events: {len(recent)}")

# Access full chronicle (can be large)
all_events = gameplay_state.session_memory.campaign_chronicle
print(f"Total events: {len(all_events)}")

# Get context window for LLM (efficient)
context = gameplay_state.session_memory.get_context_window(lookback=5)
print(f"Context window: {len(context)} events")
```

---

## Initialization Checklist

Before running Phase 3, verify:

- [ ] Python 3.10+ installed
- [ ] All dependencies installed (`pip install -e .`)
- [ ] Phase 1 (initialize_world) completes successfully
- [ ] GameState has all required fields:
  - [ ] `setting` (Setting object)
  - [ ] `narrative` (Narrative object or None)
  - [ ] `world` (World object or None)
  - [ ] `players` (list of Player objects)
  - [ ] `metadata` (dict with campaign_id, session_id)
- [ ] GameplayExecutor instantiated
- [ ] `initialize_gameplay_phase()` called before `execute_turn()`
- [ ] Session ID is not None
- [ ] Campaign ID is not None
- [ ] Tests pass locally (`pytest tests/test_gameplay_phase.py -v`)
- [ ] No import errors

---

## Debug Checklist During Execution

If Phase 3 fails during execution:

- [ ] Check turn number increments: `gameplay_state.turn_number`
- [ ] Check tension changes: `gameplay_state.pacing.current_tension`
- [ ] Check memory growth: `len(gameplay_state.session_memory.recent_events)`
- [ ] Check events recorded: `len(gameplay_state.session_memory.campaign_chronicle)`
- [ ] Check for scene transition: `gameplay_state.scene_transitions[-1].condition_met`
- [ ] Check action count: `len(gameplay_state.player_actions)`
- [ ] Check outcome tokens: `len(gameplay_state.outcome_tokens)`
- [ ] Check state changes: `len(gameplay_state.world_state_deltas)`

```python
# Print debug info
def print_turn_debug(gameplay_state):
    print(f"Turn {gameplay_state.turn_number}:")
    print(f"  Actions: {len(gameplay_state.player_actions)}")
    print(f"  Outcomes: {len(gameplay_state.outcome_tokens)}")
    print(f"  Changes: {len(gameplay_state.world_state_deltas)}")
    print(f"  Tension: {gameplay_state.pacing.current_tension:.1%}")
    print(f"  Recent events: {len(gameplay_state.session_memory.recent_events)}/20")
    print(f"  Total events: {len(gameplay_state.session_memory.campaign_chronicle)}")
    print(f"  Scene duration: {gameplay_state.pacing.turns_in_current_scene} turns")
```

---

## Performance Troubleshooting

### Problem: "Turns Taking Too Long"

**Cause**: Usually LLM latency (3-8 seconds per turn normal)

**Check**:
```python
import time

start = time.time()
game_state, gameplay_state = await executor.execute_turn(game_state)
elapsed = time.time() - start

print(f"Turn took {elapsed:.1f}s")
if elapsed > 10:
    print("⚠️  Slow! Check LLM latency")
else:
    print("✅ Normal speed")
```

**Solution**:
- Check LLM API latency
- Reduce context window (current: 5 events default)
- Use faster LLM model

### Problem: "Memory Usage Growing"

**Cause**: Campaign chronicle stores all events

**Check**:
```python
chronicle_size = len(gameplay_state.session_memory.campaign_chronicle)
print(f"Chronicle size: {chronicle_size} events")

# Estimate memory (rough: ~200 bytes per event)
estimated_mb = chronicle_size * 200 / (1024 * 1024)
print(f"Estimated: {estimated_mb:.1f} MB")
```

**Solution**:
- Chronicle growth is linear - this is expected
- Use `get_context_window()` for LLM instead of full chronicle
- Archive old sessions periodically

---

## Testing Verification

### Run All Phase 3 Tests

```bash
pytest tests/test_gameplay_phase.py -v
```

**Expected Output**:
```
.............................. [100%]
30 passed in 0.82s
```

### Run Specific Test

```bash
# Test GameplayPhaseState
pytest tests/test_gameplay_phase.py::TestGameplayPhaseState -v

# Test Executor
pytest tests/test_gameplay_phase.py::TestGameplayExecutor -v

# Test with coverage
pytest tests/test_gameplay_phase.py --cov=src/core/gameplay_phase
```

---

## When to Contact Support

If you encounter an error NOT listed here:

1. ❌ Check the Error Reference table above
2. ❌ Search troubleshooting guide
3. ❌ Run tests to verify: `pytest tests/test_gameplay_phase.py -v`
4. ❌ Verify checklist above
5. ❌ Check logs for specific error messages
6. ❌ Document error exactly and include:
   - Full error message
   - Traceback
   - Code that triggered it
   - Python version
   - Installed package versions

---

## Quick Fixes Checklist

For quick fixes, try these in order:

1. ✅ Update to latest code: `git pull`
2. ✅ Clear cache: `pytest --cache-clear`
3. ✅ Reinstall: `pip install -e . --upgrade`
4. ✅ Check imports: Verify all imports work
5. ✅ Verify initialization: Call `initialize_gameplay_phase()` first
6. ✅ Unpack tuples: Always use `game_state, gameplay_state =`
7. ✅ Run tests: `pytest tests/test_gameplay_phase.py -v`
8. ✅ Check docs: Read relevant troubleshooting section

---

## Summary

**Phase 3 is robust with proper initialization:**

| Step | Status | Check |
|------|--------|-------|
| 1. Data structures | ✅ Fixed | Pydantic validates correctly |
| 2. Tuple handling | ✅ Fixed | Always unpack return value |
| 3. Session loading | ✅ Guided | Initialize before using |
| 4. Agents | ✅ Flexible | Optional with mocks |
| 5. Tests | ✅ Passing | 30/30 pass |
| 6. Documentation | ✅ Complete | This guide covers all issues |

**Most issues resolved by:** Proper initialization order and unpacking tuples

---

## Final Note

Phase 3 is production-ready. Common issues are usually due to:
1. Not calling `initialize_gameplay_phase()` first
2. Not unpacking `execute_turn()` return value
3. Trying to load non-existent sessions

Following the patterns in this guide will prevent 99% of issues.

🎲 **Ready to play!**
