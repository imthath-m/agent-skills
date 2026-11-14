#!/usr/bin/env python3
"""Skill trigger evals: does headless `claude -p` invoke the right repo skill for each prompt?

Usage:
  python3 scripts/run_trigger_evals.py --label baseline [--skills a,b] [--model sonnet] [--limit N]
  python3 scripts/run_trigger_evals.py --compare baseline after
"""
import argparse, json, re, shutil, subprocess, sys, tempfile, threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "evals"
RESULTS = EVALS / "results"
TEXT_CUTOFF = 1500  # chars of plain text with no tool call => model chose to answer directly


def frontmatter(skill_md):
    m = re.match(r"---\n(.*?)\n---", skill_md.read_text(), re.S)
    fields = {}
    for line in (m.group(1).splitlines() if m else []):
        k, _, v = line.partition(":")
        if v:
            fields[k.strip()] = v.strip().strip("\"'")
    return fields


def discover():
    """Return {skill_dir_name: {"name": frontmatter name, "description": str}}."""
    return {p.parent.name: {"name": (fm := frontmatter(p)).get("name", p.parent.name),
                            "description": fm.get("description", "")}
            for p in sorted(REPO.glob("*/SKILL.md"))}


def cli_version():
    try:
        r = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def run_case(prompt, sandbox, model, timeout):
    """Run one headless turn and return (fired skill names, error or None).

    Reads the stream-json events and stops the process as soon as the first top-level assistant
    message ends, so the model's chosen tool calls are known but not run to completion."""
    cmd = ["claude", "-p", prompt, "--model", model, "--output-format", "stream-json", "--verbose",
           "--max-turns", "1", "--no-session-persistence", "--permission-prompts", "none"]
    proc = subprocess.Popen(cmd, cwd=sandbox, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    timer = threading.Timer(timeout, proc.kill)
    timer.start()
    blocks, fired, text_len, done, error = {}, [], 0, False, None
    try:
        for line in proc.stdout:
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("parent_tool_use_id"):  # sub-agent traffic
                continue
            if ev.get("type") == "result":
                done = True
                if ev.get("is_error") and ev.get("subtype") not in ("error_max_turns",) and not fired:
                    error = f"cli result {ev.get('subtype')}: {str(ev.get('result'))[:200]}"
                break
            if ev.get("type") != "stream_event":
                continue
            e = ev["event"]
            if e["type"] == "content_block_start":
                blocks[e["index"]] = {**e["content_block"], "json": ""}
            elif e["type"] == "content_block_delta":
                d = e["delta"]
                if d["type"] == "input_json_delta":
                    blocks[e["index"]]["json"] += d["partial_json"]
                elif d["type"] == "text_delta":
                    text_len += len(d["text"])
            elif e["type"] == "content_block_stop":
                b = blocks.get(e["index"], {})
                if b.get("type") == "tool_use" and b.get("name") == "Skill":
                    try:
                        fired.append(json.loads(b["json"] or "{}").get("skill", "?"))
                    except json.JSONDecodeError:
                        fired.append("?")
            elif e["type"] == "message_stop":
                done = True
                break
            if text_len > TEXT_CUTOFF and not any(b.get("type") == "tool_use" for b in blocks.values()):
                done = True
                break
    finally:
        timed_out = not timer.is_alive() and not done
        timer.cancel()
        proc.kill()
        stderr = proc.stderr.read() if proc.stderr else ""
        proc.wait()
    if timed_out:
        error = f"timeout after {timeout}s"
    elif not done and not error:
        error = f"cli exited {proc.returncode} without a response: {stderr.strip()[-300:]}"
    return fired, error


def ratio(a, b):
    return round(a / b, 3) if b else None


def metrics(records):
    ok = [r for r in records if not r["error"]]
    c = {k: sum(1 for r in ok if (r["should_trigger"], r["triggered"]) == v)
         for k, v in {"TP": (True, True), "FP": (False, True), "FN": (True, False), "TN": (False, False)}.items()}
    return {**c, "precision": ratio(c["TP"], c["TP"] + c["FP"]), "recall": ratio(c["TP"], c["TP"] + c["FN"]),
            "errors": len(records) - len(ok), "cases": len(records)}


def fmt(x):
    return "n/a" if x is None else f"{x:.2f}"


def run(args):
    version = cli_version()
    if not version:
        print("ERROR: `claude` CLI is unavailable (not on PATH or `claude --version` failed). "
              "No results were produced.", file=sys.stderr)
        return 2
    skills = discover()
    wanted = args.skills.split(",") if args.skills else [s for s in skills if (EVALS / s / "cases.jsonl").exists()]
    cases = []
    for s in wanted:
        if s not in skills or not (EVALS / s / "cases.jsonl").exists():
            print(f"ERROR: no skill dir or evals/{s}/cases.jsonl for '{s}'", file=sys.stderr)
            return 1
        lines = [json.loads(l) for l in (EVALS / s / "cases.jsonl").read_text().splitlines() if l.strip()]
        cases += [{**c, "skill": s} for c in lines[:args.limit or None]]

    sandbox = Path(tempfile.mkdtemp(prefix="skill-trigger-evals-"))
    try:
        for s in skills:  # every repo skill is installed so the others act as distractors
            shutil.copytree(REPO / s, sandbox / ".claude" / "skills" / s)

        def one(c):
            fired, error = run_case(c["prompt"], sandbox, args.model, args.timeout)
            ids = {c["skill"], skills[c["skill"]]["name"]}
            triggered = any(f in ids or f.split(":")[-1] in ids for f in fired)
            print(f"  {c['id']}: fired={fired or '-'}{' ERROR ' + error if error else ''}", file=sys.stderr)
            return {"id": c["id"], "skill": c["skill"], "prompt": c["prompt"], "should_trigger": c["should_trigger"],
                    "fired": fired, "triggered": triggered,
                    "correct": None if error else triggered == c["should_trigger"], "error": error}

        print(f"Running {len(cases)} cases with {args.model}, concurrency {args.concurrency}...", file=sys.stderr)
        with ThreadPoolExecutor(args.concurrency) as pool:
            records = list(pool.map(one, cases))
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)

    per_skill = {s: {"description": skills[s]["description"], "frontmatter_name": skills[s]["name"],
                     **metrics([r for r in records if r["skill"] == s])} for s in wanted}
    out = {"label": args.label, "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "model": args.model, "cli_version": version, "concurrency": args.concurrency,
           "num_cases": len(records), "overall": metrics(records), "skills": per_skill, "cases": records}
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{args.label}.json"
    path.write_text(json.dumps(out, indent=2) + "\n")

    print("| skill | precision | recall | TP | FP | FN | TN | errors |\n|---|---|---|---|---|---|---|---|")
    for s, m in [*per_skill.items(), ("**overall (micro)**", out["overall"])]:
        print(f"| {s} | {fmt(m['precision'])} | {fmt(m['recall'])} | {m['TP']} | {m['FP']} | {m['FN']} | {m['TN']} | {m['errors']} |")
    wrong = [r for r in records if r["correct"] is False]
    print(f"\nMisclassified ({len(wrong)}):")
    for r in wrong:
        print(f"- {r['id']} (should_trigger={r['should_trigger']}) fired={r['fired'] or 'none'}")
    errs = [r for r in records if r["error"]]
    if errs:
        print(f"\nErrored, excluded from metrics ({len(errs)}):")
        for r in errs:
            print(f"- {r['id']}: {r['error']}")
    print(f"\nWrote {path.relative_to(REPO)}")
    return 0


