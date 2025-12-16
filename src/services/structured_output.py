"""
Helper utilities for structured output parsing with custom LLM endpoints.
Provides fallback mechanisms when native structured output is not supported.
"""

import json
import re
from typing import TypeVar, Type
from pydantic import BaseModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

T = TypeVar("T", bound=BaseModel)


async def get_structured_output(
    llm: ChatOpenAI,
    messages: list[BaseMessage],
    output_model: Type[T],
    max_retries: int = 3,
) -> T:
    """
    Get structured output from LLM with robust JSON parsing and retry logic.

    Args:
        llm: The language model instance
        messages: List of messages to send to the LLM
        output_model: Pydantic model class for the expected output
        max_retries: Maximum number of retry attempts

    Returns:
        Instance of output_model parsed from LLM response

    Raises:
        ValueError: If parsing fails after all retries
    """
    # Add JSON format instruction to the system message
    schema = output_model.model_json_schema()
    json_instruction = f"""

IMPORTANT: You MUST respond with valid JSON only. No other text before or after.
The JSON must match this schema:
{json.dumps(schema, indent=2)}

Example format:
{json.dumps(get_example_from_schema(output_model), indent=2)}
"""

    # Add instruction to the last system message or create new one
    enhanced_messages = messages.copy()
    for i, msg in enumerate(enhanced_messages):
        if msg.type == "system":
            enhanced_messages[i].content += json_instruction
            break

    for attempt in range(max_retries):
        try:
            response = await llm.ainvoke(enhanced_messages)
            content = response.content.strip()

            # Try to extract JSON if wrapped in markdown code blocks
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
            if json_match:
                content = json_match.group(1)

            # Try to find JSON object in the response
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                content = json_match.group(0)

            # Parse JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    # Add error feedback for retry
                    enhanced_messages.append(response)
                    enhanced_messages.append(
                        BaseMessage(
                            content=f"Your response was not valid JSON. Error: {str(e)}. Please respond with ONLY valid JSON matching the schema.",
                            type="human",
                        )
                    )
                    continue
                raise ValueError(
                    f"Failed to parse JSON after {max_retries} attempts: {str(e)}\nContent: {content}"
                )

            # Validate and create Pydantic model
            return output_model(**data)

        except Exception as e:
            if attempt < max_retries - 1:
                continue
            raise ValueError(
                f"Failed to get structured output after {max_retries} attempts: {str(e)}"
            )

    raise ValueError(f"Failed to get structured output after {max_retries} attempts")


def get_example_from_schema(model: Type[BaseModel]) -> dict:
    """Generate an example instance from a Pydantic model."""
    example = {}
    for field_name, field_info in model.model_fields.items():
        annotation = field_info.annotation

        # Handle common types
        if annotation is str:
            example[field_name] = "example string"
        elif annotation is int:
            example[field_name] = 0
        elif annotation is float:
            example[field_name] = 0.0
        elif annotation is bool:
            example[field_name] = True
        elif hasattr(annotation, "__origin__"):
            if annotation.__origin__ is list:
                example[field_name] = ["item1", "item2"]
            elif annotation.__origin__ is dict:
                example[field_name] = {"key": "value"}
            else:
                example[field_name] = None
        else:
            example[field_name] = None

    return example
