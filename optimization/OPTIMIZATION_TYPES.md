# Optimization Types

## Context Optimizer

Duplicate removal, ghost-token cleanup, relevance ranking, pruning, metadata reduction, history decay, and Context budgeting. Use for mixed or over-budget Context while preserving protected and high-priority segments.

## Prompt Optimizer

Normalization, simplification, budgeting, structured-prompt compaction, and JSON optimization. Use only on declared mutable prompt sections; system, security, approval, and output-contract semantics remain protected.

## Repository Optimizer

Symbol, function, and class retrieval; repository targeting; and AST-aware retrieval. Use for code questions where targeted structural evidence is safer than broad file inclusion.

## Skill Optimizer

Relevant Skill selection, deduplication, ranking, and Context-aware loading. Use to avoid loading unrelated or overlapping Skills; compatibility and ownership remain authoritative.

## Artifact Optimizer

Markdown reduction, JSON minimization, report summarization, and documentation filtering. Use with artifact type, ownership, sensitivity, and provenance constraints.

## Terminal Optimizer

stdout/stderr reduction and test/build summarization. Preserve exit status, failures, warnings, affected paths, recovery reference, and enough surrounding evidence for diagnosis.

## Conversation Optimizer

History pruning, summary checkpoints, duplicate detection, and long-session optimization. Preserve decisions, unresolved work, approvals, user intent, provenance, and recent causal context.
