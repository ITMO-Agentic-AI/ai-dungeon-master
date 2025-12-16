# Session Loading Error Fix: NoneType has no attribute 'aget_state'

**Date**: December 17, 2025  
**Status**: 🔧 Diagnosed & Solution Provided  
**Error**: `'NoneType' object has no attribute 'aget_state'`  
**Cause**: Attempting to load uninitialized or non-existent session  

---

## Error Message

```
Failed to load session: 'NoneType' object has no attribute 'aget_state'
Traceback:
  File "orchestrator_service.py", line X
  state = await saver.aget_state(config)
         ^
AttributeError: 'NoneType' object has no attribute 'aget_state'
```

---

## Root Cause Analysis

### What's Happening

1. Code tries to load a session:
   ```python
   saver = get_saver()  # Returns None
   state = await saver.aget_state(config)  # ERROR: NoneType has no method
   ```

2. The `saver` object is None because:
   - Session saver not initialized
   - No checkpointing backend configured
   - Session hasn't been created yet
   - Trying to load non-existent session

### Why This Happens

The orchestrator tries to load existing session state, but:
- Session backend (saver) is None
- No fallback for missing sessions
- Assumption that saver always exists

---

## Solution Patterns

### Pattern 1: Check Before Accessing

```python
# BEFORE (ERROR)
saver = get_saver()
state = await saver.aget_state(config)  # NoneType error

# AFTER (SAFE)
saver = get_saver()
if saver is not None:
    state = await saver.aget_state(config)
else:
    state = None  # No prior state
```

### Pattern 2: Initialize Session First

```python
# Ensure session is created before loading
from src.services.orchestrator_service import orchestrator_service

# Always initialize a new session first
gameplay_state = await orchestrator_service.initialize_gameplay_phase(
    game_state,
    campaign_id="camp_001",
    session_id="sess_001"
)

# THEN use the session
# Don't try to load non-existent sessions
```

### Pattern 3: Use Try-Except for Robustness

```python
try:
    saver = get_saver()
    if saver is not None:
        state = await saver.aget_state(config)
    else:
        state = None
except AttributeError as e:
    if "'NoneType' object has no attribute" in str(e):
        print("Error: Session saver not initialized. Call initialize_gameplay_phase first.")
        state = None
    else:
        raise
```

---

## Correct Usage Flow

### Phase 1: Initialize World

```python
from src.services.orchestrator_service import orchestrator_service
from src.core.types import GameState, Setting

# Initialize Phase 1
game_state = await orchestrator_service.initialize_world(
    GameState(
        setting=Setting(theme="Dark Fantasy", player_concepts=[...]),
        metadata={"campaign_id": "camp_001", "session_id": "sess_001"},
        players=[],
        narrative=None,
        world=None,
        messages=[]
    )
)

print(f"✅ World initialized")
```

### Phase 3: Initialize Gameplay

```python
# Initialize Phase 3 (creates session)
gameplay_state = await orchestrator_service.initialize_gameplay_phase(
    game_state,
    campaign_id="camp_001",
    session_id="sess_001"
)

print(f"✅ Gameplay session created")
print(f"   Session ID: {gameplay_state.session_memory.session_id}")
print(f"   Turn: {gameplay_state.turn_number}")
```

### Phase 3: Execute Turns

```python
# Now execute turns (session is initialized)
for turn in range(num_turns):
    game_state, gameplay_state = await orchestrator_service.execute_turn(
        game_state,
        # agents...
    )
    
    print(f"Turn {gameplay_state.turn_number} complete")
```

---

## Common Mistakes

### Mistake #1: Skipping initialization

```python
# ❌ WRONG - No session initialized
executor = GameplayExecutor()
gameplay_state = executor.execute_turn(game_state)  # ERROR: session is None

# ✅ CORRECT - Initialize first
executor = GameplayExecutor()
gameplay_state = executor.initialize_gameplay_phase(game_state, "camp", "sess")
await executor.execute_turn(game_state)  # OK: session exists
```

### Mistake #2: Trying to load non-existent session

```python
# ❌ WRONG - Session "sess_999" doesn't exist
saver = get_saver()
state = await saver.aget_state({"configurable": {"thread_id": "sess_999"}})

# ✅ CORRECT - Create new session
gameplay_state = executor.initialize_gameplay_phase(
    game_state, "camp_001", "sess_001"
)
```

### Mistake #3: Forgetting to await async calls

```python
# ❌ WRONG - Not awaiting async call
saver = get_saver()
state = saver.aget_state(config)  # Returns coroutine, not state

# ✅ CORRECT - Await the coroutine
saver = get_saver()
state = await saver.aget_state(config)  # Returns actual state
```

---

## Preventive Measures

### Check 1: Verify Saver Exists

```python
def ensure_saver():
    """Ensure session saver is available."""
    saver = get_saver()
    if saver is None:
        raise RuntimeError("Session saver not initialized. Check LangGraph configuration.")
    return saver
```

### Check 2: Validate Session Before Loading

```python
async def load_session_safe(session_id: str):
    """Safely load session with error handling."""
    saver = get_saver()
    if saver is None:
        print(f"⚠️  Warning: No session saver. Creating new session.")
        return None
    
    try:
        state = await saver.aget_state({"configurable": {"thread_id": session_id}})
        if state is None:
            print(f"⚠️  Warning: Session {session_id} not found. Creating new session.")
        return state
    except AttributeError as e:
        if "'NoneType'" in str(e):
            print(f"❌ Error: Session saver improperly configured.")
            return None
        raise
```

