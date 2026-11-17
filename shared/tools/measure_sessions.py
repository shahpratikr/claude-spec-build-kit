"""Measure Claude Code sessions that ran these skills: cost, effort, skill escapes, context, reviewers, rounds, phase timings.

Reads the transcripts Claude Code writes under ~/.claude/projects/<project>/<session>.jsonl and their
subagents/ folders. Usage: python3 measure_sessions.py [--filter TEXT] [--since YYYY-MM-DD] [SESSION_PREFIX ...]
"""
import argparse
import bisect
import collections
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / ".claude" / "projects"
RECORD = re.compile(r"^\s*-?\s*(R[123]):\s*(.*)$", re.M)
FIX_PLAN = re.compile(r"fix-plan check r\d+:[^\n]*")
VERDICT = re.compile(r"Verdict:\s*(PASS|NEEDS REVIEW)[^\n]*")
ORIGIN = re.compile(r"Origin counts:\s*FIX\s*(\d+),\s*MISSED\s*(\d+)")
FIX_PLAN_START = re.compile(r"fix plan r(\d+) start")
FIX_PLAN_END = re.compile(r"fix-plan check r(\d+):")
REVIEWERS = {"ac-auditor", "gap-hunter", "convention-checker", "fix-verifier"}
IDLE_SECONDS = 15 * 60


def entries(path):
    """Yield the JSON lines of a transcript, skipping a partial last line."""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def texts(message):
    content = message.get("content")
    if isinstance(content, str):
        return [content]
    return [c.get("text", "") for c in content or [] if isinstance(c, dict) and c.get("type") == "text"]


def calls(path):
    """One record per API request: the last usage seen for each requestId wins."""
    by_request, order = {}, []
    for d in entries(path):
        if d.get("type") != "assistant" or d["message"].get("model") == "<synthetic>":
            continue
        rid = d.get("requestId") or d["message"].get("id")
        if rid not in by_request:
            order.append(rid)
        by_request[rid] = d
    return [by_request[r] for r in order]


def subagents(session_dir):
    rows = []
    for meta_path in sorted((session_dir / "subagents").glob("*.meta.json")):
        meta = json.loads(meta_path.read_text())
        transcript = meta_path.with_name(meta_path.name.replace(".meta.json", ".jsonl"))
        cs = calls(transcript) if transcript.exists() else []
        usage = collections.Counter()
        for d in cs:
            u = d["message"].get("usage") or {}
            usage["out"] += u.get("output_tokens", 0)
            usage["read"] += u.get("cache_read_input_tokens", 0)
        origin = None
        for d in entries(transcript) if transcript.exists() else []:
            if d.get("type") == "assistant":
                for c in d["message"].get("content", []):
                    blob = c.get("text", "") if c.get("type") == "text" else json.dumps(c.get("input", "")) if c.get("type") == "tool_use" else ""
                    m = ORIGIN.search(blob.replace("\\n", "\n"))
                    if m:
                        origin = (int(m.group(1)), int(m.group(2)))
        rows.append({
            "type": meta.get("agentType", "?"),
            "shape": meta.get("requestShape", "?"),
            "models": sorted({d["message"].get("model") for d in cs}),
            "efforts": sorted({str(d.get("effort")) for d in cs}),
            "calls": len(cs), "out": usage["out"], "read": usage["read"], "origin": origin,
        })
    return rows


def parse_time(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError):
        return None


class Clock:
    """Active time between two instants: every gap between transcript entries over 15 minutes counts as idle."""

    def __init__(self, stamps):
        self.stamps = sorted(stamps)
        self.cumulative = [0.0]
        for a, b in zip(self.stamps, self.stamps[1:]):
            self.cumulative.append(self.cumulative[-1] + (b - a if b - a <= IDLE_SECONDS else 0))

    def between(self, t0, t1):
        i = bisect.bisect_left(self.stamps, t0)
        j = bisect.bisect_right(self.stamps, t1) - 1
        return max(0.0, self.cumulative[j] - self.cumulative[i]) if self.stamps and 0 <= i <= j < len(self.stamps) else 0.0


def phases(path):
    """Active minutes, time before the first review, reviewer wall time per round, the gap between rounds and each fix plan."""
    stamps, started, ended, spawned = [], {}, {}, {}
    markers = {"start": {}, "end": {}}
    for d in entries(path):
        t = parse_time(d.get("timestamp"))
        if t is None:
            continue
        stamps.append(t)
        content = d.get("message", {}).get("content") if isinstance(d.get("message"), dict) else None
        for c in content if isinstance(content, list) else []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use" and c.get("name") in ("Agent", "Task"):
                kind = (c.get("input") or {}).get("subagent_type")
                if kind in REVIEWERS:
                    started[c["id"]], spawned[c["id"]] = t, kind
            elif c.get("type") == "tool_result" and c.get("tool_use_id") in started:
                ended[c["tool_use_id"]] = t
            elif c.get("type") == "text" and d.get("type") == "assistant":
                for pattern, key in ((FIX_PLAN_START, "start"), (FIX_PLAN_END, "end")):
                    for n in pattern.findall(c.get("text", "")):
                        markers[key].setdefault(int(n), t)
    if not stamps:
        return None
    clock = Clock(stamps)
    runs = sorted((started[i], ended.get(i, started[i])) for i in started)
    rounds = []
    for t0, t1 in runs:
        if rounds and t0 <= rounds[-1][1]:
            rounds[-1][1] = max(rounds[-1][1], t1)
        else:
            rounds.append([t0, t1])
    return {
        "active": clock.between(stamps[0], stamps[-1]) / 60,
        "before_review": clock.between(stamps[0], rounds[0][0]) / 60 if rounds else None,
        "rounds": [clock.between(a, b) / 60 for a, b in rounds],
        "gaps": [clock.between(rounds[k][1], rounds[k + 1][0]) / 60 for k in range(len(rounds) - 1)],
        "fix_plans": {n: clock.between(markers["start"][n], markers["end"][n]) / 60
                      for n in sorted(markers["start"]) if n in markers["end"] and markers["end"][n] >= markers["start"][n]},
    }


