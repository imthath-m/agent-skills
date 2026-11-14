#!/usr/bin/env python3
"""Judge-vs-human agreement metrics (stdlib only).

Usage: python agreement.py labels.csv [--order low,mid,high] [--boot 2000] [--seed 0]

CSV needs columns `human` and `judge`. Labels are strings; if all parse as
numbers they are ordered numerically, otherwise alphabetically unless --order is given.
Reports: raw agreement, Cohen's kappa, linear/quadratic weighted kappa (only
meaningful for ordinal labels), confusion matrix (rows=human, cols=judge),
per-class precision/recall (human = reference), bootstrap 95% CI for kappas.
"""
import argparse, csv, random


def kappa(pairs, cats, power=0):
    """power=0 unweighted, 1 linear, 2 quadratic. Returns None if undefined."""
    k, n = len(cats), len(pairs)
    idx = {c: i for i, c in enumerate(cats)}
    obs = [[0] * k for _ in range(k)]
    for h, j in pairs:
        obs[idx[h]][idx[j]] += 1
    rh = [sum(r) for r in obs]
    cj = [sum(obs[i][j] for i in range(k)) for j in range(k)]

    def w(i, j):  # disagreement weight
        if power == 0:
            return 0.0 if i == j else 1.0
        return (abs(i - j) / (k - 1)) ** power if k > 1 else 0.0

    num = sum(w(i, j) * obs[i][j] for i in range(k) for j in range(k))
    den = sum(w(i, j) * rh[i] * cj[j] / n for i in range(k) for j in range(k))
    return None if den == 0 else 1 - num / den


def boot_ci(pairs, cats, power, B, rng):
    vals = []
    for _ in range(B):
        s = [rng.choice(pairs) for _ in pairs]
        v = kappa(s, cats, power)
        if v is not None:
            vals.append(v)
    if len(vals) < B * 0.5:
        return None
    vals.sort()
    return vals[int(0.025 * len(vals))], vals[min(int(0.975 * len(vals)), len(vals) - 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--order", help="comma-separated label order (ordinal scales)")
    ap.add_argument("--boot", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    with open(a.csv, newline="") as f:
        rows = [(r["human"].strip(), r["judge"].strip()) for r in csv.DictReader(f)]
    if not rows:
        raise SystemExit("no rows")
    cats = set(x for p in rows for x in p)
    if a.order:
        cats = a.order.split(",")
        missing = set(x for p in rows for x in p) - set(cats)
        if missing:
            raise SystemExit(f"labels not in --order: {sorted(missing)}")
    else:
        try:
            cats = sorted(cats, key=float)
        except ValueError:
            cats = sorted(cats)
    n, k = len(rows), len(cats)
    rng = random.Random(a.seed)

    print(f"n={n} classes={cats}")
    print(f"raw agreement: {sum(h == j for h, j in rows) / n:.3f}")
    for name, p in [("cohen kappa", 0), ("linear weighted kappa", 1), ("quadratic weighted kappa", 2)]:
        v = kappa(rows, cats, p)
        if v is None:
            print(f"{name}: undefined (no variation in labels)")
            continue
        ci = boot_ci(rows, cats, p, a.boot, rng) if a.boot else None
        extra = f"  95% bootstrap CI [{ci[0]:.3f}, {ci[1]:.3f}]" if ci else ""
        print(f"{name}: {v:.3f}{extra}")

    print("\nconfusion matrix (rows=human, cols=judge)")
    print("\t" + "\t".join(cats))
    for h in cats:
        print(h + "\t" + "\t".join(str(sum(1 for x in rows if x == (h, j))) for j in cats))

    print("\nper-class (human = reference)\nclass\tprecision\trecall\tsupport")
    for c in cats:
        tp = sum(1 for h, j in rows if h == c and j == c)
        pj = sum(1 for _, j in rows if j == c)
        ph = sum(1 for h, _ in rows if h == c)
        prec = f"{tp / pj:.3f}" if pj else "n/a"
        rec = f"{tp / ph:.3f}" if ph else "n/a"
        print(f"{c}\t{prec}\t{rec}\t{ph}")


if __name__ == "__main__":
    main()
