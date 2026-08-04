class RiskEngine:
    WEIGHTS={"filesystem":20,"shell":40,"network":30,"database":30,"browser":25,"sensitive":40,"mcp":20}
    def score(self,permissions:set[str]|frozenset[str])->int:return min(100,sum(self.WEIGHTS.get(item,0) for item in permissions))
