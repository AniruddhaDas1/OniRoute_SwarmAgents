from collections.abc import Iterator


class StreamResponse:
    def __init__(self,chunks:Iterator[str]):self.chunks=chunks
    def __iter__(self):return iter(self.chunks)
