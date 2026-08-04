import json


def optimize_artifact(value, kind: str = "text"):
    if kind == "json": return json.loads(json.dumps(value, separators=(",", ":")))
    if kind == "markdown": return "\n".join(line.rstrip() for line in str(value).splitlines() if line.strip())
    return value
