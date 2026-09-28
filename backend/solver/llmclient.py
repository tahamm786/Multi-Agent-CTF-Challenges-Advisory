from google import genai
from google.genai import types
from django.conf import settings
from .tools import fetch_page, check_path, extract_links, TOOL_SCHEMAS, TOOL_MAP
from groq import Groq
from django.conf import settings
import json
from openai import OpenAI
 
groq_client = Groq(api_key=settings.GROQ_API_KEY)

openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)

def call_agent_openrouter(prompt, tools=None, tool_map=None, model="nvidia/nemotron-3-ultra-550b-a55b:free", max_steps=25):
    messages = [{"role": "user", "content": prompt}]
    MAX_HISTORY = 10

    for step in range(max_steps):
        trimmed = [messages[0]] + messages[-MAX_HISTORY:] if len(messages) > MAX_HISTORY + 1 else messages
        try:
            response = openrouter_client.chat.completions.create(
                model=model,
                messages=trimmed,
                tools=tools if tools else None,
                max_tokens=2048,
            )
        except Exception as e:
            if "tool_use_failed" in str(e) or "tool" in str(e).lower():
                messages.append({"role": "user", "content": "Your last response had a malformed tool call. Retry using proper tool-calling format."})
                continue
            raise

        msg = response.choices[0].message
        print(f"--- Step {step} ---")
        print("Content:", msg.content)
        print("Tool calls:", msg.tool_calls)

        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            return msg.content

        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            result = tool_map[func_name](**func_args)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return "Max tool-call steps reached without a final answer."

def call_agent(prompt: str, tools: list = None, tool_map: dict = None, model: str = "qwen/qwen3.8-27b",max_steps=25):
    """
    tools: list of OpenAI-format tool schemas (dicts)
    tool_map: dict mapping tool name (str) -> actual Python function to call
    """
    messages = [{"role": "user", "content": prompt}]

    MAX_HISTORY=10


    for step in range(max_steps): 
        if len(messages) > MAX_HISTORY + 1:
                messages = [messages[0]] + messages[-MAX_HISTORY:]

        try:
            response = groq_client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools if tools else None,
                max_tokens=2048,
            )

        except Exception as e:
            if "tool_use_failed" in str(e):
                # Model malformed a tool call -- nudge it and retry this step
                messages.append({
                    "role": "user",
                    "content": "Your last response had a malformed tool call. Please retry using the proper tool-calling format, one clear action at a time."
                })
                continue
            raise  # re-raise anything else (like real rate limits) so you still see it
    
        msg = response.choices[0].message
        print(f"--- Step {step} ---")
        print("Content:", msg.content)
        print("Tool calls:", msg.tool_calls)

        messages.append(msg)

        if not msg.tool_calls:
            return msg.content  # model is done, no more tools requested

        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            print(f"Calling {func_name} with {func_args}")
            result = tool_map[func_name](**func_args)
            print(f"Result: {str(result)[:300]}")
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return "Max tool-call steps reached without a final answer."