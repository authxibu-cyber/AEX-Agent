# Merlin Agent ☤

<p align="center">
  <b>The Sovereign, Self-Improving AI Agent Harness</b><br>
  <i>Built upon the pioneering architecture of Nous Research Hermes Agent and elevated by the GodEye Mandate.</i>
</p>

---

## Overview

**Merlin Agent** is an autonomous, infrastructure-agnostic AI agent harness designed for persistent, long-horizon workflows. Unlike transient chatbot wrappers, Merlin Agent treats the local filesystem as a filing cabinet: it remembers interactions across sessions in bounded persistent memory files, dynamically acquires new capabilities by writing its own executable skills, and operates seamlessly across native terminals, background cron schedules, and messaging gateways.

Elevated by the **GodEye Mandate**, Merlin Agent embeds **Tier-3 deep architectural principles**:
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
| **Universal Model Support** | Native adapters for **Nous Portal** (Hermes 3 / Hermes 2 Pro), **OpenRouter**, **OpenAI**, **Anthropic**, **Gemini**, and **Local LLMs** (vLLM / Ollama). Switch on the fly with `merlin model`. |
| **Multi-Channel Gateway** | High-performance FastAPI server running on port `8642` with OpenAI-compatible `/v1/chat/completions` (SSE streaming) plus Telegram, Discord, and Slack connectors. |
| **Embedded Cron Scheduler** | Unattended natural-language periodic automations (`schedule_cron`) with conversational memory injection so the agent recalls past background task outputs. |
| **Subagent Delegation** | Spawns parallel subagent instances (`delegate_task`) to collapse complex multi-stage tasks into zero-context-cost turns. |
| **Research Trajectories** | ShareGPT and Hermes-RL compatible trajectory logging (`~/.ex/trajectories/`) for agent post-training and RL fine-tuning. |

---

## Installation & Setup

### 1. Windows Native (PowerShell)

Run PowerShell in the project directory:
```powershell
.\scripts\install.ps1
```
Or directly install via pip:
```powershell
pip install -e .
```

### 2. Linux, macOS, WSL2

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

### 3. First-Run Setup Wizard

After installation, if `merlin` is not recognized (common on Windows non-admin installs — pip places the command outside PATH), run the self-repair:

```powershell
python -m merlin_agent doctor
```

This adds the command to PATH automatically. Then configure your provider, model, and API key interactively:

```bash
merlin setup
```

The wizard:
- **Pick a provider** from a numbered table (openrouter, nous_portal, openai, anthropic, gemini, groq, deepseek, together, mistral, xai, ollama, vllm, or `custom` for any OpenAI-compatible endpoint)
- **Set the base URL** (editable — defaults per provider; `custom` requires manual entry)
- **Paste your API key** (input is masked; stored in `MERLIN_HOME/.env`, never in config.yaml)
- **Runs a live connection test** against the real endpoint before saving — you see `✔ Connection OK` or the exact HTTP error

Home directory (`MERLIN_HOME`) defaults to `%LOCALAPPDATA%\merlin` on Windows, `~/.merlin` on Linux/macOS.

### 4. Environment Configuration (manual alternative)

Copy `.env.example` to `.env` or set environment variables:
```bash
cp .env.example .env
```
Configure your primary API key (e.g. `Merlin_API_KEY`, `OPENROUTER_API_KEY`, `NOUS_PORTAL_API_KEY`, or `OPENAI_API_KEY`). Model/provider can be set with `Merlin_MODEL`, `Merlin_PROVIDER`, `Merlin_BASE_URL`.

---

## Quick Usage

### Start Interactive Chat Session
```bash
merlin
```
or explicitly:
```bash
merlin chat
```
The full-screen Textual TUI launches with the header panel, scrollable transcript, tool-call cards, and the bottom telemetry bar (`☤ model │ ~212K/1M │ [██░░░░░░░░] 20% │ ◎ health │ ◷ latency │ ↑ ↓ tokens`).

For the classic prompt_toolkit interface:
```bash
merlin chat --classic
```

### Switch Model & Provider
```bash
# View active model
merlin model

# Switch model
merlin model glm-5.3-flash --provider ollama
```

Provider names: `openrouter`, `nous_portal`, `openai`, `anthropic`, `gemini`, `groq`, `deepseek`, `together`, `mistral`, `xai`, `ollama`, `vllm`, or set any OpenAI-compatible endpoint via `merlin setup` → `custom`.

### Start Gateway API Server & Cron Daemon
```bash
merlin gateway --port 8642
```
Once launched, connect any OpenAI-compatible client or Open WebUI to `http://localhost:8642/v1`.

### Inspect & Manage Memory
```bash
merlin memory
```

### List Skills Catalog
```bash
merlin skills
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
