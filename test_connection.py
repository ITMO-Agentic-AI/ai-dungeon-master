#!/usr/bin/env python3
"""
Connection Test Script for AI Dungeon Master

Use this to diagnose connection issues with the LLM API.
Run: python test_connection.py
"""

import os
import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_connection():
    """Test connection to LLM API."""
    print("="*70)
    print("🧪 AI Dungeon Master - Connection Test")
    print("="*70)
    print()

    # Step 1: Check environment variables
    print("Step 1: Checking Environment Variables")
    print("-" * 70)

    api_key = os.getenv("OPENAI_API_KEY")
    model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini")
    api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

    if not api_key:
        print("❌ OPENAI_API_KEY is not set")
        print("   Fix: export OPENAI_API_KEY=sk-...")
        return False
    else:
        # Show masked key for security
        masked_key = api_key[:7] + "***" + api_key[-4:] if len(api_key) > 11 else "***"
        print(f"✅ OPENAI_API_KEY: {masked_key}")

    print(f"✅ Model: {model_name}")
    print(f"✅ API Base: {api_base}")
    print()

    # Step 2: Test DNS/Network
    print("Step 2: Testing Network Connectivity")
    print("-" * 70)

    try:
        import socket
        import urllib.request

        # Test DNS resolution
        host = api_base.replace("https://", "").replace("http://", "").split("/")[0]
        print(f"Testing DNS resolution for: {host}")
        ip = socket.gethostbyname(host)
        print(f"✅ DNS resolved: {host} -> {ip}")

        # Test HTTPS connection
        print(f"Testing HTTPS connection to: {api_base}")
        try:
            with urllib.request.urlopen(f"{api_base}/models", timeout=5) as response:
                print(f"✅ HTTPS connection successful (status: {response.status})")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print(f"⚠️  HTTP 401 - Check API key validity")
            else:
                print(f"⚠️  HTTP {e.code}")
        except Exception as e:
            print(f"⚠️  Connection test: {type(e).__name__}: {str(e)}")

    except Exception as e:
        print(f"❌ Network error: {type(e).__name__}: {str(e)}")
        print("   Check firewall and internet connection")
        return False

    print()

    # Step 3: Test LangChain/OpenAI
    print("Step 3: Testing LangChain Integration")
    print("-" * 70)

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        print(f"Creating ChatOpenAI client...")
        llm = ChatOpenAI(
            api_key=api_key,
            model=model_name,
            temperature=0.7,
            timeout=30,
            max_retries=1,
        )
        print(f"✅ ChatOpenAI client created")

        print(f"Sending test message...")
        response = llm.invoke([HumanMessage(content="Say 'Connection successful!' and nothing else.")])
        print(f"✅ Response received: {response.content}")

        if "successful" in response.content.lower():
            print(f"✅ Connection successful!")
        else:
            print(f"⚠️  Unexpected response: {response.content}")

        print()

    except Exception as e:
        print(f"❌ LangChain error: {type(e).__name__}: {str(e)}")

        # Diagnose specific errors
        error_str = str(e).lower()
        if "authentication" in error_str or "invalid" in error_str:
            print("   → Issue: Invalid or expired API key")
            print("   Fix: Update OPENAI_API_KEY")
        elif "timeout" in error_str:
            print("   → Issue: Connection timeout")
            print("   Fix: Check internet connection or try again later")
        elif "rate" in error_str or "quota" in error_str:
            print("   → Issue: Rate limit or quota exceeded")
            print("   Fix: Wait a moment before retrying")
        elif "model" in error_str:
            print("   → Issue: Model not found or not available")
            print(f"   Fix: Check OPENAI_MODEL_NAME (current: {model_name})")
        else:
            print("   For more details, enable debug logging:")
            print("   export LOGLEVEL=DEBUG")

        return False

    # Step 4: Test Structured Output
    print("Step 4: Testing Structured Output")
    print("-" * 70)

    try:
        from pydantic import BaseModel
        from src.services.structured_output import get_structured_output

        class TestOutput(BaseModel):
            message: str
            success: bool

        print("Testing structured output with simple schema...")
        result = await get_structured_output(
            llm,
            [
                HumanMessage(
                    content='Respond with JSON: {"message": "test", "success": true}'
                )
            ],
            TestOutput,
            max_retries=1,
        )

        print(f"✅ Structured output successful")
        print(f"   Result: {result}")

    except Exception as e:
        print(f"❌ Structured output error: {type(e).__name__}: {str(e)}")
        return False

    print()
    print("=" * 70)
    print("✅ All tests passed! Your connection is working.")
    print("=" * 70)
    return True


async def main():
    """Main entry point."""
    try:
        success = await test_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
