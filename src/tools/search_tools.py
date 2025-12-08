from langchain.tools import tool


@tool
def search_rules(query: str) -> dict:
    """Search D&D rules database (not yet implemented)."""
    return {"query": query, "results": [], "message": "Rule search not yet implemented"}


@tool
def search_lore(query: str) -> dict:
    """Search campaign lore and history (not yet implemented)."""
    return {"query": query, "results": [], "message": "Lore search not yet implemented"}
