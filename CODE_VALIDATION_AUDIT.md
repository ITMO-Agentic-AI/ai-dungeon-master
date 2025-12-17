# 🔍 Code Validation Audit Report

**Date**: December 17, 2025  
**Status**: ❌ **12 CRITICAL ISSUES IDENTIFIED**  
**Severity**: 🔴 HIGH - Blocks gameplay, broken mechanics  

---

## Executive Summary

### Issues Found: 12 Critical
- ❌ **4 Dice Roll Issues** - Rolls not integrated, no modifiers applied
- ❌ **3 Narration Issues** - Repeats instead of action outcomes
- ❌ **2 Type Errors** - None assertions, type mismatches
- ❌ **2 Logic Errors** - Outcome tokens not passed to DM, JSON extraction broken
- ❌ **1 State Management Error** - No outcome persistence

### Game Status
- **Playable**: ❌ **NO** - DM narration repeats every turn
- **Mechanics**: ❌ **NO** - Dice rolls not affecting gameplay
- **Production Ready**: ❌ **NO**

---

## 🔴 CRITICAL ISSUES

### ISSUE #1: Dice Rolls Exist But Not Used
**File**: `src/services/gameplay_executor.py` (lines 280-310)  
**Severity**: 🔴 CRITICAL  
**Status**: ❌ NOT FIXED

**Problem**:
```python
def _generate_roll_for_intent(self, ...) -> RollResult:
    """Generate appropriate D&D roll"""
    # Line 295: Generates RollResult with d20 + modifier
    return RollResult(
        dice_type="d20",
        rolls=[random.randint(1, 20)],  # ✓ Correct
        modifier=modifier,               # ✓ Correct
        total=rolls[0] + modifier,       # ✓ Correct
        ...
    )
```

**Then in _step2_validate_actions (line 230)**:
```python
primary_roll = self._generate_roll_for_intent(intent_type, game_state, performer_id)
dc = 10  # DC IS HARDCODED!
meets_dc = primary_roll.total >= dc  # ✓ Comparison is OK
```

**Issue**: 
- ✅ Rolls ARE generated correctly
- ❌ DC is ALWAYS 10 (hardcoded)
- ❌ No ability score modifiers applied to rolls
- ❌ No advantage/disadvantage system
- ❌ Rolls don't affect narration

**Example**:
```
Turn 1: Roll 18 - "The action unfolds before you..."
Turn 2: Roll 8 - "The action unfolds before you..."  ← SAME NARRATION!
```

**Fix Needed**:
1. Calculate DC based on action difficulty
2. Apply ability modifiers correctly
3. Pass roll result to DM narration
4. Make narration outcome-aware

---

### ISSUE #2: DM Narration Ignores Roll Results
**File**: `src/agents/dungeon_master/graph.py` (lines 175-185)  
**Severity**: 🔴 CRITICAL  
**Status**: ❌ NOT FIXED

**Problem**:
```python
async def narrate_outcome(self, state: GameState) -> dict:
    outcome = state.get("last_outcome")
    directives = state.get("director_directives")
    action = state.get("current_action")
    
    # MISSING: outcome_tokens = state.get("outcome_tokens")  ← NOT RETRIEVED!
    # MISSING: roll_results = state.get("roll_results")      ← NOT RETRIEVED!
    
    context_block = f"""
Action: {action.description if action else 'Unknown'}
Outcome: {outcome.narrative_result}  ← Generic outcome!
Location: {actor_location}
    """
```

**Issue**:
- ❌ Doesn't receive ActionOutcomeToken from Step 2
- ❌ Doesn't see RollResult from dice
- ❌ Doesn't know if roll was success/failure
- ❌ Narration is generic: "The action unfolds"
- ❌ Same narration every turn

**Example**:
```
Player: "I attack the goblin"
Roll: 18 vs DC 10 = SUCCESS
DM: "The action unfolds before you."  ← Should say "Your blade cleaves through!"

Player: "I attack the goblin again"
Roll: 4 vs DC 10 = FAILURE
DM: "The action unfolds before you."  ← Same narration! Should say "You miss wildly!"
```

**Fix Needed**:
1. Pass outcome_tokens to DM
2. Pass roll_results to DM
3. Include success/failure in prompt
4. Make narration outcome-aware

---

### ISSUE #3: ActionOutcomeToken Not Passed to DM
**File**: `src/services/gameplay_executor.py` (line 170)  
**Severity**: 🔴 CRITICAL  
**Status**: ❌ NOT FIXED

**Problem**:
```python
# STEP 2: Generate outcome tokens with dice rolls
outcome_tokens = await self._step2_validate_actions(...)
self.gameplay_state.outcome_tokens = outcome_tokens

# STEP 4: Call DM to narrate
narration_result = await self._step4_narrate_outcome(
    game_state,
    outcome_tokens,   # ← PASSED TO FUNCTION
    state_changes,
    dm
)
```

