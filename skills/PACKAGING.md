# OniRoute Skill Package Format

An OniRoute Skill Package is a versioned directory or archive with this standard layout:

```text
skill/
├── skill.yaml
├── README.md
├── examples/
├── tests/
├── artifacts/
├── LICENSE
└── CHANGELOG.md
```

`skill.yaml` contains metadata conforming to the universal Skill Specification. `README.md` explains the package contract and boundaries. `examples/`, `tests/`, and `artifacts/` are reserved package sections; their content and execution are governed by later phases. `LICENSE` preserves licensing terms, and `CHANGELOG.md` records version history.

Packages must have one stable Skill ID, one declared version, complete provenance, and no undeclared executable behavior. A package is not a Skill merely because it has this directory shape; registry validation is required.
