from __future__ import annotations

from .models import OptimizationPlugin


class PluginRegistry:
    def __init__(self): self.plugins: dict[str, OptimizationPlugin] = {}
    def register(self, plugin: OptimizationPlugin) -> None: self.plugins[plugin.id] = plugin
    def discover(self) -> tuple[OptimizationPlugin, ...]:
        native = OptimizationPlugin(id="native", version="1.0.0", capabilities=("context", "prompt", "repository", "artifact", "terminal", "conversation", "skill"), trust="Official", health="Healthy", optional=False)
        self.register(native)
        for identifier, capability in (("rtk", "terminal"), ("ast", "repository"), ("repository-graph", "repository")):
            self.register(OptimizationPlugin(id=identifier, version="unavailable", capabilities=(capability,), optional=True))
        return tuple(self.plugins.values())
