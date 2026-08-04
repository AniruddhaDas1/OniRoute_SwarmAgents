from typing import Any


def optimize_context(data: dict[str, Any], protected: set[str] | frozenset[str] = (), budget: int | None = None) -> tuple[dict[str, Any], list[str], list[str]]:
    seen=set(); result={}; removed=[]
    for key,value in data.items():
        marker=repr(value)
        if marker in seen and key not in protected: removed.append(key); continue
        if value in (None, "", [], {}) and key not in protected: removed.append(key); continue
        seen.add(marker); result[key]=value
    if budget is not None:
        for key in list(result):
            if len(repr(result)) <= budget: break
            if key not in protected: removed.append(key); result.pop(key)
    return result, ["duplicate removal", "ghost context cleanup", "context budgeting"], removed
