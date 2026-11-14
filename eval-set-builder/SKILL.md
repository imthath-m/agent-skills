---
name: eval-set-builder
description: Builds a curated evaluation (golden, test, regression) set for an LLM feature or agent from real transcripts, logs, traces or support tickets, including turning logged failures into cases and splitting dev/held-out. Use when asked to build, curate, extend or audit such a set from real usage data.
---

# Eval Set Builder

Turn real usage logs into a small, trustworthy, leak-free eval set. Quality of coverage and gold labels matters more than size.

## 1. Define the purpose
- State the decision the set must inform (ship/no-ship, model swap, prompt change, regression gate).
- Fix the unit of evaluation: single turn, full conversation, or agent trajectory (tool calls + outcome). Cases must be self-contained at that unit.
- Write down what "good" means per task (correctness, safety, tone, tool use).

## 2. Permission and privacy
- Confirm you may use the logs for evaluation (terms, consent, retention policy, data owner sign-off).
- Scrub PII and secrets (names, emails, phones, IDs, keys, addresses) before cases leave the source system. Replace consistently (e.g. `<EMAIL_1>`) so references still make sense.
- Check scrubbed text still reads naturally and the answer did not depend on the removed detail. Keep an access-controlled mapping only if needed.

## 3. Coverage plan (from data, not guesses)
- Read a random sample of the logs (start with ~100-200; adapt to traffic diversity) and build a taxonomy: intents/task types x difficulty x known failure modes.
- Set target counts per cell. Choose allocation deliberately: traffic-weighted (reflects typical use) vs risk-weighted (oversample costly or sensitive cells). Usually mix: a traffic-weighted base plus risk top-ups, reported separately.
- Keep rare-but-critical cells at a minimum count even if traffic share is tiny, and say that the aggregate score is then not a traffic estimate.
- Record what is deliberately excluded (languages, modalities, out-of-scope intents) and why.
- Defaults to adapt, not rules: dozens of cases per important cell lets you spot regressions; a few hundred total is often workable. Small sets give wide uncertainty, so report counts, not just percentages.

## 4. Sample from logs
- Stratify by taxonomy cell, not by recency or frequency alone. Sample across time, users, channels and versions.
- Dedupe exact and near-duplicates (normalise text; compare token shingles). Collapse templated or bot traffic to a few representatives.
- Cap cases per user/conversation so heavy users do not dominate.

## 5. Hard cases and the easy floor
- Mine on purpose: failures, escalations, thumbs-down, retries/rephrasings, abandoned sessions, long or ambiguous inputs, adversarial/injection attempts, multi-intent requests, and tool errors.
- Include cases where the right behaviour is to refuse, or to ask a clarifying question.
- Keep a share of easy, typical cases as a regression floor so fixes for hard cases do not break the basics.
- Tag each case with how it was found so you can report hard-mined and random slices separately.

## 6. Gold answers
- Choose the gold form per task: reference answer (one right answer), rubric/assertions (checkable properties, e.g. "cites refund policy", "calls `lookup_order` once"), or acceptable-set (several valid outputs or actions).
- Have someone who knows the domain write or approve gold. Never accept the current model's output unreviewed; if a model drafts gold, a human must verify it.
- Have a second reviewer label a subset (e.g. 10-20%); resolve disagreements and refine the guidelines.
- Record ambiguity in a `notes` field. Drop or flag cases with no defensible gold instead of forcing one.

## 7. Leakage checks
- No eval input may appear in few-shot or prompt examples, fine-tuning data, or RAG/index content containing the answer verbatim.
- Check near-duplicates across splits, not only exact matches.
- Group by conversation, user, ticket or template so related items stay in one split.
- If the system learns from later data, use a time cutoff: eval cases newer than anything it was tuned or indexed on.
- Run `python3 scripts/check_leakage.py cases.jsonl --ref prompt.txt fewshot.txt` (stdlib only; flags exact/near duplicates across splits, groups spanning splits, inputs found in reference files; exits non-zero on findings). It does not inspect fine-tuning sets or indexes automatically; pass exports as `--ref`.

## 8. Dev / held-out split
- Dev: used freely for iteration and error analysis. Held-out: touched only for final checks.
- Split by group, not by row; stratify so each taxonomy cell appears in both.
- Keep a log of each held-out run (date, system version, who). When it has been consulted often enough that you tune against it, treat it as burnt and refresh it with newly sampled cases.

## 9. Case schema and versioning
One JSON object per line:
```json
{"id": "ref-0042", "input": "...", "context": {}, "gold": {"type": "rubric", "assertions": ["..."]},
 "tags": ["billing", "hard", "refusal"], "source": "ticket-export-2026-10", "split": "dev",
 "group": "conv-981", "version": "1.2.0", "notes": ""}
```
- `context`: system state needed to run the case (prior turns, tool fixtures, docs).
- Version the dataset (semver-style). Keep a CHANGELOG: cases added/removed/relabelled, why, and which scores are no longer comparable.
- Never edit a case silently; relabel with a new version entry.

## Done checklist
- [ ] Decision and unit of evaluation written down
- [ ] Permission confirmed; PII scrubbed and spot-checked
- [ ] Taxonomy built from a log sample; per-cell targets and exclusions recorded
- [ ] Sampling stratified and deduped; hard and easy cases both present
- [ ] Gold written by a domain expert; subset double-reviewed; ambiguous cases flagged or dropped
- [ ] Leakage script clean; group and time splits applied
- [ ] Held-out split sealed and access logged
- [ ] Schema validated; version and changelog written

## Common pitfalls
- Only sampling recent or most frequent traffic, so the set mirrors the easy head.
- Accepting model output as gold, which rewards the current model's mistakes.
- Splitting by row so one conversation or template sits in both splits.
- Tuning on held-out until it stops being held-out.
- Reporting one aggregate over mixed traffic- and risk-weighted cases.
- Scrubbing PII so aggressively that the case becomes unanswerable.
