# 🛑 EMERGENCY RECOVERY & FIXES

**CRITICAL**: chainlit_app.py was accidentally corrupted during bugfix session.

## Immediate Recovery Required

### Problem
The file `chainlit_app.py` currently only contains `"""` (3 bytes) and is non-functional.

### Solution Options

#### Option 1: Git Reset (RECOMMENDED)
```bash
# Find the last commit before corruption
git log --all --full-history -- chainlit_app.py

# Look for commit BEFORE "fix: add checkpoint saving..."
# Should be around commit cc840ee or earlier

# Reset that specific file
git checkout cc840ee8987fa3477c39312cdb40408eb4b6c6af -- chainlit_app.py
git add chainlit_app.py
git commit -m "restore: chainlit_app.py from pre-corruption state"
```

#### Option 2: Restore from Backup
If you have a local backup or the file in your working directory:
```bash
cp /path/to/backup/chainlit_app.py ./chainlit_app.py
git add chainlit_app.py
git commit -m "restore: chainlit_app.py from backup"
```

#### Option 3: Manual Reconstruction
If neither works, you'll need to reconstruct from the code provided in earlier documentation or from your development environment.

---

## Once Restored: Apply These Critical Fixes

### FIX #1: Session Persistence

**File**: `chainlit_app.py`  
**Function**: `handle_message` (around line 500-550)  
**Problem**: Turns don't save to checkpoint

**Find this section:**
```python
@cl.on_message
async def handle_message(message: cl.Message):
    state: GameState | None = cl.user_session.get("game_state")
    session_id: str | None = cl.user_session.get("session_id")
    
    # ... action setup code ...
    
    # Execute turn
    msg = cl.Message(
        content="Resolving action...", 
        author="Dungeon Master", 
        elements=[sfx] if sfx else []
    )
    await msg.send()

    try:
        state = await orchestrator_service.execute_turn(state)  # ❌ OLD - NO CONFIG
        
        # Update turn counter
        turn = state.get("metadata", {}).get("turn", 0) + 1
        state["metadata"]["turn"] = turn

        # Save session
        session_service.update_session(session_id, turn)
        cl.user_session.set("game_state", state)
```

**Replace with:**
```python
@cl.on_message
async def handle_message(message: cl.Message):
    state: GameState | None = cl.user_session.get("game_state")
    session_id: str | None = cl.user_session.get("session_id")
    
    # ... action setup code ...
    
    # Execute turn
    msg = cl.Message(
        content="Resolving action...", 
        author="Dungeon Master", 
        elements=[sfx] if sfx else []
    )
    await msg.send()

    try:
        # CRITICAL FIX: Create config with session_id for checkpoint
        config = {"configurable": {"thread_id": session_id}}
        
        # Execute turn WITH config
        state, gameplay_state = await orchestrator_service.execute_turn(state, config=config)
        
        # Update turn counter
        turn = state.get("metadata", {}).get("turn", 0) + 1
        state["metadata"]["turn"] = turn
        
        # CRITICAL FIX: Save to LangGraph checkpoint explicitly
        await orchestrator_service.compiled_graph.aupdate_state(config, state)
        logger.log_event("System", "Checkpoint", f"Turn {turn} saved")

        # Update session metadata
        session_service.update_session(session_id, turn)
        cl.user_session.set("game_state", state)
```

**Changes Made:**
1. Added `config` dict with session_id
2. Changed `execute_turn(state)` to `execute_turn(state, config=config)`
3. Added explicit checkpoint save with `aupdate_state()`
4. Added logging for checkpoint

---

### FIX #2: Action-Specific Narration

**File**: `src/agents/dungeon_master/graph.py`  
**Method**: `narrate_outcome_with_tokens` (around line 350-430)  
**Problem**: All actions get identical narration

**Step 1: Add action hints mapping (after imports, around line 10)**
```python
# After existing imports, add:
from src.core.gameplay_phase import ActionIntentType

# Add action-specific narration hints
ACTION_NARRATION_HINTS = {
    ActionIntentType.ATTACK: "Describe the combat maneuver, weapon impact, and enemy reaction.",
    ActionIntentType.CAST_SPELL: "Describe magical energy, spell effects, and arcane outcomes.",
    ActionIntentType.INVESTIGATE: "Describe what the character discovers, notices, or learns.",
    ActionIntentType.DIALOGUE: "Describe the conversation, NPC reactions, and social dynamics.",
    ActionIntentType.MOVE: "Describe the movement, terrain, and arrival at destination.",
    ActionIntentType.DEFEND: "Describe defensive positioning, protection, and reaction.",
    ActionIntentType.STEALTH: "Describe sneaking, hiding, and avoiding detection.",
    ActionIntentType.SKILL_CHECK: "Describe the attempt, technique used, and result.",
}
```

