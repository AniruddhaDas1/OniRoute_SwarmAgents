# Skill Contract

Every Skill must declare metadata that points to a bounded contract. The contract describes capability expectations; it does not contain implementation instructions.

## Purpose

State the capability the Skill supports and the problem boundary it addresses.

## Inputs

Identify required context, information, artifacts, and input shape.

## Outputs

Identify produced context, findings, decisions, or artifacts at the contract level.

## Preconditions

State required approvals, context, dependencies, tools, compatibility, and validation state before use.

## Postconditions

State what is true about the declared output and traceability after successful use.

## Failure Conditions

Describe invalid inputs, missing dependencies, incompatibility, unsafe assumptions, and validation failures.

## Expected Behavior

Describe deterministic boundaries, evidence expectations, escalation, and non-destructive behavior without prescribing implementation.

## Non-goals

Explicitly exclude responsibilities owned by Agents, Workflows, infrastructure, providers, or runtime systems.
