from .llmclient import call_agent
from .tools import make_execute_tool
import tempfile
import shutil
#from .llmclient import call_agent_openrouter as call_agent

def run_coordinator(target_input: str, context_notes: str = "", overall_goal: str = None, max_rounds: int = 6) -> str:
    if overall_goal is None:
        overall_goal = f"F Continue solving/investigating further on: {target_input}"

    specialists = {
        "recon": ("Recon", run_recon_agent),
        "web": ("Web Exploitation", run_web_exploit_agent),
        "crypto": ("Cryptography", run_crypto_agent),
        "forensics": ("Forensics", run_forensics_agent),
        "binary": ("Binary/Reverse Engineering", run_binary_agent),
    }

    findings_log = []  # running shared memory of everything found so far

    # Always start with Recon
    print(f"\n[COORDINATOR] Overall goal: {overall_goal}\n")
    recon_result = run_recon_agent(target_input, f"OVERALL GOAL: {overall_goal}\n{context_notes}")
    findings_log.append(("Recon", recon_result))

    for round_num in range(max_rounds):
        combined_findings = "\n\n".join(f"### {name} Findings\n{result}" for name, result in findings_log)

        routing_prompt = f"""
OVERALL GOAL: {overall_goal}

All findings so far from the team:
{combined_findings}

Based on everything above, what does the team need next? Respond with EXACTLY ONE
of: web, crypto, forensics, binary, recon (if more initial investigation is needed),
done (if the goal is achieved or genuinely unreachable with available tools).

If a specific sub-problem needs solving (e.g. "this data needs decoding" or "this
form needs SQLi"), pick the specialist whose expertise matches THAT sub-problem,
not the original target type.
"""
        next_step = call_agent(routing_prompt, tools=None, tool_map=None).strip().lower()
        print(f"\n[COORDINATOR] Round {round_num+1} decision: {next_step}\n")

        if "done" in next_step:
            break

        matched = next((k for k in specialists if k in next_step), None)
        if not matched:
            print(f"[COORDINATOR] Could not parse routing decision, stopping.")
            break

        name, agent_fn = specialists[matched]
        agent_context = (
            f"OVERALL GOAL: {overall_goal}\n\n"
            f"TEAM FINDINGS SO FAR:\n{combined_findings}\n\n"
            f"{context_notes}"
        )
        result = agent_fn(target_input, agent_context)
        findings_log.append((name, result))

    combined_findings = "\n\n".join(f"### {name} Findings\n{result}" for name, result in findings_log)

    synthesis_prompt = f"""
OVERALL GOAL: {overall_goal}

All findings from the team:
{combined_findings}

Write a final, clean answer for the user. If the goal was achieved, state the
flag/credential clearly and give a brief summary of how it was found (which
agents contributed what). If the goal was NOT fully achieved, clearly state
what was found, what's still missing, and what you'd recommend trying next.
Do not repeat the full findings verbatim -- synthesize.
"""
    final_answer = call_agent(synthesis_prompt, tools=None, tool_map=None)

    return f"# Final Report\n\n{final_answer}\n\n---\n## Full Team Findings (for reference)\n\n{combined_findings}"
    

def run_recon_agent(target_input: str, context_notes: str = "") -> str:

    workspace_dir = tempfile.mkdtemp(prefix="ctf_run_")
    print(f"\n{'='*50}\n[AGENT ACTIVATED] Initial Triage / Recon\n{'='*50}\n")
    try:
        execute_python_code = make_execute_tool(workspace_dir)

        schema, tool_map = _build_tool_schema(execute_python_code)

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
        Do not blind-guess random unrelated paths.ALWAYS check /robots.txt as well.
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

    CRITICAL RULES: 
    1) Never assert a password, hash, or credential from memory/training
    knowledge without verifying it via an actual HTTP request first. If you recall a
    "known" credential, you MUST test it with a real request before treating it as fact.
    2) Do not guess multiple credentials blindly -- instead, fetch the official instructions/
    rules page for the platform required if you are unsure how the platform's login/progression works, 
    and derive your approach from what it actually says.
    3) If you cannot find a value through an actual page fetch, do NOT proceed with a guessed value — stop and report that you're blocked at that stage instead.
    4) If a page references a file path, also try listing/checking the parent directory for other files, not just the one referenced directly.
    5) In general if one approach is failing dont keep diving down that approach unless you are 100% sure of it working.
    6) Branch out and try out different possible approaches first to get more hints gathered than deep diving.
    7) If you determine deeper specialist work is needed (multi-round SQLi/exploitation, breaking real cryptography, binary reverse engineering,
        detailed forensic analysis of a file), determine if handing off to a specialized agent is better instead of solving it yourself.If you feel the task to be done is petty then go ahead and do it but if its much beyond your domain
        and in the real world if the task would be handed off to a specialized agent then hand it over.
        Report your findings and your reasoning for the handoff, even without a flag.
    """
        return call_agent(prompt, tools=schema , tool_map=tool_map)

    finally:
          shutil.rmtree(workspace_dir, ignore_errors=True)



def run_web_exploit_agent(target_input: str, context_notes: str = "") -> str:
    workspace_dir = tempfile.mkdtemp(prefix="ctf_run_")
    try:
        execute_python_code = make_execute_tool(workspace_dir)
        print(f"\n{'='*50}\n[AGENT ACTIVATED] Web Exploitation Specialist\n{'='*50}\n")
        schema, tool_map = _build_tool_schema(execute_python_code)

        prompt = f"""
