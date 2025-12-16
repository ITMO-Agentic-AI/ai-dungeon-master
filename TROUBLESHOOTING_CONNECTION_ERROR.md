# 🔧 Troubleshooting: ValueError - Failed to get structured output

## Error Message
```
ValueError: Failed to get structured output after 3 attempts: All connection attempts failed
During task with name 'story_architect' and id '977eb108-a9dc-9e09-233d-3f1c050e1090'
```

## Root Cause Analysis

### Primary Issues

This error occurs when:
1. **Network connection fails** - Can't reach the LLM API endpoint
2. **API endpoint is unreachable** - DNS resolution or network timeout
3. **API credentials are invalid/expired** - Authentication failure
4. **Rate limiting is active** - Too many requests in short time
5. **LLM service is down** - Temporary outage or maintenance

### Where the Error Occurs

**File:** `src/services/structured_output.py`  
**Function:** `get_structured_output()`  
**Line:** The error is raised when all 3 retry attempts fail to establish a connection

```python
raise ValueError(
    f"Failed to get structured output after {max_retries} attempts: {str(e)}"
)
```

---

## Step-by-Step Fix

### 1. Check Environment Variables

```bash
# Verify these are set and correct:
echo $OPENAI_API_KEY          # Should not be empty
echo $OPENAI_API_BASE         # Optional, check if custom endpoint
echo $OPENAI_MODEL_NAME       # Should match available model
```

**Fix if missing:**
```bash
# Create/update .env file:
OPENAI_API_KEY=sk-xxxxxxxxxxxx
OPENAI_API_BASE=https://api.openai.com/v1  # or your custom endpoint
OPENAI_MODEL_NAME=gpt-4o-mini              # or gpt-4, etc.
```

### 2. Test API Connectivity

**Quick test script:**
```python
import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

api_key = os.getenv("OPENAI_API_KEY")
model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")

if not api_key:
    print("❌ OPENAI_API_KEY not set")
    exit(1)

print(f"Testing connection to {model_name}...")

try:
    llm = ChatOpenAI(
        api_key=api_key,
        model=model_name,
        temperature=0.7,
        timeout=10,  # 10 second timeout
    )
    
    response = llm.invoke([HumanMessage(content="Say 'test successful'")])
    print(f"✅ Connection successful!")
    print(f"Response: {response.content}")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print(f"Error type: {type(e).__name__}")
```

**Run it:**
```bash
python test_connection.py
```

### 3. Check Network Configuration

**If using a proxy or custom endpoint:**

```python
import os
import requests

# Test DNS resolution
try:
    response = requests.get('https://api.openai.com', timeout=5)
    print("✅ DNS and network reachable")
except requests.exceptions.Timeout:
    print("❌ Connection timeout")
except requests.exceptions.ConnectionError:
    print("❌ Cannot reach API endpoint")
except Exception as e:
    print(f"❌ Error: {e}")
```

### 4. Update Connection Timeout

The default timeout might be too short. Edit `src/services/model_service.py`:

```python
# BEFORE:
llm = ChatOpenAI(
    model=settings.model_name,
    temperature=settings.model_temperature,
)

# AFTER (with longer timeout and retry config):
llm = ChatOpenAI(
    model=settings.model_name,
    temperature=settings.model_temperature,
    timeout=30,  # Increased from default (5s)
    max_retries=3,  # LangChain built-in retry
    api_key=settings.openai_api_key,
    # If using custom endpoint:
    # api_base=settings.openai_api_base,
)
```

### 5. Add Enhanced Error Handling

Update `src/services/structured_output.py` to provide better diagnostics:

