from enum import StrEnum


class Permission(StrEnum):
    READ_ONLY="read_only"; READ_WRITE="read_write"; EXECUTE="execute"; NETWORK="network"; FILESYSTEM="filesystem"; SHELL="shell"; DATABASE="database"; BROWSER="browser"; SENSITIVE="sensitive"; HUMAN_APPROVAL="human_approval"

class PermissionPolicy:
    def __init__(self,allowed:set[Permission]):self.allowed=allowed
    def permits(self,required:set[Permission]|frozenset[Permission])->bool:return set(required).issubset(self.allowed)
