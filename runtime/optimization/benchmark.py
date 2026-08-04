from time import perf_counter

from .models import OptimizationBenchmark
from .report import measurements


def benchmark(name, operation, value):
    started=perf_counter(); result=operation(value); latency=(perf_counter()-started)*1000
    return result, OptimizationBenchmark(name=name, results=(measurements(value,result,latency),))
