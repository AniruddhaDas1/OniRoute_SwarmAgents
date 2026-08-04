from pathlib import Path

from typer.testing import CliRunner

from cli.main import app
from runtime.models import Capability, ModelManager, SelectionRequest

ROOT=Path(__file__).parents[2]

def test_catalog_registry_and_aliases():
    manager=ModelManager(ROOT/"config/models.yaml")
    assert manager.registry.models
    assert manager.resolver.find_model("default-local").id=="local-metadata-placeholder"
    assert manager.resolver.find_provider("custom")
    assert manager.resolver.find_protocol("local-process")
    assert manager.resolver.find_capability("reasoning")==Capability.REASONING

def test_capability_selection_and_fallback():
    manager=ModelManager(ROOT/"config/models.yaml")
    selected=manager.select_best_model(SelectionRequest(capabilities=frozenset({Capability.CODING}),local_only=True,user_preference=("custom",)))
    assert selected.local and Capability.CODING in selected.capabilities

def test_model_cli():
    runner=CliRunner()
    for args in (["models","--repository-root",str(ROOT)],["providers","--repository-root",str(ROOT)],["capabilities"],["inspect","model","default-local","--repository-root",str(ROOT)],["inspect","provider","custom","--repository-root",str(ROOT)],["recommend-model","--capability","reasoning","--repository-root",str(ROOT)]):
        result=runner.invoke(app,args); assert result.exit_code==0,result.stdout
