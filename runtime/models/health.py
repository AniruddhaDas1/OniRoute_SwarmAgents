from .models import HealthStatus


class HealthTracker:
    def __init__(self):self._status:dict[str,HealthStatus]={}
    def set(self,identifier:str,status:HealthStatus)->None:self._status[identifier]=status
    def get(self,identifier:str)->HealthStatus:return self._status.get(identifier,HealthStatus.UNKNOWN)
