#!/usr/bin/env python3
"""apex-router telemetry report.

Usage:
  python3 report.py [.router/log.jsonl] [--prices prices.json]

Reads hook records (source="hook") and orchestrator outcome records
(any other line with a "tier" field). Prints tier mix, escalation rate,
verifier approve rate, fallback rate, and token totals per tier.

Cost is reported only when you pass --prices with your current rates,
e.g. {"haiku": {"in": 1.0, "out": 5.0}, "sonnet": {...}, "opus": {...}}
in USD per million tokens. Without it, the script makes no cost claim.
"""
import json
import sys
from collections import Counter, defaultdict

MODEL_OF_TIER = {"S": "haiku", "E": "haiku", "V": "haiku",
                 "N": "sonnet", "H": "opus", "X": "fable"}


def load(path):
    recs, bad = [], 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                bad += 1
    return recs, bad


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "n/a"


def main(argv):
    path, prices = ".router/log.jsonl", None
    args = list(argv)
    if "--prices" in args:
        i = args.index("--prices")
        with open(args[i + 1], encoding="utf-8") as f:
            prices = json.load(f)
        del args[i:i + 2]
    if args:
        path = args[0]
    try:
        recs, bad = load(path)
    except FileNotFoundError:
        print(f"No log at {path}. Nothing has been routed in this project yet.")
        return 0

    hook = [r for r in recs if r.get("source") == "hook"]
    outc = [r for r in recs if r.get("source") != "hook" and "tier" in r]

    print(f"apex-router report  ({path})")
    print(f"records: {len(recs)}  hook: {len(hook)}  outcomes: {len(outc)}  unreadable: {bad}")

    if hook:
        mix = Counter(r.get("tier", "?") for r in hook)
        print("\nDelegations by tier (hook):")
        for t in ["S", "E", "N", "H", "X", "V", "?"]:
            if mix[t]:
                print(f"  {t}: {mix[t]:>4}  {pct(mix[t], len(hook))}")
        fb = sum(1 for r in hook if r.get("fallback"))
        np_ = sum(1 for r in hook if r.get("model") == "(not passed)")
        esc = sum(1 for r in hook if r.get("escalated_from"))
        work = sum(1 for r in hook if r.get("tier") not in ("V", "?"))
        print(f"\nfallback (proxy agent) rate: {pct(fb, len(hook))}  ({fb})")
        print(f"model not passed explicitly: {np_}")
        print(f"escalations: {esc}  rate vs work delegations: {pct(esc, work)}"
              + ("  <-- above 30%, specs are too thin" if work and esc / work > 0.3 else ""))

        tok = defaultdict(lambda: {"in": 0, "out": 0})
        known = 0
        for r in hook:
            t = r.get("tokens") or {}
            if not t:
                continue
            known += 1
            m = r.get("model") if r.get("model") not in (None, "(not passed)") \
                else MODEL_OF_TIER.get(r.get("tier"), "unknown")
            tok[m]["in"] += (t.get("input_tokens", 0) + t.get("cache_creation_input_tokens", 0)
                             + t.get("cache_read_input_tokens", 0))
            tok[m]["out"] += t.get("output_tokens", 0)
            if "total_tokens" in t and not t.get("output_tokens"):
                tok[m]["in"] += t["total_tokens"]
        print(f"\ntoken data present on {known}/{len(hook)} delegations")
        for m, v in sorted(tok.items()):
            print(f"  {m:<8} in={v['in']:>10,}  out={v['out']:>9,}")
        if prices and tok:
            actual = base = 0.0
            op = prices.get("opus")
            for m, v in tok.items():
                p = prices.get(m)
                if p:
                    actual += (v["in"] * p["in"] + v["out"] * p["out"]) / 1e6
                if op:
                    base += (v["in"] * op["in"] + v["out"] * op["out"]) / 1e6
            print(f"\nestimated cost: ${actual:,.4f}   all-Opus baseline: ${base:,.4f}"
                  f"   saving: {pct(base - actual, base)}  (estimate, logged tokens only)")

    if outc:
        v = Counter(r.get("verdict") for r in outc)
        d = Counter(r.get("done_check") for r in outc)
        judged = v["approve"] + v["reject"]
        print("\nOutcomes (orchestrator):")
        print(f"  verifier approve rate: {pct(v['approve'], judged)}  "
              f"(approve {v['approve']}, reject {v['reject']}, skipped {v['skipped']})")
        print(f"  done-check pass rate: {pct(d['pass'], d['pass'] + d['fail'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
