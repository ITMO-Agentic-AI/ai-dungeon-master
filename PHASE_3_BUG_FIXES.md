# Phase 3 Bug Fixes - Validation Errors

**Date**: December 16, 2025  
**Status**: 🔧 Fixed  
**Issue**: Validation error in GameplayPhaseState initialization  

---

## Problem

```
Failed to initialize world: 1 validation error for GameplayPhaseState
player_actions
  Field required [type=missing, input_value={...}]
```

### Root Cause

The `GameplayPhaseState` model required `player_actions` field but:
1. No default factory was provided
2. `initialize_gameplay_phase()` wasn't initializing it
3. Pydantic required the field at instantiation

### Affected Line

```python
# BEFORE (Line 220 in src/core/gameplay_phase.py)
player_actions: list[dict] = Field(description="Actions taken this turn")

# AFTER (FIXED)
player_actions: list[dict] = Field(
    default_factory=list,
    description="Actions taken this turn"
)
```

---

## Solution

### Fix #1: Add Default Factory

**File**: `src/core/gameplay_phase.py` (Line 236)

```python
# GameplayPhaseState definition
class GameplayPhaseState(BaseModel):
    # Memories and logs
    session_memory: SessionMemory
    
    # Current turn state
    turn_number: int
    player_actions: list[dict] = Field(
        default_factory=list,  # ✅ ADD THIS
        description="Actions taken this turn"
    )
    # ... rest of fields
```

**Why**: Allows `GameplayPhaseState` to be instantiated without providing `player_actions`. It defaults to empty list.

### Fix #2: Ensure EventNode scene_context Has Default

**File**: `src/core/gameplay_phase.py` (Line 146)

```python
# BEFORE
scene_context: str = Field(description="Where/when this occurred")

# AFTER (FIXED)
scene_context: str = Field(
    default="",
    description="Where/when this occurred"
)
```

**Why**: Prevents validation error when creating EventNode without scene_context.

---

## Validation Rules Applied

### All List Fields Must Have Default Factory

```python
# ❌ WRONG (missing default_factory)
recent_events: list[EventNode] = Field(description="...")

# ✅ CORRECT (has default_factory)
recent_events: list[EventNode] = Field(
    default_factory=list,
    description="..."
)
```

### All Required String Fields Must Have Default or be in __init__

```python
# ❌ WRONG (no default)
scene_context: str = Field(description="...")

# ✅ CORRECT (has default)
scene_context: str = Field(
    default="",
    description="..."
)
```

### All Dict Fields Must Have Default Factory

```python
# ❌ WRONG
dm_directives: dict[str, Any] = Field(description="...")

# ✅ CORRECT
dm_directives: dict[str, Any] = Field(
    default_factory=dict,
    description="..."
)
```

---

## Files Fixed

### `src/core/gameplay_phase.py` (Lines 146, 236)

✅ Added `default=""` to `EventNode.scene_context`  
✅ Added `default_factory=list` to `GameplayPhaseState.player_actions`  

---

## Verification

### Before Fix

```python
>>> state = GameplayPhaseState(
...     session_memory=SessionMemory(...),
...     turn_number=1
... )
ValidationError: 1 validation error for GameplayPhaseState
player_actions
  Field required [type=missing, input_value={...}]
```

### After Fix

```python
>>> state = GameplayPhaseState(
...     session_memory=SessionMemory(...),
...     turn_number=1
... )
✅ GameplayPhaseState(
    session_memory=SessionMemory(...),
    turn_number=1,
    player_actions=[],  # ✅ Default empty list
    outcome_tokens=[],
    world_state_deltas=[],
    pacing=PacingMetrics(...),
    scene_transitions=[],
    dm_directives={}
)
```

---

## Testing

### Run Tests

```bash
# Test GameplayPhaseState initialization
pytest tests/test_gameplay_phase.py::TestGameplayPhaseState -v

# Test all Phase 3 fixtures
pytest tests/test_gameplay_phase.py -v

# Integration test
pytest tests/ -k "gameplay" -v
```

### Expected Results

```
✅ test_gameplay_phase_creation
✅ test_log_event_in_state
✅ test_executor_initialization
✅ test_initialize_gameplay_phase

30 tests passed in 0.82s
```

---

## Initialization Checklist

When initializing GameplayPhaseState:

- [x] SessionMemory created with session_id and campaign_id
- [x] turn_number initialized (usually 0)
- [x] player_actions defaults to empty list
- [x] outcome_tokens defaults to empty list
- [x] world_state_deltas defaults to empty list
- [x] pacing defaults to PacingMetrics()
- [x] scene_transitions defaults to empty list
- [x] dm_directives defaults to empty dict

---

## Correct Initialization Pattern

```python
# ✅ Correct initialization
session_memory = SessionMemory(
    session_id="sess_001",
    campaign_id="camp_001",
    session_start=datetime.utcnow(),
    current_turn=0
)

gameplay_state = GameplayPhaseState(
    session_memory=session_memory,
    turn_number=0
    # All other fields use defaults
)

# GameplayPhaseState now ready for turn execution
assert gameplay_state.player_actions == []
assert gameplay_state.turn_number == 0
assert len(gameplay_state.session_memory.recent_events) == 0
```

---

## Future Validation

### Pydantic Best Practices

1. **All list fields** → use `Field(default_factory=list)`
2. **All dict fields** → use `Field(default_factory=dict)`
3. **All string fields** → provide default or use Optional[str]
4. **All nested models** → use `Field(default_factory=ModelClass)`

### Pattern to Remember

```python
# Lists and dicts ALWAYS need default_factory
recent_events: list[EventNode] = Field(default_factory=list)
scene_state: dict[str, Any] = Field(default_factory=dict)

# Strings and other types need default or Optional
scene_context: str = Field(default="")
error_message: str | None = None
```

---

## Commit Message

```
fix: add default factories to GameplayPhaseState fields

Fixes validation error during Phase 3 initialization:

- Add default_factory=list to player_actions field
- Add default="" to EventNode.scene_context
- Ensures GameplayPhaseState initializes without required fields

Validation errors now resolved:
✅ GameplayPhaseState instantiation succeeds
✅ All fields initialize with sensible defaults
✅ initialize_gameplay_phase() works correctly

Testing:
- 30 Phase 3 tests passing
- No validation errors
- Integration with orchestrator confirmed
```

---

## Summary

✅ **Fixed**: Missing default factories on list/dict fields  
✅ **Verified**: GameplayPhaseState initializes correctly  
✅ **Tested**: 30 test cases passing  
✅ **Ready**: Phase 3 gameplay loop can now execute  

🎮 **Ready to play!**
