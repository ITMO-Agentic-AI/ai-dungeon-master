# 🤖 Model Configuration Guide

## Overview

AI Dungeon Master supports **two model backends**:

1. **Ollama** (Local LLM) - Default, free, runs locally
2. **Custom OpenAI-Compatible API** - Remote or on-premises endpoint

---

## Quick Start

### Option 1: Use Ollama (Recommended for Local Development)

```bash
# Step 1: Install Ollama
# https://ollama.ai

# Step 2: Start Ollama
ollama serve

# Step 3: Create .env file
cp .env.example .env

# Step 4: Set in .env
CUSTOM_MODEL_ENABLED=false
MODEL_NAME=qwen:7b
MODEL_TEMPERATURE=0.7

# Step 5: Run the game
python main.py
```

### Option 2: Use Custom OpenAI-Compatible Endpoint

```bash
# Step 1: Create .env file
cp .env.example .env

# Step 2: Set in .env
CUSTOM_MODEL_ENABLED=true
CUSTOM_MODEL_NAME=gpt-4o-mini
CUSTOM_MODEL_BASE_URL=https://api.openai.com/v1
CUSTOM_MODEL_API_KEY=sk-your-api-key-here

# Step 3: Run the game
python main.py
```

---

## Detailed Configuration

### Backend 1: Ollama (Local LLM)

#### What is Ollama?
Ollama is a lightweight framework for running large language models locally. No API keys, no internet required (after setup).

#### Installation

**macOS/Linux:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

