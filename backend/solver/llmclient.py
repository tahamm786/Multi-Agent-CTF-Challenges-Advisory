from google import genai
from google.genai import types
from django.conf import settings
from .tools import fetch_page, check_path, extract_links, TOOL_SCHEMAS, TOOL_MAP
from groq import Groq
from django.conf import settings
import json
 
groq_client = Groq(api_key=settings.GROQ_API_KEY)

def call_agent(prompt: str, tools: list = None, tool_map: dict = None, model: str = "qwen/qwen3.8-27b",max_steps=25):
    """
    tools: list of OpenAI-format tool schemas (dicts)
    tool_map: dict mapping tool name (str) -> actual Python function to call
    """
    messages = [{"role": "user", "content": prompt}]

    for step in range(max_steps): 
        response = groq_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools if tools else None,
        )
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