# Runtime Governance

The centralized Policy Engine evaluates Model → Tool → Permission → Approval → Budget → Risk policy and returns one execution decision. Approval can be Automatic, Manual, Human Approval, Organization Policy, or scoped by Workflow, Agent, Skill, and Tool. Permissions and security rules cover filesystem, shell, network, secrets, database, browser, MCP, external services, and sensitive artifacts.

Budgets track invocation count, estimated tokens/cost class, tool requests, and runtime locally per process. Immutable audit records capture request identity, model/provider/tool metadata, approval, decision, risk, policy reasons, timestamp, and outcome. No telemetry, remote policy server, IAM, authentication provider, secret management, or organization sync is used.
