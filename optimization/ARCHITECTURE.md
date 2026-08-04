# ICOE Architecture

## Position

ICOE consumes immutable Context prepared by the frozen Context Engine and returns an optimization result for UMAL selection and Invocation. It does not alter source Context, choose a provider, invoke a model, or mutate frozen metadata.

```text
Workflow Contract
      ↓
Execution Plan
      ↓
Context Engine ── immutable source context
      ↓
ICOE Policy Gate
      ↓
Module Selection → Optimization Plan → Candidate Transformations
      ↓                              ↘ evidence / rejected candidates
Validation → Budget Check → Optimized Context Envelope
      ↓
UMAL → Invocation → Model
```

## Canonical contracts

An **Optimization Request** identifies source Context, target capability, model-neutral budget, protected content, module permissions, quality threshold, and provenance. An **Optimization Plan** records ordered plugins, scopes, budgets, expected transformations, and fallback. An **Optimized Context Envelope** contains the optimized payload, retained provenance, change manifest, token/byte estimates, quality evidence, discarded-content references, and validation state. An **Optimization Report** records before/after measures and policy decisions.

## Principles

- Provider, tokenizer, runtime, storage, parser, and implementation independence.
- Deterministic output for identical inputs, plugin versions, and policies.
- Source Context remains immutable; optimization creates derived Context.
- Protected instructions, approvals, security labels, provenance, and artifact ownership cannot be silently removed.
- Lossy transformations require declared quality thresholds and safe fallback to less aggressive or original Context.
- Optimization failure must not become invocation failure when original Context remains within policy budget.
- Plugins receive minimum necessary Context and cannot transfer ownership.

## Extension boundaries

Native modules may implement stable core transformations in a future approved phase. RTK-like terminal filtering belongs behind optional Tool metadata and governance. AST and repository-graph retrieval belong behind optional Knowledge/MCP or local index contracts. None is a mandatory dependency.
