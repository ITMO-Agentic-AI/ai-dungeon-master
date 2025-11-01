from langchain.tools import tool
import httpx
from src.core.config import get_settings

settings = get_settings()


@tool
async def get_spell_info(spell_name: str) -> dict:
    async with httpx.AsyncClient() as client:
        spell_slug = spell_name.lower().replace(" ", "-")
        response = await client.get(f"{settings.dnd_api_base_url}/spells/{spell_slug}")
        if response.status_code == 200:
            return response.json()
        return {"error": f"Spell '{spell_name}' not found"}


@tool
async def get_monster_info(monster_name: str) -> dict:
    async with httpx.AsyncClient() as client:
        monster_slug = monster_name.lower().replace(" ", "-")
        response = await client.get(f"{settings.dnd_api_base_url}/monsters/{monster_slug}")
        if response.status_code == 200:
            return response.json()
        return {"error": f"Monster '{monster_name}' not found"}


@tool
async def get_equipment_info(equipment_name: str) -> dict:
    async with httpx.AsyncClient() as client:
        equipment_slug = equipment_name.lower().replace(" ", "-")
        response = await client.get(f"{settings.dnd_api_base_url}/equipment/{equipment_slug}")
        if response.status_code == 200:
            return response.json()
        return {"error": f"Equipment '{equipment_name}' not found"}


@tool
async def get_class_info(class_name: str) -> dict:
    async with httpx.AsyncClient() as client:
        class_slug = class_name.lower()
        response = await client.get(f"{settings.dnd_api_base_url}/classes/{class_slug}")
        if response.status_code == 200:
            return response.json()
        return {"error": f"Class '{class_name}' not found"}


@tool
async def get_race_info(race_name: str) -> dict:
    async with httpx.AsyncClient() as client:
        race_slug = race_name.lower().replace(" ", "-")
        response = await client.get(f"{settings.dnd_api_base_url}/races/{race_slug}")
        if response.status_code == 200:
            return response.json()
        return {"error": f"Race '{race_name}' not found"}
