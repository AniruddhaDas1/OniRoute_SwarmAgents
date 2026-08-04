from .models import OptimizationMeasurements


def measurements(before, after, latency_ms=0):
    return OptimizationMeasurements(before_bytes=len(repr(before)),after_bytes=len(repr(after)),estimated_tokens_before=len(repr(before))//4,estimated_tokens_after=len(repr(after))//4,latency_ms=latency_ms)
