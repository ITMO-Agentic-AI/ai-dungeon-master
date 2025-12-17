# 🔴 FINAL CRITICAL BUGS - Session & Turn Issues

**Date**: December 17, 2025, 12:00 PM MSK  
**Status**: 🔴 **2 CRITICAL RUNTIME ISSUES IDENTIFIED**  
**Severity**: Production Blocking  

---

## Bug #13: Session Saver Not Configured

**Error**: "Session saver not configured, starting new session while trying to load older session"  
**Location**: `chainlit_app.py` + `orchestrator_service.py`  
**Severity**: 🔴 CRITICAL - Sessions not persisting  
**Impact**: Cannot resume games, all progress lost  

### Root Cause Analysis

#### Issue 1: execute_turn() Not Saving to Checkpoint

```python
# File: src/services/orchestrator_service.py, line 518
async def execute_turn(...) -> tuple[GameState, Any]:
    # ...
    updated_state, gameplay_state = await self.gameplay_executor.execute_turn(
        state,
        self.resolver,
        self.judge,
        self.world_engine,
        self.lore_builder,
        self.dm,
        self.director
    )
    logger.debug(f"Turn {turn} completed successfully")
    return updated_state, gameplay_state  # ❌ Returns but DOESN'T SAVE TO CHECKPOINT!
```

**Problem**: execute_turn() modifies state but doesn't save to LangGraph checkpoint

#### Issue 2: Chainlit Not Invoking Graph

```python
# File: chainlit_app.py, line 530
try:
    state = await orchestrator_service.execute_turn(state)  # ❌ Calls executor DIRECTLY
    # SHOULD BE:
    # state = await orchestrator_service.compiled_graph.ainvoke(state, config=config)
```

**Problem**: Chainlit bypasses the LangGraph, so checkpoints never save

#### Issue 3: Config Not Passed to execute_turn

```python
# chainlit_app.py line 530
state = await orchestrator_service.execute_turn(state)  # ❌ No config!
# Config with session_id needed for checkpoint
```

### The Fix

**Part 1: Make execute_turn save to checkpoint**

```python
# orchestrator_service.py
async def execute_turn(
    self, state: GameState, config: dict[str, Any] | None = None
) -> tuple[GameState, Any]:
    # ...
    
    # Execute gameplay
    updated_state, gameplay_state = await self.gameplay_executor.execute_turn(...)
    
    # CRITICAL FIX: Save to checkpoint
    if config:
        await self.compiled_graph.aupdate_state(config, updated_state)
        logger.info(f"Checkpoint saved for turn {turn}")
    
    return updated_state, gameplay_state
```

**Part 2: Pass config from chainlit**

```python
# chainlit_app.py line 530
config = {"configurable": {"thread_id": session_id}}
state, gameplay_state = await orchestrator_service.execute_turn(state, config=config)
```

**Part 3: Alternative - Use graph.ainvoke() for turns**

```python
# Better approach: Use graph for state management
config = {"configurable": {"thread_id": session_id}}
state = await orchestrator_service.compiled_graph.ainvoke(state, config=config)
```

---

## Bug #14: Each Turn Same Output (No Action Variety)

**Error**: DM narrates identical response regardless of player action  
**Location**: Multiple files  
**Severity**: 🔴 CRITICAL - Game is not interactive  
**Impact**: Player actions don't affect narration  

### Root Cause Analysis

#### Issue 1: Action Not Passed Through GameplayExecutor

```python
# gameplay_executor.py line 200
async def _step1_generate_actions(self, game_state: GameState) -> list[dict]:
    current_action = game_state.get("current_action")
    
    if current_action:
        actions.append({
            "performer_id": current_action.player_id,
            "intent_type": self._classify_intent(current_action.description),
            "description": current_action.description,  # ✅ Uses description
            # ...
        })
```

**This looks OK**, BUT:

#### Issue 2: DM Ignores Action Description in Prompt

```python
# dungeon_master/graph.py line 421
context_block = f"""
Action: {action.description}  # ✅ Includes description
Roll Details: {token.mechanical_summary}
Location: {actor_location}
"""  # ✅ This looks OK too
```

**Still OK**, SO WHERE'S THE PROBLEM?

#### Issue 3: Narration Uses Generic Template

```python
# dungeon_master/graph.py line 380-390
system_prompt = f"""
** MECHANICAL OUTCOME (narrate based on this):**
- Roll: {roll_total} vs DC {dc}
- Result: {'SUCCESS' if is_success else 'FAILURE'}
- Effectiveness: {effectiveness:.0%}
- Damage Dealt: {damage} HP

CRITICAL RULES:
1. {'Show what happens as a direct result of their SUCCESSFUL action' if is_success else 'Show the consequences of their FAILED attempt'}.
# ❌ DOESN'T MENTION THE SPECIFIC ACTION TYPE!
```

**Problem**: Prompt doesn't emphasize WHAT action was taken, only success/failure

