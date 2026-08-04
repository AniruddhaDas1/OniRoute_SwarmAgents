# Registry Search Strategy

Search is a declarative query over registry metadata; this phase does not implement a search engine.

## Query Examples

- **Find all SQL skills:** `category=database AND tags contains sql`.
- **Find all Backend skills:** `compatible_agents contains backend`.
- **Find all Verified skills:** `validation_state=passed`.
- **Find all compatible with Backend/API Design:** `compatible_agents contains backend AND compatible_sub_agents contains backend-api-design`.

Queries should support exact filters, tag/category intersections, compatibility filters, version constraints, license and author filters, provider filters, validation state, quality thresholds, and installation status. Results must expose provenance, version, dependencies, compatibility, and validation evidence. Ranking may prefer Official status, higher quality score, exact compatibility, current version, and trusted provenance, but ranking must not hide lower-ranked records.
