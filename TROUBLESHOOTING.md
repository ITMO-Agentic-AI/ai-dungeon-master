# 🎮 AI Dungeon Master - Troubleshooting & Fixes Guide

## Recent Fixes Applied

### ✅ Fix 1: Unicode Encoding Error (Windows Compatibility)

**Problem:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2192' in position 94
```

**Root Cause:**
- Windows uses `cp1252` encoding by default, which doesn't support Unicode arrow `→` (U+2192)
- The logger tried to print: `"Phase 1: Story Architect → Lore Builder → ..."`

**Solution Applied:**
- Replaced Unicode arrow `→` with ASCII `->` in `orchestrator_service.py`
- Changed: `"Phase 1: Story Architect → Lore Builder → World Engine → Player Creator (PARALLEL) → Initial DM"`
- To: `"Phase 1: Story Architect -> Lore Builder -> World Engine -> Player Creator (PARALLEL) -> Initial DM"`

**Status:** ✅ FIXED - Commit: `3fb9f49`

---

### ✅ Fix 2: LangGraph Recursion Limit Error (Phase 1)

**Problem:**
```
GraphRecursionError: Recursion limit of 25 reached without hitting a stop condition.
```

**Root Cause:**
- Phase 1 setup was routing to `dm_planner` instead of exiting
- The graph tried to loop Phase 2 gameplay logic during initialization
- No clear exit point from Phase 1, causing infinite recursion

**Architecture Issue:**
```
❌ WRONG (creates infinite loop):
story_architect -> lore_builder -> world_engine -> player_creator -> initial_dm -> dm_planner
                                                                                     ↑_______↓
                                                                                   (loops forever)

✅ CORRECT (exits Phase 1 cleanly):
story_architect -> lore_builder -> world_engine -> player_creator -> initial_dm -> phase1_complete -> END
```

**Solution Applied:**
1. Created new `_phase1_complete_node()` that marks end of setup
2. Changed edge from `initial_dm` → `dm_planner` to `initial_dm` → `phase1_complete` → `END`
3. Phase 2 gameplay now only runs when `execute_turn()` is called from main.py

**Status:** ✅ FIXED - Commit: `34f53a19`

---

### ✅ Fix 3: Phase 2 Infinite Loop (Gameplay Turn Recursion)

**Problem:**
```
GraphRecursionError: Recursion limit of 25 reached without hitting a stop condition.
2025-12-11 11:15:25,122 - Turn 1 execution failed: Recursion limit of 25...
```

**Symptoms:**
- Game starts fine, Phase 1 completes
- Player enters a command like "What can I do?"
- Game says "⚙️ Resolving action..."
- After ~3 minutes, crashes with recursion limit error
- Player stats are updating multiple times during the resolution

**Root Cause:**
- Phase 2 gameplay loop had `dm_outcome -> dm_planner` edge
- This created an **infinite loop within a single `ainvoke()` call**
- Flow: dm_planner -> (resolve/question) -> director -> dm_outcome -> dm_planner -> ... (repeat forever)
- Graph would loop until recursion_limit (25) was hit, causing crash

**Architecture Issue:**
```
❌ WRONG (infinite loop):
dm_planner -> action_resolver -> judge -> world_update -> director -> dm_outcome
                                                                         ↑________↓
                                                                    (loops forever)
                                                                  dm_planner

