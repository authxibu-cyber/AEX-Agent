# AEX Agent ☤

<p align="center">
  <b>The Sovereign, Self-Improving AI Agent Harness</b><br>
  <i>Built upon the pioneering architecture of Nous Research Hermes Agent and elevated by the GodEye Mandate.</i>
</p>

---

## Overview

**AEX Agent** is an autonomous, infrastructure-agnostic AI agent harness designed for persistent, long-horizon workflows. Unlike transient chatbot wrappers, AEX Agent treats the local filesystem as a filing cabinet: it remembers interactions across sessions in bounded persistent memory files, dynamically acquires new capabilities by writing its own executable skills, and operates seamlessly across native terminals, background cron schedules, and messaging gateways.

Elevated by the **GodEye Mandate**, AEX Agent embeds **Tier-3 deep architectural principles**:
- **Sovereign Cognitive Pulse:** Input-dependent selectivity gates ($\Delta_t, B_t, C_t$) and Kogge-Stone parallel associative scans ($O(L) \to O(\log L)$) for dynamic context compression.
- **Hardware-Aware Execution:** Native Tensor Core (BF16/TF32) audit and fused operators.
- **Closed Learning Loop:** Autonomous post-task knowledge distillation and automated skill synthesis conforming to the `agentskills.io` standard.

---

## Flagship Capabilities

| Feature | Description |
| :--- | :--- |
| **Interactive Terminal TUI** | Multiline editing via `prompt_toolkit`, slash-command autocomplete, live streaming Markdown with `rich`, collapsible `<thought>` / reasoning display, and real-time tool execution spinners. |
| **3-Layer Bounded Memory** | `MEMORY.md` (~2,200 char world/project facts) and `USER.md` (~1,375 char user traits) with automatic FIFO consolidation to maintain zero context bloat. |
| **FTS5 Cross-Session Recall** | SQLite with Write-Ahead Logging (WAL) and FTS5 BM25-ranked full-text search across all historical conversation turns. |
| **Autonomous Skill Creation** | Self-authoring skill loop (`/learn` and `learn_skill` tool) that writes YAML-frontmattered `SKILL.md` packages into `~/.ex/skills/`. |
| **Universal Model Support** | Native adapters for **Nous Portal** (Hermes 3 / Hermes 2 Pro), **OpenRouter**, **OpenAI**, **Anthropic**, **Gemini**, and **Local LLMs** (vLLM / Ollama). Switch on the fly with `aex model`. |
| **Multi-Channel Gateway** | High-performance FastAPI server running on port `8642` with OpenAI-compatible `/v1/chat/completions` (SSE streaming) plus Telegram, Discord, and Slack connectors. |
| **Embedded Cron Scheduler** | Unattended natural-language periodic automations (`schedule_cron`) with conversational memory injection so the agent recalls past background task outputs. |
| **Subagent Delegation** | Spawns parallel subagent instances (`delegate_task`) to collapse complex multi-stage tasks into zero-context-cost turns. |
| **Research Trajectories** | ShareGPT and Hermes-RL compatible trajectory logging (`~/.ex/trajectories/`) for agent post-training and RL fine-tuning. |

---

## Directory & Package Architecture

