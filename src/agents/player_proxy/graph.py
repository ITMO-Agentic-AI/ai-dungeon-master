import json
import re
from typing import Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.runtime import Runtime
from src.core.types import GameState
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service


class PlayerProxyAgent(BaseAgent):
    """
    Phase 1:
    - 创建D&D 5e角色卡(Stats, Inventory, Backstory)
    Phase 3:
    - 根据环境和记忆模拟玩家行动
    """
    def __init__(self):
        super().__init__("Player Proxy")
        self.model = model_service.get_model()

    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)

        # 两个核心节点
        graph.add_node("create_character", self.create_character)
        graph.add_node("simulate_action", self.simulate_action)

        # 定义条件边: 起点 -> 是否创建角色 -> 分流
        graph.add_conditional_edges(
            "__start__",
            self.route_step,
            {
                "create": "create_character",
                "play": "simulate_action"
            }
        )
        
        # 两个节点执行完都结束
        graph.add_edge("create_character", END)
        graph.add_edge("simulate_action", END)

        return graph
    
    # 路由逻辑(Router)
    def route_step(self, state: GameState) -> Literal["create", "play"]:
        # 决定是创建角色还是进行游戏
        players = state.get("players", [])

        # 如果players列表为空, 或者里面的数据不完整(没有属性), 进入创建模式
        if not players or (isinstance(players, list) and len(players) == 0):
            return "create"
        
        # 游戏模式
        return "play"

    # Phase 1: 角色创建
    async def create_character(self, state: GameState, runtime: Runtime) -> dict[str, Any]:
        """生成符合D&D 5e规则的完整角色卡"""

        # 获取输入的建议, 比如Story Architect可能会在state中放一个"character_proposal": "A elven rogue"
        proposal = state.get("character_proposal", "A fantasy adventurer suitable for a level 1 party.")

        prompt = (
            f"You are a D&D 5e Character Generator.\n"
            f"Task: Create a level 1 character based on this concept: '{proposal}'.\n"
            f"Requirements:\n"
            f"1. Generate standard Ability Scores (STR, DEX, CON, INT, WIS, CHA).\n"
            f"2. Calculate HP and AC based on class/dex.\n"
            f"3. List starting equipment and inventory.\n"
            f"4. Write a short backstory (2 sentences) and personality traits.\n\n"
            f"Respond ONLY in valid JSON format:\n"
            f"{{\n"
            f"  \"name\": \"Name\",\n"
            f"  \"race\": \"Race\",\n"
            f"  \"class\": \"Class\",\n"
            f"  \"stats\": {{ \"STR\": 10, \"DEX\": 10, ... }},\n"
            f"  \"hp\": 10,\n"
            f"  \"ac\": 12,\n"
            f"  \"inventory\": [\"Dagger\", \"Rations\"],\n"
            f"  \"personality\": \"Personality description\",\n"
            f"  \"backstory\": \"Short backstory\"\n"
            f"}}"
        )

        try:
            print(f"DEBUG: Generating Character for -> {proposal}")
            response = await self.model.ainvoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # Re提取JSON
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                char_data = json.loads(json_match.group())
            else:
                raise ValueError("No JSON found")
        
        except Exception as e:
            print(f"ERROR: Character Generation Failed: {e}")
            # Fallback默认角色
            char_data = {
                "name": "Sivi",
                "class": "Rogue",
                "stats": {"STR": 10, "DEX": 16},
                "personality": "Greedy and cautious",
                "inventory": ["Dagger"]
            }
        
        # 将生成的角色存入State P.S.通常是列表, 支持多玩家
        return {
            "players": [char_data]
        }

    # Phase 3: 游戏行动
    async def simulate_action(self, state: GameState, runtime: Runtime) -> dict[str, Any]:
        # 读取世界状态
        world = dict(state.get("world", {}))
        time_of_day = int(world.get("time_of_day", 12))  # 强转int防止报错
        weather = world.get("weather", "sunny")
        location = world.get("current_location", "unknown place")
        description = world.get("Description", "")

        # 读取角色卡(character profile)
        player_data = state.get("players", {})

        # 容错处理，获取玩家设定
        if isinstance(player_data, list) and len(player_data) > 0:
            p_profile = player_data[0]  # 第一个玩家
        elif isinstance(player_data, dict) and "name" in player_data:
            p_profile = player_data
        else:
            # 如果没有找到配置，给一个默认的角色(贪婪盗贼)用于测试
            p_profile = {
                "name": "Sivi",
                "personality": "Default"
            }

        name = p_profile.get("name", "Adventurer")
        personality = p_profile.get("personality", "Curious")
        char_class = p_profile.get("class", "Traveller")

        # 读取记忆，查看DM或其他Agent信息
        messages = state.get("messages", [])
        # 取最近的5条记录作为上下文
        recent_msgs = messages[-5:] if messages else []
        history_text = ""

        for msg in recent_msgs:
            # 兼容对象和字典格式读取
            content = ""
            role = ""
            if hasattr(msg, "content"):
                content = msg.content
                role = getattr(msg, "type", "unknown")
            elif isinstance(msg, dict):
                content = msg.get("content", "")
                role = msg.get("type", "unknown")
            
            if content:
                history_text += f"[{role}]: {content}\n"
        
        if not history_text:
            history_text = "[System]: Game begins."


        # 构造prompt
        prompt = (
            f"Roleplay Instructions:\n"
            f"You are {name}, a {char_class}. Your personality is: {personality}.\n"
            f"Current Context:\n"
            f"- Time: {time_of_day}:00\n"
            f"- Weather: {weather}\n"
            f"- Location: {location}\n"
            f"- Scene Description: {description}\n\n"
            f"Recent Chat History:\n"
            f"{history_text}\n\n"
            f"Task:\n"
            f"Based on the history and your personality, describe what you do next in ONE vivid sentence.\n"
            f"Do not describe the outcome, only your attempt. Do not speak for the DM.\n"
            f"Action:"
        )

        # 调用模型
        try:
            response = await self.model.ainvoke(prompt)
            action_text = (
                response.content
                if hasattr(response, "content")
                else str(response)
            ).strip()
        except Exception as e:
            action_text = f"{name} looks around, unsure what to do. (Error: {e})"

        # 返回结果, 写入公告频道
        # 把行动包装成一条Standard message, Langgraph可以把它添加到messages列表
        # World Engine可以读到
        new_message = {
            "type": "human",  # 玩家行动
            "name": name,
            "content": action_text
        }

        # 只返回增量消息, 不覆盖整个state
        return {
            "messages": [new_message]
        }

    async def process(self, state: GameState, runtime: Runtime = None) -> dict[str, Any]:
        """
        Langgraph的invoke可能不会自动走图, 我们根据条件手动调用
        通常.compile()后的graph会自动处理
        这里为了兼容BaseAgent接口, 需要特殊处理
        在Langgraph体系下, 通常直接运行graph.invoke(state)
        这里的process是为了兼容BaseAgent类定义
        我们直接复用路由逻辑(Router)判断, 或者直接外部调用graph
        如果BaseAgent强制要求process返回字典, 则写为:
        """
        step = self.route_step(state)
        if step == "create":
            return await self.create_character(state, runtime)
        else:
            return await self.simulate_action(state, runtime)


graph = PlayerProxyAgent().compile()
