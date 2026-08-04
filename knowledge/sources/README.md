# Knowledge Source Architecture

The `sources/` layer defines how OniRoute identifies, evaluates, and tracks external origins. It is deliberately separate from the Skill Registry: a Source can expose many asset types and does not become a Skill by being registered.

## Boundaries

Source registration records identity, provenance, trust, capabilities, discovery status, and access requirements. Future connectors may implement discovery against these contracts, but this phase does not connect to or copy any source.

## Documents

- [`SOURCE_SPECIFICATION.md`](SOURCE_SPECIFICATION.md)
- [`SOURCE_TYPES.md`](SOURCE_TYPES.md)
- [`SOURCE_LIFECYCLE.md`](SOURCE_LIFECYCLE.md)
- [`TRUST_MODEL.md`](TRUST_MODEL.md)
- [`PROVENANCE_MODEL.md`](PROVENANCE_MODEL.md)
- [`DISCOVERY_MODEL.md`](DISCOVERY_MODEL.md)
