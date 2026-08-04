def optimize_conversation(messages: list[dict], max_messages: int | None = None) -> tuple[list[dict], list[str]]:
    seen=set(); result=[]; removed=[]
    for message in messages:
        marker=repr(message)
        if marker in seen: removed.append(marker); continue
        seen.add(marker); result.append(message)
    if max_messages: result=result[-max_messages:]
    return result,removed