✅ CORRECT (exits after one turn):
dm_planner -> action_resolver -> judge -> world_update -> director -> dm_outcome -> turn_complete -> END
```

**Key Insight:**
- `main.py` calls `execute_turn()` once per player action
- The graph should complete ONE TURN and exit, not loop within ainvoke()
- Main.py's game loop handles the iteration: "player input" -> "execute_turn()" -> "show narration" -> "repeat"

**Solution Applied:**
1. Created new `_turn_complete_node()` that marks end of single turn
2. Changed edge from `dm_outcome` → `dm_planner` to `dm_outcome` → `turn_complete` → `END`
3. Graph now exits after narration, returning control to main.py
4. Main.py's outer loop handles "next turn" by calling execute_turn() again

**Changes Made:**
- File: `src/services/orchestrator_service.py`
- Added: `turn_complete` node and `_turn_complete_node()` method
- Modified: `dm_outcome` exit edge (was `->dm_planner`, now `->turn_complete`)
- Updated: Docstrings to explain single-turn semantics

**Status:** ✅ FIXED - Commit: `5f261e1685aa582`

---

## Understanding the Two-Phase Architecture

### Phase 1: World Initialization (One-Time Setup)

**Runs once** when the game starts. All agents collaborate to create the world:

```
initialize_world() in main.py
    ↓
orchestrator.initialize_world(state)
    ↓
Graph execution (START -> END):
  1. story_architect.plan_narrative()      [Create narrative]
  2. lore_builder.build_lore()             [Create world lore]
  3. world_engine.instantiate_world()      [Create locations & NPCs]
  4. player_proxy.process()                [Create characters IN PARALLEL]
  5. dm.narrate_initial()                  [Opening narration]
  6. phase1_complete()                     [Mark end of setup]
  7. END                                   [Graph exits]
    ↓
Return state to main.py
```

**Key:** Graph exits after narrate_initial. Does NOT continue to gameplay loop.

### Phase 2: Gameplay Loop (Per-Turn Execution)

**Runs repeatedly** (once per player action). Each call to `execute_turn()` processes ONE complete turn:

```
main.py game loop:
  for each turn:
      ↓
    execute_turn(state) [This calls ainvoke() ONCE]
      ↓
    Graph execution (START -> END):
      1. dm_planner.plan_response()        [Classify: action/question/exit]
      2. [Route based on classification]
         - If action: action_resolver -> judge -> world_update
         - If question: lore_builder_question -> director
      3. director.direct_scene()           [Pacing & mood]
      4. dm_outcome.narrate_outcome()      [Describe results]
      5. turn_complete()                   [Mark end of turn]
      6. END                               [Graph exits]
      ↓
    Return state to main.py
      ↓
    Display narration to player
      ↓
    Loop: get next player input
```

**Key:** Each `execute_turn()` call runs exactly ONE complete graph from dm_planner to END.
Then control returns to main.py, which loops and calls execute_turn() again.

---

## How to Test the Fixes

### 1. Update Your Local Repository
```bash
git pull origin main
```

### 2. Run the Game
```bash
python main.py
```

### 3. Watch for Success Indicators

**Phase 1 (World Initialization):**
```
🎲 Initializing game world...
This may take a moment as the AI creates your adventure...

[LLM API calls...]

✅ World Created!
📖 Campaign: [Campaign Name]
👥 Your Characters:
  • [Character Name] - [Race] [Class]
  • ...

📜 DUNGEON MASTER
[Opening narrative with embedded action suggestions]
```

**Phase 2 (First Turn):**
```
> What can I do?

⚙️  Resolving action...

📜 DUNGEON MASTER
[Narrative response with embedded next-action suggestions]