```python
import json
import re
import os
from typing import TypeVar, Type
from pydantic import BaseModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


async def get_structured_output(
    llm: ChatOpenAI,
    messages: list[BaseMessage],
    output_model: Type[T],
    max_retries: int = 3,
) -> T:
    """
    Get structured output from LLM with robust JSON parsing and retry logic.
    
    Enhanced with better error diagnostics.
    """
    schema = output_model.model_json_schema()
    json_instruction = f"""

IMPORTANT: You MUST respond with valid JSON only. No other text before or after.
The JSON must match this schema:
{json.dumps(schema, indent=2)}

Example format:
{json.dumps(get_example_from_schema(output_model), indent=2)}
"""

    enhanced_messages = messages.copy()
    for i, msg in enumerate(enhanced_messages):
        if msg.type == "system":
            enhanced_messages[i].content += json_instruction
            break

    last_error = None
    for attempt in range(max_retries):
        try:
            # Add logging for debugging
            logger.debug(f"Attempt {attempt + 1}/{max_retries}")
            
            response = await llm.ainvoke(enhanced_messages, timeout=30)
            content = response.content.strip()

            # Try to extract JSON if wrapped in markdown code blocks
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
            if json_match:
                content = json_match.group(1)

            # Try to find JSON object in the response
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

            # Parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    enhanced_messages.append(response)
                    enhanced_messages.append(
                        BaseMessage(
                            content=f"Your response was not valid JSON. Error: {str(e)}. Please respond with ONLY valid JSON matching the schema.",
                            type="human",
                        )
                    )
                    continue
                last_error = f"JSON Parse Error: {str(e)}"
                continue

            # Validate and create Pydantic model
            return output_model(**data)

        except Exception as e:
            last_error = str(e)
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            
            # Diagnose connection errors specifically
            if isinstance(e, TimeoutError) or "timeout" in str(e).lower():
                logger.error("❌ Connection timeout - API endpoint not responding")
            elif "authentication" in str(e).lower() or "invalid" in str(e).lower():
                logger.error("❌ Authentication error - check OPENAI_API_KEY")
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                logger.error("❌ Network error - check internet connection")
            elif "rate" in str(e).lower():
                logger.error("❌ Rate limit hit - wait before retrying")
            
            if attempt < max_retries - 1:
                # Wait a bit before retry
                import asyncio
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue

    # Provide detailed error message
    error_details = {
        "model": os.getenv("OPENAI_MODEL_NAME", "unknown"),
        "api_key_set": bool(os.getenv("OPENAI_API_KEY")),
        "last_error": last_error,
        "max_retries_reached": max_retries,
    }
    
    raise ValueError(
        f"Failed to get structured output after {max_retries} attempts.\n"
        f"Last error: {last_error}\n"
        f"Diagnostics: {error_details}\n"
        f"\nTroubleshooting steps:\n"
        f"1. Check OPENAI_API_KEY is set correctly\n"
        f"2. Run: python test_connection.py (see guide)\n"
        f"3. Check internet connection\n"
        f"4. Verify API endpoint is accessible\n"
        f"5. Check for rate limiting or quota issues"
    )


def get_example_from_schema(model: Type[BaseModel]) -> dict:
    """Generate an example instance from a Pydantic model."""
    example = {}
    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation

        if annotation is str:
            example[field_name] = "example string"
        elif annotation is int:
            example[field_name] = 0
        elif annotation is float:
            example[field_name] = 0.0
        elif annotation is bool:
            example[field_name] = True
        elif hasattr(annotation, "__origin__"):
            if annotation.__origin__ is list:
                example[field_name] = ["item1", "item2"]
            elif annotation.__origin__ is dict:
                example[field_name] = {"key": "value"}
            else:
                example[field_name] = None
        else:
            example[field_name] = None

    return example
```

---

## Common Solutions

### Solution 1: API Key Not Set (Most Common)
```bash
# For Linux/Mac:
export OPENAI_API_KEY="sk-your-actual-api-key"

# For Windows (PowerShell):
$env:OPENAI_API_KEY="sk-your-actual-api-key"

# Or create .env file:
echo 'OPENAI_API_KEY=sk-your-actual-api-key' > .env
```

### Solution 2: Wrong Model Name
```bash
# Check available models (requires valid API key):
python -c "from langchain_openai import ChatOpenAI; print('Valid models: gpt-4, gpt-4o-mini, gpt-3.5-turbo')"

# Set in .env:
OPENAI_MODEL_NAME=gpt-4o-mini  # Free tier friendly
```

### Solution 3: Network/Firewall Issue
```bash
# Test connectivity:
curl -I https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# If behind proxy, set:
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
```

### Solution 4: Rate Limiting
```python
# Add exponential backoff (already implemented in updated code above)
# Default: 1s, 2s, 4s between retries
```

### Solution 5: Custom Endpoint Issues
```python
# If using custom endpoint, verify:
1. Endpoint URL is correct
2. API key is valid for that endpoint
3. Endpoint supports your model name
4. Endpoint is accessible from your network

# Set in .env:
OPENAI_API_BASE=https://your-endpoint.com/v1
```

---

## Verification Checklist

- [ ] `OPENAI_API_KEY` is set and not empty
- [ ] API key is valid (test with the connection script)
- [ ] Model name is correct (gpt-4o-mini, gpt-4, etc.)
- [ ] Internet connection is working
- [ ] Can reach api.openai.com (or custom endpoint)
- [ ] No firewall/proxy blocking the connection
- [ ] API quota is not exceeded
- [ ] API key has not expired
- [ ] No rate limiting active (check OpenAI dashboard)
- [ ] Using correct timeout values (30s recommended)

---

## Debug Mode

Enable verbose logging:

```python
# In your main script before running:
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('langchain')
logger.setLevel(logging.DEBUG)
```

---

## Report If Issue Persists

If still failing after all steps, provide:

1. Error message (full traceback)
2. Output of connection test script
3. `.env` file contents (without API key)
4. Python version (`python --version`)
5. LangChain version (`pip show langchain`)
6. OS and network setup

---

**Last Updated:** 2025-12-16  
**Issue:** ValueError - Failed to get structured output  
**Status:** Diagnostics Enhanced
