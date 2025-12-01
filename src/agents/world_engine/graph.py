import json
import re
from typing import Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.runtime import Runtime
from src.core.types import GameState
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service


class WorldEngineAgent(BaseAgent):
    """
    Phase 1:
    - 生成初始化的位置, 时间, 天气, 基础描述
    Phase 3:
    - 根据事件更新时间, 天气, 描述
    """
    def __init__(self):
        super().__init__("World Engine")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)

        # 定义两个核心节点
        graph.add_node("init_world", self.init_world)
        graph.add_node("update_world", self.update_world)

        # 路由逻辑
        graph.add_conditional_edges(
            "__start__",
            self.route_step,
            {
                "init": "init_world",
                "update": "update_world"
            }
        )

        graph.add_edge("init_world", END)
        graph.add_edge("update_world", END)

        return graph
    
    # 路由逻辑(Router)
    def route_step(self, state: GameState) -> Literal["init", "update"]:
        # 检查world是否已经初始化(查看有没有位置信息)
        world = state.get("world", {})
        if not world or "current_location" not in world:
            return "init"
        return "update"

    
    # Phase 1: 世界初始化
    async def init_world(self, state: GameState, runtime: Runtime) -> dict[str, Any]:
        """根据Lore设定生成初始世界状态"""
        
        # 获取Lore Agent的输入(如果没有则为默认)
        lore_summary = state.get("lore_summary", "A dark fantasy world ruled by dragonlords.")
        
        prompt = (
            f"You are the World Engine for a D&D game.\n"
            f"Task: Initialize the starting state based on this lore: '{lore_summary}'"
            f"Requirements:\n"
            f"1. Choose a starting location name.\n"
            f"2. Set a starting time (0-23) and appropriate weather.\n"
            f"3. Write a vivid scene description for the game start.\n\n"
            f"Respond ONLY in valid JSON format:\n"
            f"{{"
            f"  \"current_location\": \"Location Name\",\n"
            f"  \"time_of_day\": 8,\n"
            f"  \"weather\": \"Sunny\",\n"
            f"  \"Description\": \"Immersive description...\"\n"
            f"}}"
        )

        try:
            print(f"DEBUG: Initializing World for -> {lore_summary[:50]}...")
            response = await self.model.ainvoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # Re提取JSON
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                world_data = json.loads(json_match.group())
            else:
                raise ValueError("No JSON Found")
        
        except Exception as e:
            print(f"ERROR: World Init Failed: {e}")
            world_data = {
                "current_location": "Village Tavern",
                "time_of_day": 18,
                "weather": "Rainy",
                "Description": "You sit in a dimly lit tavern, rain hammering against the roof."
            }
        
        # 写入world状态
        return {
            "world": world_data
        }


    # Phase 3: 更新世界
    async def update_world(self, state: GameState, runtime: Runtime) -> dict[str, Any]:
        # 1. 取出原始世界状态，避免直接修改原始对象
        current_world = state.get("world", {}).copy()
        # 获取当前基础数值
        try:
            curr_time = int(current_world.get("time_of_day", 10))
        except (ValueError, TypeError):
            curr_time = 10  # 如果转换失败，默认值为10点

        curr_weather = current_world.get("weather", "sunny")
        curr_location = current_world.get("current_location", "village square")

        # 2. 获取上下文，理解刚刚发生了什么, 优先读取Messages
        messages = state.get("messages", [])
        # messages对象兼容处理
        last_event = "The game session has just begun."

        if messages and len(messages) > 0:
            last_msg = messages[-1]
            # 如果是对象则取.content, 字典取["content"], 字符串直接使用
            if hasattr(last_msg, "content"):
                last_event = last_msg.content
            elif isinstance(last_msg, dict):
                last_event = last_msg.get("content", str(last_msg))
            else:
                last_event = str(last_msg)
        # 如果Message为空，尝试读取Actions列表
        elif "Actions" in state and state["Actions"]:
            last_event = str(state["Actions"][-1])

        # 3. LLM决策，解析事件，用AI判断时间流逝和地点变化
        analysis_prompt = (
            f"You are the Game Engine. Analyze the World State changes based on the recent event. \n"
            f"Current State:\n"
            f"- Time: {curr_time}:00\n"
            f"- Weather: {curr_weather}\n"
            f"- Location: {curr_location}\n\n"
            f"Recent Event: \"{last_event}\"\n\n"
            f"Instructions:\n"
            f"1. Did the location change in the event? If yes, extract the new location name.\n"
            f"2. Did time pass? (e.g., 'short rest' = +1 hour, 'travel' = +hours). If unsure, assume 0.\n"
            f"3. Did the weather change dramatically? If not, keep '{curr_weather}'.\n\n"
            f"Respond ONLY in valid JSON format like this:\n"
            f"{{\n"
            f"  \"time_passed_hours\": 0, \n"
            f"  \"new_location\": \"{curr_location}\",\n"
            f"  \"new_weather\": \"{curr_weather}\"\n"
            f"}}"
        )

        try:
            # 调用模型
            response = await self.model.ainvoke(analysis_prompt)
            content = response.content if hasattr(response, "content") else str(response)
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found in response")

            # 解析结果
            time_delta = int(result.get("time_passed_hours", 0))
            next_location = result.get("new_location", curr_location)
            next_weather = result.get("new_weather", curr_weather)
        
        except Exception as e:
            # 如果模型解析失败，保持现状
            print(f"World Engine Analysis Error: {e}")
            time_delta = 0
            next_location = curr_location
            next_weather = curr_weather

        # 计算新时间
        next_time = (curr_time + time_delta) % 24

        # 4. 生成环境描述，只有当环境发生实质变化才重新生成描述
        state_changed = (
            next_location != curr_location or
            next_weather != curr_weather or
            time_delta > 0
        )

        if state_changed or "Description" not in current_world:
            desc_prompt = (
                f"Describe the current scene in one immersive sentence.\n"
                f"Location: {next_location}\n"
                f"Time: {next_time}:00\n"
                f"Weather: {next_weather}\n"
                f"Focus on the sensory details (e.g. light, sound, smell)."
            )
            try:
                desc_res = await self.model.ainvoke(desc_prompt)
                new_description = desc_res.content if hasattr(desc_res, "content") else str(desc_res)
            except:
                new_description = "The world waits quietly."
        else:
            new_description = current_world.get("Description", "")
        
        # 5. 更新状态，更新world字典
        current_world.update({
            "time_of_day": next_time,
            "weather": next_weather,
            "current_location": next_location,
            "Description": new_description
        })

        # 记录这次更新的操作日志
        logs = state.get("Logs", {}).copy()
        logs["World_Update"] = {
            "Trigger_Event": last_event[:50] + "...",  # 只记录前50个字符作为摘要
            "Time_Shift": time_delta,
            "New_Location": next_location
        }

        # 返回新的完整状态
        # 注意：这里我们返回update后的字典，LangGraph会负责含并
        return {
            "world": current_world,
            "Logs": logs
        }

    async def process(self, state: GameState, runtime: Runtime = None) -> dict[str, Any]:
        step = self.route_step(state)
        if step == "init":
            return await self.init_world(state, runtime)
        else:
            return await self.update_world(state, runtime)


graph = WorldEngineAgent().compile()