**But in _step4_narrate_outcome**:
```python
async def _step4_narrate_outcome(
    self,
    game_state: GameState,
    outcome_tokens: list[ActionOutcomeToken],  # ← RECEIVED
    state_changes: list[WorldStateChange],
    dm: Any
) -> ActionOutcome:
    # ...
    if dm is None:
        outcome = ActionOutcome(...)  # Mock
    else:
        dm_response = await dm.narrate_outcome(game_state)  # ← ONLY PASSED game_state!
```

**Issue**:
- ❌ outcome_tokens are passed to _step4 but NOT to DM.narrate_outcome()
- ❌ DM function signature doesn't accept outcome_tokens
- ❌ DM can't access dice roll results
- ❌ DM only gets generic game_state

**Fix Needed**:
1. Update DM.narrate_outcome() signature to accept outcome_tokens
2. Pass outcome_tokens from _step4_narrate_outcome to dm.narrate_outcome()
3. Update game_state to include outcome_tokens

---

### ISSUE #4: No Outcome Stored in GameState Between Steps
**File**: `src/services/gameplay_executor.py` (lines 145-180)  
**Severity**: 🔴 CRITICAL  
**Status**: ❌ NOT FIXED

**Problem**:
```python
# Step 2: Generate outcomes
outcome_tokens = await self._step2_validate_actions(...)
self.gameplay_state.outcome_tokens = outcome_tokens  # ← Stored in gameplay_state

# NOT stored in game_state!
# game_state doesn't have outcome_tokens

# Later: game_state["last_outcome"] = narration_result
# But narration_result doesn't know about roll results
```

**Issue**:
- ❌ outcome_tokens stored in gameplay_state, not game_state
- ❌ DM narrate_outcome() only receives game_state
- ❌ DM can't access outcome_tokens
- ❌ Information flow broken

**Fix Needed**:
1. Store outcome_tokens in game_state dict
2. Store roll_results in game_state dict
3. Pass through all steps

---

### ISSUE #5: JSON Extraction Breaks Narration
**File**: `src/agents/dungeon_master/graph.py` (lines 190-230)  
**Severity**: 🔴 CRITICAL  
**Status**: ❌ NOT FIXED

**Problem**:
```python
def _extract_narrative_and_suggestions(self, content: str) -> tuple[str, list[str]]:
    """
    Expected format:
    [Narrative text...]
    
    ```json
    {"action_suggestions": ["Suggestion 1", ...]}
    ```
    """
    try:
        if "```json" in content:
            start = content.find("```json") + len("```json")
            end = content.find("```", start)
            if end > start:
                json_str = content[start:end].strip()
                json_data = json.loads(json_str)
                suggestions = json_data.get("action_suggestions", default_suggestions)
                narrative = content[: content.find("```json")].strip()
                return narrative, suggestions  # ← Returns ONLY text before JSON
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse suggestions JSON: {e}")
    
    # Fallback: return full content as narrative with defaults
    return content, default_suggestions
```

**Issue**:
- ✓ Logic looks correct
- ❌ But LLM might not output JSON
- ❌ LLM might output incomplete JSON
- ❌ Fallback returns full content (including failed JSON attempts)
- ❌ No validation of output format

**Fix Needed**:
1. Validate LLM output format
2. Regenerate if invalid
3. Better error messages
4. Ensure JSON is always present

---

### ISSUE #6: No DC Calculation Based on Action Type
**File**: `src/services/gameplay_executor.py` (line 225)  
**Severity**: 🔴 CRITICAL  
**Status**: ❌ NOT FIXED

**Problem**:
```python
async def _step2_validate_actions(...):
    for action_idx, action in enumerate(player_actions):
        intent_type = action["intent_type"]
        # ...
        dc = 10  # ← ALWAYS 10! No variation!
        meets_dc = primary_roll.total >= dc
```

**Should be**:
```python
dc = self._get_dc_for_intent(intent_type)  # Varies by action

def _get_dc_for_intent(self, intent_type: ActionIntentType) -> int:
    """Get DC based on action difficulty"""
    dc_map = {
        ActionIntentType.ATTACK: 12,       # Moderate
        ActionIntentType.INVESTIGATE: 10,  # Easy
        ActionIntentType.DIALOGUE: 11,     # Moderate
        ActionIntentType.CAST_SPELL: 13,   # Hard
        ActionIntentType.MOVE: 8,          # Easy
        ActionIntentType.DEFEND: 10,       # Moderate
    }
    return dc_map.get(intent_type, 10)