**Windows:**
Download from [ollama.ai](https://ollama.ai)

#### Starting Ollama

```bash
# Start Ollama server (runs on localhost:11434)
ollama serve

# In another terminal, verify it's running
curl http://localhost:11434/api/tags
```

#### Available Models

**Popular models (pick one):**

| Model | Size | Memory | Speed | Quality |
|-------|------|--------|-------|----------|
| `qwen:7b` | 4.4GB | ~8GB | Fast | Good |
| `llama2:7b` | 3.8GB | ~8GB | Fast | Good |
| `neural-chat:7b` | 4.8GB | ~8GB | Fast | Good |
| `mistral:7b` | 4.1GB | ~8GB | Fast | Good |
| `qwen:14b` | 9.2GB | ~16GB | Medium | Better |
| `llama2:13b` | 7.4GB | ~16GB | Medium | Better |

#### Download a Model

```bash
# Download and use a model
ollama pull qwen:7b      # Small, fast
ollama pull llama2:7b    # Popular, good quality
ollama pull mistral:7b   # Fast, efficient

# List downloaded models
ollama list

# Test a model
ollama run qwen:7b "Hello, describe yourself"
```

#### Configuration

**.env file:**
```ini
CUSTOM_MODEL_ENABLED=false
MODEL_NAME=qwen:7b
MODEL_TEMPERATURE=0.7
```

**Temperature explained:**
- `0.0` - Deterministic, always same response
- `0.3-0.5` - Focused, consistent storytelling
- `0.7` - Balanced (recommended)
- `1.0+` - Creative, random

#### Troubleshooting Ollama

**Connection refused:**
```bash
# Make sure Ollama is running
ps aux | grep ollama

# Or restart it
kill $(pgrep -f "ollama")
ollama serve
```

**Model not found:**
```bash
# List available models
ollama list

# Pull a new model
ollama pull qwen:7b
```

**Out of memory:**
```bash
# Use a smaller model
ollama pull qwen:7b      # Instead of larger models

# Or free up RAM
# Close other applications
```

**Slow responses:**
```bash
# Use a smaller model for faster responses
ollama pull neural-chat:7b  # Fast
# vs
ollama pull llama2:13b      # Slower but better quality
```

---

### Backend 2: Custom OpenAI-Compatible API

#### Supported Services

1. **OpenAI** (Official)
   - Models: gpt-4, gpt-4o, gpt-4o-mini, gpt-3.5-turbo
   - URL: `https://api.openai.com/v1`
   - Get API key: https://platform.openai.com/api-keys

2. **Azure OpenAI**
   - Models: Same as OpenAI, but hosted on Azure
   - URL: `https://{resource-name}.openai.azure.com/v1`
   - Get API key: Azure Portal

3. **Anthropic Claude** (via API)
   - Models: claude-3-opus, claude-3-sonnet, etc.
   - URL: `https://api.anthropic.com/v1`
   - Get API key: https://console.anthropic.com

4. **Local vLLM** (Self-hosted)
   - Any model you want to host locally
   - URL: `http://localhost:8000/v1`
   - No API key needed (unless configured)

5. **Other OpenAI-Compatible APIs**
   - Together AI, Replicate, etc.
   - Check their documentation for URL and key

#### Configuration

**.env file:**
```ini
CUSTOM_MODEL_ENABLED=true
CUSTOM_MODEL_NAME=gpt-4o-mini
CUSTOM_MODEL_BASE_URL=https://api.openai.com/v1
CUSTOM_MODEL_API_KEY=sk-your-api-key-here
```

#### Example: OpenAI

**Get API Key:**
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key

**.env configuration:**
```ini
CUSTOM_MODEL_ENABLED=true
CUSTOM_MODEL_NAME=gpt-4o-mini
CUSTOM_MODEL_BASE_URL=https://api.openai.com/v1
CUSTOM_MODEL_API_KEY=sk-proj-abcdef123456...
```

#### Example: Azure OpenAI

**.env configuration:**
```ini
CUSTOM_MODEL_ENABLED=true
CUSTOM_MODEL_NAME=gpt-4
CUSTOM_MODEL_BASE_URL=https://your-resource.openai.azure.com/v1
CUSTOM_MODEL_API_KEY=your-azure-api-key
```

#### Example: Local vLLM

**Start vLLM:**
```bash
# Install vLLM
pip install vllm

# Start server (uses any HuggingFace model)
vllm serve mistralai/Mistral-7B-v0.1 --port 8000
```

**.env configuration:**
```ini
CUSTOM_MODEL_ENABLED=true
CUSTOM_MODEL_NAME=mistralai/Mistral-7B-v0.1
CUSTOM_MODEL_BASE_URL=http://localhost:8000/v1
CUSTOM_MODEL_API_KEY=  # Not needed for local vLLM
```

#### Cost Comparison

| Backend | Cost | Speed | Setup |
|---------|------|-------|-------|
| **Ollama** | Free | Variable | ~10 min |
| **OpenAI** | $0.15-$3/1M tokens | Fast | ~5 min |
| **Azure OpenAI** | Variable | Fast | ~20 min |
| **vLLM** | Free (host cost) | Depends on hardware | ~15 min |

---

## How Model Selection Works

### Configuration Priority

```
1. Check CUSTOM_MODEL_ENABLED flag
   ├─ If true:
   │  └─ Use ChatOpenAI with custom settings
   │     ├─ CUSTOM_MODEL_NAME
   │     ├─ CUSTOM_MODEL_BASE_URL
   │     └─ CUSTOM_MODEL_API_KEY
   └─ If false:
      └─ Use ChatOllama with default settings
         ├─ MODEL_NAME
         └─ MODEL_TEMPERATURE
```

### Settings File Structure

**File:** `src/core/config.py`
```python
class Settings(BaseSettings):
    # Ollama Settings
    model_name: str = "qwen3-32b"              # Default model
    model_temperature: float = 0.7              # Creativity level
    
    # Custom Model Settings
    custom_model_enabled: bool = False          # Enable/disable custom
    custom_model_name: str = "qwen3-32b"       # Model name
    custom_model_base_url: str = "http://..."  # API endpoint
    custom_model_api_key: str = ""             # API key
```

### Model Service Logic

**File:** `src/services/model_service.py`
```python
class ModelService:
    def get_model(self, model_name=None, temperature=None):
        if self.settings.custom_model_enabled:
            # Use OpenAI-compatible API
            return ChatOpenAI(
                model=self.settings.custom_model_name,
                api_key=self.settings.custom_model_api_key,
                base_url=self.settings.custom_model_base_url,
                temperature=temperature,
            )
        else:
            # Use Ollama (local)
            return ChatOllama(
                model=self.settings.model_name,
                temperature=temperature,
            )
```

---

## Switching Between Models

### From Ollama to OpenAI

**Current .env (Ollama):**
```ini
CUSTOM_MODEL_ENABLED=false
MODEL_NAME=qwen:7b
```

**New .env (OpenAI):**
```ini
CUSTOM_MODEL_ENABLED=true
CUSTOM_MODEL_NAME=gpt-4o-mini
CUSTOM_MODEL_BASE_URL=https://api.openai.com/v1
CUSTOM_MODEL_API_KEY=sk-your-key
```

**Restart the game:**
```bash
python main.py
```

### From OpenAI to Ollama

**Current .env (OpenAI):**
```ini
CUSTOM_MODEL_ENABLED=true
CUSTOM_MODEL_NAME=gpt-4o-mini
CUSTOM_MODEL_BASE_URL=https://api.openai.com/v1
CUSTOM_MODEL_API_KEY=sk-...
```

**New .env (Ollama):**
```ini
CUSTOM_MODEL_ENABLED=false
MODEL_NAME=qwen:7b
```

**Make sure Ollama is running:**
```bash
ollama serve

# In another terminal
python main.py
```

---

## Debugging Model Configuration

### Check Current Configuration

**Run test script:**
```bash
python test_connection.py
```

Output shows:
```
✅ OPENAI_API_KEY: sk-...***
✅ Model: gpt-4o-mini
✅ API Base: https://api.openai.com/v1
```

### Enable Debug Logging

```python
# Add to your script before main()
import logging
logging.basicConfig(level=logging.DEBUG)
```

Run with debug output:
```bash
DEBUG=1 python main.py
```

### Check Model Service Initialization

**Python REPL:**
```python
from src.services.model_service import model_service
from src.core.config import get_settings

# Check settings
settings = get_settings()
print(f"Custom model enabled: {settings.custom_model_enabled}")
print(f"Model name: {settings.model_name}")

# Get model
model = model_service.get_model()
print(f"Model type: {type(model).__name__}")
print(f"Model: {model.model_name if hasattr(model, 'model_name') else 'Unknown'}")
```

---

## Common Issues

### Issue: "Model not found" error

**For Ollama:**
```bash
# Check available models
ollama list

# Pull missing model
ollama pull qwen:7b
```

**For Custom API:**
```bash
# Verify model name in API documentation
# Common models: gpt-4o-mini, gpt-4, gpt-3.5-turbo
echo $CUSTOM_MODEL_NAME
```

### Issue: "Connection refused"

**For Ollama:**
```bash
# Restart Ollama
kill $(pgrep -f "ollama")
ollama serve
```

**For Custom API:**
```bash
# Check API endpoint
curl https://api.openai.com/v1/models -H "Authorization: Bearer $API_KEY"
```

### Issue: Very slow responses

**Solutions:**
1. Use a smaller model: `qwen:7b` instead of `llama2:13b`
2. Reduce context size in prompts
3. Switch to faster API: `gpt-3.5-turbo` instead of `gpt-4`
4. Add more RAM/GPU if using local model

---

## Best Practices

✅ **Do:**
- Keep `.env` file with secrets (don't commit)
- Test configuration with `test_connection.py`
- Document your model choice in README
- Monitor API usage if using paid service
- Use smaller models for development, larger for production

❌ **Don't:**
- Commit `.env` file to git
- Hardcode API keys in code
- Share your `.env` file publicly
- Leave Ollama using high-memory models 24/7
- Forget to restart service when changing .env

---

## Summary

| Aspect | Ollama | Custom API |
|--------|--------|------------|
| **Cost** | Free | Paid (unless self-hosted) |
| **Speed** | Variable | Fast (usually) |
| **Setup Time** | ~10 min | ~5 min |
| **Model Choice** | Limited | Extensive |
| **Internet Required** | No | Yes (unless vLLM) |
| **Best For** | Development | Production |

---

**Last Updated:** 2025-12-16  
**Status:** Complete  
**Configuration Fixed:** ✅
