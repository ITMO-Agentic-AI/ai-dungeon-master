# 🔧 CRITICAL FIXES TO APPLY MANUALLY

**IMPORTANT**: chainlit_app.py was accidentally corrupted. Restore it from commit `0399fbca` first, then apply these fixes.

---

## How to Restore chainlit_app.py

```bash
# Restore the file from the last good commit
git checkout 0399fbca88c7fccd81ef39a3c0c1bda2d7551efe -- chainlit_app.py
git add chainlit_app.py
git commit -m "restore: chainlit_app.py from last good commit"
```

---

## FIX #1: Session Persistence (chainlit_app.py)

### Problem
Turns execute but don't save to checkpoint, so games can't be resumed.

### Location
File: `chainlit_app.py`  
Line: ~530 (in `handle_message` function)

### Current Code (BROKEN)
```python
# Execute turn
msg = cl.Message(
    content="Resolving action...", author="Dungeon Master", elements=[sfx] if sfx else []
)
await msg.send()

try:
    state = await orchestrator_service.execute_turn(state)  # ❌ No config passed!

    # Update turn counter
    turn = state.get("metadata", {}).get("turn", 0) + 1
    state["metadata"]["turn"] = turn

    # Save session
    session_service.update_session(session_id, turn)  # ❌ Only updates metadata, not checkpoint
    cl.user_session.set("game_state", state)
```

### Fixed Code
```python
# Execute turn
msg = cl.Message(
    content="Resolving action...", author="Dungeon Master", elements=[sfx] if sfx else []
)
await msg.send()

try:
    # CRITICAL FIX: Pass config with session_id for checkpoint saving
    config = {"configurable": {"thread_id": session_id}}
    
    # Option 1: Use execute_turn with config (recommended)
    state, gameplay_state = await orchestrator_service.execute_turn(state, config=config)
    
    # Option 2: Use graph.ainvoke directly (alternative)
    # state = await orchestrator_service.compiled_graph.ainvoke(state, config=config)

    # Update turn counter
    turn = state.get("metadata", {}).get("turn", 0) + 1
    state["metadata"]["turn"] = turn
    
    # Save to checkpoint explicitly (if using Option 1)
    await orchestrator_service.compiled_graph.aupdate_state(config, state)
    logger.log_event("System", "Checkpoint", f"Turn {turn} saved to checkpoint")

    # Update session metadata
    session_service.update_session(session_id, turn)
    cl.user_session.set("game_state", state)
```

---

## FIX #2: Action-Specific Narration (dungeon_master/graph.py)

### Problem
All actions get the same narration regardless of what player did.

### Location
File: `src/agents/dungeon_master/graph.py`  
Method: `narrate_outcome_with_tokens`  
Lines: ~380-430

### Current Code (INCOMPLETE)
```python
# Line 380
system_prompt = f"""
You are the Dungeon Master.

Narrate the IMMEDIATE CONSEQUENCE of the player's action in visceral, immersive prose.

** MECHANICAL OUTCOME (narrate based on this):**
- Roll: {roll_total} vs DC {dc}
- Result: {'SUCCESS' if is_success else 'FAILURE'}
- Effectiveness: {effectiveness:.0%}
- Damage Dealt: {damage} HP

CRITICAL RULES:
1. {'Show what happens as a direct result of their SUCCESSFUL action' if is_success else 'Show the consequences of their FAILED attempt'}.
# ❌ Doesn't emphasize WHAT action was taken!
```

### Fixed Code
```python
# Line 380 - Enhanced prompt with action emphasis
from src.core.gameplay_phase import ActionIntentType

# Get action type for specific guidance
action_hints = {
    ActionIntentType.ATTACK: "Describe the combat maneuver, weapon impact, and enemy reaction.",
    ActionIntentType.CAST_SPELL: "Describe magical energy, spell effects, and arcane outcomes.",
    ActionIntentType.INVESTIGATE: "Describe what the character discovers, notices, or learns.",
    ActionIntentType.DIALOGUE: "Describe the conversation, NPC reactions, and social dynamics.",
    ActionIntentType.MOVE: "Describe the movement, terrain, and arrival at destination.",
    ActionIntentType.DEFEND: "Describe defensive positioning, protection, and reaction.",
}

action_hint = action_hints.get(
    token.intent_type,
    "Describe what happens as a result of this specific action."
)

system_prompt = f"""
You are the Dungeon Master.

Narrate the IMMEDIATE CONSEQUENCE of the player's SPECIFIC action in visceral, immersive prose.

** PLAYER ACTION:**
- Action Type: {token.intent_type.value if hasattr(token.intent_type, 'value') else str(token.intent_type)}
- What They Did: "{action.description}"
- Narration Focus: {action_hint}

** MECHANICAL OUTCOME:**
- Roll: {roll_total} vs DC {dc}
- Result: {'SUCCESS - The action achieves its intended effect' if is_success else 'FAILURE - The action does not succeed as intended'}
- Effectiveness: {effectiveness:.0%}
- Damage Dealt: {damage} HP (if combat)

CRITICAL RULES:
1. Narrate SPECIFICALLY what happens when the player "{action.description}".
2. {'Show how their action SUCCEEDS and what it achieves' if is_success else 'Show how their action FAILS and what goes wrong'}.
3. Make it FELT through sensory detail - match the action type.
4. {tone_hint}
5. Use BOLD for sudden changes/revelations and > blockquotes for reactions.
6. Keep momentum going. The next action should feel inevitable.
7. ABSOLUTELY NO action menu format. Pure narrative continuation only.
8. Target length: 150-250 words.

AFTER the narrative (on a new line), you MUST output a JSON block with action suggestions:

```json
{{
  "action_suggestions": [
    "Suggestion 1 - A specific action the player could take next",
    "Suggestion 2 - Another viable action",
    "Suggestion 3 - A third option"
  ]
}}
```

Make suggestions concrete, action-oriented, and contextual to what just happened.
"""
```

