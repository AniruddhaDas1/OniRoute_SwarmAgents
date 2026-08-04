# Resolution Context

## Required Context

An Agent request must identify the requesting Agent or sub-agent, desired capability, required input and output contracts, mandatory tools, policy constraints, and acceptable Skill version or lifecycle range.

## Optional Context

Optional context may include audience, provider, environment, quality threshold, license preferences, latency or cost goals, preferred governance class, and replacement policy.

## Produced Context

A resolution result produces selected Skill records, composition and dependency graph, provenance, ranking evidence, rejected alternatives, assumptions, compatibility findings, confidence, cache metadata, and unresolved risks.

## Context Propagation

Only declared context contracts may flow between selected Skills. Propagation preserves source identity, version, sensitivity classification, and ownership. Missing, incompatible, or ambiguous context blocks selection or produces an explicit review state. Resolution context does not become Agent state and does not alter Workflow sequencing.
