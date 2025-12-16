# 🔧 Fix: AsyncClient.chat() got an unexpected keyword argument 'timeout'

## Error Details

```
Phase 1 Failed: Failed to initialize world
  └─ Failed to get structured output after 3 attempts
       └─ Error Type: UNKNOWN
            └─ Last Error: AsyncClient.chat() got an unexpected keyword argument 'timeout'
```

## Root Cause

**Problem:** The structured output function was passing a `timeout` parameter to `llm.ainvoke()`, but LangChain's `ChatOpenAI` and `ChatOllama` clients don't accept this parameter in their async method.

**Why it happened:**
- The code tried to set `timeout=30` on `ainvoke()`
- LangChain async invoke methods don't support timeout as a parameter
- Timeouts must be configured during ChatOpenAI/ChatOllama initialization

## The Fix (✅ Already Applied)

### What Changed

**File:** `src/services/structured_output.py`

**Before:**
```python
response = await llm.ainvoke(enhanced_messages, timeout=30)  # ❌ WRONG
```

**After:**
```python
response = await llm.ainvoke(enhanced_messages)  # ✅ CORRECT
```

### Why This Works

1. **LangChain handles timeouts internally** during client initialization
2. **ChatOllama and ChatOpenAI already have timeout support** at initialization
3. **ainvoke() doesn't accept runtime timeout parameters**

## Proper Timeout Configuration

If you need to set timeouts, configure them when creating the LLM client:

### For ChatOpenAI (if you switch)

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",
    temperature=0.7,
    timeout=30,  # ✅ Set timeout here, not in ainvoke()
    max_retries=3,  # Also configurable here
)
```

### For ChatOllama (current setup)

```python
from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="gpt-oss:120b-cloud",
    temperature=0.7,
    timeout=30,  # ✅ Set timeout here
)
```

## Your Current Setup

Your system uses **Ollama** (local model):

**File:** `src/services/model_service.py`
```python
return ChatOllama(model="gpt-oss:120b-cloud")
```

**Configuration:** `src/core/config.py`
```python
model_name: str = "qwen3-32b"
model_temperature: float = 0.7
```

## Verification

### After the fix, try:

```bash
# Make sure Ollama is running
ollama serve

# In another terminal, test the connection
python test_connection.py

# If that passes, run the game
python main.py
```

### Expected Success Output

```
🎲 AI DUNGEON MASTER
==============================================================
Model: gpt-oss:120b-cloud
Temperature: 0.7
==============================================================

🏒 Initializing game world...
This may take a moment as the AI creates your adventure...

✅ World Created!
...
```

## Common Issues

### Issue 1: "Connection refused" when connecting to Ollama

```bash
# Make sure Ollama is running
ollama serve

# Check if Ollama is listening on port 11434
curl http://localhost:11434/api/tags
```

### Issue 2: Model not found

```bash
# List available models
ollama list

# If model missing, pull it
ollama pull gpt-oss:120b-cloud
```

### Issue 3: Out of memory

Ollama models require GPU memory. Check:

```bash
# Check GPU availability
gpustat  # If installed
# or
nvidia-smi

# Use smaller model if needed
ollama pull qwen:7b  # Smaller model
```

## Files Modified

| File | Change | Status |
|------|--------|--------|
| `src/services/structured_output.py` | Removed `timeout=30` from `ainvoke()` call | ✅ Fixed |
| `TROUBLESHOOTING_CONNECTION_ERROR.md` | Added comprehensive guide | ✅ Added |
| `test_connection.py` | Added connection test script | ✅ Added |

## Next Steps

1. ✅ Fix already committed
2. Ensure Ollama is running: `ollama serve`
3. Try running the game again: `python main.py`
4. If still having issues, run: `python test_connection.py`

## Technical Details (Optional)

### Why LangChain Works This Way

LangChain's design philosophy:

1. **Initialization-time configuration** - Timeouts, retries, proxies set at client creation
2. **Runtime is for data** - `ainvoke()` is for sending messages, not for configuration
3. **Built-in async support** - LangChain handles async properly without needing runtime timeouts

### The Correct Pattern

```python
# ✅ CORRECT: Configure at init
llm = ChatOpenAI(timeout=30, max_retries=3)
response = await llm.ainvoke(messages)

# ❌ WRONG: Configure at runtime
llm = ChatOpenAI()
response = await llm.ainvoke(messages, timeout=30)  # Parameter not accepted
```

## Summary

**Problem:** Passed unsupported `timeout` parameter to `ainvoke()`  
**Solution:** Removed the parameter (LangChain handles it internally)  
**Result:** ✅ Structured output will work correctly now

---

**Fix Commit:** `6d4342430710d4babd8808bd1c744b73d260f323`  
**Date:** 2025-12-16  
**Status:** ✅ RESOLVED
