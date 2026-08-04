from pathlib import Path

import yaml
from typer.testing import CliRunner

from cli.main import app
from runtime.tools import Permission, PermissionPolicy, ToolCapability, ToolCatalog, ToolSelectionRequest
from runtime.tools.resolver import ToolResolver
from runtime.tools.selection import ToolSelector

ROOT=Path(__file__).parents[2]

def setup():
    config=yaml.safe_load((ROOT/"config/tools.yaml").read_text());registry=ToolCatalog.load(ROOT/"config/tools.yaml");selector=ToolSelector(registry,PermissionPolicy({Permission(x) for x in config["permission_policy"]}),tuple(config["preferred_local_tools"]));return registry,selector

def test_tool_catalog_registry_and_alias():
    registry,_=setup();resolver=ToolResolver(registry)
    assert registry.tools and registry.local_tools and registry.mcp_servers
    assert resolver.find_tool("git").id=="git-metadata"
    assert resolver.find_mcp("example-mcp")
    assert resolver.find_capability("filesystem")==ToolCapability.FILESYSTEM

def test_permission_and_capability_selection():
    registry,selector=setup();assert PermissionPolicy({Permission.READ_ONLY}).permits({Permission.READ_ONLY})
    assert selector.recommend(ToolSelectionRequest(capabilities=frozenset({ToolCapability.GIT}))).id=="git-metadata"
    assert selector.recommend(ToolSelectionRequest(capabilities=frozenset({ToolCapability.DATABASE}))).id=="sqlite-metadata"

def test_tool_cli():
    runner=CliRunner()
    commands=(["tools"],["mcp"],["inspect","tool","git"],["inspect","mcp","example-mcp"],["recommend-tool","--capability","database"])
    for command in commands:
        result=runner.invoke(app,[*command,"--repository-root",str(ROOT)]);assert result.exit_code==0,result.stdout
