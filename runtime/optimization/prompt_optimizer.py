import json


def optimize_prompt(prompt: str, budget: int | None = None, protected: set[str] | frozenset[str] = ()) -> tuple[str, list[str], list[str]]:
    normalized=" ".join(prompt.split()); actions=["prompt normalization", "whitespace cleanup"]; removed=[]
    if budget and len(normalized)>budget: normalized=normalized[:budget]; actions.append("prompt budgeting")
    return normalized,actions,removed

def optimize_json(value): return json.loads(json.dumps(value, separators=(",", ":")))
