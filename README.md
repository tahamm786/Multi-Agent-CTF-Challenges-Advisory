# Sentinel — Multi-Agent CTF Solver

An AI-assisted CTF (Capture The Flag) companion. You give it a target — a URL, a hash, a ciphertext — and a team of specialist LLM agents investigates it: fetching pages, running code in sandboxed Docker containers, chaining discovered credentials, and reporting findings back through a live event feed.

This is a recon/triage assistant, not a guaranteed autopilot: agents investigate, try reasonable techniques, and report what they found and where they got stuck — same as a junior teammate would.

## Live deployment

**http://15.252.169.76**

Hosted on an AWS EC2 instance that's billed hourly, so it isn't guaranteed to be running at all times — if the link doesn't respond, the instance is likely stopped to save cost. Reach out and I can spin it back up on request, or run the project locally using the setup instructions below.

---

## A brief primer on agentic AI

This project is a hands-on exploration of the **agentic AI** pattern: instead of a single prompt → single response, an LLM is given a **goal**, a set of **tools** it can call, and run in a **loop** where it decides each step what to do next — call a tool, inspect the result, and either continue or produce a final answer.

The core loop (implemented here in `llmclient.py`) looks like:

```
while not done:
    model decides: call a tool, or respond with a final answer
    if tool call: execute it, feed the result back into the conversation
    if final answer: stop
```

Key ideas this project puts into practice:
- **Tool use / function calling** — the model doesn't just generate text, it can invoke real functions (here, a Python code-execution sandbox) and reason over their output.
- **Multi-agent orchestration** — rather than one generalist agent, specialized agents (Recon, Web Exploitation, Cryptography, Forensics, Binary) each handle a narrower domain, with a Coordinator agent that routes work between them based on findings so far.
- **Shared state / handoff** — each agent's findings are passed to the next, so the team builds on prior work rather than starting cold each time.
- **Bounded autonomy** — every agent runs with a hard tool-call budget and explicit instructions to report "stuck" rather than loop indefinitely, which matters a lot once an LLM is making real decisions with real side effects (network requests, code execution).

This hand-rolled orchestration loop was a deliberate first step before adopting a dedicated agent framework — **LangGraph** is the next planned iteration, to move from a custom state/routing loop to a graph-based agent framework with built-in state management, cycles, and more structured multi-agent coordination.

---

## How it works, end to end

```
React frontend (Sentinel UI)
        │  REST + SSE, token-authenticated
        ▼
Django + DRF backend
        │
        ├── Coordinator agent — classifies the target, decides which
        │   specialist to route to, synthesizes a final report
        │
        ├── Recon / Web Exploit / Crypto / Forensics / Binary agents
        │   — each gets one tool: execute_python_code
        │
        └── execute_python_code → spins up a disposable Docker
            container (image: ctf-sandbox) with `requests` + `bs4`
            pre-installed and internet access. Agent-written Python
            runs inside it; the container is destroyed after.
```

Every tool call, tool result, and handoff decision is logged to the database (`AgentEvent`) and streamed to the frontend live via Server-Sent Events, so you watch the agents work in real time instead of waiting for a final answer.

### The agent team

| Agent | Role |
|---|---|
| **Coordinator** | First classifies whether the input is a plausible CTF target at all. Always runs Recon first, then reads all findings so far and decides which specialist to route to next, round by round, until it decides the goal is met or unreachable. |
| **Recon** | Initial triage — identifies whether the target is web/file/ciphertext, fetches pages, checks `robots.txt`, follows obvious clues. |
| **Web Exploitation** | SQLi, auth/session bypass, header-based bypass, common misconfigurations (exposed `.git`, backups). |
| **Cryptography** | Encoding detection (base64/hex/ROT13), classical ciphers, hash identification, weak crypto patterns. |
| **Forensics** | File-type/magic-byte identification, steganography (LSB, appended data), string extraction. |
| **Binary/Reverse Engineering** | File format inspection, string extraction for hardcoded clues — explicitly **not** expected to do real disassembly; this agent is honest about that limit. |

Each specialist works from the same single tool, `execute_python_code`, with a budget of 12–25 tool calls depending on the agent, and is instructed to hand off rather than grind forever on something outside its expertise.

---

## Tech stack

**Backend**
- **Django + Django REST Framework** — core API, ORM, auth
- **PostgreSQL** — primary database (sessions, event logs, allowlist)
- **Token-based authentication** (DRF `TokenAuthentication`) with per-user ownership scoping and rate limiting
- **Server-Sent Events (SSE)** — live streaming of agent activity to the frontend without polling
- **Docker SDK for Python** — programmatic sandbox container lifecycle management
- **OpenRouter API** (OpenAI-compatible client) — LLM backend for agent tool-calling; Groq supported as an alternate provider

**Frontend**
- **React + Vite**
- **axios** — API client with token-attach interceptor
- **Tailwind-style utility CSS**

**Infrastructure / Deployment**
- **AWS EC2** (Ubuntu) — application host
- **nginx** — reverse proxy, HTTPS termination, static file serving, SSE-aware proxy config
- **Gunicorn** — WSGI application server, managed via **systemd**
- **Docker** — isolated, resource-capped sandbox execution environment for agent-run code
- **Certbot / Let's Encrypt** — TLS

**Sandbox environment**
- A custom Docker image (`ctf-sandbox`, Python 3.11-slim + `requests`/`beautifulsoup4`) spun up fresh per tool call, network-enabled, resource-capped (256MB RAM, 1 CPU core, 30s timeout), and destroyed after each run.