def compare(a, b):
    ra, rb = (json.loads((RESULTS / f"{x}.json").read_text()) for x in (a, b))
    print(f"| skill | precision ({a} → {b}) | recall ({a} → {b}) |\n|---|---|---|")
    rows = sorted(set(ra["skills"]) | set(rb["skills"]))
    for s, ma, mb in [(s, ra["skills"].get(s, {}), rb["skills"].get(s, {})) for s in rows] + \
                     [("**overall (micro)**", ra["overall"], rb["overall"])]:
        print(f"| {s} | {fmt(ma.get('precision'))} → {fmt(mb.get('precision'))} "
              f"| {fmt(ma.get('recall'))} → {fmt(mb.get('recall'))} |")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--compare", nargs=2, metavar=("LABEL_A", "LABEL_B"))
    p.add_argument("--label", help="results go to evals/results/<label>.json (required unless --compare)")
    p.add_argument("--skills", help="comma-separated skills whose cases to run (default: all with cases)")
    p.add_argument("--model", default="sonnet")
    p.add_argument("--concurrency", type=int, default=6)
    p.add_argument("--timeout", type=int, default=120, help="seconds per case")
    p.add_argument("--limit", type=int, help="first N cases per skill")
    args = p.parse_args()
    if args.compare:
        return compare(*args.compare)
    if not args.label:
        p.error("--label is required")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
