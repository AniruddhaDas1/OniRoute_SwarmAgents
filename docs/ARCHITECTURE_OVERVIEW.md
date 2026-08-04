# Architecture Overview

OniRoute separates organizational definitions from runtime implementation. Frozen metadata layers define Agents, Skills, Workflows, Knowledge, Packages, and mappings. The v0.6 runtime loads these records into memory, validates them, resolves a read-only graph, creates immutable Context, plans and executes deterministic Workflow steps, selects Models and Tools by metadata, invokes only through protocol adapters, and requires governance decisions at AI and Tool choke points. See the phase freeze documents for normative boundaries.
