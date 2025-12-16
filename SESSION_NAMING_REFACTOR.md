# 🎮 Session Naming Refactor

## Overview

Refactored the session management system to use **user-created session names** instead of time-based IDs.

**Before:**
```
Session ID: 2025-12-16T09:01:23.456789
(Auto-generated, not user-friendly)
```

**After:**
```
Session Name: "Temple Run #1"
Session ID: temple_run_1 (derived from name)
(User-friendly, semantic, easy to remember)
```

---

## Changes Made

### 1. `main.py` - CLI Interface

**New function: `prompt_for_session_name()`**
- Prompts user to enter a descriptive session name
- Validates input (1-50 chars, alphanumeric + spaces/hyphens/underscores)
- Derives a URL-safe `session_id` from the name:
  - `"Temple Run #1"` → `"temple_run_1"`
  - `"Dragon Hunt"` → `"dragon_hunt"`
  - `"Campaign-2"` → `"campaign_2"`
- Checks for duplicate session names

**Updated function: `initialize_game_state()`**
- Now accepts `session_id` and `session_name` as parameters
- Stores both in `metadata`:
  ```python
  "metadata": {
      "session_id": session_id,
      "session_name": session_name,  # NEW
      "turn": 0,
      "started_at": ...
  }
  ```

**Updated function: `select_or_create_session()`**
- Calls `prompt_for_session_name()` when user chooses "New Game"
- Passes user-provided name to `initialize_game_state()`

**Updated function: `run_game_loop()`**
- When saving new session, uses user-provided session_name instead of auto-generated ID
- Displays session name in "Session Loaded" message

**Example Flow:**
```
🎲 AI DUNGEON MASTER - SESSION MANAGER 🎲

📚 Saved Sessions:
  1. "Temple Run #1"
     Turn 5 | Created: 2025-12-16 | Last: 2025-12-16
     ID: temple_run_1

  N. Start New Game
  Q. Quit

Select option (1-1, N, Q): N

📝 Enter a name for this session (e.g. 'Temple Run #1'): Dragon Hunt Campaign

Session created: dragon_hunt_campaign
```

### 2. `chainlit_app.py` - Web Interface

**New function: `derive_session_id_from_name()`**
- Same logic as CLI version (normalize session name to ID)
- Used when user enters session name via Chainlit web UI

**Updated function: `initialize_game_state()`**
- Now accepts `session_id` and `session_name` parameters
- Stores both in metadata, same as CLI

**Updated function: `start_new_game()`**
- Asks user for session name via `cl.AskUserMessage()`:
  ```
  📝 Name your session (e.g. 'Temple Run #1'):
  ```
- Derives `session_id` from user input
- Passes both to `initialize_game_state()`
- Saves session with user-provided name

**Updated function: `load_existing_game()`**
- Displays session name in loaded game info
- Shows: "**Session:** {session_name}"

---

## Session ID Derivation Rules

The system converts user-friendly session names to URL-safe session IDs:

```python
# Algorithm:
1. Convert to lowercase
2. Replace spaces with underscores
3. Replace hyphens with underscores
4. Collapse multiple underscores
5. Remove leading/trailing underscores

# Examples:
"The Lost Temple" → "the_lost_temple"
"Dragon Hunt #1" → "dragon_hunt_1"
"Campaign - 2" → "campaign_2"
"My-Campaign" → "my_campaign"
```

---

## Session Storage

### Metadata (GameState)
```python
state["metadata"] = {
    "session_id": "temple_run_1",      # Derived ID, used for LangGraph
    "session_name": "Temple Run #1",   # User-provided name
    "turn": 0,
    "started_at": "2025-12-16T09:01:00"
}
```

### Database (sessions table)
```sql
INSERT INTO sessions 
(session_id, title, created_at, last_played, turn_count, status)
VALUES 
("temple_run_1", "Temple Run #1", ..., ..., 0, "active")
```

