# Supported Source Types

## GitHub Repository

Convenient discovery and version history. Trust requires repository ownership, pinned revision, license evidence, and protection against mutable default branches or unreviewed actions.

## Git Repository

Supports decentralized and private hosting with commit-level provenance. Trust requires a reachable immutable commit, repository identity, and license verification; network availability and submodules may complicate reproducibility.

## ZIP Archive

Portable and easy to preserve as a digest-addressed artifact. Trust requires checksum, archive-root inspection, path traversal protection, provenance, and license evidence; history and update authenticity may be limited.

## Local Folder

Useful for internal development and offline review. Trust requires an explicit owner, captured content digest, stable root, and local license evidence; reproducibility and provenance are weaker without a recorded snapshot.

## Future MCP Registry

May provide structured metadata and governed discovery. Trust depends on authenticated server identity, response provenance, protocol version, and registry policy. No MCP integration is implemented here.

## Future OCI Registry

May provide immutable, digest-addressed distribution. Trust depends on signed artifacts, registry identity, manifest integrity, and license metadata. No OCI client is implemented here.

## Future HTTP Registry

May provide broad remote distribution. Trust requires HTTPS, authenticated or signed metadata, immutable version references, checksums, and source attribution. No HTTP client is implemented here.
