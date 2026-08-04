# Organization

OniRoute_SwarmAgents models an AI Engineering Organization through three departments with distinct ownership boundaries.

## Executive

Executive owns strategic direction, prioritization, governance, organizational context, and cross-department decisions. It defines outcomes and constraints without performing engineering or platform implementation.

## Engineering

Engineering translates strategic direction into software designs, technical plans, delegated implementation direction, and quality-evidence requirements. It owns provider-independent engineering decisions and coordinates specialist disciplines without performing implementation directly.

Presentation Engineering is an Engineering discipline responsible for presentation architecture, storytelling, executive, business, technical, visual, and data communication governance. It remains separate from Documentation and Knowledge ownership and does not generate presentation artifacts.

Motion Engineering is an Engineering discipline responsible for motion architecture, animation strategy, interaction motion, accessibility, performance guidance, and quality review. It remains separate from Frontend implementation and from graphics, video, and design-asset production.

## Platform

Platform supplies expertise for specific technologies, infrastructure systems, managed services, and cloud providers. It makes vendor-specific constraints explicit while supporting Engineering-owned designs.

## Organizational model

The departments form a responsibility hierarchy:

1. Executive establishes direction and constraints.
2. Engineering turns that direction into technical outcomes.
3. Platform advises Engineering on specific implementation technologies.

The hierarchy defines ownership and reporting relationships only. It is not an executable agent system, orchestration workflow, or mandatory runtime call chain.

The Executive, Engineering, and Platform agents are now defined and frozen as the top-level architecture. Platform sub-agents, skills, workflows, adapters, MCP integrations, and execution systems remain later-phase concerns.