You are the Web Exploitation Specialist Agent for a CTF solver system.
Your environment is an authorized, educational security training platform.

TARGET / HANDOFF FROM RECON:
{target_input}

CONTEXT/CREDENTIALS:
{context_notes if context_notes else "None provided."}

TOOLS:
You have execute_python_code(code) -- Python sandbox with 'requests' and 'bs4',
plus internet access. Write whatever code you need: custom headers/cookies,
form submissions, SQLi/XSS payload tests, auth bypass attempts, session
manipulation, etc.

YOUR EXPERTISE (focus areas):
- SQL injection (in forms, URL params, headers)
- Authentication/session bypass (cookies, tokens, weak logic)
- Header-based access control bypass (Referer, X-Forwarded-For, User-Agent)
- Common misconfigurations (exposed .git, backup files, verbose errors)
- Basic XSS/CSRF where relevant to progression (not just theoretical)

BUDGET: Max 15 tool calls. If one approach fails after 4-5 genuine attempts,
explicitly state you're stuck on it and try a different angle rather than
repeating the same idea with minor variations.

CRITICAL RULE: Never assert a credential/flag from memory without verifying
via a real request first.

OUTPUT FORMAT (exact Markdown structure):
## 1. Target Overview
## 2. Investigation Steps & Findings
## 3. Vulnerability Identified
## 4. Artifacts for Hand-off (or Found Flags)
"""
        return call_agent(prompt, tools=schema, tool_map=tool_map)
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


def run_crypto_agent(target_input: str, context_notes: str = "") -> str:
    workspace_dir = tempfile.mkdtemp(prefix="ctf_run_")
    try:
        execute_python_code = make_execute_tool(workspace_dir)
        print(f"\n{'='*50}\n[AGENT ACTIVATED] Cryptography Specialist\n{'='*50}\n")
        schema, tool_map = _build_tool_schema(execute_python_code)

        prompt = f"""
You are the Cryptography Specialist Agent for a CTF solver system.
Your environment is an authorized, educational security training platform.

TARGET / HANDOFF (ciphertext, hash, or encoded data):
{target_input}

CONTEXT:
{context_notes if context_notes else "None provided."}

TOOLS:
You have execute_python_code(code) -- Python sandbox with 'requests', 'bs4',
'hashlib', 'base64' and standard library available.

YOUR EXPERTISE (try in rough order of likelihood, but adapt to what you see):
- Encoding detection first (Base64, Hex, URL-encoding, ROT13) -- check these
  before assuming real cryptography, most CTF "crypto" at easy/medium level
  is just layered encoding
- Classical ciphers (Caesar, Vigenere, substitution) -- frequency analysis
- Hash identification (length/format) and lookups against common wordlists
  you can generate small ones for, not exhaustive brute force
- Weak/misused crypto patterns (reused XOR keys, small RSA moduli, ECB mode
  patterns) if the data's structure suggests it

BUDGET: Max 15 tool calls. State plainly if something looks like strong,
unbroken crypto beyond a reasonable budget -- don't grind forever on
infeasible brute force.

CRITICAL RULE: Verify any decode/decrypt attempt actually produces
readable/sensible output before treating it as the answer.