#### Issue 4: Same Narration for All Action Types

```python
# Example outputs:
Attack: "Your blade finds its mark..."
Cast Spell: "Your blade finds its mark..."  ← WRONG!
Investigate: "Your blade finds its mark..."  ← WRONG!
```

**Problem**: LLM defaults to combat narration because it's most common

### The Fix

**Part 1: Include Action Type in Prompt**

```python
# dungeon_master/graph.py line 380
system_prompt = f"""
You are the Dungeon Master.

** PLAYER ACTION:**
- Action Type: {token.intent_type.value}  # NEW!
- Action Description: "{action.description}"  # NEW!
- Roll: {roll_total} vs DC {dc}
- Result: {'SUCCESS' if is_success else 'FAILURE'}
- Effectiveness: {effectiveness:.0%}
- Damage Dealt: {damage} HP

CRITICAL RULES:
1. Narrate the SPECIFIC action: {action.description}  # NEW!
2. {'Show what happens when this action SUCCEEDS' if is_success else 'Show what happens when this action FAILS'}.
3. Make it vivid and specific to the action type.
# ...
```

**Part 2: Add Action-Specific Guidance**

```python
# Add action-specific narration hints
action_hints = {
    ActionIntentType.ATTACK: "Describe the combat maneuver, weapon impact, and enemy reaction.",
    ActionIntentType.CAST_SPELL: "Describe magical energy, spell effects, and arcane outcomes.",
    ActionIntentType.INVESTIGATE: "Describe what the character discovers, notices, or learns.",
    ActionIntentType.DIALOGUE: "Describe the conversation, NPC reactions, and social dynamics.",
    ActionIntentType.MOVE: "Describe the movement, terrain, and arrival at destination.",
}

hint = action_hints.get(token.intent_type, "Describe what happens.")

system_prompt = f"""
...
NARRATION FOCUS: {hint}
...
"""
```

**Part 3: Emphasize Action Context in Context Block**

```python
# dungeon_master/graph.py line 421
context_block = f"""
PLAYER ACTION:
  Type: {token.intent_type.value}
  What They Did: "{action.description}"
  
MECHANICAL RESULT:
  Roll: {token.mechanical_summary}
  Outcome: {'SUCCESS - Action achieves its goal' if token.meets_dc else 'FAILURE - Action does not succeed'}
  
SETTING:
  Location: {actor_location}
  Changes: {len(world_changes)} state change(s)
  
NARRATE: Describe specifically what happens when the player {action.description}.
"""
```

---

## Implementation Priority

### CRITICAL (Must Fix Now)
1. **Bug #13**: Session persistence
   - Part 1: Make execute_turn save checkpoint
   - Part 2: Pass config from chainlit
   - Time: 30 minutes

2. **Bug #14**: Action-specific narration
   - Part 1: Include action in prompt
   - Part 2: Add action hints
   - Part 3: Emphasize in context
   - Time: 20 minutes

**Total Time**: 50 minutes

---

## Testing Checklist

### Bug #13 Testing
- [ ] Start new game
- [ ] Play 2 turns
- [ ] Close browser
- [ ] Reopen and select "Load Game"
- [ ] Verify turn counter shows "2"
- [ ] Verify players/world state intact
- [ ] Continue playing from turn 3

### Bug #14 Testing
- [ ] Attack action → Should describe combat
- [ ] Cast spell → Should describe magic
- [ ] Investigate → Should describe discovery
- [ ] Talk → Should describe conversation
- [ ] Each action has DIFFERENT narration
- [ ] Narration mentions what player did

---

## Code Changes Summary

### File 1: orchestrator_service.py
**Changes**: Update execute_turn to save checkpoint  
**Lines**: Add 3-5 lines after line 518  
**Impact**: Sessions persist properly  

### File 2: chainlit_app.py
**Changes**: Pass config to execute_turn  
**Lines**: Modify line 530  
**Impact**: Checkpoint saving works  

### File 3: dungeon_master/graph.py
**Changes**: Improve narration prompts  
**Lines**: Update 380-390, 421-430  
**Impact**: Narration varies by action  

---

## Expected Results

### Before Fixes
```
Turn 1: "I attack the goblin"
DM: "Your action succeeds!"

Turn 2: "I cast fireball"
DM: "Your action succeeds!"  ← IDENTICAL!

Close & Reload:
  ❌ Session not found
  ❌ Start from beginning
```

### After Fixes
```
Turn 1: "I attack the goblin"
DM: "Your blade cleaves through the goblin's armor..."

Turn 2: "I cast fireball"
DM: "Flames erupt from your hands, engulfing the area..."

Close & Reload:
  ✅ Session found
  ✅ Resume from Turn 2
  ✅ All state intact
```

---

**Status**: 🔴 2 CRITICAL BUGS IDENTIFIED - READY FOR FIX

**Next**: Apply fixes to repository