> [Next player input]
```

**Success Conditions:**
- ❌ NO UnicodeEncodeError with `→` character
- ❌ NO "Recursion limit of 25" error
- ✅ "World Created!" displays
- ✅ Opening narration shows
- ✅ Player can enter action
- ✅ Narration response shows
- ✅ Game accepts another action

---

## Common Issues & Solutions

### Issue: "Recursion limit of 25 reached" DURING GAMEPLAY

**Symptoms:**
- World initializes fine (✅ Phase 1 complete)
- Player enters first action
- Game says "⚙️ Resolving action..."
- After 2-3 minutes: "❌ Recursion limit of 25 reached"

**Why it happens:**
- Graph routing is looping instead of exiting
- Phase 2 edges still have old routing (dm_outcome -> dm_planner)
- Fix was not applied or pulled

**Solution:**
- ✅ Already fixed in latest commit (`5f261e1685aa582`)
- Make sure you've pulled:
  ```bash
  git pull origin main
  ```
- Clear Python cache:
  ```bash
  find . -type d -name __pycache__ -exec rm -r {} +
  find . -type f -name "*.pyc" -delete
  ```
- Run again:
  ```bash
  python main.py
  ```

### Issue: "Recursion limit of 25 reached" DURING WORLD INIT

**Symptoms:**
- Game shows "🎲 Initializing game world..."
- After 1-2 minutes: "❌ Recursion limit of 25 reached"
- World NEVER initializes

**Why it happens:**
- Old code still has Phase 1 looping (initial_dm -> dm_planner)
- Phase 1 wasn't separated from Phase 2 properly

**Solution:**
- ✅ Already fixed in earlier commit (`34f53a19`)
- Ensure you have commit `34f53a19` or later:
  ```bash
  git log --oneline | head -5
  ```
- If not, pull and check out latest:
  ```bash
  git pull origin main
  git checkout main
  ```

### Issue: "UnicodeEncodeError: 'charmap' codec" on Windows

**Symptoms:**
- Windows console error during initialization
- Message mentions 'charmap' or cp1252
- Game won't start

**Why it happens:**
- Non-ASCII characters (like `→`) in log messages
- Windows using cp1252 instead of UTF-8

**Solution:**
- ✅ Already fixed by replacing `→` with `->`
- If still occurring, set environment variable:
  ```bash
  set PYTHONIOENCODING=utf-8
  python main.py
  ```

### Issue: Game gets stuck during world initialization (no errors, just hangs)

**Symptoms:**
- "🎲 Initializing game world..." stays on screen
- No error message
- No progress after 5+ minutes

**Why it happens:**
- LLM API is slow or unresponsive
- Network timeout
- Model is processing complex prompts

**Solution:**
1. Check LLM API is running:
   ```bash
   curl http://a6k2.dgx:34000/v1/chat/completions
   ```
2. Check logs for details:
   ```bash
   tail -f game.log
   ```
3. Look for HTTP POST calls - these show LLM is responding
4. If stuck for >10 minutes, try:
   - Kill process (Ctrl+C)
   - Check LLM server status
   - Increase timeout in `src/core/config.py` if needed

### Issue: Player stats updating when they shouldn't be

**Symptoms:**
- Player asks "What can I do?" (a question, not an action)
- Player HP or stats change
- Expected: Just narration, no mechanical changes
- Actual: "[Player Proxy] Updating Player Sheets (Gameplay)"

**Why it happens:**
- Question is being routed as action (check `dm.plan_response()` classification)
- Action resolver is processing what should be a question
- World update is happening even though player didn't take a mechanical action

**Solution:**
1. Check `plan_response()` in `src/agents/dungeon_master/graph.py`
   - Look at keyword lists for "is_action" and "is_question"
   - "What can I do?" should match "is_question" (contains "what")
2. Verify routing in orchestrator:
   - "question" classification should route to `lore_builder_question`
   - NOT to `action_resolver`
3. If still wrong, add logging:
   ```python
   logger.debug(f"Classification: is_action={is_action}, is_question={is_question}")
   ```
4. Adjust keyword detection if needed

### Issue: No action suggestions in DM narration

**Symptoms:**
- DM narration shows
- But ends abruptly
- Missing: "You notice...", "A sound...", "Ahead lies..."
- Player doesn't know what to do next

**Why it happens:**
- LLM might be cutting off output
- System prompt not clear enough
- Model temperature too low (not creative enough)
- Prompt is too long, model hits token limit

**Solution:**
1. Check system prompt in `narrate_outcome()`:
   - Rule #3 should be: "End with 2-3 natural narrative prompts"
   - Examples should include: "A sound...", "You notice...", "Ahead lies..."
2. Test with shorter action:
   - Instead of "What can I do?", try "look around"
   - See if narration includes suggestions
3. Increase model temperature:
   - In `src/core/config.py`: `model_temperature = 0.8` or higher
   - This makes model more creative
4. Check LLM output in logs:
   ```bash
   grep "Narrate the IMMEDIATE" game.log
   ```
   - Look for full narration text
   - See if suggestions are there but cut off

---

## Testing Checklist

Before considering the fix complete, verify:

- [ ] Game starts without UnicodeEncodeError
- [ ] World initialization completes (no recursion error during Phase 1)
- [ ] Campaign and character info displays
- [ ] Opening narration shows with embedded action suggestions
- [ ] Player can enter first action
- [ ] "⚙️ Resolving action..." shows briefly (~5-10 sec)
- [ ] NO "Recursion limit" error after player's first action
- [ ] DM narration displays for first turn
- [ ] Player can enter second action
- [ ] Game continues smoothly for 3+ turns
- [ ] No "Recursion limit" errors in logs
- [ ] game.log contains "Turn X complete. Returning to main.py." for each turn
- [ ] Player can type "quit" to exit cleanly

---

## File Changes Summary

### All Fixes (3 commits)

**Commit 1: Unicode Fix (`3fb9f49`)**
- File: `src/services/orchestrator_service.py`
- Change: Line 272 - Replace `→` with `->`

**Commit 2: Phase 1 Exit Fix (`34f53a19`)**
- File: `src/services/orchestrator_service.py`
- Changes:
  - Added `_phase1_complete_node()` method
  - Changed edge `initial_dm → phase1_complete → END`
  - Updated docstrings to explain Phase 1 separation

**Commit 3: Phase 2 Loop Fix (`5f261e1685aa582`)**
- File: `src/services/orchestrator_service.py`
- Changes:
  - Added `turn_complete` node
  - Added `_turn_complete_node()` method
  - Changed edge `dm_outcome → turn_complete → END` (was `dm_outcome → dm_planner`)
  - Updated docstrings to explain single-turn execution semantics
  - Added detailed explanation of Phase 2 flow

---

## Next Steps

If you encounter new issues:

1. **Check logs first**: `tail -f game.log` for detailed error messages
2. **Test in isolation**: Disable features one by one to find culprit
3. **Add logging**: Insert `logger.debug()` calls to trace execution
4. **Increase recursion limit (temporary)**: In `orchestrator_service.py`:
   ```python
   config = {"configurable": {"thread_id": session_id, "recursion_limit": 50}}
   ```
5. **Report issues** with:
   - Full error traceback from game.log
   - Python version: `python --version`
   - OS: Windows/macOS/Linux
   - LLM API status
   - Exact steps to reproduce

---

## Reference: Graph Structure Comparison

### Before Fixes (Broken)

```
Phase 1:
  START -> story_architect -> lore_builder -> world_engine -> player_creator -> initial_dm
           ↓
           dm_planner  ← WRONG! Should exit here
           ↓
           (looped forever, recursion error)

Phase 2:
  dm_planner -> ... -> dm_outcome
                ↑_______|  WRONG! Should exit here
                (looped forever, recursion error)
```

### After Fixes (Working)

```
Phase 1:
  START -> story_architect -> lore_builder -> world_engine -> player_creator -> initial_dm
           ↓                                                                      ↓
           phase1_complete -> END  ✅ CORRECT: Exits Phase 1

Phase 2:
  dm_planner -> action_resolver -> judge -> world_update -> director -> dm_outcome
                    or                                                    ↓
  dm_planner -> lore_builder_question -> director -> dm_outcome -> turn_complete -> END
                    or                                              ✅ CORRECT: Exits each turn
  dm_planner -> exit_check -> END
```

---

## Summary

✅ **Unicode Error:** Fixed by replacing `→` with `->`
✅ **Phase 1 Loop:** Fixed by adding `phase1_complete` node
✅ **Phase 2 Loop:** Fixed by adding `turn_complete` node

**Next Action:** Pull latest commits and test the game!

```bash
git pull origin main
python main.py
```

Enjoy your adventure! 🎭
