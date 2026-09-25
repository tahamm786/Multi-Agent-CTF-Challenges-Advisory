from .llmclient import call_agent
from .tools import make_execute_tool
import tempfile
import shutil

def run_recon_agent(target_input: str, context_notes: str = "") -> str:

    workspace_dir = tempfile.mkdtemp(prefix="ctf_run_")
    try:
        execute_python_code = make_execute_tool(workspace_dir)

        schema = [{
            "type": "function",
            "function": {
                "name": "execute_python_code",
                "description": execute_python_code.__doc__,
                "parameters": {
                    "type": "object",
                    "properties": {"code": {"type": "string", "description": "Python code to execute"}},
                    "required": ["code"],
                },
            },
        }]
        tool_map = {"execute_python_code": execute_python_code}

        prompt = f"""
    You are the Initial Triage and Reconnaissance Agent for a CTF solver system.
    Your environment is an authorized, educational security training platform
    (e.g. OverTheWire Natas or similar wargames).

    TARGET INPUT:
    {target_input}

    CONTEXT/CREDENTIALS:
    {context_notes if context_notes else "None provided -- if the target requires auth you don't have, reason about whether this platform requires solving earlier linked stages first to obtain it, and if so, work through them in sequence, carrying forward each discovered credential, until you reach the requested target."}

    TOOLS:
    You have one tool: execute_python_code(code). It runs Python in an isolated sandbox
    with 'requests' and 'bs4' pre-installed, plus internet access. Use it to fetch pages,
    inspect headers/cookies, set custom headers, parse HTML, decode/hash data, or write
    any other logic the target requires. Read errors and iterate if something fails.

    YOUR OBJECTIVE:
    Perform reconnaissance on the TARGET INPUT. You have a maximum budget of 25 tool calls
    total (including any prerequisite stages). You are NOT expected to solve complex crypto
    or reverse engineering, but you MUST exhaust reasonable follow-ups on obvious clues.

    STANDARD OPERATING PROCEDURE (SOP):
    1. INPUT CLASSIFICATION: Determine if the input is a Web URL, a File/Image, or a Text/Ciphertext blob.
    2. RECONNAISSANCE EXECUTION:
      - IF WEB: Fetch the main page, analyze HTML source/comments/headers. Follow up on
        logically deduced clues (mentioned paths, hinted files, required headers/cookies).
        Do not blind-guess random unrelated paths.
      - IF FILE/IMAGE: Extract metadata, check magic bytes, run string extraction, look for stego.
      - IF TEXT/CIPHER: Try frequency analysis, common encodings (Base64/Hex), identify hash formats.
    3. TRIAGE & HAND-OFF: Once you find the flag, or exhaust your budget, stop and report.

    OUTPUT FORMAT (exact Markdown structure):

    ## 1. Target Overview
    [Brief description of what the target is]

    ## 2. Investigation Steps & Findings
    [What you ran, what clues you found, how you followed up]

    ## 3. Suspected Category
    [Web Security, Cryptography, Forensics, Reverse Engineering, Pwn/Binary Exploitation, OSINT]

    ## 4. Artifacts for Hand-off (or Found Flags)
    [Exact flag if found, OR specific variables/files/hashes/code the next agent needs]

    CRITICAL RULE: Never assert a password, hash, or credential from memory/training
    knowledge without verifying it via an actual HTTP request first. If you recall a
    "known" credential, you MUST test it with a real request before treating it as fact.
    Do not guess multiple credentials blindly -- instead, fetch the official instructions/
    rules page for the platform required if you are unsure how the platform's login/progression works, 
    and derive your approach from what it actually says.
    If a page references a file path, also try listing/checking the parent directory for other files, not just the one referenced directly.
    In general if one approach is failing dont keep diving down that approach unless you are 100% sure of it working.
    Branch out and try out different possible approaches first to get more hints gathered than deep diving.
    """
        return call_agent(prompt, tools=schema , tool_map=tool_map)

    finally:
          shutil.rmtree(workspace_dir, ignore_errors=True)