**Step 2: Update system_prompt (around line 380-410)**

**Find this section:**
```python
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
```

**Replace with:**
```python
        # Get action-specific narration hint
        action_hint = ACTION_NARRATION_HINTS.get(
            token.intent_type,
            "Describe what happens as a result of this specific action."
        )
        
        # Get action type as string
        action_type_str = token.intent_type.value if hasattr(token.intent_type, 'value') else str(token.intent_type)
        
        system_prompt = f"""
You are the Dungeon Master.

Narrate the IMMEDIATE CONSEQUENCE of the player's SPECIFIC action in visceral, immersive prose.

** PLAYER ACTION:**
- Action Type: {action_type_str}
- What They Did: "{action.description}"
- Narration Focus: {action_hint}

** MECHANICAL OUTCOME:**
- Roll: {roll_total} vs DC {dc}
- Result: {'SUCCESS - The action achieves its intended effect' if is_success else 'FAILURE - The action does not succeed as intended'}
- Effectiveness: {effectiveness:.0%}
- Damage Dealt: {damage} HP (if applicable)

CRITICAL RULES:
1. Narrate SPECIFICALLY what happens when the player "{action.description}".
2. {'Show how their action SUCCEEDS and what it achieves' if is_success else 'Show how their action FAILS and what goes wrong'}.
3. Make it FELT through sensory detail - match the action type.
```

**Step 3: Update context_block (around line 420-430)**

**Find this section:**
```python
        context_block = f"""
Action: {action.description}
Roll Details: {token.mechanical_summary}
Location: {actor_location}
World Changes: {len(world_changes)} state change(s) applied
        """
```

**Replace with:**
```python
        # Enhanced context with action emphasis
        action_type_str = token.intent_type.value if hasattr(token.intent_type, 'value') else str(token.intent_type)
        
        context_block = f"""
PLAYER ACTION:
  Type: {action_type_str}
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
The narration MUST be different based on whether they attacked, cast a spell, investigated, talked, etc.
        """
```

---

## Testing After Fixes

### Test 1: Session Persistence
```
1. Start new game
2. Play 2 turns
3. Note turn number in UI
4. Close browser completely
5. Reopen application
6. Select "Load Game"
7. VERIFY: Previous session appears
8. VERIFY: Turn counter matches
9. VERIFY: Can continue playing
10. Play 1 more turn
11. Close and reload again
12. VERIFY: Now shows 3 turns
```

**Expected**: ✅ Sessions persist, game resumes correctly

### Test 2: Action Variety
```
Turn 1: "I attack the goblin with my sword"
  EXPECT: Narration about sword, blade, strike, combat
  
Turn 2: "I cast fireball at the enemies"
  EXPECT: Narration about fire, magic, flames, spell
  NOT: Any mention of swords or melee
  
Turn 3: "I search the room for hidden doors"
  EXPECT: Narration about searching, finding, discovering
  NOT: Any mention of combat or magic
  
Turn 4: "I try to persuade the guard to let us pass"
  EXPECT: Narration about talking, convincing, social interaction
  NOT: Any mention of attacking or searching
```

**Expected**: ✅ Each action gets unique, contextual narration

---

## Verification Checklist

- [ ] chainlit_app.py restored and functional
- [ ] Session persistence fix applied (config parameter)
- [ ] Checkpoint saving added (aupdate_state call)
- [ ] Action hints dictionary added to DM graph
- [ ] System prompt updated with action details
- [ ] Context block updated with action emphasis
- [ ] Test 1 passed (sessions persist)
- [ ] Test 2 passed (actions vary)
- [ ] No errors in logs
- [ ] Game runs smoothly

---

## Commit Messages

```bash
# After restoring file
git add chainlit_app.py
git commit -m "restore: chainlit_app.py from pre-corruption state"

# After applying Fix #1
git add chainlit_app.py
git commit -m "fix: add session persistence with checkpoint saving"

# After applying Fix #2
git add src/agents/dungeon_master/graph.py
git commit -m "fix: add action-specific narration with contextual hints"

# Push all fixes
git push origin main
```

---

## If Recovery Fails

If you cannot recover chainlit_app.py from git history or backups:

1. Check your local development environment
2. Look for IDE backup files (.bak, ~, etc.)
3. Check CI/CD artifacts
4. Reconstruct from documentation in earlier commits
5. Reach out to team members for their local copy

The file structure is documented in:
- Earlier commits (before fae28b3)
- This repository's commit history
- Team members' working directories

---

**PRIORITY**: Restore chainlit_app.py FIRST, then apply fixes

**TIME ESTIMATE**: 
- Recovery: 10-15 minutes
- Fix #1: 5 minutes
- Fix #2: 15 minutes
- Testing: 20 minutes
- **Total: ~1 hour**
