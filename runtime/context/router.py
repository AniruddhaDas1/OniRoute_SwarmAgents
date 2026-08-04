from runtime.resolver import Resolver

from .models import RouteStep, RoutingPlan


class ContextRouter:
    def __init__(self, resolver: Resolver): self.resolver = resolver

    def plan(self, workflow_id: str) -> RoutingPlan:
        workflow = self.resolver.find_workflow(workflow_id)
        if not workflow: raise KeyError(workflow_id)
        data = workflow.data; steps: list[RouteStep] = []; unresolved: list[str] = []
        agent = str(data.get("entry_agent", "")); skills = [str(x) for x in data.get("compatible_skills", [])]; artifacts = [str(x) for x in data.get("produced_artifacts", [])]
        if agent: steps.append(RouteStep(source=workflow_id, target=agent, relationship="workflow_to_agent"))
        for skill in skills: steps.append(RouteStep(source=agent or workflow_id, target=skill, relationship="agent_to_skill"))
        prior = skills[-1] if skills else agent or workflow_id
        for artifact in artifacts: steps.append(RouteStep(source=prior, target=artifact, relationship="skill_to_artifact"))
        exit_agent = str(data.get("exit_agent", ""))
        if exit_agent and artifacts: steps.append(RouteStep(source=artifacts[-1], target=exit_agent, relationship="artifact_to_next_agent"))
        for target in [agent, exit_agent]:
            if target and not self.resolver.find_agent(target): unresolved.append(target)
        for skill in skills:
            if not self.resolver.find_skill(skill): unresolved.append(skill)
        return RoutingPlan(workflow_id=workflow_id, steps=tuple(steps), unresolved=tuple(sorted(set(unresolved))))
