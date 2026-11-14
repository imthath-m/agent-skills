# agent-skills

Agent skills with trigger evals. Each skill is a folder with a `SKILL.md` (frontmatter `name` + `description`, then the instructions).

## Skills

| skill | what it does |
|---|---|
| [`llm-judge-validation`](llm-judge-validation/SKILL.md) | Validates an LLM judge against human labels: stratified sampling, blind labelling, kappa with bootstrap CIs, pass criteria fixed up front, judge prompt versioning. Ships `scripts/agreement.py`. |
| [`eval-set-builder`](eval-set-builder/SKILL.md) | Builds an eval set from real transcripts or logs: coverage plan, hard cases, gold answers, leakage checks, dev/held-out split. Ships `scripts/check_leakage.py`. |
| [`low-level-design`](low-level-design/SKILL.md) | Writes a modular Low-Level Design from product requirements: decoupled packages, domain layer, orchestrator, platform packages. |
| [`issue-breakdown`](issue-breakdown/SKILL.md) | Breaks a plan or PRD into vertical-slice issues with dependencies. Adapted from Matt Pocock's `to-issues` skill, attributed in the file. |
| [`manage-tasks-with-subagents`](manage-tasks-with-subagents/SKILL.md) | Delegates unblocked `AFK` GitHub issues to parallel sub-agents in worktrees, stopping at PR creation. |

## Install

Link every skill into `~/.agents/skills` (the directory must exist):

```bash
mkdir -p ~/.agents/skills
```

```bash
./link-skills.sh
```

For Claude Code, link a skill into `~/.claude/skills` instead:

```bash
ln -s "$PWD/llm-judge-validation" ~/.claude/skills/llm-judge-validation
```

## Trigger evals

Each skill has `evals/<skill>/cases.jsonl`: 10 user messages that should trigger it and 10 that should not, including near misses.

Run all 100 cases (needs the `claude` CLI; roughly 2 minutes):

```bash
python3 scripts/run_trigger_evals.py --label my-run
```

Compare two runs:

```bash
python3 scripts/run_trigger_evals.py --compare baseline revised
```

- The runner installs all skills in a temporary sandbox project and runs each case with headless `claude -p`.
- It records which skill the model invokes in its first message, then reports precision and recall per skill.
- Output goes to `evals/results/<label>.json`.
- If the `claude` CLI is missing, the runner says so, exits 2, and writes nothing.
- Useful flags: `--skills a,b`, `--model`, `--concurrency`, `--limit`.

## Results

One run per condition, `--model sonnet`, Claude Code 2.1.325. "After" is one revision of every description.

| skill | precision before → after | recall before → after |
|---|---|---|
| eval-set-builder | 1.00 → 1.00 | 1.00 → 1.00 |
| issue-breakdown | 1.00 → 1.00 | 0.90 → 0.90 |
| llm-judge-validation | 1.00 → 1.00 | 0.90 → 0.90 |
| low-level-design | 1.00 → 1.00 | 0.80 → 0.70 |
| manage-tasks-with-subagents | 1.00 → 1.00 | 1.00 → 1.00 |
| **overall (micro)** | 1.00 → 1.00 | 0.92 → 0.90 |

The revision did not improve the scores, and the differences are single-case flips on n = 10 per skill. Analysis and limitations: [`evals/RESULTS.md`](evals/RESULTS.md).
