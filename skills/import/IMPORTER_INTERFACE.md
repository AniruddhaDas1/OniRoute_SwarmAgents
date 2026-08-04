# Importer Interface Contract

Importers are source-specific implementations that must conform to one conceptual contract. This document defines capabilities, not executable APIs or method signatures.

Every importer must provide concepts for:

- Source detection and source-type declaration.
- Manifest reading and package-layout reporting.
- Metadata extraction with source locations and confidence.
- Capability discovery.
- Dependency discovery and version constraints.
- License discovery and attribution evidence.
- Provenance capture, including immutable revision where available.
- Normalization request and mapping report.
- Validation request and validation evidence.

An importer must expose read-only evidence to the pipeline, identify unsupported layouts explicitly, preserve original metadata, and never silently infer missing ownership, licensing, compatibility, or version information. It must not perform installation, execution, or Registry state changes directly.
