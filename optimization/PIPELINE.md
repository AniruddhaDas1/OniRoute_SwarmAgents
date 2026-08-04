# Optimization Pipeline

The normative metadata pipeline is:

1. **Receive Context** — accept immutable Context, provenance, sensitivity, and target capability.
2. **Classify** — identify Context types, protected segments, duplicates, recency, ownership, and risk.
3. **Establish Budget** — derive model-independent byte/token estimates and reserve output/tool headroom.
4. **Select Modules** — choose permitted optimizers by Context type, capability, policy, health, trust, and cost.
5. **Plan** — order transformations and declare expected loss, fallback, and evidence.
6. **Retrieve** — optionally request targeted symbols, Skills, graph neighborhoods, or artifacts through governed contracts.
7. **Transform** — produce candidate derived Context; never mutate the source.
8. **Validate** — check protected content, contracts, provenance, semantic/structural integrity, security, and budget.
9. **Rank Candidates** — prefer the smallest candidate that meets quality and policy thresholds.
10. **Emit Envelope** — return optimized Context, manifest, measurements, and fallback chain to UMAL/Invocation.

Optimization order is type-aware. Repository retrieval precedes code pruning; duplicate removal precedes summarization; error-preserving terminal filtering precedes generic truncation; protected prompt sections are excluded from destructive transformation. Parallel means logical candidate evaluation only, not execution semantics.
