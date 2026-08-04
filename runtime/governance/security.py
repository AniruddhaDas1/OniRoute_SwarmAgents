class SecurityEngine:
    def __init__(self,rules:dict):self.rules=rules
    def violations(self,permissions:set[str]|frozenset[str])->tuple[str,...]:return tuple(item for item in permissions if self.rules.get(item)=="deny")
