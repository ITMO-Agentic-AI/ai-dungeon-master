# Changelog - AI Dungeon Master

## [Latest] - 2025-12-16

### 🔧 Fixes

#### Fixed: AsyncClient.chat() timeout parameter error
- **Issue:** `AsyncClient.chat() got an unexpected keyword argument 'timeout'`
- **Root Cause:** Passed unsupported `timeout` parameter to `llm.ainvoke()`
- **Solution:** Removed timeout from runtime call; LangChain handles it at client initialization
- **File:** `src/services/structured_output.py`
- **Commit:** `6d4342430710d4babd8808bd1c744b73d260f323`
- **Status:** ✅ RESOLVED

#### Fixed: Connection error handling
- **Issue:** Generic error messages on LLM connection failures
- **Solution:** Added detailed error diagnostics and exponential backoff retry logic
- **File:** `src/services/structured_output.py`
- **Features:**
  - Exponential backoff (1s, 2s, 4s between retries)
  - Error classification (Authentication, Network, Rate Limit, Timeout)
  - Detailed diagnostics output
  - Helpful troubleshooting guidance
- **Commit:** `66f30c98ddc92e552684b553ef795878d9bfb8dc`
- **Status:** ✅ RESOLVED

### ✨ New Features

#### Connection Test Script
- **File:** `test_connection.py`
- **Purpose:** Automated diagnostic tool for API/Ollama connectivity
- **Tests:**
  - Environment variables validation
  - DNS/Network connectivity
  - LangChain integration
  - Structured output handling
- **Usage:** `python test_connection.py`
- **Commit:** `c73203e71571054875fa63fda590713d1d4595c9`
- **Status:** ✅ NEW

### 📚 Documentation

#### Added: Troubleshooting Guide
- **File:** `TROUBLESHOOTING_CONNECTION_ERROR.md`
- **Content:**
  - Root cause analysis
  - Step-by-step fixes
  - Common solutions
  - Debug mode instructions
  - Verification checklist
- **Commit:** `60968b597d1feed804bfe801269a6110d27cc233`
- **Status:** ✅ NEW

#### Added: Timeout Parameter Fix Guide
- **File:** `FIX_TIMEOUT_PARAMETER_ERROR.md`
- **Content:**
  - Detailed explanation of the timeout issue
  - Why the fix works
  - Proper timeout configuration patterns
  - Ollama-specific guidance
- **Commit:** `a59acb20449c57836c1f97623a7e7c74422e525b`
- **Status:** ✅ NEW

#### Added: Session Naming Refactor Documentation
- **File:** `SESSION_NAMING_REFACTOR.md`
- **Content:**
  - User-friendly session naming system
  - Implementation details
  - CLI and web interface updates
  - Testing guidelines
- **Commit:** `5f98e5ca2a7b64358961cfddd1037378584750d1`
- **Status:** ✅ NEW

### 🔄 Updated

#### Session Management
- **Files Modified:**
  - `main.py` - Added session naming prompt
  - `chainlit_app.py` - Added session naming dialog
- **Features:**
  - User-provided session names
  - Automatic ID derivation
  - Duplicate detection
  - Backward compatibility
- **Commit:** `cf37004b0692aa67d4871c5a14feada35534f4cf` (main.py)
- **Commit:** `144fc8b5a5c8f0d1b4c35a131b4790d40986e574` (chainlit_app.py)
- **Status:** ✅ COMPLETE

---

## System Information

### Architecture
- **LLM Backend:** Ollama (Local)
- **Model:** `gpt-oss:120b-cloud` (default)
- **Web Framework:** Chainlit
- **CLI Framework:** Standard Python asyncio
- **Orchestration:** LangGraph

### Key Services
- **Structured Output:** `src/services/structured_output.py` - JSON response parsing
- **Model Service:** `src/services/model_service.py` - LLM client management
- **Session Service:** `src/services/session_service.py` - Game session persistence
- **Orchestrator:** `src/services/orchestrator_service.py` - Multi-agent coordination

---

## Getting Started

### Prerequisites
1. Ollama installed and running: `ollama serve`
2. Python 3.8+
3. Dependencies: `poetry install`

### Quick Start

**CLI Mode:**
```bash
python main.py
```

**Web Mode:**
```bash
chainlit run chainlit_app.py
```

**Test Connection:**
```bash
python test_connection.py
```

### Troubleshooting

See documentation:
- `TROUBLESHOOTING_CONNECTION_ERROR.md` - General connection issues
- `FIX_TIMEOUT_PARAMETER_ERROR.md` - Timeout-specific issues
- `SESSION_NAMING_REFACTOR.md` - Session management

---

## Version History

### Current Version
- **Release Date:** 2025-12-16
- **Status:** Beta (actively fixing issues)
- **Last Updated:** 2025-12-16 09:25 MSK

---

## Support

For issues:
1. Run `python test_connection.py`
2. Check relevant documentation
3. Enable debug mode for detailed logs
4. Report with full error traceback

---

**Repository:** [ITMO-Agentic-AI/ai-dungeon-master](https://github.com/ITMO-Agentic-AI/ai-dungeon-master)  
**Last Updated:** 2025-12-16