```

**Issue**:
- ❌ All actions have DC 10
- ❌ Spells not harder than movement
- ❌ Attacks not harder than investigation
- ❌ No difficulty scaling

**Fix Needed**:
Implement DC calculation by action type

---

### ISSUE #7: ActionOutcomeToken.damage_dealt Never Set
**File**: `src/services/gameplay_executor.py` (lines 238-252)  
**Severity**: 🔴 CRITICAL  
**Status**: ❌ NOT FIXED

**Problem**:
```python
token = ActionOutcomeToken(
    action_id=f"action_{...}",
    performer_id=performer_id,
    intent_type=intent_type,
    status=ActionResolutionStatus.RESOLVED,
    primary_roll=primary_roll,
    difficulty_class=dc,
    meets_dc=meets_dc,
    mechanical_summary=f"...",
    effectiveness=min(1.0, primary_roll.total / dc) if dc > 0 else 1.0,
    is_valid=True
    # MISSING: damage_dealt not set!
    # MISSING: ability_check not set!
    # MISSING: modifier_breakdown not set!
)
```

**Then later**:
```python
if token.damage_dealt > 0:  # ← AttributeError! Never set!
    change = WorldStateChange(...)
```

**Issue**:
- ❌ damage_dealt never set
- ❌ Creates AttributeError when checking `if token.damage_dealt`
- ❌ World state changes not applied
- ❌ Actions have no mechanical effect

**Fix Needed**:
1. Set damage_dealt for ATTACK actions
2. Set ability_check for all rolls
3. Set modifier_breakdown
4. Calculate based on intent and roll success

---

### ISSUE #8: World State Changes Not Applied
**File**: `src/services/gameplay_executor.py` (line 265)  
**Severity**: 🟠 HIGH  
**Status**: ❌ NOT FIXED

**Problem**:
```python
async def _step3_update_world(...):
    state_changes: list[WorldStateChange] = []
    
    for token in outcome_tokens:
        if token.meets_dc:
            if token.damage_dealt > 0:  # ← This throws AttributeError!
                change = WorldStateChange(...)
                state_changes.append(change)
        else:
            logger.info(f"Action failed")
    
    # state_changes are created but never applied to game_state!
    return state_changes  # ← Returns but doesn't modify game_state
```

**Issue**:
- ❌ Changes generated but not applied
- ❌ No updates to player health
- ❌ No updates to enemy health
- ❌ No updates to world state
- ❌ Actions are purely narrative

**Fix Needed**:
1. Apply state_changes to game_state
2. Update player/NPC health
3. Update world locations
4. Track consequences

---

### ISSUE #9: ActionOutcomeToken Type Has Missing Fields
**File**: `src/core/types.py` (ActionOutcomeToken definition)  
**Severity**: 🟠 HIGH  
**Status**: ❌ NOT FIXED

**Problem**:
If ActionOutcomeToken doesn't have all required fields:
- damage_dealt
- ability_check
- modifier_breakdown
- secondary_roll
- status_effects

Then the code will fail.

**Check**: Need to verify ActionOutcomeToken has all required fields

**Fix Needed**:
Ensure ActionOutcomeToken has all mechanical fields

---

### ISSUE #10: No Outcome Persistence Between Turns
**File**: `src/services/gameplay_executor.py` (line 200)  
**Severity**: 🟠 HIGH  
**Status**: ❌ NOT FIXED

**Problem**:
```python
game_state["last_outcome"] = narration_result
# narration_result is ActionOutcome with just narrative_result
# No mechanical outcome stored
# No roll results stored
# No effectiveness stored
```

**Issue**:
- ❌ Only narrative stored, not mechanical outcome
- ❌ No way to verify actions had effect
- ❌ No persistent state of world changes
- ❌ No way to track cumulative damage

**Fix Needed**:
1. Store full ActionOutcomeToken in game_state
2. Store mechanical outcomes
3. Persist world state changes

---

### ISSUE #11: DM Doesn't Know Action Success/Failure
**File**: `src/agents/dungeon_master/graph.py` (lines 175-185)  
**Severity**: 🟠 HIGH  
**Status**: ❌ NOT FIXED

**Problem**:
```python
async def narrate_outcome(self, state: GameState) -> dict[str, Any]:
    outcome = state.get("last_outcome")  # ← Generic outcome
    # Doesn't have:
    # - Roll total
    # - DC value
    # - Success/failure flag
    # - Effectiveness percentage
    # - Damage dealt
