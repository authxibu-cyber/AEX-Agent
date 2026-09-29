---
name: code-review
description: Performs rigorous, Tier-3 architectural code analysis focusing on correctness, memory leaks, and concurrency.
triggers:
  - "review this code"
  - "audit code"
  - "check for bugs"
tools:
  - file_read
  - terminal
---
# Tier-3 Code Review Protocol

When invoked to review code:
1. **Structural Integrity:** Check concurrency safety, race conditions, async deadlocks, and exception barriers.
2. **Computational Complexity:** Identify accidental $O(N^2)$ algorithmic bottlenecks and propose vectorization or associative scan transformations.
3. **Hardware Utilization:** Check cache locality, excessive memory allocations, and recommend tensor core or buffer pooling optimizations where applicable.
4. **Actionable Diffs:** Always deliver exact line-numbered recommendations and drop-in code fixes.
