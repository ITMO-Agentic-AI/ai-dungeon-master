.PHONY: install dev dev-langgraph dev-game test format lint clean docker-build docker-run help

help:
	@echo "Available commands:"
	@echo "  make install              - Install dependencies with Poetry"
	@echo "  make dev                  - Run development environment setup"
	@echo "  make dev-langgraph-AGENT  - Run specific agent (e.g., dev-langgraph-story_architect)"
	@echo "  make dev-game             - Run the full game orchestrator"
	@echo "  make test                 - Run tests"
	@echo "  make format               - Format code with ruff"
	@echo "  make lint                 - Lint code with ruff"
	@echo "  make clean                - Clean cache and temporary files"
	@echo "  make docker-build         - Build Docker image"
	@echo "  make docker-run           - Run Docker container"
	@echo ""
	@echo "Available agents for dev-langgraph:"
	@echo "  story_architect, dungeon_master, player_proxy, world_engine"
	@echo "  action_resolver, director, lore_builder, rule_judge"

install:
	poetry install

dev:
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file. Please update with your API keys."; fi
	poetry install

dev-langgraph-story_architect:
	@echo "Starting Story Architect agent..."
	cd src/agents/story_architect && poetry run langgraph dev --port 8123

dev-langgraph-dungeon_master:
	@echo "Starting Dungeon Master agent..."
	cd src/agents/dungeon_master && poetry run langgraph dev --port 8123

dev-langgraph-player_proxy:
	@echo "Starting Player Proxy agent..."
	cd src/agents/player_proxy && poetry run langgraph dev --port 8123

dev-langgraph-world_engine:
	@echo "Starting World Engine agent..."
	cd src/agents/world_engine && poetry run langgraph dev --port 8123

dev-langgraph-action_resolver:
	@echo "Starting Action Resolver agent..."
	cd src/agents/action_resolver && poetry run langgraph dev --port 8123

dev-langgraph-director:
	@echo "Starting Director agent..."
	cd src/agents/director && poetry run langgraph dev --port 8123

dev-langgraph-lore_builder:
	@echo "Starting Lore Builder agent..."
	cd src/agents/lore_builder && poetry run langgraph dev --port 8123

dev-langgraph-rule_judge:
	@echo "Starting Rule Judge agent..."
	cd src/agents/rule_judge && poetry run langgraph dev --port 8123

dev-game:
	@echo "Starting full game orchestrator..."
	poetry run python main.py

test:
	poetry run pytest tests/ -v

format:
	poetry run ruff format src/ tests/

lint:
	poetry run ruff check src/ tests/
	poetry run mypy src/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

docker-build:
	docker build -t ai-dungeon-master:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env ai-dungeon-master:latest

docker-compose-up:
	docker-compose up -d

docker-compose-down:
	docker-compose down

act-env:
	poetry shell