```

**Issue**:
- ❌ DM doesn't know roll value
- ❌ DM doesn't know DC
- ❌ DM doesn't know success/failure
- ❌ DM can't narrate consequences properly

**Example**:
```
Player: "I attack"
Roll: 18 vs DC 10
DM doesn't know: "The action unfolds"
Should know: "Your blade slices cleanly across..."
```

**Fix Needed**:
Include outcome_tokens in state passed to DM

---

### ISSUE #12: No Ability Score Checks Beyond STR
**File**: `src/services/gameplay_executor.py` (lines 290-310)  
**Severity**: 🟠 HIGH  
**Status**: ❌ PARTIALLY IMPLEMENTED

**Problem**:
```python
def _generate_roll_for_intent(...):
    if intent_type == ActionIntentType.ATTACK:
        modifier = (player.stats.strength - 10) // 2
    elif intent_type == ActionIntentType.CAST_SPELL:
        modifier = (player.stats.intelligence - 10) // 2
    elif intent_type == ActionIntentType.DIALOGUE:
        modifier = (player.stats.charisma - 10) // 2
    elif intent_type == ActionIntentType.INVESTIGATE:
        modifier = (player.stats.wisdom - 10) // 2
    # MISSING: DEX checks
    # MISSING: CON checks
    # MISSING: Proficiency bonus
    # MISSING: Advantage/disadvantage
```

**Issue**:
- ✓ Basic ability modifiers work
- ❌ Missing DEX-based actions
- ❌ No proficiency bonus
- ❌ No advantage/disadvantage
- ❌ No skill modifiers

**Fix Needed**:
1. Add DEX checks for MOVE actions
2. Add proficiency bonus
3. Add advantage/disadvantage system

---

## Summary Table

| # | Issue | File | Line | Severity | Status |
|---|-------|------|------|----------|--------|
| 1 | Dice rolls not affecting narration | gameplay_executor.py | 230 | 🔴 | ❌ |
| 2 | DM ignores roll results | dungeon_master/graph.py | 175 | 🔴 | ❌ |
| 3 | outcome_tokens not passed to DM | gameplay_executor.py | 170 | 🔴 | ❌ |
| 4 | No outcome in GameState | gameplay_executor.py | 145 | 🔴 | ❌ |
| 5 | JSON extraction issues | dungeon_master/graph.py | 190 | 🔴 | ⚠️ |
| 6 | DC always 10 (no variation) | gameplay_executor.py | 225 | 🔴 | ❌ |
| 7 | damage_dealt never set | gameplay_executor.py | 240 | 🔴 | ❌ |
| 8 | State changes not applied | gameplay_executor.py | 265 | 🟠 | ❌ |
| 9 | ActionOutcomeToken missing fields | types.py | ? | 🟠 | ❓ |
| 10 | No outcome persistence | gameplay_executor.py | 200 | 🟠 | ❌ |
| 11 | DM doesn't know success/failure | dungeon_master/graph.py | 175 | 🟠 | ❌ |
| 12 | Missing ability checks | gameplay_executor.py | 290 | 🟠 | ⚠️ |

---

## Impact on Gameplay

### Current Behavior
```
Turn 1:
  Player: "I attack the goblin"
  Roll: 18 (success)
  DM: "The action unfolds before you..."
  Effect: NONE

Turn 2:
  Player: "I attack the goblin again"
  Roll: 4 (failure)
  DM: "The action unfolds before you..."  ← SAME!
  Effect: NONE
```

### Expected Behavior
```
Turn 1:
  Player: "I attack the goblin"
  Roll: 18+3=21 vs DC 12 = SUCCESS
  DM: "Your blade finds its mark! The goblin reels back, blood streaming."
  Effect: Goblin takes 7 damage (18-11)

Turn 2:
  Player: "I attack the goblin again"
  Roll: 4+3=7 vs DC 12 = FAILURE
  DM: "Your swing goes wide! The goblin laughs mockingly."
  Effect: NONE
```

---

## Next Steps

### Immediate (Priority 1)
1. Fix outcome_tokens state management
2. Pass roll results to DM narration
3. Make narration outcome-aware
4. Set DC by action type

### Short Term (Priority 2)
1. Calculate damage properly
2. Apply world state changes
3. Add ability checks for all action types
4. Add proficiency bonuses

### Medium Term (Priority 3)
1. Add advantage/disadvantage
2. Add skill modifier system
3. Add critical hits/fumbles
4. Add combat modifiers (cover, range, etc)

---

## Files to Modify

1. `src/services/gameplay_executor.py` - Fix outcome tracking and state management
2. `src/agents/dungeon_master/graph.py` - Accept and use outcome_tokens
3. `src/core/types.py` - Verify ActionOutcomeToken fields
4. `src/core/gameplay_phase.py` - Add missing fields to ActionOutcomeToken

---

**Status**: 🔴 BROKEN - Multiple critical issues prevent proper gameplay

**Blockers**: Issues #1-4, #6-7 must be fixed before game is playable
