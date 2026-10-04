from django.conf import settings
from groq import Groq
from openai import OpenAI
import json
from .models import AgentEvent
import time

groq_client = Groq(api_key=settings.GROQ_API_KEY)
openrouter_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)

def _trim_history(messages, max_history):
    """
    Keep the original prompt plus the last `max_history` messages, but never let
    the kept window start on an orphaned 'tool' message (its assistant tool_calls
    message would have been trimmed away, which providers reject with a 400).
    """
    if len(messages) <= max_history + 1:
        return messages
    tail = messages[-max_history:]
    while tail and tail[0].get("role") == "tool":
        tail = tail[1:]
    return [messages[0]] + tail

def _log(session_id, agent_name, event_type, content):
    if session_id is None:
        return
    try:
        AgentEvent.objects.create(
            session_id=session_id, agent_name=agent_name,
            event_type=event_type, content=str(content)[:5000],
        )
    except Exception as e:
        print(f"  [!] Failed to log event: {e}")


def _run_agent_loop(client, prompt, tools=None, tool_map=None, model="", max_steps=25,
                     max_history=10, max_output_tokens=2048,session_id=None,agent_name="agent"): # Helper fn denoted by underscore before fn name, not to be called from outside this file
    """
    Shared tool-calling loop used by both providers. Keeps only the last
    `max_history` messages (plus the original prompt) in context per call,
    to control input-token growth on long multi-step runs. `max_output_tokens`
    caps each individual response to avoid mid-generation truncation.
    """
    messages = [{"role": "user", "content": prompt}]
    empty_retries = 0
    consecutive_errors = 0

    _log(session_id, agent_name, "agent_started", f"Starting with target input.")

    for step in range(max_steps):
        trimmed = _trim_history(messages, max_history)

        try:
            response = client.chat.completions.create(
                model=model,
                messages=trimmed,
                tools=tools if tools else None,
                max_tokens=max_output_tokens,
            )
        except Exception as e:
            err = str(e).lower()
            if "tool_use_failed" in err or "failed_generation" in err or "malformed tool" in err:
                print(f"  [!] Malformed tool call at step {step}, nudging retry...")
                messages.append({
                    "role": "user",
                    "content": "Your last response had a malformed tool call. Retry using proper tool-calling format, one clear action at a time."
                })
                continue
            raise

        if not getattr(response, "choices", None):
            error_info = getattr(response, "error", None) or "No choices returned (provider error or rate limit)"
            err_str = str(error_info).lower()

            if "overloaded" in err_str or "rate limit" in err_str or "503" in err_str:
                _log(session_id, agent_name, "tool_result", f"Provider overloaded, retrying once: {error_info}")
                time.sleep(3)
                try:
                    response = client.chat.completions.create(
                        model=model, messages=trimmed,
                        tools=tools if tools else None, max_tokens=max_output_tokens,
                    )
                except Exception:
                    pass  # fall through to the check below with whatever we got (or didn't)

            if not getattr(response, "choices", None):
                error_info = getattr(response, "error", None) or "No choices returned (provider error or rate limit)"
                _log(session_id, agent_name, "agent_finished", f"Provider error: {error_info}")
                return f"Agent failed: provider returned no response ({error_info})"

        msg = response.choices[0].message

        # Empty turn (no text, no tool calls): don't treat it as a final answer.
        if not msg.tool_calls and not (msg.content or "").strip():
            empty_retries += 1
            print(f"  [!] Empty response at step {step} "
                  f"(finish_reason={response.choices[0].finish_reason}), attempt {empty_retries}")
            if empty_retries <= 2:
                messages.append({
                    "role": "user",
                    "content": "Your last response was empty. Give your final report now in the requested format, or continue with a tool call."
                })
                continue
            return msg.content or ""
        
        messages.append(msg.model_dump(exclude_none=True))

        if msg.content:
            preview = msg.content
            print(f"  [Step {step}] {preview}")

        if not msg.tool_calls:
            _log(session_id, agent_name, "agent_finished", msg.content)
            return msg.content

        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            try:
                func_args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError as e:
                func_args = None
                result = {"error": f"Invalid JSON in tool arguments: {e}"}

            _log(session_id, agent_name, "tool_call", f"{func_name}({_short(func_args)})")

            if func_args is not None:
                print(f"  [Step {step}] -> calling {func_name}({_short(func_args)})")
                if func_name not in (tool_map or {}):
                    result = {"error": f"Unknown tool '{func_name}'. Available: {list((tool_map or {}).keys())}"}
                else:
                    try:
                        result = tool_map[func_name](**func_args)
                    except Exception as e:
                        result = {"error": f"Tool '{func_name}' raised: {e}"}

            _log(session_id, agent_name, "tool_result", _short(result))
            print(f"  [Step {step}] <- result: {_short(result)}")

            if isinstance(result, dict) and "error" in result:
                consecutive_errors += 1
            else:
                consecutive_errors = 0

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

            if consecutive_errors >= 4:
                messages.append({
                    "role": "user",
                    "content": (
                        "You've had several consecutive tool errors in a row. Pause and assess: "
                        "is this approach working? If not, either try a genuinely different approach, "
                        "or stop here and clearly report that you're stuck/handing off, rather than "
                        "repeating similar code."
                    )
                })
                consecutive_errors = 0
    
    print(f"  [!] Max steps ({max_steps}) reached without a final answer.")
    _log(session_id, agent_name, "agent_finished", "Max steps reached without a final answer.")
    return "Max tool-call steps reached without a final answer."


def _short(obj, limit=800):
    """Compact one-line preview of a dict/string for clean terminal logs."""
    s = json.dumps(obj) if isinstance(obj, (dict, list)) else str(obj)
    return s[:limit] + ("..." if len(s) > limit else "")


def call_agent_qwen(prompt, tools=None, tool_map=None, model="qwen/qwen3.8-27b", max_steps=25,session_id=None, agent_name="agent"):
    """Groq-backed agent call. Kept as a fallback alongside OpenRouter."""
    return _run_agent_loop(groq_client, prompt, tools, tool_map, model, max_steps,session_id=session_id,agent_name=agent_name)


def call_agent_openrouter(prompt, tools=None, tool_map=None,
                           model="nvidia/nemotron-3-ultra-550b-a55b:free", max_steps=25,session_id=None, agent_name="agent"):
    """OpenRouter-backed agent call -- current default provider."""
    return _run_agent_loop(openrouter_client, prompt, tools, tool_map, model, max_steps,session_id=session_id,agent_name=agent_name)