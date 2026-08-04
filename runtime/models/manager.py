from pathlib import Path

import yaml

from .catalog import ModelCatalog
from .models import SelectionRequest
from .resolver import ModelResolver
from .selection import ModelSelector


class ModelManager:
    def __init__(self,config_path:Path):
        self.config=yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}; self.registry=ModelCatalog.load(config_path); self.resolver=ModelResolver(self.registry); self.selector=ModelSelector(self.registry,tuple(self.config.get("fallback_order",[])))
    def select_best_model(self,request:SelectionRequest):return self.selector.select(request)
