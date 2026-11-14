---
name: llm-judge-validation
description: Validates and calibrates an LLM judge (autograder) against human labels and decides whether it is trustworthy. Use when measuring judge-human agreement, checking a judge before relying on it, or re-validating after a judge prompt, model, or parameter change.
---

# LLM Judge Validation

Treat the judge as a measuring instrument: prove it agrees with humans, on the slices you care about, before trusting its scores. Bundled helper: `scripts/agreement.py`.

## Workflow

**1. Fix the rubric and unit of judgement**
- State what is judged (one response, a pair, a full trace), the label schema (binary, nominal, ordinal), and written definitions with examples per label.
- Prefer binary or few-level scales; they are easier to label consistently.
- Do not change the rubric mid-study. If it changes, restart.

**2. Sample**
- Stratify across judge score bands, task types, and known failure modes. Oversample rare classes and borderline cases; record each item's stratum.
- Aim for roughly 100-200 items, with at least ~30-50 per class that matters. Reason: kappa and per-class recall on 20 items have confidence intervals too wide to decide anything. Rare-class metrics are driven by that class's count, not total n.
- Sampling from the judge's own scores is fine for stratification, but keep a plain random subset to estimate overall performance.
- Reserve a fresh held-out set for any re-validation (step 6).

**3. Label blind**
- Humans label without seeing judge output, judge rationale, or each other's labels.
- Have 2+ annotators label an overlap subset (e.g. 20-30% of items). Compute human-human agreement first; it is the practical ceiling for the judge.
- If humans disagree widely, fix the rubric before judging the judge.
- Adjudicate disagreements (discussion or a senior reviewer) to produce one gold label; keep the raw labels.

**4. Measure agreement**
- Run `python scripts/agreement.py labels.csv [--order low,mid,high]` on a CSV with `human` and `judge` columns.
- Cohen's kappa for binary/nominal labels; linear or quadratic weighted kappa for ordinal ones (state which weighting).
- Raw agreement misleads under class imbalance: if 90% of items are "pass", always saying "pass" scores 90% with kappa near 0.
- Always report the confusion matrix and per-class precision/recall, since kappa hides which direction the judge errs.
- Report bootstrap 95% confidence intervals. Judge the lower bound, not just the point estimate.
- Compute the same metrics per slice (task type, failure mode, score band).
- Kappa bands (e.g. Landis & Koch "substantial" 0.61-0.80) are a common convention but arbitrary; do not treat them as proof of quality.

**5. Set pass criteria before looking at results**
Write them down first. Defaults to adapt to the stakes, not universal truths:
- Judge-human kappa at least ~0.9x human-human kappa, or an absolute floor (e.g. >= 0.6 for low-stakes triage, higher for gating decisions).
- Lower CI bound above the floor.
- No systematic bias: the confusion matrix is not lopsided (e.g. judge is not consistently more lenient or harsher; false-pass and false-fail rates are both acceptable for the use).
- Minimum per-slice performance (e.g. no slice far below overall, no critical failure mode with recall under a stated bar).
- If humans cannot agree among themselves, the judge cannot be validated beyond that ceiling; say so.

**6. Analyze errors and iterate**
- Read every disagreement (or a large sample). Classify causes: rubric ambiguity, judge misreading, length/position/style bias, label error, missing context.
- Fix rubric or label errors first, then the judge prompt (clearer criteria, examples, reasoning-then-verdict, different model).
- After tuning, re-validate on FRESH held-out labels. Never report agreement on items used to tune the prompt or choose few-shot examples; it is optimistic.

**7. Version and maintain**
- Give each judge a version id: hash of prompt text + model name/version + temperature and other params + rubric + parsing code.
- Tie every validation report to that id. Any change to those inputs invalidates the validation.
- Re-validate on: prompt/rubric/model/params change, a provider model update, a shift in the data distribution, new failure modes.
- Run periodic drift checks: label a small fresh sample on a schedule and compare to the validated baseline; also re-run a fixed anchor set to detect model drift.
- Test judge stability: repeat runs on the same items and report self-agreement.

## Report template
```
Judge: <id/hash>  Model/params: <...>  Rubric: <ver>  Date: <...>
Data: n=<..> (strata: <..>), annotators=<..>, overlap n=<..>
Human-human: kappa <..> [CI]   Judge-human: kappa <..> [CI] (weighting: <..>)
Raw agreement <..>; confusion matrix; per-class precision/recall
Per-slice: <slice: kappa/recall>
Criteria (set before analysis): <...>   Result: PASS / FAIL / CONDITIONAL
Known weaknesses & bias direction: <...>
Allowed use: <e.g. aggregate trend only, not per-item gating>
Next re-validation trigger: <...>
```

## Common pitfalls
- Reporting raw agreement on imbalanced data.
- Humans who saw the judge's output (anchoring) or each other's labels.
- Tuning on the validation set, then reporting on it.
- Setting thresholds after seeing the numbers.
- Too few items in the rare class; wide CIs ignored.
- Averaging over slices so a failing slice is hidden.
- Using unweighted kappa on ordinal scales, or weighted kappa on nominal ones.
- Forgetting that a model or prompt change voids the validation.
- Treating one validated rubric as valid for a different task or distribution.
