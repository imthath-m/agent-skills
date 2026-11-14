#!/usr/bin/env python3
"""Leakage check for an eval set.

Usage: check_leakage.py EVAL.jsonl [--ref FILE ...] [--threshold 0.8] [--shingle 3]

EVAL.jsonl rows need: id, input (string), split ("dev"/"heldout"/...), optional group.
Reports: duplicates across splits, groups spanning splits, inputs found in reference files.
Exit code 1 if any finding, 0 if clean, 2 on bad input.
"""
import argparse, json, re, sys
from itertools import combinations


def norm(text):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(text).lower())).strip()


def shingles(text, k):
    toks = text.split()
    if len(toks) <= k:
        return {tuple(toks)}
    return {tuple(toks[i:i + k]) for i in range(len(toks) - k + 1)}


def jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("eval_file")
    ap.add_argument("--ref", nargs="*", default=[], help="prompt/few-shot/other reference text files")
    ap.add_argument("--threshold", type=float, default=0.8, help="near-duplicate Jaccard threshold")
    ap.add_argument("--shingle", type=int, default=3, help="token shingle size")
    args = ap.parse_args()

    rows = []
    try:
        with open(args.eval_file, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                if line.strip():
                    r = json.loads(line)
                    for key in ("id", "input", "split"):
                        if key not in r:
                            raise ValueError(f"line {n}: missing '{key}'")
                    rows.append(r)
    except (OSError, ValueError) as e:  # JSONDecodeError is a ValueError
        print(f"error: {e}", file=sys.stderr)
        return 2

    for r in rows:
        r["_n"] = norm(r["input"])
        r["_s"] = shingles(r["_n"], args.shingle)

    findings = []
    for a, b in combinations(rows, 2):
        if a["split"] == b["split"]:
            continue
        if a["_n"] == b["_n"]:
            findings.append(f"EXACT_DUP across splits: {a['id']} ({a['split']}) == {b['id']} ({b['split']})")
        else:
            j = jaccard(a["_s"], b["_s"])
            if j >= args.threshold:
                findings.append(f"NEAR_DUP across splits (jaccard={j:.2f}): {a['id']} ({a['split']}) ~ {b['id']} ({b['split']})")

    groups = {}
    for r in rows:
        if r.get("group") not in (None, ""):
            groups.setdefault(r["group"], set()).add(r["split"])
    for g, splits in sorted(groups.items(), key=lambda kv: str(kv[0])):
        if len(splits) > 1:
            findings.append(f"GROUP_SPANS_SPLITS: group '{g}' in {sorted(splits)}")

    for path in args.ref:
        try:
            with open(path, encoding="utf-8") as f:
                ref = norm(f.read())
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        for r in rows:
            if r["_n"] and r["_n"] in ref:
                findings.append(f"IN_REFERENCE: {r['id']} ({r['split']}) appears in {path}")

    for line in findings:
        print(line)
    print(f"{len(rows)} cases checked, {len(findings)} finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