---

## Project layout

```
backend/
  config/            Django project settings, root urls.py, wsgi/asgi
  solver/
    models.py        SolveSession, AgentEvent, AllowedTargetDomain
    views.py         REST endpoints + SSE stream + auth (register/login)
    agents.py        The five specialist agents + Coordinator orchestration
    llmclient.py      Shared tool-calling loop, used by all agents (OpenRouter)
    tools.py         execute_python_code + the Docker sandbox + network guard
    allowlist.py     Target-domain allowlist enforcement
    serializer.py    DRF serializers
    admin.py         Django admin registrations
  sandbox/
    Dockerfile       Defines the ctf-sandbox image (python:3.11-slim + requests/bs4)
frontend/
  src/
    AuthForm.jsx, Sidebar.jsx, NewSessionForm.jsx, EventFeed.jsx, StatusBadge.jsx
    api/client.js    axios wrapper, token auth, SSE connection
```

---

## Setting it up locally

```bash
# backend
cd backend
python3 -m venv agent
source agent/bin/activate   # or agent\Scripts\activate on Windows
pip install -r requirements.txt

# .env (create this file, never commit it)
GROQ_API_KEY=...
OPENROUTER_API_KEY=...
SECRET_KEY=...
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
CSRF_TRUSTED_ORIGINS=http://localhost:5173
DB_NAME=... DB_USER=... DB_PASSWORD=... DB_HOST=localhost DB_PORT=5432

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# build the sandbox image (one-time, needed before any session will work)
cd backend/sandbox
docker build -t ctf-sandbox .

# frontend
cd frontend
npm install
npm run dev
```

Seed the target allowlist (see below) via Django admin or shell before running real sessions.

## Using it

1. Register an account (or log in).
2. **New session** → enter a target (URL, hash, ciphertext) and optional context notes / overall goal.
3. Watch the event feed — each agent's tool calls and results stream in live.
4. The session ends in `solved`, `failed`, or `rejected` (non-CTF input, e.g. casual conversation).

---

## Security model — what's actually enforced

This matters more than usual for this project, because the Web Exploitation agent genuinely attempts SQLi, auth bypass, and similar techniques against whatever target it's given, from a container with real internet access.

- **Auth**: token-based (DRF `TokenAuthentication`). Register/login issue a token; every API call (including the SSE stream, via a `?token=` query param since `EventSource` can't set headers) requires it.
- **Ownership scoping**: a user only ever sees their own sessions.
- **Rate limiting**: session creation is throttled (5/hour per user).
- **Target allowlist**: before a session starts, if `target_input` looks like a URL, its host must match an entry in `AllowedTargetDomain` (managed via Django admin, no redeploy needed to add one). Non-URL inputs (ciphertext, hashes) skip this check — they can't be a live exploitation target.
- **Sandbox network guard**: every `execute_python_code` run has a small snippet prepended that monkey-patches Python's `requests` library to check the same allowlist, so an agent can't bypass the allowlist by fetching a URL it discovered mid-investigation rather than the one submitted — only `target_input` is checked otherwise.
- **Sandbox resource limits**: each container is capped at 256MB RAM, 1 CPU core, and a 30-second hard execution timeout, and is destroyed after each call.

### Known limitation of the network guard

The guard patches `requests.Session.request`. If agent-generated code uses `urllib.request`, raw sockets, or shells out to `curl`/`wget` via `subprocess` instead of `requests`, the guard **does not catch it**. A stronger (but more involved) fix would be Docker/iptables-level egress filtering on the sandbox's network, which isn't implemented yet.

---

## Engineering notes

A few non-obvious issues surfaced and were resolved during development, worth knowing if you're extending this:

- Session ownership is enforced on the SSE stream endpoint as well as the REST endpoints, since `EventSource` can't carry standard auth headers and needs its own token-ownership check.
- Postgres 15+ changed default schema privileges, which affects first-time `migrate` in a fresh production database — the app's DB user needs explicit schema ownership.
- The Coordinator's routing logic and per-agent stopping conditions are an active area of refinement — multi-agent handoffs don't always preserve full context efficiently yet.
- Background agent runs currently execute in-process (Python threads) rather than via a durable task queue, so they don't survive an application restart mid-run. Migrating this to Celery or a similar queue is a natural next step.

---

## Limitations

- **Not fully autonomous.** Results depend on the underlying LLM's reliability across long multi-step tool-calling chains — this is a recon/triage assistant, not a guaranteed solver.
- **Single-instance deployment.** Runs on one EC2 instance with no auto-scaling or load balancing — built for personal/demo use, not concurrent production traffic.
- **In-progress durability and orchestration work.** Background sessions and multi-agent handoff efficiency are areas of active improvement (see Engineering notes above).
- **No automated test suite yet.**
- **Moving to LangGraph next** to replace the current hand-rolled orchestration loop with a more structured, graph-based agent framework — see the Agentic AI primer above.

---

## Authorization note

The Web Exploitation agent performs real exploitation attempts (SQLi, auth bypass, etc.) against whatever target it's given. **Only point this at targets you are authorized to test** — public CTF/wargame platforms designed for this (OverTheWire, picoCTF, PortSwigger Web Security Academy, vendor-hosted vulnerable demo apps like `testphp.vulnweb.com`), your own infrastructure, or a third party's system with their explicit, informed, written permission. The allowlist exists specifically to make this the default, enforced behavior rather than something that depends on remembering to check every time.