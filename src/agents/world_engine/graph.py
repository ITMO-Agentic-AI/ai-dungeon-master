from typing import Any, Dict, List
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph
from pydantic import BaseModel, Field
import uuid

from src.core.types import GameState, WorldState, LocationNode, ActiveNPC
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service

# Helper model for the LLM's output
class LocationBatch(BaseModel):
    locations: List[LocationNode]

class WorldEngineAgent(BaseAgent):
    def __init__(self):
        super().__init__("World Engine")
        self.model = model_service.get_model()
        # We will generate locations batch by batch to manage context
        self.structured_llm = self.model.with_structured_output(LocationBatch)

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        graph.add_node("instantiate_world", self.instantiate_world)
        graph.add_edge("__start__", "instantiate_world")
        return graph

    async def instantiate_world(self, state: GameState) -> Dict[str, Any]:
        """
        Step 3: Canonical World State Creation.
        Turns 'Lore' into 'Locations' and 'Active Entities'.
        """
        world_state: WorldState = state["world"]
        regions = world_state.regions
        
        # 1. Generate Locations for each Region
        all_locations = {}
        
        # We create a prompt that asks for specific navigable nodes for the regions
        system_prompt = """You are the World Engine. 
        Your job is to break down broad 'Regions' into specific, navigable 'Location Nodes' for a text adventure game.
        Establish connections (paths) between them to form a logical map."""

        # Prepare context from Phase 2
        regions_desc = "\n".join([f"- {r.name}: {r.description} ({r.environmental_hook})" for r in regions])
        
        user_prompt = f"""
        Context Regions:
        {regions_desc}

        Task:
        Create 3-4 specific locations for EACH region listed above.
        - Ensure IDs are unique (e.g., 'reg_darkwood_clearing').
        - Include connections between locations within the same region.
        - designate one location per region as a 'Gateway' that connects to other regions.
        """

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", user_prompt)
        ])

        # Invoke LLM
        chain = prompt | self.structured_llm
        result: LocationBatch = await chain.ainvoke({})
        
        # Index locations by ID
        for loc in result.locations:
            all_locations[loc.id] = loc

        # 2. Place NPCs
        # We map the 'static' NPCs from Phase 2 into 'ActiveNPCs'
        active_npcs = {}
        lore_npcs = world_state.important_npcs or []
        
        # Simple logic: Try to match NPC region string to a location in that region
        # If no match, put them in the first location of that region
        for npc in lore_npcs:
            # Find a location that matches the NPC's region
            start_loc_id = None
            
            # Try to find a location in the NPC's declared region
            for loc_id, loc in all_locations.items():
                if loc.region_name.lower() in npc.region.lower() or npc.region.lower() in loc.region_name.lower():
                    start_loc_id = loc_id
                    break
            
            # Fallback: just pick the first location generated
            if not start_loc_id and all_locations:
                start_loc_id = list(all_locations.keys())[0]
                
            if start_loc_id:
                # Create the ActiveNPC
                npc_id = f"npc_{uuid.uuid4().hex[:8]}"
                new_active_npc = ActiveNPC(
                    id=npc_id,
                    base_data=npc,
                    current_location_id=start_loc_id,
                    current_activity="Standing by",
                    status="Alive"
                )
                active_npcs[npc_id] = new_active_npc
                
                # Update the location to know the NPC is there
                all_locations[start_loc_id].npc_ids.append(npc_id)

        # 3. Update the WorldState with the new mechanical data
        # We must copy the existing state to preserve Lore, then add the new maps
        updated_world = world_state.model_copy(update={
            "locations": all_locations,
            "active_npcs": active_npcs,
            "global_time": 1
        })

        return {"world": updated_world}

    async def process(self, state: GameState) -> Dict[str, Any]:
        return await self.instantiate_world(state)
