from enum import StrEnum
from time import sleep

from pydantic import BaseModel, ConfigDict


class FailurePolicy(StrEnum): RETRY="Retry"; FALLBACK="Fallback"; FAIL_FAST="Fail Fast"; TIMEOUT="Timeout"; CIRCUIT_BREAKER="Circuit Breaker"
class RetryPolicy(BaseModel):
    model_config=ConfigDict(frozen=True);mode:FailurePolicy=FailurePolicy.FAIL_FAST;attempts:int=1;delay_seconds:float=0;timeout_seconds:float=60
def with_retry(operation,policy:RetryPolicy):
    error=None
    for attempt in range(max(1,policy.attempts)):
        try:return operation()
        except Exception as exc:
            error=exc
            if policy.mode not in (FailurePolicy.RETRY,FailurePolicy.FALLBACK) or attempt+1>=policy.attempts:raise
            if policy.delay_seconds:sleep(policy.delay_seconds)
    raise error
