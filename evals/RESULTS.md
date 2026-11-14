# Trigger eval results

All numbers below are copied from committed runner output: `results/baseline.json` and `results/revised.json`. Nothing is hand-entered.

## Setup

- Runner: `scripts/run_trigger_evals.py`, headless `claude -p`, Claude Code 2.1.325, `--model sonnet`.
- 100 cases: 5 skills x (10 should-trigger + 10 should-not-trigger, near misses included).
- All 5 skills installed in a sandbox project, so each skill's siblings act as distractors.
- A case counts as triggered if the skill under test is invoked via the `Skill` tool in the first assistant message.
- One run per condition. Baseline 2026-11-14 05:38 UTC, revised 05:40 UTC. 0 errored cases in both.

## Before and after one description revision

| skill | precision before → after | recall before → after | FN before → after | FP before → after |
|---|---|---|---|---|
| eval-set-builder | 1.00 → 1.00 | 1.00 → 1.00 | 0 → 0 | 0 → 0 |
| issue-breakdown | 1.00 → 1.00 | 0.90 → 0.90 | 1 → 1 | 0 → 0 |
| llm-judge-validation | 1.00 → 1.00 | 0.90 → 0.90 | 1 → 1 | 0 → 0 |
| low-level-design | 1.00 → 1.00 | 0.80 → 0.70 | 2 → 3 | 0 → 0 |
| manage-tasks-with-subagents | 1.00 → 1.00 | 1.00 → 1.00 | 0 → 0 | 0 → 0 |
| **overall (micro)** | 1.00 → 1.00 | 0.92 → 0.90 | 4 → 5 | 0 → 0 |

Reproduce the table: `python3 scripts/run_trigger_evals.py --compare baseline revised`.

## What the revision changed

Each description was revised once, targeting the baseline misses and adding explicit "Not for ..." boundaries. Exact before/after text is stored per skill in the two results files.

| skill | baseline miss | change |
|---|---|---|
| issue-breakdown | 09: "Create Linear tickets for each piece of the migration plan" | Named trackers (GitHub, Linear, Jira), "tickets", "migration plan". Added exclusions. |
| llm-judge-validation | 08: drift of an "eval scorer" after provider model updates | Added "eval scorer" and drift checks. Added exclusions. |
| low-level-design | 02: "Write an LLD for the PRD in docs/prd/sync.md"; 10: modular design with orchestrator | Named PRD input, orchestrator, platform packages, module structure. Added exclusions. |
| eval-set-builder | none | Added exclusions only. |
| manage-tasks-with-subagents | none | Tightened wording. Added exclusions. |

## Reading the result honestly

- The revision did not improve the scores. Recall went 0.92 → 0.90 overall. Precision was already 1.00.
- Misses after revision: issue-breakdown-09, llm-judge-validation-04, low-level-design-02, -05, -10.
- Three misses persisted (issue-breakdown-09, low-level-design-02, -10) despite wording aimed directly at them. That suggests the cause is not the description. Likely candidates: the model answers directly, or reaches for another tool first (e.g. reading the referenced file), which this runner scores as not triggered.
- llm-judge-validation-08 was fixed and -04 newly missed. low-level-design-05 newly missed. With one run per condition these single-case flips cannot be separated from sampling noise.
- Precision of 1.00 with 50 negatives means the near misses are not yet hard enough to produce false positives.

## Limitations

- n = 10 positives per skill, single run, no confidence intervals. A one-case change moves recall by 0.10.
- No run-to-run variance estimate. Repeating each condition several times is the obvious next step.
- No held-out split. The revision was tuned on the same cases it was scored on, so a gain would have been optimistic anyway.
- Only the first assistant message is inspected. A skill invoked after another tool call is missed.
- The sandbox inherits user-level skills and the user's global `CLAUDE.md`. It is not a clean room.
- One model only (`sonnet` alias). Triggering may differ on other models.