```
AEX-Agent/
├── pyproject.toml                 # Package definition & CLI entry points
├── setup.py                       # Setup installer
├── requirements.txt               # Core dependencies
├── aex_constants.py                # Environment & directory path resolver
├── AGENTS.md                      # Workspace & project guidelines
├── SOUL.md                        # Sovereign persona & cognitive stance
├── .env.example                   # Environment configuration template
├── aex_agent/
│   ├── agent/
│   │   ├── core.py                # EXAgent main loop & turn coordinator
│   │   ├── parser.py              # Resilient parser for OpenAI & Hermes XML tool calls
│   │   ├── selective_pulse.py     # GodEye Tier-3 cognitive selectivity gate (SSM scan)
│   │   ├── state.py               # Session state & turn telemetry
│   │   ├── subagent.py            # Isolated subagent worker spawner
│   │   └── trajectory.py          # ShareGPT trajectory recorder
│   ├── memory/
│   │   ├── persistent.py          # Bounded MEMORY.md & USER.md engine
│   │   ├── store.py               # SQLite + FTS5 full-text session storage (WAL mode)
│   │   └── context.py             # Hierarchical project discovery (AGENTS.md / SOUL.md)
│   ├── skills/
│   │   ├── manager.py             # agentskills.io YAML SKILL.md scanner
│   │   ├── learner.py             # Autonomous self-improving skill creator
│   │   └── builtin/               # Bundled skills (code-review, web-research, mlops-surgery)
│   ├── tools/
│   │   ├── base.py                # @tool decorator & function schema generator
│   │   ├── executor.py            # Async parallel execution pool & approval gates
│   │   ├── terminal.py            # Native PowerShell / POSIX shell execution
│   │   ├── filesystem.py          # Surgical file read, write, patch, find, list
│   │   ├── web.py                 # DuckDuckGo search & clean web page scraper
│   │   ├── memory_tools.py        # update_memory, update_user_model, session_search
│   │   ├── skill_tools.py         # learn_skill, list_skills, read_skill
│   │   ├── code_sandbox.py        # Isolated Python execution runner
│   │   ├── mcp_tool.py            # Model Context Protocol (MCP) client bridge
│   │   └── toolsets.py            # Toolset bundles (terminal, file, web, safe, all)
│   ├── providers/
│   │   ├── base.py                # Unified async streaming provider interface
│   │   ├── openai_provider.py     # OpenAI / OpenRouter / Nous Portal adapter
│   │   ├── anthropic_provider.py  # Anthropic Claude adapter
│   │   └── local_provider.py      # Ollama / vLLM local hardware-aware adapter
│   ├── gateway/
│   │   ├── server.py              # FastAPI OpenAI-compatible API server (:8642)
│   │   ├── scheduler.py           # Embedded non-blocking Cron scheduler
│   │   └── channels/              # Telegram, Discord, and Slack bridges
│   └── cli/
│       ├── main.py                # Command-line router (`aex`)
│       ├── tui.py                 # Rich interactive TUI with slash-autocomplete
│       ├── commands.py            # Authoritative slash-command registry
│       └── setup_wizard.py        # Interactive onboarding wizard
├── scripts/
│   ├── install.ps1                # Native Windows PowerShell installer
│   ├── install.sh                 # Linux/macOS/WSL2 installer
│   └── run_aex.bat                 # Windows quick launcher
└── tests/                         # Pytest test suite
```

---

## Installation & Setup

### 1. Windows Native (PowerShell)

Run PowerShell in the project directory:
```powershell
.\scripts\install.ps1
```
Or directly install via pip:
```bash
pip install -e .
```

### 2. Linux, macOS, WSL2

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

### 3. Environment Configuration

Copy `.env.example` to `.env` or set environment variables:
```bash
cp .env.example .env
```
Configure your primary API key (e.g. `OPENROUTER_API_KEY`, `NOUS_PORTAL_API_KEY`, or `OPENAI_API_KEY`).

---

## Quick Usage

### Start Interactive Chat Session
```bash
aex chat
```
or simply:
```bash
ex
```

### Switch Model & Provider
```bash
# View active model
aex model

# Switch model
aex model nousresearch/hermes-3-llama-3.1-8b --provider openrouter
```

### Start Gateway API Server & Cron Daemon
```bash
aex gateway --port 8642
```
Once launched, connect any OpenAI-compatible client or Open WebUI to `http://localhost:8642/v1`.

### Inspect & Manage Memory
```bash
aex memory
```

### List Skills Catalog
```bash
aex skills
```

---

## Slash Commands (Inside Chat TUI)

While inside the interactive chat interface, use standard slash commands:

- `/help` — List all registered slash commands.
- `/model [name]` — View or switch the active model on the fly.
- `/provider [name]` — Switch provider (`openrouter`, `nous_portal`, `openai`, `anthropic`, `ollama`, `vllm`).
- `/memory` — Inspect persistent `MEMORY.md` and `USER.md` content and character budgets.
- `/skills` — List all available skills and their trigger keywords.
- `/learn <name> <description>` — Author and register a new persistent skill.
- `/tools` — Inspect active tools and toolsets.
- `/sessions` — List past conversation sessions from SQLite.
- `/search <query>` — Execute an FTS5 full-text search across all past conversations.
- `/cron` — View active automated background tasks.
- `/export` — Export current conversation trajectory to ShareGPT format for model training.
- `/clear` — Clear the screen.

---

## License

MIT License. Designed and engineered for persistent, autonomous AI operations.
