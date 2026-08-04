from datetime import datetime,timezone

from .models import AuditRecord

class AuditEngine:
    def __init__(self):self.records:list[AuditRecord]=[]
    def record(self,request,result,outcome:str):
        item=AuditRecord(id=f"audit:{len(self.records)+1}",timestamp=datetime.now(timezone.utc),request=request,result=result,outcome=outcome);self.records.append(item);return item
