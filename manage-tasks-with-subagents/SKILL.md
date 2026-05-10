---
name: manage-tasks-with-subagents
description: Orchestrate parallel feature implementation by simultaneously delegating non-blocking GitHub issues with the 'AFK' label to sub-agents in a single turn. Use when you need to progress multiple independent tasks concurrently.
---

# Manage Tasks with Sub-agents

## Quick start

1. **Find Issues**: Use `mcp_github-mcp-server_list_issues` or `search_issues` if available. Fallback: `gh issue list --label AFK --state open`
2. **Filter**: Identify issues marked "blocked by none" or with no blockers in the description.
3. **Parallel Delegation**: Invoke `generalist` sub-agents for **all** unblocked issues **simultaneously** within a single response turn. Set `waitForPreviousTools: false` for each call.

## Workflows

### 1. Triage and Selection
- Search for open issues with the `AFK` label using GitHub MCP tools (e.g., `list_issues`).
- Inspect descriptions for the string "blocked by none".
- Verify if any other open issues are listed as blockers (e.g., "Blocked by #15").

### 2. Preparation (Mandatory)
Before delegating any task, you **MUST**:
- Locate and read the **Low-Level Design (LLD)** document (e.g., `docs/feature-1/lld.md`).
- Review relevant **Architectural Decision Records (ADRs)** in `docs/adr/`.
- Ensure the sub-agent prompt explicitly instructs them to adhere to these documents.

### 3. Parallel Execution Strategy (CRITICAL)
To ensure sub-agents run in parallel and are not triggered sequentially:
- **Single Turn**: You MUST emit all sub-agent tool calls (e.g., `browser_subagent`) in a single response turn. Do not wait for one to finish before starting another.
- **Parallel Flags**: Set `waitForPreviousTools: false` for every sub-agent tool call in the batch.
- **Context Preservation**: Each sub-agent call should be self-contained with all necessary context (LLD, ADRs, issue details).

### 4. Delegation Prompt Template
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
5. Push and create a Pull Request to `main`. Use `mcp_github-mcp-server_create_pull_request` if available.
6. **IMPORTANT**: Include "Closes #[NUMBER]" in the PR description to link the issue.
7. **Cleanup**: Before returning, ensure all changes are either pushed or discarded. The worktree MUST be pristine with no uncommitted changes.
8. **Remove Worktree**: Delete the worktree using `git worktree remove --force /tmp/kural-issue-[NUMBER]` before finishing.
9. **STRICTLY PROHIBITED**: DO NOT MERGE the PR. The task ends immediately after PR creation and local cleanup.

## Safety
Use a git worktree at /tmp/kural-issue-[NUMBER] to avoid filesystem collisions.
```

### 5. Monitoring and Cleanup
- Track sub-agent results.
- Ensure PRs are created and issues are linked.
- **NEVER** merge PRs autonomously. The workflow stops at PR creation. Merging is strictly reserved for humans.
- Confirm that implementations match the architectural direction defined in the LLD.
- **Orchestrator Verification**: Once the flow is almost complete with the subagents, the orchestrator MUST verify that there are no uncommitted changes in the local main repository and no stale worktrees remain. All sub-agent changes must be in the PRs, with zero local footprint.

## Mandates

- **Link Issues**: Every PR must contain the "Closes #123" keyword.
- **Consult Design**: LLD and ADRs are the source of truth for implementation logic.
- **Human in the Loop**: The orchestrator's job and the sub-agent's job end at PR creation. Merging is reserved EXCLUSIVELY for humans. No agent should ever call a merge tool or command.
- **Strict Parallelism**: Sub-agents MUST be triggered in parallel as much as possible.
- **Isolated Workspaces**: Always use `git worktree` for parallel sub-agents.
- **Pristine Local State**: Each sub-agent must delete its worktree after pushing. Before returning control to the user, the main orchestrator MUST ensure no local changes exist in any worktree or the main repository.

## Tooling Preference

- **GitHub MCP Server**: Use GitHub MCP tools for ALL operations (searching issues, reading content, creating PRs, adding comments) as the primary method.
- **GitHub CLI (`gh`)**: Use as a fallback only if the MCP server is unavailable or lacks a specific capability required for the task.
- **Merge Tools**: Tools like `mcp_github-mcp-server_merge_pull_request` or `gh pr merge` are STRICTLY PROHIBITED for both the orchestrator and sub-agents.
