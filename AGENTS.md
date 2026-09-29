# EX AGENT REPOSITORY CONTEXT & PROTOCOLS

Welcome to the **EX Agent** workspace.
EX Agent is a self-improving, autonomous AI agent platform architected for persistent execution, multi-channel orchestration, and Tier-3 deep algorithmic optimizations.

## Core Rules for EX Agent

1. **Self-Improving Memory Loop:**
   - Always read and respect `MEMORY.md` (World facts) and `USER.md` (User habits/preferences).
   - After completing complex engineering workflows or learning novel solutions, invoke `update_memory` or create an executable skill in `skills/`.
   - Maintain character bounds for persistent files (~2,200 chars for `MEMORY.md`, ~1,375 chars for `USER.md`) by pruning outdated facts.

2. **GodEye Mandate (Tier 3 Deep Architecture):**
   - Default to the deepest, most optimized architectural level.
   - Bypass surface-level wrappers. Implement fused operations, asynchronous pipelining, and associative scans ($O(L) \to O(\log L)$).
   - When deploying local models, configure BF16/TF32 Tensor Core execution and flash attention primitives.

3. **Tool Execution Standards:**
   - Execute terminal commands safely with timeouts and structured output streams.
   - Provide file modifications with surgical line ranges and strict content verification.
   - Maintain full trajectory logs in ShareGPT/Hermes-RL compatible format for self-evolution.

4. **Multi-Platform Continuity:**
   - Ensure sessions are indexed in SQLite with FTS5 for cross-session semantic search.
   - Gateway channels (CLI, Telegram, Discord, Slack, REST API) share the persistent state store.
