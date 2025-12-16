"""
Helper utilities for structured output parsing with custom LLM endpoints.
Provides fallback mechanisms when native structured output is not supported.

Enhanced with:
- Better error diagnostics
- Exponential backoff retry logic
- Connection error handling
- Detailed error messages
"""

import asyncio
import json
import logging
import os
import re
from typing import TypeVar, Type

from pydantic import BaseModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


async def get_structured_output(
    llm: ChatOpenAI,
    messages: list[BaseMessage],
    output_model: Type[T],
    max_retries: int = 3,
) -> T:
    """
    Get structured output from LLM with robust JSON parsing and retry logic.

    Features:
    - Exponential backoff between retries
    - Detailed error diagnostics
    - JSON extraction from markdown code blocks
    - Retry logic for transient failures

    Args:
        llm: The language model instance
        messages: List of messages to send to the LLM
        output_model: Pydantic model class for the expected output
        max_retries: Maximum number of retry attempts (default: 3)

    Returns:
        Instance of output_model parsed from LLM response

    Raises:
        ValueError: If parsing fails after all retries with diagnostic info
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

    last_error = None
    last_error_type = None

    for attempt in range(max_retries):
        try:
            logger.debug(f"Structured output attempt {attempt + 1}/{max_retries}")

            # Invoke LLM WITHOUT timeout parameter (not supported by ainvoke)
            # LangChain ChatOpenAI handles its own timeouts internally
            response = await llm.ainvoke(enhanced_messages)
            content = response.content.strip()
            logger.debug(f"Got response of length: {len(content)}")

            # Try to extract JSON if wrapped in markdown code blocks
            json_match = re.search(
                r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL
            )
            if json_match:
                content = json_match.group(1)
                logger.debug("Extracted JSON from markdown code block")

            # Try to find JSON object in the response
            if not json_match:
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                    logger.debug("Extracted JSON object from response")

            # Parse JSON
            try:
                data = json.loads(content)
                logger.debug("JSON parsing successful")
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed: {str(e)}")
                if attempt < max_retries - 1:
                    # Add error feedback for retry
                    enhanced_messages.append(response)
                    enhanced_messages.append(
                        BaseMessage(
                            content=f"Your response was not valid JSON. Error: {str(e)}. Please respond with ONLY valid JSON matching the schema.",
                            type="human",
                        )
                    )
                    # Exponential backoff: 1s, 2s, 4s
                    wait_time = 2**attempt
                    logger.info(
                        f"Retrying JSON parse in {wait_time}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                last_error = f"JSON Parse Error: {str(e)}"
                last_error_type = "JSON_PARSE"
                continue

            # Validate and create Pydantic model
            try:
                result = output_model(**data)
                logger.debug(f"Successfully created {output_model.__name__}")
                return result
            except Exception as e:
                logger.error(f"Pydantic validation failed: {str(e)}")
                raise

        except Exception as e:
            error_str = str(e).lower()
            last_error = str(e)

            # Diagnose connection errors specifically
            if "authentication" in error_str or "invalid" in error_str:
                last_error_type = "AUTHENTICATION"
                logger.error(
                    f"❌ Authentication error (attempt {attempt + 1}): {str(e)}"
                )
                logger.error(
                    "   → Check OPENAI_API_KEY is set correctly and not expired"
                )
            elif "network" in error_str or "connection" in error_str:
                last_error_type = "NETWORK"
                logger.error(
                    f"❌ Network error (attempt {attempt + 1}): {str(e)}"
                )
                logger.error(
                    "   → Check internet connection and firewall settings"
                )
            elif "rate" in error_str or "quota" in error_str:
                last_error_type = "RATE_LIMIT"
                logger.error(f"❌ Rate limit/quota error (attempt {attempt + 1}): {str(e)}")
                logger.error("   → Wait before retrying or check API quota")
            elif "timeout" in error_str:
                last_error_type = "TIMEOUT"
                logger.error(f"❌ Timeout error (attempt {attempt + 1}): {str(e)}")
                logger.error("   → API endpoint slow or unreachable")
            else:
                last_error_type = "UNKNOWN"
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")

            if attempt < max_retries - 1:
                # Exponential backoff
                wait_time = 2**attempt
                logger.info(
                    f"Retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})..."
                )
                await asyncio.sleep(wait_time)
                continue

    # All retries exhausted - provide detailed error message
    api_key_env = os.getenv("OPENAI_API_KEY")
    model_env = os.getenv("OPENAI_MODEL_NAME", "unknown")
    api_base_env = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

    error_diagnostics = {
        "error_type": last_error_type,
        "last_error": last_error,
        "max_retries": max_retries,
        "attempts_made": max_retries,
        "model": model_env,
        "api_key_set": bool(api_key_env),
        "api_base": api_base_env,
    }

    troubleshooting_steps = [
        "1. Verify OPENAI_API_KEY is set: export OPENAI_API_KEY=sk-...",
        "2. Verify API key is valid and not expired",
        "3. Check internet connection and firewall",
        "4. Verify model name is correct (gpt-4o-mini, gpt-4, etc.)",
        "5. Check for rate limiting in OpenAI dashboard",
        "6. Run connection test: python test_connection.py",
        "7. Check logs for detailed error information",
    ]

    error_message = (
        f"Failed to get structured output after {max_retries} attempts\n"
        f"Error Type: {last_error_type}\n"
        f"Last Error: {last_error}\n\n"
        f"Diagnostics:\n"
    )

    for key, value in error_diagnostics.items():
        error_message += f"  {key}: {value}\n"

    error_message += "\nTroubleshooting Steps:\n"
    for step in troubleshooting_steps:
        error_message += f"  {step}\n"

    error_message += (
        "\nFor more help, see: TROUBLESHOOTING_CONNECTION_ERROR.md"
    )

    raise ValueError(error_message)


def get_example_from_schema(model: Type[BaseModel]) -> dict:
    """Generate an example instance from a Pydantic model.

    Args:
        model: Pydantic model class

    Returns:
        dict: Example instance with placeholder values
    """
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
