# License Decision Record

| Community source | License class | Import result | Compliance decision | Reason |
|---|---|---|---|---|
| `alirezarezvani/claude-skills` | MIT | 785 metadata entries | Reference Only | Metadata/provenance retained; no source body distributed |
| `open-gsd/gsd-core` | MIT | 71 metadata entries | Reference Only | Metadata/provenance retained; no source body distributed |
| `garrytan/gstack` | MIT | 59 metadata entries | Reference Only | Metadata/provenance retained; no source body distributed |
| `pbakaus/impeccable` | Apache-2.0 | 14 metadata entries | Reference Only | Metadata/provenance retained; no Apache implementation or documentation distributed |
| `mattpocock/skills` | MIT | 41 metadata entries | Reference Only | Metadata/provenance retained; no source body distributed |
| `leonxlnx/taste-skill` | MIT | 13 metadata entries | Reference Only | Metadata/provenance retained; no source body distributed |
| `vuejs-ai/skills` | MIT | 8 metadata entries | Reference Only | Metadata/provenance retained; no source body distributed |
| `knoxgraeme/skillfish` | AGPL-3.0 | Zero entries | Reference Only; Review Required | Catalog metadata only; no AGPL code, prompt, documentation, example, or test is present |
| `multica-ai/andrej-karpathy-skills` | Unknown | Zero entries; one rejected candidate | Excluded | No determinable license is recorded; the decision record rejects admission |

## AGPL assessment

Skillfish contributes only `IMPORT_METADATA.yaml`, `SOURCE.md`, `README.md`, and `CATALOG.md` catalog/provenance records. There is no `normalized/` directory and no copied code, prompt, documentation body, example, test, workflow, script, or asset. AGPL source availability and network-use obligations are therefore not triggered by distribution of an AGPL implementation in the current tree. The source remains Review Required for any future use beyond factual metadata/reference.

## Unknown-license assessment

`multica-ai/andrej-karpathy-skills` remains license-undetermined. Its sole detected candidate is explicitly `Rejected` with reason `license_undetermined`, and no normalized entry exists. The source should remain excluded from the Community catalog's admitted/usable set. Retaining a factual rejection/provenance record is acceptable; any presentation as an available Community Skill should be removed before stable release.

## Provenance result

Every imported entry records repository, owner/author, URL, license, import date, normalization version, original path, commit, blob SHA, and an accepted decision. The AGPL and unknown-license sources have zero imported entries and retain source-level provenance. No provenance correction to frozen Community records is required in this phase.
