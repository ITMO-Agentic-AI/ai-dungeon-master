"""Knowledge Graph Service - Maintains semantic relationships between world entities."""

from typing import Set, Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeLink:
    """Represents a relationship between two entities."""

    source: str  # Entity ID
    relation: str  # "located_in", "ally_of", "possesses", etc.
    target: str  # Target entity ID
    confidence: float = 1.0
    source_agent: str = ""


class KnowledgeGraphService:
    """Maintains semantic relationships between world entities."""

    def __init__(self):
        """Initialize the knowledge graph."""
        self.links: List[KnowledgeLink] = []
        self.entities: Dict[str, Dict] = {}  # entity_id -> metadata
        logger.debug("KnowledgeGraphService initialized")

    def add_entity(
        self, entity_id: str, entity_type: str, data: Dict
    ) -> None:
        """Register an entity (location, NPC, item, faction).

        Args:
            entity_id: Unique identifier for the entity
            entity_type: Type of entity (location, npc, item, faction, etc.)
            data: Entity metadata
        """
        self.entities[entity_id] = {
            "type": entity_type,
            "data": data,
            "discovered_by": [],
            "modified_by": [],
        }
        logger.debug(f"Entity added: {entity_id} ({entity_type})")

    def add_relation(
        self,
        source: str,
        relation: str,
        target: str,
        confidence: float = 1.0,
        source_agent: str = "",
    ) -> None:
        """Add relationship between entities.

        Args:
            source: Source entity ID
            relation: Type of relationship
            target: Target entity ID
            confidence: Confidence score (0-1)
            source_agent: Name of agent creating this link
        """
        link = KnowledgeLink(
            source, relation, target, confidence, source_agent
        )
        self.links.append(link)
        logger.debug(f"Relation added: {source} --{relation}--> {target}")

    def get_connected(
        self, entity_id: str, relation: Optional[str] = None
    ) -> List[str]:
        """Find all entities connected to given entity.

        Args:
            entity_id: The entity to find connections for
            relation: Optional filter by relation type

        Returns:
            List of connected entity IDs
        """
        connected = []
        for link in self.links:
            if link.source == entity_id:
                if relation is None or link.relation == relation:
                    connected.append(link.target)
            elif link.target == entity_id and relation is None:
                connected.append(link.source)
        return connected

    def get_entity_context(self, entity_id: str) -> Dict:
        """Get full context around an entity.

        Args:
            entity_id: The entity to get context for

        Returns:
            Dictionary with entity and its connections
        """
        if entity_id not in self.entities:
            return {}

        entity = self.entities[entity_id]

        # Find all connections
        connections = {}
        for link in self.links:
            if link.source == entity_id:
                rel = link.relation
                if rel not in connections:
                    connections[rel] = []
                connections[rel].append(link.target)

        return {
            "entity": entity,
            "connections": connections,
            "related_entities": [
                self.entities.get(eid, {})
                for eid in self.get_connected(entity_id)
            ],
        }

    def find_path(
        self, start: str, end: str, max_depth: int = 3
    ) -> List[str]:
        """Find path between two entities (BFS).

        Args:
            start: Starting entity ID
            end: Target entity ID
            max_depth: Maximum search depth

        Returns:
            List of entity IDs forming a path, or empty list if no path found
        """
        queue = deque([(start, [start])])
        visited = {start}
        depth = 0

        while queue and depth < max_depth:
            current, path = queue.popleft()

            if current == end:
                return path

            for neighbor in self.get_connected(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

            depth += 1

        return []

    def generate_consistency_report(self) -> Dict:
        """Check for inconsistencies in the graph.

        Returns:
            Dictionary with consistency analysis
        """
        issues = []

        # Check for orphaned entities
        referenced = set()
        for link in self.links:
            referenced.add(link.source)
            referenced.add(link.target)

        orphaned = set(self.entities.keys()) - referenced
        if orphaned:
            issues.append(f"Orphaned entities: {orphaned}")

        # Check for circular contradictions
        for link in self.links:
            reverse_links = [
                l
                for l in self.links
                if l.source == link.target
                and l.target == link.source
                and "not_" in l.relation
            ]
            if reverse_links:
                issues.append(
                    f"Contradiction: {link.source} {link.relation} "
                    f"{link.target}, but also {reverse_links[0].source} "
                    f"{reverse_links[0].relation} {reverse_links[0].target}"
                )

        consistency_score = max(
            0, 1.0 - len(issues) / max(1, len(self.links))
        )

        return {
            "total_entities": len(self.entities),
            "total_relations": len(self.links),
            "orphaned_count": len(orphaned),
            "issues": issues,
            "consistency_score": consistency_score,
        }

    def get_entities_by_type(self, entity_type: str) -> List[str]:
        """Get all entities of a specific type.

        Args:
            entity_type: The type to filter by

        Returns:
            List of entity IDs of that type
        """
        return [
            eid
            for eid, data in self.entities.items()
            if data.get("type") == entity_type
        ]

    def get_entity_summary(self) -> Dict[str, int]:
        """Get summary of entities by type.

        Returns:
            Dictionary with entity type counts
        """
        summary = {}
        for entity in self.entities.values():
            entity_type = entity.get("type", "unknown")
            summary[entity_type] = summary.get(entity_type, 0) + 1
        return summary

    def export_as_dict(self) -> Dict:
        """Export graph as dictionary for serialization.

        Returns:
            Dictionary representation of the graph
        """
        return {
            "entities": self.entities,
            "links": [
                {
                    "source": link.source,
                    "relation": link.relation,
                    "target": link.target,
                    "confidence": link.confidence,
                    "source_agent": link.source_agent,
                }
                for link in self.links
            ],
        }

    def import_from_dict(self, data: Dict) -> None:
        """Import graph from dictionary.

        Args:
            data: Dictionary representation of the graph
        """
        self.entities = data.get("entities", {})
        self.links = [
            KnowledgeLink(
                link["source"],
                link["relation"],
                link["target"],
                link.get("confidence", 1.0),
                link.get("source_agent", ""),
            )
            for link in data.get("links", [])
        ]
        logger.debug(f"Graph imported: {len(self.entities)} entities, {len(self.links)} links")
