# src/agents/world_engine/graph.py
from typing import Any, Dict, List, Literal
import uuid
import json

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from src.core.types import GameState, WorldState, LocationNode, ActiveNPC, Region, KeyNPC
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service
from src.services.structured_output import get_structured_output


class LocationNodeInput(BaseModel):
    name: str
    description: str
    region_name: str
    exits: str = Field(description="List of IDs of connected locations")


class LocationBatch(BaseModel):
    locations: List[LocationNodeInput]


class WorldUpdateOutput(BaseModel):
    time_passed_hours: int = Field(description="Hours passed since last event")
    new_weather: str = Field(description="Current weather condition")
    # description直接通过update_world返回给user, 或者存入world state


class WorldEngineAgent(BaseAgent):
    """
    WorldEngineAgent:
    - 实例化: 将背景设定(区域/非玩家角色)转换为可玩地图(地点/活跃非玩家角色)
    - 更新: 在游戏过程中管理时间, 天气和环境描述
    """

    def __init__(self):
        super().__init__("World Engine")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)

        # 添加节点
        graph.add_node("instantiate_world", self.instantiate_world)
        graph.add_node("update_world", self.update_world)

        # 路由逻辑(Router)
        graph.add_conditional_edges(
            "__start__",
            self.route_step,
            {"instantiate": "instantiate_world", "update": "update_world"},
        )

        # 添加边
        graph.add_edge("instantiate_world", END)
        graph.add_edge("update_world", END)

        return graph

    def route_step(self, state: GameState) -> Literal["instantiate", "update"]:
        """
        检查世界地图是否存在
        如果不存在, 则创建它(instantiate), 如果存在, 则模拟环境(update)
        """
        world = state.get("world")

        if not world:
            return "instantiate"

        if isinstance(world, dict):
            has_regions = bool(world.get("regions"))
            has_locations = bool(world.get("locations"))
        else:
            has_regions = bool(getattr(world, "regions", []))
            has_locations = bool(getattr(world, "locations", {}))

        if has_regions and not has_locations:
            return "instantiate"

        return "update"

    # Phase 1: 初始化世界(Instantiate World, Map Generation)
    async def instantiate_world(self, state: GameState) -> Dict[str, Any]:
        """
        Turns 'Lore' (Regions) into 'Locations' and places 'Active Entities'
        """
        print("--- [World Engine] Instantiating World Map & NPCs ---")

        world_state = state.get("world")

        # 如果是空测试, world_state为None, 创造一个标准的默认世界设定
        if not world_state:
            print("DEBUG: No world state found, creating default test region.")
            # 创建一个符合src/core/types.py定义的默认Region
            default_region = Region(
                name="The Shadow Realm",
                description="A misty, gray dimension used for testing.",
                dominant_factions=["Testers"],
                key_landmarks=["The Debug Console"],
                environmental_hook="Eternal Twilight",
            )
            # 初始化一个WorldState
            world_state = WorldState(regions=[default_region], important_npcs=[])

        regions_data = []
        if isinstance(world_state, dict):
            regions_data = world_state.get("regions", [])
        else:
            regions_data = getattr(world_state, "regions", [])

        desc_list = []
        for r in regions_data:
            if isinstance(r, dict):
                r_name = r.get("name", "Unknown")
                r_desc = r.get("description", "")
                r_hook = r.get("environmental_hook", "")
            else:
                r_name = getattr(r, "name", "Unknown")
                r_desc = getattr(r, "description", "")
                r_hook = getattr(r, "environmental_hook", "")
            desc_list.append(f"- {r_name}: {r_desc} ({r_hook})")

        regions_desc = "\n".join(desc_list)

        # 为每个区域生成地点
        all_locations = {}

        system_prompt = """You are the World Engine.
        Your job is to break down broad 'Regions' into specific, navigable 'Location Nodes' for a text adventure game.
        Establish connections (paths) between them to form a logical map.
        Output strictly in JSON format."""

        user_prompt = f"""
        Context Regions:
        {regions_desc}

        Task:
        Create 3 specific locations for EACH region listed above.
        Output must constitute a valid JSON object matching the LocationBatch schema.
        
        # SCHEMA REQUIREMENTS:
        - 'name': specific name.
        - 'region_name': MUST match one of the Context Region names exactly.
        - 'description': 1 vivid sentence.
        - 'exits': A comma-separated STRING of connected location IDs.
           - Example: "loc_forest_edge, loc_cave_mouth"
        """

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        result = await get_structured_output(self.model, messages, LocationBatch)

        # 转换为内部LocationNode类型并进行索引
        for loc_input in result.locations:
            # 生成一个干净的ID
            loc_id = f"loc_{uuid.uuid4().hex[:8]}"

            raw_exits = loc_input.exits
            if raw_exits:
                connected_ids = [e.strip() for e in raw_exits.split(",") if e.strip()]
            else:
                connected_ids = []

            # Map 'exits' (LLM term) to 'connected_ids' (Internal term)
            new_node = LocationNode(
                id=loc_id,
                name=loc_input.name,
                region_name=loc_input.region_name,
                description=loc_input.description,
                connected_ids=connected_ids,
                npc_ids=[],
                clues=[],
            )
            all_locations[loc_id] = new_node

        # 放置NPC(将背景故事中的NPC映射到实际游戏中的NPC)
        active_npcs = {}
        lore_npcs = world_state.important_npcs or []

        for npc in lore_npcs:
            start_loc_id = None

            # 简单的匹配逻辑: 找到一个与NPC所在区域匹配的位置
            for loc_id, loc in all_locations.items():
                if npc.region and (
                    loc.region_name.lower() in npc.region.lower()
                    or npc.region.lower() in loc.region_name.lower()
                ):
                    start_loc_id = loc_id
                    break

            # 备选: 选择第一个可用的位置
            if not start_loc_id and all_locations:
                start_loc_id = list(all_locations.keys())[0]

            if start_loc_id:
                npc_id = f"npc_{uuid.uuid4().hex[:8]}"
                new_active_npc = ActiveNPC(
                    id=npc_id,
                    base_data=npc,
                    current_location_id=start_loc_id,
                    current_activity="Standing by",
                    status="Alive",
                )
                active_npcs[npc_id] = new_active_npc

                # 更新位置信息以记录NPC的存在
                if npc_id not in all_locations[start_loc_id].npc_ids:
                    all_locations[start_loc_id].npc_ids.append(npc_id)

        # 返回更新后的世界状态, 创建一个副本确保Pydantic验证通过
        updated_world = world_state.model_copy(
            update={
                "locations": all_locations,
                "active_npcs": active_npcs,
                "global_time": 8,  # 早上8点开始
                "weather": "Clear",
            }
        )

        return {"world": updated_world}

    # Phase 3: 更新世界(Time & Weather)
    async def update_world(self, state: GameState) -> Dict[str, Any]:
        """
        分析上一个事件, 以推进时间和天气变化
        """
        world_state = state.get("world")
        # 避免报错
        if not world_state:
            return {}

        if isinstance(world_state, dict):
            curr_time = world_state.get("global_time", 8)
            curr_weather = world_state.get("weather", "Clear")
        else:
            curr_time = getattr(world_state, "global_time", 8)
            curr_weather = getattr(world_state, "weather", "Clear")

        messages = state.get("messages", [])

        # 安全获得之前的信息
        last_event = "The game begins."
        if messages:
            last_msg = messages[-1]
            # 处理不同类型的消息
            if isinstance(last_msg, dict):
                last_event = last_msg.get("content", str(last_msg))
            else:
                last_event = getattr(last_msg, "content", str(last_msg))

        system_prompt = "You are the Game Simulation Engine. Analyze the event to update world time and weather. Output JSON."
        user_prompt = f"""
        Current Time: {curr_time}:00
        Current Weather: {curr_weather}
        Recent Event: "{last_event}"

        Task:
        1. Determine how much time passed (in hours). Combat/Talking ~ 0. Travel/Rest ~ 1-8.
        2. Determine if weather changes (keep it consistent unless drastic change implies it).
        """

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        try:
            result = await get_structured_output(self.model, messages, WorldUpdateOutput)
            time_delta = result.time_passed_hours
            new_weather = result.new_weather
        except Exception as e:
            print(f"World update failed, using defaults: {e}")
            time_delta = 0
            new_weather = curr_weather

        # Update Time
        new_time = (curr_time + time_delta) % 24

        if isinstance(world_state, dict):
            updated_world = world_state.copy()
            updated_world["global_time"] = new_time
            updated_world["weather"] = new_weather
            return {"world": updated_world}
        else:
            updated_world = world_state.model_copy(
                update={"global_time": new_time, "weather": new_weather}
            )
            return {"world": updated_world}

    async def process(self, state: GameState, runtime: Runtime = None) -> Dict[str, Any]:
        step = self.route_step(state)
        if step == "instantiate":
            return await self.instantiate_world(state)
        else:
            return await self.update_world(state)


graph = WorldEngineAgent().build_graph().compile()