Note: We reuse the `title` column to store the user-provided session name. No DB schema changes required.

### LangGraph Checkpoint
```python
config = {"configurable": {"thread_id": "temple_run_1"}}
```

LangGraph uses the derived `session_id` as thread ID for checkpointing. This remains unchanged.

---

## Validation Rules

**Session names must:**
- Be 1-50 characters
- Contain only: letters, numbers, spaces, hyphens, underscores
- Not be empty or whitespace-only
- Be unique (no duplicate session names)

**Examples:**
- ✅ "Temple Run #1"
- ✅ "Dragon Hunt"
- ✅ "Campaign-2"
- ✅ "My Campaign 3"
- ❌ "" (empty)
- ❌ "Campaign @ Night" (invalid character @)
- ❌ "A" × 51 (too long)

---

## User Experience

### CLI Experience
```
🎲 AI DUNGEON MASTER
════════════════════════════════════════════════

📚 Saved Sessions:

  1. Temple Run #1
     Turn 5 | Created: 2025-12-16 | Last: 2025-12-16
     ID: temple_run_1

  2. Dragon Hunt
     Turn 3 | Created: 2025-12-15 | Last: 2025-12-15
     ID: dragon_hunt

  N. Start New Game
  Q. Quit

Select option (1-2, N, Q): N

📝 Enter a name for this session (e.g. 'Temple Run #1'): Necromancer's Tower
Session created: necromancers_tower

🎲 Initializing game world...
```

### Web Experience
```
# Welcome to AI Dungeon Master

Initializing game system...

[Session Selection]
Would you like to continue a saved game or start new?

- Temple Run #1 (Turn 5)
- Dragon Hunt (Turn 3)
- Start New Game

[User clicks "Start New Game"]

📝 Name your session (e.g. 'Temple Run #1'):
[User types: Necromancer's Tower]

[Creates new adventure...]
```

---

## Implementation Notes

1. **No Breaking Changes:** Existing sessions can still be loaded using their old ID format if stored
2. **Backward Compatible:** The system validates and accepts both old timestamp IDs and new user-provided IDs
3. **No DB Migration:** Reuses existing `title` column, no schema changes required
4. **LangGraph Compatible:** Session IDs remain valid as thread IDs
5. **Accessible UI:** Both CLI and web interfaces ask for user input

---

## Files Modified

| File | Changes |
|------|--------|
| `main.py` | Added `prompt_for_session_name()`, updated `initialize_game_state()`, `select_or_create_session()`, `run_game_loop()` |
| `chainlit_app.py` | Added `derive_session_id_from_name()`, updated `initialize_game_state()`, `start_new_game()`, `load_existing_game()` |

---

## Testing Checklist

- [ ] **CLI - New Session:** User creates "Temple Run #1" → session_id = "temple_run_1"
- [ ] **CLI - Load Session:** User loads existing session by number
- [ ] **CLI - Duplicate Name:** User tries to create session with existing name → error shown
- [ ] **CLI - Invalid Name:** User enters name with special characters → validation error
- [ ] **Web - New Session:** User enters session name via prompt
- [ ] **Web - Session Loaded:** Previous session loads and displays user name
- [ ] **DB:** Session metadata saved with user name in `title` column
- [ ] **Persistence:** Close and reopen game → session loads with correct name

---

## Future Enhancements

1. **Session Renaming:** Allow users to rename existing sessions
2. **Session Archiving:** Archive old sessions without deleting
3. **Session Export:** Export session data to JSON/CSV
4. **Session Sharing:** Share session IDs to collaborate
5. **Session Backup:** Automatic backup of session state

---

**Commit:** `144fc8b5a5c8f0d1b4c35a131b4790d40986e574` (chainlit)
**Commit:** `cf37004b0692aa67d4871c5a14feada35534f4cf` (main.py)

Enjoy your new user-friendly session management! 🎭
