---
name: manage-tasks-with-subagents
description: Orchestrate parallel feature implementation by delegating non-blocking GitHub issues with the 'AFK' label to sub-agents. Use when you need to progress multiple independent tasks simultaneously or automate the implementation-to-PR pipeline.
---

# Manage Tasks with Sub-agents

## Quick start

1. **Find Issues**: `gh issue list --label AFK --state open`
2. **Filter**: Identify issues marked "blocked by none" or with no blockers in the description.
3. **Delegate**: Invoke a `generalist` sub-agent for each unblocked issue, providing paths to LLD and relevant ADRs.

## Workflows

### 1. Triage and Selection
- Search for open issues with the `AFK` label.
- Inspect descriptions for the string "blocked by none".
- Verify if any other open issues are listed as blockers (e.g., "Blocked by #15").

### 2. Preparation (Mandatory)
Before delegating any task, you **MUST**:
- Locate and read the **Low-Level Design (LLD)** document (e.g., `docs/feature-1/lld.md`).
- Review relevant **Architectural Decision Records (ADRs)** in `docs/adr/`.
- Ensure the sub-agent prompt explicitly instructs them to adhere to these documents.

### 3. Delegation Prompt Template
Use the following structure when invoking sub-agents:
```text
You are tasked with resolving Issue #[NUMBER]: "[TITLE]".

## Goal
[Paste 'What to build' from issue]

## Architectural Constraints
- Refer to [LLD Path] and [ADR Path] for implementation patterns.
- Follow naming and module conventions in CONTEXT.md.

## Acceptance Criteria
[Paste 'Acceptance criteria' from issue]

## Workflow
1. Create a new branch `feature/issue-[NUMBER]-[slug]`.
2. Implement code.
3. Verify as per instructions (add tests if applicable).
4. Create a commit.
5. Push and create a Pull Request to `main`.
6. **IMPORTANT**: Include "Closes #[NUMBER]" in the PR description to link the issue.
7. **DO NOT MERGE** the PR. Stop after PR creation.

## Safety
Use a git worktree at /tmp/kural-issue-[NUMBER] to avoid filesystem collisions.
```

### 4. Monitoring and Cleanup
- Track sub-agent results.
- Ensure PRs are created and issues are linked.
- **NEVER** merge PRs autonomously; stop and wait for human review.
- Confirm that implementations match the architectural direction defined in the LLD.

## Mandates

- **Link Issues**: Every PR must contain the "Closes #123" keyword.
- **Consult Design**: LLD and ADRs are the source of truth for implementation logic.
- **Human in the Loop**: The orchestrator's job ends at PR creation. Merging is reserved for humans.
- **Isolated Workspaces**: Always use `git worktree` for parallel sub-agents to prevent state corruption.
