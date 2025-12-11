# 💡 Action Suggestions System

## Overview

The DM now **explicitly returns action suggestions** in the GameState, rather than embedding them in narrative text and hoping the client extracts them.

This is a much cleaner and more reliable approach:

**Before:**
```
Narration: "[Vivid story text with hidden prompts buried in it...]"
Client tries to parse and extract suggestions from narrative
❌ Fragile, unreliable, error-prone
```

**After:**
```
Narration: "[Vivid story text]"
Action Suggestions: ["Attack the goblin", "Search the room", "Talk to NPC"]
✅ Clean, explicit, reliable
```

---

## How It Works

### 1. DM System Prompt (Updated)

The DungeonMaster's `narrate_outcome()` now requests explicit JSON output:

```python
AFTER the narrative (on a new line), you MUST output a JSON block with action suggestions:

```json
{
  "action_suggestions": [
    "Suggestion 1 - A specific action the player could take next",
    "Suggestion 2 - Another viable action",
    "Suggestion 3 - A third option"
  ]
}
```
```

### 2. Parsing & Extraction

The DM extracts narrative and suggestions using `_extract_narrative_and_suggestions()`:

```python
def _extract_narrative_and_suggestions(self, content: str) -> tuple[str, list[str]]:
    # Finds the JSON block in the response
    # Extracts action_suggestions array
    # Returns (narrative_text, suggestions_list)
```

**Fallback:** If JSON parsing fails, returns default suggestions:
```python
default_suggestions = ["Look around", "Wait", "Ask for clarification"]
```

### 3. Return Value

Both `narrate_initial()` and `narrate_outcome()` return:

```python
return {
    "messages": [AIMessage(content=narrative_text)],
    "action_suggestions": suggestions  # e.g., ["Attack", "Search", "Talk"]
}
```

### 4. Display in Main Loop

The main game loop displays suggestions before asking for player input:

```python
suggestions = state.get("action_suggestions", [])
if suggestions and len(suggestions) > 0:
    print("\n💡 What might you do?")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"   {i}. {suggestion}")
    print()

print("", end="")
description = input("> ").strip()
```

**Output:**
```
💡 What might you do?
   1. Attack the goblin
   2. Search the desk
   3. Flee through the window

> [player input]
```

---

## Changes Made

### 1. `src/core/types.py`

Added to GameState:
```python
action_suggestions: List[str]  # DM returns 2-3 suggested actions
```

### 2. `src/agents/dungeon_master/graph.py`

**Updated:**
- `narrate_initial()` - Returns suggestions for opening narration
- `narrate_outcome()` - Returns suggestions after each turn

**New:**
- `_extract_narrative_and_suggestions()` - Parses JSON from LLM response

**System Prompt:** Now requests explicit JSON with action_suggestions

### 3. `main.py`

**Updated:**
- `initialize_game_state()` - Adds `action_suggestions: []`
- `validate_game_state()` - Validates `action_suggestions` field
- `get_user_action()` - Displays suggestions from state

**Removed:**
- `extract_action_suggestions()` function (no longer needed)
- All narrative parsing logic

---

## Expected Gameplay Flow

```
🎲 AI DUNGEON MASTER
🎲 Initializing game world...

✅ World Created!
📖 Campaign: The Lost Temple of Azurath
📝 Adventurers seek an ancient, forgotten shrine.
👥 Your Characters:
  • Theron - Human Rogue

📜 DUNGEON MASTER
================================================== 
The Rusty Dragon tavern reeks of spiced ale and old wood.
Sunlight pierces the grimy windows. You sit at a corner table,
a weathered map before you. A hooded figure approaches...

💡 What might you do?
   1. Greet the figure and ask their business
   2. Examine the map more carefully
   3. Reach for your dagger cautiously

> greet the figure

⚙️  Resolving action...

📜 DUNGEON MASTER
==================================================
"You there," the figure says, pulling back their hood to reveal...

💡 What might you do?
   1. Ask about the temple's location
   2. Notice something suspicious about them
   3. Stand up to face them directly

> [player input]
```

---

## Advantages of This Approach

✅ **Explicit:** DM explicitly generates suggestions in JSON
✅ **Reliable:** No fragile text parsing or regex
✅ **Structured:** Clear, predictable data format
✅ **Fallback:** Default suggestions if parsing fails
✅ **Clean:** Narrative and suggestions are separate concerns
✅ **Scalable:** Easy to extend with more metadata later

---

## Testing

```bash
# Pull latest changes
git pull origin main

# Run the game
python main.py

# Watch for:
# 1. Opening narration displays
# 2. 💡 What might you do? prompt appears
# 3. 2-3 numbered suggestions show
# 4. Player can use suggestions or type own action
# 5. After each turn, new suggestions appear
```

---

## Future Enhancements

Possible improvements:

1. **Difficulty-Based Suggestions**
   ```python
   {
     "action_suggestions": [...],
     "difficulty_ratings": ["Easy", "Medium", "Hard"]
   }
   ```

2. **Consequence Preview**
   ```python
   {
     "action_suggestions": [...],
     "likely_outcomes": ["Combat", "Negotiation", "Discovery"]
   }
   ```

3. **Contextual Metadata**
   ```python
   {
     "action_suggestions": [...],
     "npcs_affected": [["NPC1"], ["NPC2"], []],
     "mechanics_triggered": [["Attack Roll"], [], ["Investigation Check"]]
   }
   ```

---

## Files Modified

| File | Change |
|------|--------|
| `src/core/types.py` | Added `action_suggestions: List[str]` to GameState |
| `src/agents/dungeon_master/graph.py` | Updated narrate methods to return suggestions in JSON |
| `main.py` | Simplified to use action_suggestions from state |

---

**Commit:** `fa1966c5ed27b7940936798703568e7bbb866977`

Enjoy! 🎭
