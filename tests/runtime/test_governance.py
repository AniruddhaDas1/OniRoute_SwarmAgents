from pathlib import Path

import pytest
from typer.testing import CliRunner

from cli.main import app
from runtime.governance import AuditEngine,BudgetLimits,BudgetTracker,Decision,GovernanceRequest,PolicyEngine
from runtime.governance.exceptions import BudgetExceededError

ROOT=Path(__file__).parents[2]

def make(config=None):return PolicyEngine(config or {"permission_defaults":["read_only"],"approval_defaults":"Automatic","security_rules":{"network":"deny"},"risk_threshold":40},BudgetTracker(BudgetLimits(invocations=2,estimated_tokens=10)),AuditEngine())

def test_policy_permissions_security_and_audit():
    engine=make();result=engine.authorize(GovernanceRequest(kind="model",model="local",permissions=frozenset({"read_only"}),estimated_tokens=2));assert result.decision==Decision.ALLOW;assert len(engine.audit.records)==1
    denied=engine.authorize(GovernanceRequest(kind="tool",tool="net",permissions=frozenset({"network"})));assert denied.decision==Decision.DENY

def test_approval_and_budget_limits():
    engine=make({"permission_defaults":[],"approval_defaults":"Manual","risk_threshold":100});assert engine.authorize(GovernanceRequest(kind="model")).decision==Decision.REQUIRE_APPROVAL
    budget=BudgetTracker(BudgetLimits(invocations=1));budget.check("model");budget.record("model")
    with pytest.raises(BudgetExceededError):budget.check("model")

def test_governance_cli():
    runner=CliRunner()
    for command in (["policy"],["audit"],["approvals"],["permissions"],["budget"]):
        result=runner.invoke(app,[*command,"--repository-root",str(ROOT)]);assert result.exit_code==0,result.stdout
