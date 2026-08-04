class GovernancePermissions:
    def __init__(self,allowed:set[str]):self.allowed=allowed
    def check(self,requested:set[str]|frozenset[str])->bool:return set(requested).issubset(self.allowed)
