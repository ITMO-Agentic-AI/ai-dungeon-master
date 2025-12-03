# src/agents/player_proxy/graph.py

import uuid
import operator
from typing import Any, Dict, List, Literal, Annotated, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.types import Send  # 用于并行分发任务
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field  # 引入Pydantic

from src.core.types import GameState, Player, DnDCharacterStats
from src.agents.base.agent import BaseAgent
from src.services.model_service import model_service


# 角色输入结构
class PlayerGenInput(BaseModel):
    name: str = Field(default="Unknown", description="Character name")
    class_name: str = Field(default="Adventurer", description="Class name e.g. Warrior")
    race: str = Field(default="Human")
    background: str = Field(default="Unknown")
    motivation: str = Field(default="To explore")
    backstory: str = Field(default="A mysterious traveler.")
    location_id: str = Field(default="unknown")

    # stats
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    max_hit_points: int = 10
    current_hit_points: int = 10
    armor_class: int = 10
    
    # **这里没有id字段, 设为optional, 因为LLM生成的ID过于难以控制, 所以直接代码内生成
    id: Optional[str] = Field(default=None)


class PlayerProxyAgent(BaseAgent):
    """
    Phase 1:
    - 并行创建角色(Parallel Character Creation)
    - 使用Send API同时生成多个D&D 5e角色卡
    Phase 3:
    - Gameplay Loop
    - 根据环境和记忆模拟player行动
    """
    def __init__(self):
        super().__init__("Player Proxy")
        self.model = model_service.get_model()
        # 使用model.with_structured_output生成player对象, 不再使用Re抓取JSON
        # 使用Wrapper类来接收输出, LLM就算嵌套生成了character也能正确解析
        self.structured_llm = self.model.with_structured_output(PlayerGenInput)
    
    def build_graph(self) -> StateGraph:
        graph = StateGraph(GameState)
        # 定义两个核心节点
        # create_single_character: 单个人的人工节点
        # simulate_action: 游戏运行主节点
        graph.add_node("create_single_character", self.create_single_character)
        graph.add_node("simulate_action", self.simulate_action)

        # 定义条件边: 起点 -> Router判断 -> 分发给多个工人 OR Enter Game
        graph.add_conditional_edges(
            "__start__",
            self.route_step,
            ["create_single_character", "simulate_action"]
        )

        # 造完人之后结束(结果自动汇聚), 游戏回合结束也会停止
        graph.add_edge("create_single_character", END)
        graph.add_edge("simulate_action", END)

        return graph
    

    # 路由逻辑(Map Step Router)
    def route_step(self, state: GameState):
        """
        检查当前状态:
        - 如果没有玩家 -> 启动并行创建(返回Send列表)
        - 如果有玩家 -> 进入游戏循环(返回"simulate_action")
        """
        players = state.get("players", [])

        # 如果players列表为空, 需要初始化生成角色
        if not players:
            # 获取设定(从State中读取)
            setting = state.get("setting")
            narrative = state.get("narrative")
            world = state.get("world")

            # 获取concepts逻辑
            concepts = ["Warrior", "Mage", "Rogue"]  # 默认值
            if isinstance(setting, dict):
                concepts = setting.get("player_concepts", concepts)
            elif hasattr(setting, "player_concepts"):
                concepts = setting.player_concepts
            
            # 读取narrative.tagline
            story_hook = "A generic adventure"
            if isinstance(narrative, dict):
                story_hook = narrative.get("tagline", story_hook)
            elif hasattr(narrative, "tagline"):
                story_hook = narrative.tagline

            # 获取世界地点(设置初始位置)
            locations = {}
            if isinstance(world, dict):
                locations = world.get("locations", {})
            elif hasattr(world, "locations"):
                locations = world.locations
            
            # 进行并发任务(Map)
            # 不在这里生成, 而是发出多个Send
            # 每个Send会启动独立的create_single_character节点
            return [
                Send("create_single_character", {
                    "concept": concept,
                    "story_hook": story_hook,
                    "locations": locations
                })
                for concept in concepts
            ]

            # 如果人已经齐了, Enter Game
        return "simulate_action"
        
    
    # Phase 1: 单个角色创建(Worker Node)
    async def create_single_character(self, state: dict) -> Dict[str, Any]:
        """
        [Worker]是一个并行节点
        接收state不是完整的GameState, 而是由Send传过来的字典(payload)
        """
        concept = state.get("concept")
        hook = state.get("story_hook")
        locations = state.get("locations")

        # 确定初始位置ID
        start_loc_id = "unknown_location"
        if locations:
            # 取第一个可用地点的ID
            start_loc_id = list(locations.keys())[0]
        
        # 构造Prompt
        system_prompt = """You are an expert D&D 5e Character Creator. 
        Your goal is to generate a valid JSON object for a player character."""

        user_prompt = f"""
        # Context
        Campaign Hook: {hook}
        Target Archetype: {concept}
        
        # Task
        Create a character profile inside a "character" object.
        
        # REQUIREMENTS (Use EXACT lowercase keys):
        1. "name": Character name.
        2. "class_name": Use "{concept}".
        3. "race": Character race.
        4. "background": Character background.
        5. "motivation": One short sentence.
        6. "backstory": Two sentences connecting to hook.
        7. "location_id": Set exactly to "{start_loc_id}".
        
        # STATS (Integers only):
        - "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"
        - "max_hit_points", "current_hit_points", "armor_class"
        
        IMPORTANT: Do NOT nest stats. Keep JSON flat.
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]

        # 调用LLM
        gen_data = await self.structured_llm.ainvoke(messages)

        # 用Python这边的代码来生成ID, 效果比LLM强
        final_id = gen_data.id if gen_data.id else f"player_{uuid.uuid4().hex[:8]}"

        # 构造Player对象(src.core.types.Player)
        # 手动组装Stats嵌套对象
        stats_obj = DnDCharacterStats(
            strength = gen_data.strength,
            dexterity = gen_data.dexterity,
            constitution = gen_data.constitution,
            intelligence = gen_data.intelligence,
            wisdom = gen_data.wisdom,
            charisma = gen_data.charisma,
            max_hit_points = gen_data.max_hit_points,
            current_hit_points = gen_data.current_hit_points,
            armor_class = gen_data.armor_class
        )

        final_player = Player(
            id = final_id,
            name = gen_data.name,
            class_name = gen_data.class_name,  # 使用处理过的class name
            race = gen_data.race,
            background = gen_data.background,
            motivation = gen_data.motivation,
            backstory = gen_data.backstory,
            location_id = start_loc_id,
            stats = stats_obj  # 传入组装好的对象
        )


        # *返回结果, 因为types.py定义了players是Annotated[List, add]
        # 所以这里的返回列表会自动追加到总列表中, 不会覆盖
        return {"players": [final_player]}

    
    # Phase 3: Gameplay Loop
    async def simulate_action(self, state: GameState, runtime: Runtime = None) -> dict[str, Any]:
        # 读取世界状态(兼容Pydantic对象访问)
        world = state.get("world")
        if world:
            time_val = getattr(world, "global_time", 0)
            if isinstance(world, dict): time_val = world.get("global_time", 0)
            context_desc = f"Turn {time_val}. "
        else:
            context_desc = "Unknown environment."
        
        # 读取角色卡
        players = state.get("players", [])
        if not players:
            return {"messages": []}
        
        # 暂时只模拟第一个玩家, 或者活跃玩家
        active_player = players[0]

        # 兼容Dict和Pydantic对象的属性读取
        if isinstance(active_player, dict):
            p_name = active_player.get("name", "Unknown")
            p_class = active_player.get("class_name", "Unknown")
            p_race = active_player.get("race", "Unknown")
            p_bg = active_player.get("background", "Unknown")
            p_backstory = active_player.get("backstory", "")
        else:
            p_name = getattr(active_player, "name", "Unknown")
            p_class = getattr(active_player, "class_name", "Unknown")
            p_race = getattr(active_player, "race", "Unknown")
            p_bg = getattr(active_player, "background", "Unknown")
            p_backstory = getattr(active_player, "backstory", "")

        # 读取记忆(Messages)
        messages = state.get("messages", [])
        recent_msgs = messages[-5:]
        history_text = ""
        for msg in recent_msgs:
            # 兼容不同类型的Message对象
            m_type = getattr(msg, "type", "unknown")
            if isinstance(msg, dict): m_type = msg.get("type", "unknown")

            m_content = getattr(msg, "content", str(msg))
            if isinstance(msg, dict): m_content = msg.get("content", "")
            
            history_text += f"[{m_type}]: {m_content}\n"
        
        if not history_text:
            history_text = "[System]: The adventure begins."
        
        # 构造Prompt
        prompt = (
            f"Roleplay Instructions:\n"
            f"You are {p_name}, a Level 1 {p_class}.\n"
            f"Race: {p_race}. Background: {p_bg}.\n"
            f"Personality/Backstory: {p_backstory}\n\n"
            f"Current Situation: {context_desc}\n"
            f"Recent History:\n{history_text}\n\n"
            f"Task: Based on your character, describe what you do next in ONE vivid sentence.\n"
            f"Focus on action and intent. Do not dictate the outcome."
        )

        # 调用模型(文本输出)
        try:
            response = await self.model.ainvoke(prompt)
            action_text = (response.content if hasattr(response, "content") else str(response)).strip()
        except Exception as e:
            action_text = f"{p_name} hesitates, unsure what to do. (Error: {e})"
        
        # 返回结果
        new_message = {
            "type": "human",
            "name": p_name,
            "content": action_text
        }

        return {
            "messages": [new_message]
        }

        
    # 入口函数(Process)
    async def process(self, state: GameState, runtime: Runtime = None) -> Dict[str, Any]:
        """
        Orchestrator调用的入口
        这里手动调用Router, 如果是Parallel task, LangGraph会处理Send对象
        """
        # 判断路由
        next_step = self.route_step(state)
        # 如果是并行任务(返回为list[Send])
        if isinstance(next_step, list):
            """
            在Orchestrator的Graph里, 如果节点返回Send对象
            LangGraph会自动调度worker节点
            直接返回Send对象即可
            """
            return next_step
        
        # 普通任务(返回字符串"simulate_action")
        elif next_step == "simulate_action":
            return await self.simulate_action(state, runtime)
        
        return {}

graph = PlayerProxyAgent().compile()