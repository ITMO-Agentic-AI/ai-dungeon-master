"""Agent Context Hub - Central communication bus for agent coordination."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of messages that can be passed between agents."""

    NARRATIVE_UPDATE = "narrative_update"
    WORLD_CHANGE = "world_change"
    CHARACTER_ACTION = "character_action"
    RULE_VIOLATION = "rule_violation"
    LORE_QUERY = "lore_query"
    LORE_RESPONSE = "lore_response"
    DIRECTOR_DECISION = "director_decision"
    JUDGE_VERDICT = "judge_verdict"


@dataclass
class AgentMessage:
    """Structured message passed between agents."""

    sender: str  # Agent name
    message_type: MessageType
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    requires_response: bool = False
    target_agents: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert message to dictionary."""
        return {
            "sender": self.sender,
            "type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "requires_response": self.requires_response,
            "targets": self.target_agents,
        }


class AgentContextHub:
    """Central communication hub for agent coordination."""

    def __init__(self, max_history: int = 50):
        """Initialize the context hub.

        Args:
            max_history: Maximum number of messages to keep in history
        """
        self.message_queue: List[AgentMessage] = []
        self.agent_memory: Dict[str, List[AgentMessage]] = {}
        self.max_history = max_history
        logger.debug("AgentContextHub initialized")

    def broadcast(self, message: AgentMessage) -> None:
        """Send message to communication hub.

        Args:
            message: The message to broadcast
        """
        self.message_queue.append(message)

        # Store in agent memory
        if message.sender not in self.agent_memory:
            self.agent_memory[message.sender] = []
        self.agent_memory[message.sender].append(message)

        # Trim history
        if len(self.message_queue) > self.max_history:
            self.message_queue.pop(0)

        logger.debug(
            f"Message broadcast from {message.sender} ({message.message_type.value})"
        )

    def get_context_for_agent(self, agent_name: str, limit: int = 10) -> List[Dict]:
        """Get relevant context for specific agent.

        Args:
            agent_name: Name of the agent requesting context
            limit: Maximum number of recent messages to return

        Returns:
            List of recent messages as dictionaries
        """
        recent = self.message_queue[-limit:]
        return [msg.to_dict() for msg in recent]

    def get_lore_context(self) -> Dict:
        """Get lore-related messages for context.

        Returns:
            Dictionary containing lore updates and recent changes
        """
        lore_msgs = [
            msg
            for msg in self.message_queue
            if msg.message_type
            in [
                MessageType.LORE_RESPONSE,
                MessageType.WORLD_CHANGE,
                MessageType.NARRATIVE_UPDATE,
            ]
        ]
        return {
            "lore_updates": [msg.to_dict() for msg in lore_msgs[-5:]],
            "recent_changes": self._extract_changes(lore_msgs),
        }

    def get_latest_narrative_context(self) -> Optional[Dict]:
        """Get the latest narrative update from Story Architect.

        Returns:
            Latest narrative message content or None
        """
        for msg in reversed(self.message_queue):
            if msg.message_type == MessageType.NARRATIVE_UPDATE:
                return msg.content
        return None

    def get_world_state_updates(self, limit: int = 5) -> List[Dict]:
        """Get recent world state updates.

        Args:
            limit: Maximum number of updates to return

        Returns:
            List of world change messages
        """
        world_msgs = [
            msg
            for msg in self.message_queue
            if msg.message_type == MessageType.WORLD_CHANGE
        ]
        return [msg.to_dict() for msg in world_msgs[-limit:]]

    def _extract_changes(self, messages: List[AgentMessage]) -> List[str]:
        """Extract key changes from messages.

        Args:
            messages: List of messages to extract from

        Returns:
            List of change descriptions
        """
        changes = []
        for msg in messages:
            if "description" in msg.content:
                changes.append(msg.content["description"])
            elif "title" in msg.content:
                changes.append(f"Story: {msg.content['title']}")
        return changes

    def clear_history(self) -> None:
        """Clear all message history."""
        self.message_queue.clear()
        self.agent_memory.clear()
        logger.debug("AgentContextHub history cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about hub usage.

        Returns:
            Dictionary with hub statistics
        """
        message_counts = {}
        for agent_name, messages in self.agent_memory.items():
            message_counts[agent_name] = len(messages)

        type_counts = {}
        for msg in self.message_queue:
            msg_type = msg.message_type.value
            type_counts[msg_type] = type_counts.get(msg_type, 0) + 1

        return {
            "total_messages": len(self.message_queue),
            "messages_by_agent": message_counts,
            "messages_by_type": type_counts,
            "active_agents": len(self.agent_memory),
        }