def phase_line(ph):
    if not ph:
        return None
    parts = [f"active {ph['active']:.0f}m"]
    if ph["before_review"] is not None:
        parts.append(f"before review {ph['before_review']:.0f}m")
    if ph["rounds"]:
        parts.append(f"reviewers {sum(ph['rounds']):.0f}m (" + ", ".join(f"R{i} {m:.0f}m" for i, m in enumerate(ph["rounds"], 1)) + ")")
    if ph["gaps"]:
        parts.append("review gaps " + ", ".join(f"R{i}->R{i + 1} {m:.0f}m" for i, m in enumerate(ph["gaps"], 1)))
    if ph["fix_plans"]:
        parts.append("fix plan " + ", ".join(f"r{n} {m:.0f}m" for n, m in ph["fix_plans"].items()))
    return "time: " + ", ".join(parts) + " (gaps over 15 min counted as idle)"


def measure(path):
    cost_state, skill_started, texts_all = None, False, []
    read_ids, read_sizes = set(), []
    for d in entries(path):
        kind = d.get("type")
        if kind == "cost-state":
            cost_state = d
        elif kind == "assistant":
            for c in d["message"].get("content", []):
                if c.get("type") == "tool_use" and c.get("name") == "Read":
                    read_ids.add(c["id"])
            texts_all += texts(d["message"])
        elif kind == "user" and isinstance(d["message"].get("content"), list):
            for c in d["message"]["content"]:
                if isinstance(c, dict) and c.get("type") == "tool_result" and c.get("tool_use_id") in read_ids:
                    read_sizes.append(len(json.dumps(c.get("content", ""))))
    main = calls(path)
    skills = collections.Counter(d.get("attributionSkill") for d in main)
    escapes = 0
    for d in main:
        if d.get("attributionSkill"):
            skill_started = True
        elif skill_started:
            escapes += 1
    peak = max((sum((d["message"].get("usage") or {}).get(k, 0) for k in
                    ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")) for d in main), default=0)
    joined = "\n".join(texts_all)
    return {
        "cost": cost_state.get("totalCostUSD", 0.0) if cost_state else 0.0,
        "lines": cost_state.get("totalLinesAdded", 0) if cost_state else 0,
        "skill": next((s for s, _ in skills.most_common() if s), None),
        "calls": len(main), "escapes": escapes, "peak": peak,
        "models": dict(collections.Counter(d.get("requestedModel") for d in main)),
        "efforts": dict(collections.Counter(str(d.get("effort")) for d in main)),
        "read_mean": sum(read_sizes) // len(read_sizes) if read_sizes else 0,
        "records": [f"{n}: {r[:150]}" for n, r in RECORD.findall(joined)
                    if "reviewers" in r or r.startswith("skipped")][-4:],
        "fix_plans": FIX_PLAN.findall(joined)[-3:],
        "verdict": (VERDICT.findall(joined) or [None])[-1],
        "subagents": subagents(path.with_suffix("")),
        "phases": phases(path),
        "start": next((d.get("timestamp") for d in main), ""),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sessions", nargs="*", help="session id prefixes (default: all that match)")
    ap.add_argument("--filter", help="only transcripts containing this text, e.g. a repository name")
    ap.add_argument("--since", help="only sessions started on or after this date (YYYY-MM-DD)")
    ap.add_argument("--projects", type=Path, default=ROOT, help="Claude Code projects folder")
    args = ap.parse_args(argv)
    paths = sorted(args.projects.glob("*/*.jsonl"))
    if args.sessions:
        paths = [p for p in paths if any(p.stem.startswith(s) for s in args.sessions)]
    if args.filter:
        paths = [p for p in paths if args.filter in p.read_text(encoding="utf-8", errors="replace")]
    total = collections.Counter()
    for path in paths:
        m = measure(path)
        if args.since and m["start"][:10] < args.since:
            continue
        total["sessions"] += 1
        total["cost"] += m["cost"]
        total["escapes"] += m["escapes"]
        print(f"{path.stem[:8]} {m['start'][:16]} skill={m['skill']} ${m['cost']:.2f} +{m['lines']} lines"
              + (f" (${100 * m['cost'] / m['lines']:.2f}/100 lines)" if m["lines"] else ""))
        print(f"  main calls {m['calls']}, outside the skill after it started {m['escapes']}, peak context {m['peak'] // 1000}k,"
              f" mean Read result {m['read_mean']} chars")
        print(f"  models {m['models']}  effort {m['efforts']}")
        for s in m["subagents"]:
            print(f"  agent {s['type']:<18} {s['shape']:<10} {','.join(filter(None, s['models']))} effort {','.join(s['efforts'])}"
                  f" calls {s['calls']} out {s['out'] // 1000}k" + (f" origin FIX {s['origin'][0]} MISSED {s['origin'][1]}" if s["origin"] else ""))
        if phase_line(m["phases"]):
            print(f"  {phase_line(m['phases'])}")
        for line in m["records"] + m["fix_plans"]:
            print(f"  {line}")
        if m["verdict"]:
            print(f"  Verdict: {m['verdict']}")
    print(f"TOTAL {total['sessions']} sessions, ${total['cost']:.2f}, {total['escapes']} main calls outside their skill")
    return 0


if __name__ == "__main__":
    sys.exit(main())