### Context Block Update (Line ~421)
```python
# Enhanced context with action emphasis
context_block = f"""
PLAYER ACTION:
  Type: {token.intent_type.value if hasattr(token.intent_type, 'value') else str(token.intent_type)}
  Description: "{action.description}"
  
MECHANICAL RESULT:
  Dice Roll: {token.mechanical_summary}
  Outcome: {'SUCCESS - Action achieves its goal' if token.meets_dc else 'FAILURE - Action does not succeed'}
  Effectiveness: {effectiveness:.0%}
  Damage: {damage} HP
  
SETTING:
  Location: {actor_location}
  World Changes: {len(world_changes)} state change(s) applied
  
NARRATE: Describe specifically and vividly what happens when the player {action.description}.
The narration should be different based on whether they attacked, cast a spell, investigated, etc.
"""
```

---

## OPTIONAL FIX #3: orchestrator_service.py Enhancement

If you want execute_turn to handle checkpoint saving automatically:

### Location
File: `src/services/orchestrator_service.py`  
Method: `execute_turn`  
Line: ~518

### Add After Line 527
```python
try:
    # Use GameplayExecutor for comprehensive turn orchestration
    updated_state, gameplay_state = await self.gameplay_executor.execute_turn(
        state,
        self.resolver,
        self.judge,
        self.world_engine,
        self.lore_builder,
        self.dm,
        self.director
    )
    
    # CRITICAL FIX: Save to checkpoint if config provided
    if config:
        await self.compiled_graph.aupdate_state(config, updated_state)
        logger.info(f"Turn {turn} checkpoint saved for session {session_id}")
    
    logger.debug(f"Turn {turn} completed successfully")
    return updated_state, gameplay_state
```

---

## Testing Checklist

### Test Session Persistence
1. Start new game
2. Play 2-3 turns
3. Note the turn counter
4. Close browser/app
5. Reopen and select "Load Game"
6. ✅ Should see previous session
7. ✅ Turn counter should match
8. ✅ Players/world should be intact
9. Continue playing
10. ✅ Game should continue from where it left off

### Test Action Variety
1. Turn 1: "I attack the goblin"
   - ✅ Should describe combat, weapon, enemy reaction
2. Turn 2: "I cast fireball at the group"
   - ✅ Should describe magic, flames, spell effects
   - ❌ Should NOT mention weapons or melee
3. Turn 3: "I investigate the room for clues"
   - ✅ Should describe searching, discovery, what's found
   - ❌ Should NOT mention combat or magic
4. Turn 4: "I try to persuade the guard"
   - ✅ Should describe conversation, social interaction
   - ❌ Should NOT mention attacking or investigating

---
## Summary

### Files to Modify
1. **chainlit_app.py** (line ~530)
   - Add config parameter
   - Call aupdate_state for checkpoint

2. **src/agents/dungeon_master/graph.py** (lines 380-430)
   - Add action type to prompt
   - Add action-specific hints
   - Emphasize action description

3. **src/services/orchestrator_service.py** (line ~527) - OPTIONAL
   - Add checkpoint saving in execute_turn

### Expected Results
- ✅ Sessions persist across restarts
- ✅ Can resume from any turn
- ✅ Different actions get different narrations
- ✅ Narration mentions what player did
- ✅ Game feels interactive and responsive

---

**CRITICAL**: First restore chainlit_app.py, THEN apply these fixes!

```bash
# 1. Restore file
git checkout 0399fbca88c7fccd81ef39a3c0c1bda2d7551efe -- chainlit_app.py

# 2. Apply fixes manually (see above)

# 3. Test thoroughly

# 4. Commit
git add chainlit_app.py src/agents/dungeon_master/graph.py
git commit -m "fix: session persistence and action-specific narration"
```
