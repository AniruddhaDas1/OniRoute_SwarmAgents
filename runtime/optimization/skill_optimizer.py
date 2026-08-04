def optimize_skills(skills: list[dict]) -> tuple[list[dict], list[str], list[str]]:
    seen=set(); result=[]; removed=[]
    for skill in skills:
        identifier=str(skill.get("id") or skill.get("name") or repr(skill))
        if identifier in seen: removed.append(identifier); continue
        seen.add(identifier); result.append(skill)
    return result,["skill deduplication", "relevant skill selection"],removed
