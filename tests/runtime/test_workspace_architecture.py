from pathlib import Path

from runtime.workspace import (
    ArtifactCategory,
    ArtifactDestination,
    DiscoveryPriority,
    DiscoveryRuleSpec,
    ExecutionContext,
    ProjectMetadata,
    ProjectType,
    TrustLevel,
    ValidationIssue,
    ValidationState,
    WorkspaceLifecycle,
    WorkspaceMetadata,
    WorkspaceStatus,
)


def test_workspace_metadata_instantiation():
    eng_root = Path("/opt/oniroute/engine")
    ws_root = Path("/home/user/projects/my_app")

    ws_meta = WorkspaceMetadata(
        workspace_id="ws-12345",
        name="my_app",
        workspace_root=ws_root,
        engine_root=eng_root,
        project_type=ProjectType.PYTHON,
        lifecycle=WorkspaceLifecycle.ACTIVE,
        status=WorkspaceStatus.VALID,
        created="2026-08-04T00:00:00Z",
        version="1.0.0",
        owner="test-user",
        artifact_root=ws_root / ".oniroute" / "artifacts",
        session_root=ws_root / ".oniroute" / "sessions",
        logs_root=ws_root / ".oniroute" / "logs",
        memory_root=ws_root / ".oniroute" / "memory",
        configuration_root=ws_root / ".oniroute" / "config",
        validation=ValidationState(valid=True, issues=[]),
        trust=TrustLevel.VERIFIED,
    )

    assert ws_meta.workspace_id == "ws-12345"
    assert ws_meta.workspace_root == ws_root
    assert ws_meta.engine_root == eng_root
    assert ws_meta.project_type == ProjectType.PYTHON
    assert ws_meta.trust == TrustLevel.VERIFIED


def test_project_metadata_instantiation():
    ws_root = Path("/home/user/projects/my_app")
    proj_meta = ProjectMetadata(
        project_id="proj-999",
        name="my_app",
        project_type=ProjectType.NEXTJS,
        root_path=ws_root,
        framework_version="14.2.0",
        language_version="18.x",
        manifest_path=ws_root / "package.json",
        is_empty=False,
    )

    assert proj_meta.project_type == ProjectType.NEXTJS
    assert proj_meta.manifest_path == ws_root / "package.json"
    assert not proj_meta.is_empty


def test_execution_context_boundaries():
    eng_root = Path("/opt/oniroute/engine")
    ws_root = Path("/home/user/projects/my_app")
    cwd = ws_root / "src"

    ctx = ExecutionContext(
        engine_root=eng_root,
        workspace_root=ws_root,
        cwd=cwd,
    )

    assert ctx.is_engine_read_only()
    assert ctx.engine_root != ctx.workspace_root


def test_artifact_destination_boundary_validation():
    eng_root = Path("/opt/oniroute/engine")
    ws_root = Path("/home/user/projects/my_app")

    valid_dest = ArtifactDestination(
        category=ArtifactCategory.SOURCE_CODE,
        relative_path=Path("src/generated.py"),
        absolute_path=ws_root / "src/generated.py",
        workspace_root=ws_root,
        engine_root=eng_root,
    )
    assert valid_dest.validate_boundary()

    invalid_dest = ArtifactDestination(
        category=ArtifactCategory.SOURCE_CODE,
        relative_path=Path("runtime/generated.py"),
        absolute_path=eng_root / "runtime/generated.py",
        workspace_root=ws_root,
        engine_root=eng_root,
    )
    assert not invalid_dest.validate_boundary()


def test_discovery_priority_enum():
    assert DiscoveryPriority.EXPLICIT_ARGUMENT == 1
    assert DiscoveryPriority.CURRENT_WORKING_DIRECTORY == 2
    assert DiscoveryPriority.PARENT_PROJECT_DETECTION == 3
    assert DiscoveryPriority.WORKSPACE_CONFIGURATION == 4

    spec = DiscoveryRuleSpec(
        priority=DiscoveryPriority.CURRENT_WORKING_DIRECTORY,
        name="CWD Discovery",
        description="Discover workspace from current working directory",
    )
    assert spec.enabled is True
