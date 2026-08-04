# Compatibility Rules

Compatibility is evidence-based and must be evaluated independently for each dimension:

- **Agents** — declared compatible Agent IDs exist and their responsibility boundaries permit the Skill.
- **Sub-agents** — declared sub-agent IDs exist, are descendants of the expected Agent, and accept the Skill's contracts.
- **Dependencies** — required Skills and version ranges resolve without cycles or incompatible constraints.
- **Context contracts** — consumed context is producible and structurally compatible; produced context does not claim unsupported ownership.
- **Tool contracts** — required tools are declared and available in the intended environment; optional tools do not become hidden requirements.
- **Future Workflows** — workflow references describe compatibility only; they do not grant sequencing or execution authority.

Unknown identities, missing contracts, provider assumptions, incompatible versions, and ambiguous context mappings result in review or rejection according to policy. Compatibility does not transfer Agent ownership or alter reporting relationships.
