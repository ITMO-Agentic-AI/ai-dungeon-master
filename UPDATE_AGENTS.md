# Agents Updated for Ollama Structured Output

## ✅ Completed
- story_architect - Uses custom structured output helper
- lore_builder - Uses custom structured output helper

## 🔄 Remaining to Update
- action_resolver
- director  
- rule_judge
- player_proxy
- world_engine

## Pattern to Apply

Replace:
```python
self.structured_llm = self.model.with_structured_output(ModelClass)
chain = prompt | self.structured_llm
result = await chain.ainvoke({})
```

With:
```python
from src.services.structured_output import get_structured_output
from langchain_core.messages import SystemMessage, HumanMessage

messages = [
    SystemMessage(content=system_prompt),
    HumanMessage(content=user_prompt)
]
result = await get_structured_output(self.model, messages, ModelClass)
```