OUTPUT FORMAT (exact Markdown structure):
## 1. Target Overview
## 2. Investigation Steps & Findings
## 3. Technique Identified
## 4. Artifacts for Hand-off (or Found Flags)
"""
        return call_agent(prompt, tools=schema, tool_map=tool_map)
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)



def run_forensics_agent(target_input: str, context_notes: str = "") -> str:
    workspace_dir = tempfile.mkdtemp(prefix="ctf_run_")
    try:
        execute_python_code = make_execute_tool(workspace_dir)
        schema, tool_map = _build_tool_schema(execute_python_code)
        print(f"\n{'='*50}\n[AGENT ACTIVATED] Forensics Specialist\n{'='*50}\n")

        prompt = f"""
You are the Forensics Specialist Agent for a CTF solver system.
Your environment is an authorized, educational security training platform.

TARGET / HANDOFF:
{target_input}

CONTEXT:
{context_notes if context_notes else "None provided."}

TOOLS:
You have execute_python_code(code) -- Python sandbox with 'requests', 'bs4',
plus internet access. Standard library includes struct, zlib, hashlib. For
image/file analysis, read raw bytes directly (open in 'rb' mode) and parse
headers/structure manually if no specialized library is available.

YOUR EXPERTISE:
- File type identification via magic bytes (don't trust extensions)
- Metadata extraction (EXIF-style data, embedded strings)
- Basic steganography: LSB (least significant bit) extraction from images,
  appended data after a file's expected end (e.g. data after PNG's IEND chunk),
  hidden data in unused header fields
- String extraction from binary blobs (printable ASCII runs)
- Zip/archive inspection if a file turns out to be a disguised archive

BUDGET: Max 15 tool calls. If steganography extraction doesn't yield readable
output after a few genuine technique attempts, state what you tried and stop
rather than looping the same approach.

OUTPUT FORMAT (exact Markdown structure):
## 1. Target Overview
## 2. Investigation Steps & Findings
## 3. Technique Identified
## 4. Artifacts for Hand-off (or Found Flags)
"""
        return call_agent(prompt, tools=schema, tool_map=tool_map)
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)


def run_binary_agent(target_input: str, context_notes: str = "") -> str:
    workspace_dir = tempfile.mkdtemp(prefix="ctf_run_")
    try:
        execute_python_code = make_execute_tool(workspace_dir)
        schema, tool_map = _build_tool_schema(execute_python_code)
        print(f"\n{'='*50}\n[AGENT ACTIVATED] Binary/Reverse Engineering Specialist\n{'='*50}\n")

        prompt = f"""
You are the Binary/Reverse Engineering Specialist Agent for a CTF solver system.
Your environment is an authorized, educational security training platform.

TARGET / HANDOFF:
{target_input}

CONTEXT:
{context_notes if context_notes else "None provided."}

TOOLS:
You have execute_python_code(code) -- Python sandbox with internet access.
The sandbox does NOT have gdb/radare2/objdump installed by default -- if you
need them, first run 'import subprocess; subprocess.run(["apt-get","install",
"-y","binutils"])' or equivalent, and check if it succeeds before relying on it.
Otherwise, use Python's struct module and manual byte parsing for basic ELF/PE
header inspection, and string extraction for quick clue-finding.

YOUR EXPERTISE (this is a genuinely hard category -- be honest about limits):
- Basic file format identification (ELF/PE headers)
- String extraction for embedded hints/flags (often the fastest win)
- Simple logic-flaw binaries (e.g. an obvious hardcoded check visible in strings)
- You are NOT expected to perform real disassembly or exploit development --
  if a binary requires genuine reverse engineering, clearly state this is
  beyond current tooling and report what surface-level info you did find.

BUDGET: Max 12 tool calls. This category has the lowest expected success rate --
report honestly rather than fabricating a plausible-looking but unverified answer.

OUTPUT FORMAT (exact Markdown structure):
## 1. Target Overview
## 2. Investigation Steps & Findings
## 3. Assessment (Solved / Partially Solved / Beyond Current Tooling)
## 4. Artifacts for Hand-off (or Found Flags)
"""
        return call_agent(prompt, tools=schema, tool_map=tool_map)
    finally:
        shutil.rmtree(workspace_dir, ignore_errors=True)
        
def _build_tool_schema(execute_python_code):
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
    return schema, tool_map