# AI Dungeon Master

A multi-agent AI system for D&D game mastering using LangGraph and LangChain.

## Architecture

### Single Shared State
All agents operate on a unified `GameState` that includes:
- Narrative state (story arc, scenes, beats)
- World state (locations, time, weather, quests)
- Player data (characters, stats, inventory)
- Combat state (initiative, turns, rounds)
- Rules context (active rules, violations)
- Emergence metrics (pacing, coherence, agency)

### 8 Specialized Agents

1. **Story Architect** - Plans narrative structure and story beats
2. **Dungeon Master** - Narrates scenes and guides gameplay
3. **Player Proxy** - Simulates autonomous player decisions
4. **World Engine** - Manages environment and world state
5. **Action Resolver** - Processes game actions and mechanics
6. **Director** - Coordinates agents and balances narrative
7. **Lore Builder** - Generates world lore and history
8. **Rule Judge** - Validates actions against D&D rules

## Quick Start

### 1. Setup Environment

```bash
# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Setup project
make dev
```

This will:
- Create `.env` from `.env.example`
- Install all dependencies with Poetry

### 2. Configure Your Model

Edit `.env` file with your settings:

**Option A: Use OpenAI**
```env
CUSTOM_MODEL_ENABLED=false
OPENAI_API_KEY=your_key_here
MODEL_NAME=gpt-4-turbo-preview
```

**Option B: Use Custom Model Server**
```env
CUSTOM_MODEL_ENABLED=true
CUSTOM_MODEL_BASE_URL=http://your-server:8000/v1
CUSTOM_MODEL_API_KEY=your_api_key
CUSTOM_MODEL_NAME=your-model-name
```

### 3. Run the Application

**Method 1: Test Individual Agents (Recommended for Development)**
```bash
make dev-langgraph
```
Access agents at:
- http://localhost:8123/story_architect
- http://localhost:8123/dungeon_master
- http://localhost:8123/player_proxy
- http://localhost:8123/world_engine
- http://localhost:8123/action_resolver
- http://localhost:8123/director
- http://localhost:8123/lore_builder
- http://localhost:8123/rule_judge

**Method 2: Run Full Game Orchestrator**
```bash
make dev-game
```
This runs all agents in a coordinated game loop.

**Method 3: Using Docker**
```bash
# Build and run
make docker-build
make docker-run

# Or use docker-compose
make docker-compose-up
```

## Development Commands

```bash
make help              # Show all available commands
make install           # Install dependencies
make format            # Format code with ruff
make lint              # Lint code
make test              # Run tests
make clean             # Clean cache files
```

## Project Structure

```
src/
├── core/               # Shared types, config, constants
├── agents/             # 8 agent implementations
│   ├── base/          # Abstract base agent class
│   ├── story_architect/
│   ├── dungeon_master/
│   ├── player_proxy/
│   ├── world_engine/
│   ├── action_resolver/
│   ├── director/
│   ├── lore_builder/
│   └── rule_judge/
├── services/           # Business logic services
├── tools/              # LangChain tools (D&D API, dice, data)
└── data/               # JSON storage and repositories
```

## Custom Model Integration

The system supports any OpenAI-compatible API endpoint. Set these in `.env`:

```env
CUSTOM_MODEL_ENABLED=true
CUSTOM_MODEL_BASE_URL=http://localhost:8000/v1
CUSTOM_MODEL_API_KEY=your-key
CUSTOM_MODEL_NAME=your-model
```

Compatible with:
- vLLM
- LM Studio
- Ollama (with OpenAI compatibility layer)
- Text Generation WebUI
- Any OpenAI-compatible server

## Tools Available

- **D&D 5e API**: Spell, monster, equipment, class, race info
- **Game Mechanics**: Dice rolling, initiative, attacks, saving throws
- **Data Access**: Player info, inventory management, HP tracking

## Docker Deployment

### Build and Run

```bash
# Build image
docker build -t ai-dungeon-master:latest .

# Run container
docker run -p 8000:8000 --env-file .env ai-dungeon-master:latest
```

### Using Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Services:
- `app`: Main game orchestrator (port 8000)
- `langgraph-dev`: LangGraph dev server (port 8123)

## Development Workflow

1. **Develop Agents Individually**
   ```bash
   make dev-langgraph
   ```
   Test each agent in isolation using LangSmith UI

2. **Implement Agent Logic**
   Edit `src/agents/{agent_name}/graph.py`

3. **Test Full System**
   ```bash
   make dev-game
   ```

4. **Format and Lint**
   ```bash
   make format
   make lint
   ```

## Next Steps

- Implement agent logic for each of the 8 agents
- Add FastAPI integration (Phase 2)
- Migrate to Chroma vector store
- Connect to frontend

## Troubleshooting

**Poetry not found?**
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

**Dependencies not installing?**
```bash
poetry lock
poetry install
```

**Environment variables not loading?**
Ensure `.env` file exists and is properly formatted.

## License

MIT
