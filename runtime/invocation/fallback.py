class FallbackChain:
    def __init__(self,models:tuple[str,...]):self.models=models
    def ordered(self,preferred:str|None=None)->tuple[str,...]:return ((preferred,) if preferred else ())+tuple(item for item in self.models if item!=preferred)
