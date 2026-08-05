# Skill Intelligence Developer Guide

## 1. Subsystem Architecture & Usage

The Skill Intelligence subsystem provides a programmatic API and CLI tools to process `EngineeringExecutionPlan` instances into `AgentProfileReport` contracts.

### Programmatic Python Usage

```python
from pathlib import Path
from runtime.loader import RepositoryLoader
from runtime.resolver import Resolver
from runtime.skills import (
    SkillDiscoveryEngine,
    SkillRankingEngine,
    SkillBundlingEngine,
    AgentProfileBuilderEngine,
)

# 1. Load Registry & Resolver
registry = RepositoryLoader(Path.cwd()).load()
resolver = Resolver(registry)

# 2. Stage P2.S1: Discover Skills
discovery_engine = SkillDiscoveryEngine(registry, resolver)
selection_report = discovery_engine.discover_skills(plan)

# 3. Stage P2.S2: Rank Skills
ranking_engine = SkillRankingEngine(registry, resolver)
ranked_report = ranking_engine.rank_skills(selection_report, plan)

# 4. Stage P2.S3: Bundle Skills
bundling_engine = SkillBundlingEngine(registry, resolver)
bundle_report = bundling_engine.bundle_skills(ranked_report, plan, selection_report)

# 5. Stage P2.S4: Build Agent Profiles
builder_engine = AgentProfileBuilderEngine(registry, resolver)
profile_report = builder_engine.build_profiles(bundle_report, plan)
```

---

## 2. Extension Rules

1. **Adding New Skills**: Add skill definition metadata to the registry. Do **NOT** modify P2 engine logic.
2. **Adding Discipline Categories**: Update `CANONICAL_DISCIPLINES` in `runtime/skills/bundling.py` and `DISCIPLINE_ROLE_MAP` in `runtime/skills/builder.py`.
3. **Contract Immutability**: All P2 reports (`SkillSelectionReport`, `RankedSkillReport`, `ExecutionSkillBundleReport`, `AgentProfileReport`) are frozen Pydantic models. Do not add mutable methods to these models.
