from pathlib import Path

import yaml

from .models import HealthStatus, ModelRecord, ProtocolRecord, ProviderRecord
from .providers import PROVIDERS
from .protocols import PROTOCOLS
from .registry import ModelRegistry


class ModelCatalog:
    @staticmethod
    def load(path:Path)->ModelRegistry:
        data=yaml.safe_load(path.read_text(encoding="utf-8")) or {}; registry=ModelRegistry()
        for protocol in PROTOCOLS:registry.add_protocol(ProtocolRecord(id=protocol,display_name=protocol.replace("-"," ").title()))
        disabled=set(data.get("disabled_providers",[])); local_names={"ollama","vllm","lm-studio","mlx","localai","llama-cpp","koboldcpp","tgi"}
        for provider in PROVIDERS:registry.add_provider(ProviderRecord(id=provider,display_name=provider.replace("-"," ").title(),status=HealthStatus.DISABLED if provider in disabled else HealthStatus.UNKNOWN,local=provider in local_names))
        for item in data.get("models",[]):registry.add_model(ModelRecord.model_validate(item))
        return registry
