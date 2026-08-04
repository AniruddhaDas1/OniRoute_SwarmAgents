from pydantic import BaseModel, ConfigDict


class AdapterMetadata(BaseModel):
    model_config=ConfigDict(frozen=True); id:str; protocol:str; provider:str; enabled:bool=False
