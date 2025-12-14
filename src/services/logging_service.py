# /src/services/logging_service.py

import json
import os
import datetime
from typing import Any, Dict, Optional, Union
from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel
from rich.text import Text
from pydantic import BaseModel

# Color style
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "error": "bold red",
    "player": "bold green",
    "dm": "bold purple",
    "world": "yellow",
    "narrative": "blue",
    "tool": "dim white"
})

class LoggingService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LoggingService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, log_dir="logs"):
        if hasattr(self, "initialized"):
            return
        
        self.console = Console(theme=custom_theme)
        self.log_dir = log_dir
        self.initialized = True
        
        # 确保日志目录存在
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 创建本次运行的日志文件 (按时间命名)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(log_dir, f"session_{timestamp}.jsonl")
        
        self.console.print(f"[info]📝 Logging initialized. Saving to: {self.log_file}[/info]")
    
    def _serialize(self, obj: Any) -> Any:
        """用于将 Pydantic 模型和其他对象转换为 JSON 安全字典的辅助工具"""
        if isinstance(obj, BaseModel):
            return obj.model_dump()
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._serialize(i) for i in obj]
        return obj
    
    def log_event(self, 
                  source: str, 
                  event_type: str, 
                  content: Any, 
                  print_to_terminal: bool = True,
                  level: str = "info"):
        """
        核心记录函数
        :param source: 来源 (e.g., "Player", "DM", "System")
        :param event_type: 类型 (e.g., "Action", "Update", "Error", "Thought")
        :param content: 具体内容 (可以是 str, dict, Pydantic Model)
        :param print_to_terminal: 是否在控制台显示
        :param level: 日志级别 (info, warning, error)
        """

        # 构造结构化日志
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "source": source,
            "type": event_type,
            "content": self._serialize(content),
            "level": level
        }

        # 写入文件(JSONL - Append Mode)
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Logging failed: {e}")

        # Console print
        if print_to_terminal:
            self._print_terminal(source, event_type, content, level)
        
    def _print_terminal(self, source: str, event_type: str, content: Any, level: str):
        # ensure style
        style = "info"
        if level == "error":
            style = "error"
        elif source.lower() in ["player", "garret", "user"]:
            style = "player"
        elif source.lower() in ["dungeon master", "dm"]:
            style = "dm"
        elif source.lower() in ["world engine", "world"]:
            style = "world"

        display_text = ""

        # str
        if isinstance(content, str):
            display_text = content
        
        # dict or object
        elif isinstance(content, dict) or isinstance(content, BaseModel):
            data = self._serialize(content)
            if "content" in data:
                display_text = str(data["content"])
            elif "description" in data:
                display_text = str(data["description"])
            elif "thought" in data:  # Mind Chain
                display_text = f"{data['thought']}"
            else:
                # 复杂对象, 只显示类型
                display_text = f"[{event_type} Data Saved to Log]"
        
        # Filter out empty or purely data-based logs and only display meaningful text interactions
        if not display_text or display_text.strip() == "":
            return

        # 使用Panel增加可读性
        title = f"[{style}]{source} ({event_type})[/{style}]"
        self.console.print(Panel(Text(display_text), title=title, border_style=style))


logger = LoggingService()