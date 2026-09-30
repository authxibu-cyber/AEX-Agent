---
name: git-workflow
description: Automates Git operations, worktree isolation, commit hygiene, and branch rebase strategies.
triggers:
  - "git commit"
  - "worktree"
  - "create branch"
  - "resolve conflict"
tools:
  - terminal
  - file_read
---
# Git Workflow & Worktree Isolation Protocol

When executing git workflows:
1. **Isolated Worktrees:** For parallel branch experiments, use `git worktree add` to prevent clobbering the active workspace.
2. **Atomic Commits:** Follow conventional commit conventions (`feat:`, `fix:`, `refactor:`, `perf:`).
3. **Conflict Resolution:** Inspect diffs surgically, ensuring semantic correctness of merged hunks.