### Check 3: Always Initialize First

```python
async def setup_gameplay_session(game_state, campaign_id, session_id):
    """Setup gameplay with proper initialization."""
    executor = GameplayExecutor()
    
    # CRITICAL: Initialize before any operations
    gameplay_state = executor.initialize_gameplay_phase(
        game_state,
        campaign_id=campaign_id,
        session_id=session_id
    )
    
    print(f"✅ Session {session_id} initialized and ready")
    return executor, gameplay_state
```

---

## Debugging Guide

### When You See This Error

**Step 1**: Check if `initialize_gameplay_phase()` was called
```python
if gameplay_state is None:
    print("ERROR: initialize_gameplay_phase() not called")
    gameplay_state = await executor.initialize_gameplay_phase(...)
```

**Step 2**: Verify session was created
```python
if gameplay_state.session_memory.session_id is None:
    print("ERROR: Session ID is None")
else:
    print(f"Session created: {gameplay_state.session_memory.session_id}")
```

**Step 3**: Check saver configuration
```python
from src.services.orchestrator_service import get_saver
saver = get_saver()
if saver is None:
    print("ERROR: Session saver not configured")
else:
    print("Session saver available")
```

---

## Complete Safe Usage Example

```python
import asyncio
from src.services.gameplay_executor import GameplayExecutor
from src.services.orchestrator_service import orchestrator_service
from src.core.types import GameState, Setting
from datetime import datetime

async def safe_gameplay_session():
    """Safe example of Phase 3 gameplay."""
    
    print("\n🎮 Phase 3: Gameplay Session Setup\n")
    
    # Step 1: Verify orchestrator is ready
    print("Step 1: Initialize orchestrator...")
    if orchestrator_service is None:
        raise RuntimeError("Orchestrator not initialized")
    print("  ✅ Orchestrator ready")
    
    # Step 2: Initialize world (Phase 1)
    print("\nStep 2: Initialize world...")
    try:
        game_state = await orchestrator_service.initialize_world(
            GameState(
                setting=Setting(
                    theme="Dark Fantasy",
                    player_concepts=["Warrior", "Mage", "Rogue"]
                ),
                metadata={
                    "campaign_id": "camp_001",
                    "session_id": "sess_001"
                },
                players=[],
                narrative=None,
                world=None,
                messages=[]
            )
        )
        print("  ✅ World initialized")
    except Exception as e:
        print(f"  ❌ Error initializing world: {e}")
        return
    
    # Step 3: Initialize gameplay session (Phase 3 setup)
    print("\nStep 3: Initialize gameplay session...")
    executor = GameplayExecutor()
    try:
        gameplay_state = executor.initialize_gameplay_phase(
            game_state,
            campaign_id="camp_001",
            session_id="sess_001"
        )
        print(f"  ✅ Session created: {gameplay_state.session_memory.session_id}")
    except Exception as e:
        print(f"  ❌ Error initializing gameplay: {e}")
        return
    
    # Step 4: Execute turns (Phase 3 gameplay)
    print("\nStep 4: Execute gameplay turns...")
    try:
        for turn_num in range(1, 4):
            print(f"  Turn {turn_num}...")
            
            # Execute turn
            game_state, gameplay_state = await executor.execute_turn(
                game_state
                # agents would go here
            )
            
            print(f"    ✅ Turn complete (tension: {gameplay_state.pacing.current_tension:.0%})")
    except Exception as e:
        print(f"  ❌ Error during gameplay: {e}")
        return
    
    print(f"\n✅ Gameplay session successful!")
    print(f"   Total turns: {gameplay_state.turn_number}")
    print(f"   Total events: {len(gameplay_state.session_memory.campaign_chronicle)}")

# Run safely
asyncio.run(safe_gameplay_session())
```

---

## Prevention Checklist

Before running Phase 3:

- [ ] Phase 1 (initialize_world) completed successfully
- [ ] GameState created with all required fields
- [ ] GameplayExecutor instantiated
- [ ] initialize_gameplay_phase() called BEFORE execute_turn()
- [ ] Session ID is not None
- [ ] Campaign ID is not None
- [ ] No attempts to load non-existent sessions
- [ ] Error handling in place for async calls
- [ ] Saver is available (or gracefully handled if None)

---

## Summary

| Issue | Cause | Solution |
|-------|-------|----------|
| NoneType error | Session not initialized | Call initialize_gameplay_phase() first |
| Saver is None | Backend not configured | Ensure LangGraph saver is set up |
| Can't load session | Session doesn't exist | Create new session, don't load non-existent |
| AttributeError on None | Forgetting to check | Always check if saver/state is not None |

---

## Key Takeaway

⚠️ **CRITICAL**: Always initialize Phase 3 before executing turns!

```python
# WRONG - Will fail
executor = GameplayExecutor()
await executor.execute_turn(game_state)  # ERROR: not initialized

# CORRECT - Will work
executor = GameplayExecutor()
gameplay_state = executor.initialize_gameplay_phase(game_state, "camp", "sess")
await executor.execute_turn(game_state)  # OK
```

---

## Next Steps

1. ✅ Verify Phase 1 completes successfully
2. ✅ Ensure initialize_gameplay_phase() is called
3. ✅ Add error handling around async calls
4. ✅ Check for None objects before using them
5. ✅ Test with safe_gameplay_session() example

**Status**: 🔧 Issue identified, solutions provided, ready to implement
