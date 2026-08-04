import json
from typing import Any

import yaml
from pydantic import BaseModel


class ContextSerializer:
    @staticmethod
    def to_dict(context: BaseModel) -> dict[str, Any]: return context.model_dump(mode="json")

    @classmethod
    def to_json(cls, context: BaseModel) -> str: return json.dumps(cls.to_dict(context), indent=2, sort_keys=True)

    @classmethod
    def to_yaml(cls, context: BaseModel) -> str: return yaml.safe_dump(cls.to_dict(context), sort_keys=True)

    @staticmethod
    def from_dict(model: type[BaseModel], data: dict[str, Any]) -> BaseModel: return model.model_validate(data)
