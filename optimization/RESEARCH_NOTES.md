# ICOE Research Notes

Research was conducted from public repository documentation on 2026-08-04. Concepts were extracted; no code, algorithms, assets, or repository content were copied or imported.

## alexgreensh/token-optimizer

Observed concepts: structural/runtime/behavioral waste categories; duplicate and stale Context control; checkpoint/restore across compaction; history/session continuity; progressive disclosure; Context quality scoring; token/cost budgeting; and recovery of archived raw output. ICOE adopts the architectural ideas of measurable optimization, checkpoints, decay, and recoverability. It does not adopt hooks, databases, dashboards, environment-specific behavior, or implementation. The repository advertises PolyForm Noncommercial licensing, reinforcing the no-copy boundary.

## rtk-ai/rtk

Observed concepts: command-aware filtering, grouping, truncation, deduplication, failures-only test summaries, compact Git/build/log views, recovery of full output, and low-overhead preprocessing. ICOE designs RTK as an optional Tool integration for Terminal Context. It must preserve exit codes, errors, warnings, and raw-output references. RTK is not a dependency and is not invoked by this architecture.

## jgravelle/jcodemunch-mcp

Observed concepts: tree-sitter indexing, exact symbol/function/class retrieval, byte-level targeted source extraction, outlines, import/reference lookup, compact wire representation, index freshness, and provenance. ICOE designs an optional AST Knowledge/MCP integration with parser-neutral contracts, freshness/confidence metadata, and absence-safety. The source describes dual/non-commercial terms; no implementation is reused.

## tirth8205/code-review-graph

Observed concepts: repository dependency graphs, callers/callees/tests/import/inheritance relationships, impact radius, execution flows, communities, hub/bridge nodes, changed-file targeting, compact minimal Context, incremental freshness, and local graph operation. ICOE designs an optional Repository Graph integration for relevance ranking and dependency-aware retrieval. Graph results remain evidence, not automatic truth, and cloud embeddings remain opt-in under governance.

## vaibkumr/prompt-optimizer

Observed concepts: protected tags, sequential optimizer composition, JSON/prompt-chain support, token-reduction metrics, semantic-quality measurement, and explicit compression-versus-performance tradeoffs. ICOE adopts protected segments, composable candidates, and quality gates. It rejects “maximum compression” as a universal objective and requires workload-specific validation.

## Planned integrations

- Existing Context Engine supplies immutable typed Context and provenance.
- Existing resolver/graph may supply repository relationships through a read-only contract.
- Tool Layer may describe optional RTK/native terminal plugins.
- Knowledge/MCP Layer may describe optional AST and repository-graph sources.
- Governance evaluates plugin permissions, security, approvals, and budgets.
- UMAL receives only a validated Optimized Context Envelope and remains unaware of plugin implementation.

All third-party names are attribution for research references, not bundled integrations or compatibility guarantees.
