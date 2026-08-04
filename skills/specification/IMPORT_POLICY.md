# Skill Import Policy

The specification supports future import from:

- GitHub repository or release
- Git repository
- ZIP archive
- Local folder
- Future MCP source
- Future OCI source
- Future remote registry

Import means metadata and provenance inspection only at this stage. No importer, network operation, registry client, unpacker, or runtime is implemented here.

An imported artifact becomes an OniRoute Skill only after source provenance, license, schema, contract, naming, dependency, compatibility, and quality validation. The original source remains authoritative for provenance; OniRoute lifecycle status records local governance state.
