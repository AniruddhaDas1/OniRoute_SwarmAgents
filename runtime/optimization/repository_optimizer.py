import ast
from pathlib import Path


def lookup_symbols(root: Path, query: str) -> list[dict]:
    matches=[]
    for path in sorted(root.rglob("*.py")):
        try: tree=ast.parse(path.read_text(encoding="utf-8"))
        except (OSError,SyntaxError): continue
        for node in ast.walk(tree):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and query.casefold() in node.name.casefold(): matches.append({"name":node.name,"kind":type(node).__name__,"path":str(path),"line":node.lineno})
    return matches
