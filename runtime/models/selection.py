from .exceptions import NoCompatibleModelError
from .models import HealthStatus, ModelRecord, SelectionRequest
from .registry import ModelRegistry


class ModelSelector:
    def __init__(self,registry:ModelRegistry,fallback_order:tuple[str,...]=()):self.registry=registry;self.fallback_order=fallback_order
    def select(self,request:SelectionRequest)->ModelRecord:
        candidates=[]
        for model in self.registry.models.values():
            provider=self.registry.providers.get(model.provider)
            if model.status in (HealthStatus.DISABLED,HealthStatus.UNAVAILABLE,HealthStatus.DEPRECATED) or provider and provider.status==HealthStatus.DISABLED:continue
            if not request.capabilities.issubset(model.capabilities):continue
            if request.protocol and model.protocol!=request.protocol:continue
            if request.provider and model.provider!=request.provider:continue
            if request.local_only and not model.local:continue
            preference=[*request.user_preference,*request.environment_preference,*self.fallback_order]
            pref_score=len(preference)-preference.index(model.provider) if model.provider in preference else 0
            health={HealthStatus.HEALTHY:3,HealthStatus.EXPERIMENTAL:1,HealthStatus.UNKNOWN:0}.get(model.status,-1)
            candidates.append(((pref_score,2 if request.local_preference and model.local else 0,health,model.priority,model.context_window,model.id),model))
        if not candidates:raise NoCompatibleModelError("No compatible model metadata found")
        return max(candidates,key=lambda item:item[0])[1]
