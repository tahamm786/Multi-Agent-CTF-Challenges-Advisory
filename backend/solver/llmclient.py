from django.conf import settings
from groq import Groq
from openai import OpenAI
import json

groq_client = Groq(api_key=settings.GROQ_API_KEY)
openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)


def _run_agent_loop(client, prompt, tools=None, tool_map=None, model="", max_steps=25,
                     max_history=10, max_output_tokens=2048): # Helper fn denoted by underscore before fn name, not to be called from outside this file
    """
    Shared tool-calling loop used by both providers. Keeps only the last
    `max_history` messages (plus the original prompt) in context per call,
    to control input-token growth on long multi-step runs. `max_output_tokens`
    caps each individual response to avoid mid-generation truncation.
    """
    messages = [{"role": "user", "content": prompt}]

    for step in range(max_steps):
        trimmed = [messages[0]] + messages[-max_history:] if len(messages) > max_history + 1 else messages

        try:
            response = client.chat.completions.create(
                model=model,
                messages=trimmed,
                tools=tools if tools else None,
                max_tokens=max_output_tokens,
            )
        except Exception as e:
            if "tool_use_failed" in str(e) or "tool" in str(e).lower():
                print(f"  [!] Malformed tool call at step {step}, nudging retry...")
                messages.append({
                    "role": "user",
                    "content": "Your last response had a malformed tool call. Retry using proper tool-calling format, one clear action at a time."
                })
                continue
            raise

        msg = response.choices[0].message
        messages.append(msg.model_dump(exclude_none=True))

        if msg.content:
            preview = msg.content
            print(f"  [Step {step}] {preview}")

        if not msg.tool_calls:
            return msg.content

        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            print(f"  [Step {step}] -> calling {func_name}({_short(func_args)})")

            result = tool_map[func_name](**func_args)
            result_preview = _short(result)
            print(f"  [Step {step}] <- result: {result_preview}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    print(f"  [!] Max steps ({max_steps}) reached without a final answer.")
    return "Max tool-call steps reached without a final answer."


def _short(obj, limit=400):
    """Compact one-line preview of a dict/string for clean terminal logs."""
    s = json.dumps(obj) if isinstance(obj, (dict, list)) else str(obj)
    return s[:limit] + ("..." if len(s) > limit else "")


def call_agent(prompt, tools=None, tool_map=None, model="qwen/qwen3.8-27b", max_steps=25):
    """Groq-backed agent call. Kept as a fallback alongside OpenRouter."""
    return _run_agent_loop(groq_client, prompt, tools, tool_map, model, max_steps)


def call_agent_openrouter(prompt, tools=None, tool_map=None,
                           model="nvidia/nemotron-3-ultra-550b-a55b:free", max_steps=25):
    """OpenRouter-backed agent call -- current default provider."""
    return _run_agent_loop(openrouter_client, prompt, tools, tool_map, model, max_steps)