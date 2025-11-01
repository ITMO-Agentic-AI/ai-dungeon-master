from langchain.tools import tool
from src.services.data_service import data_service


@tool
async def get_player_info(player_id: str) -> dict:
    player = await data_service.get_player(player_id)
    return player.model_dump() if player else {"error": "Player not found"}


@tool
async def update_player_hp(player_id: str, hp_change: int) -> dict:
    player = await data_service.get_player(player_id)
    if player:
        player.current_hp = max(0, min(player.current_hp + hp_change, player.max_hp))
        await data_service.save_player(player)
        return {
            "success": True,
            "player_id": player_id,
            "current_hp": player.current_hp,
            "max_hp": player.max_hp,
        }
    return {"success": False, "error": "Player not found"}


@tool
async def add_item_to_inventory(player_id: str, item: str) -> dict:
    player = await data_service.get_player(player_id)
    if player:
        player.inventory.append(item)
        await data_service.save_player(player)
        return {"success": True, "player_id": player_id, "inventory": player.inventory}
    return {"success": False, "error": "Player not found"}


@tool
async def remove_item_from_inventory(player_id: str, item: str) -> dict:
    player = await data_service.get_player(player_id)
    if player and item in player.inventory:
        player.inventory.remove(item)
        await data_service.save_player(player)
        return {"success": True, "player_id": player_id, "inventory": player.inventory}
    return {"success": False, "error": "Player not found or item not in inventory"}
