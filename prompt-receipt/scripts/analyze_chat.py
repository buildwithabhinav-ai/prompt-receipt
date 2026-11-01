#!/usr/bin/env python3
"""Analyze one Claude Code chat log: tokens per prompt, weak-prompt flags, rework.

Reads a session .jsonl from ~/.claude/projects (read-only, no network) and
prints JSON (default) or a plain table (--format table).

    analyze_chat.py                       # newest chat of the current folder
    analyze_chat.py --list                # recent chats, to pick one
    analyze_chat.py --session <id|path>   # a specific chat
"""
import argparse
import json
import os
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"

# Relative price weights (input = 1). Dollar cost is never hardcoded: the log's
# own cost-state total is split by these weights instead.
W_IN, W_CACHE_WRITE, W_CACHE_READ, W_OUT = 1.0, 1.25, 0.1, 5.0

SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|AIza[0-9A-Za-z_-]{20,}|ghp_[A-Za-z0-9]{20,}|"
    r"xox[abp]-[A-Za-z0-9-]{10,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}|"
    r"(?i:(?:api[_-]?key|secret|token|password|passwd)\s*[=:]\s*\S+))"
)
NOISE_PREFIXES = ("<command-", "<local-command", "<system-reminder", "Caveat:",
                  "<task-notification", "<ci-monitor", "<side-sessions")
INTERRUPT_RE = re.compile(r"^\[Request interrupted")

FILE_RE = re.compile(
    r"\b[\w./-]+\.(?:py|js|jsx|ts|tsx|html|css|scss|json|md|yml|yaml|sql|ipynb|env|"
    r"txt|csv|h5|keras|pt|pth|pkl|toml|ini|sh|vue|java|go|rs|php|dockerfile)\b", re.I)
PATH_RE = re.compile(r"(?<![\w:])(?:\.{0,2}/)?[\w-]+/[\w./-]+")
CODE_RE = re.compile(r"`[^`\n]+`|\b[a-z]+_[a-z0-9_]+\b|\b[a-z]+[A-Z][A-Za-z0-9]+\b|\b/api/\S+|localhost:\d+")
ERROR_EVIDENCE_RE = re.compile(
    r"Traceback|\b\w*(?:Error|Exception)\b|\b[45]\d\d\b|\bat \S+:\d+|ECONN\w+|ModuleNotFound|"
    r"\bline \d+\b|\bstack\b|console\b|npm ERR|failed to|cannot |can't find|not found|undefined", re.I)
PROBLEM_RE = re.compile(
    r"\b(error|errors|bug|bugs|not working|doesn'?t work|isn'?t working|broken|fail(?:s|ed|ing)?|"
    r"crash\w*|issue|issues|problem|wrong|fix)\b", re.I)
VAGUE_RE = re.compile(
    r"\b(properly|everything|whole|all of it|somehow|something|stuff|things|etc|better|good|"
    r"nice|correctly|as needed|any issue|all issues|whatever)\b", re.I)
OUTCOME_RE = re.compile(
    r"\b(should|expected|expect|so that|must|want it to|instead of|returns?|displays?|shows?|"
    r"then it|when i|result|output|response|status)\b", re.I)
ACTION_RE = re.compile(
    r"\b(add|build|create|make|implement|write|fix|change|update|remove|delete|refactor|connect|"
    r"integrate|design|generate|convert|move|rename|setup|set up|deploy|install|test|complete|"
    r"finish|improve|optimi[sz]e|replace|use)\b", re.I)
QUESTION_START_RE = re.compile(
    r"^(who|what|why|how|when|where|which|is|are|can|could|does|do|did|will|would|should|"
    r"explain|tell me|show me|list)\b", re.I)
CORRECTION_RE = re.compile(
    r"^(no\b|nope|not\b|still\b|again\b|wrong|that'?s not|thats not|i said|i asked|i told|why did|"
    r"undo|revert|instead\b|same (?:error|issue|problem)|nothing (?:changed|happened)|"
    r"it'?s still|it is still|didn'?t work|doesn'?t work|not working|but (?:it|the|now))|"
    r"\b(still (?:not|getting|showing|failing|the same)|same error|not fixed|didn'?t (?:fix|work)|"
    r"not resolved|still not)\b", re.I)
# "No", "Not yet", "no thanks" answer a question Claude asked. They are not "that did not work" complaints.
ANSWER_NO_RE = re.compile(r"^(no|nope|nah|not (yet|now)|no,? thanks|never mind)\b[^a-z0-9]*(keep it \w+|for now|later)?[^a-z0-9]*$", re.I)
APPROVAL_RE = re.compile(
    r"^(yes|yeah|yep|yup|ok|okay|sure|go ahead|go on|proceed|approved?|do it|sounds good|please do|continue)\b", re.I)
PHASES = [
    ("ml-model", r"\b(model|train|predict|inference|dataset|cnn|accuracy|epoch|tensorflow|keras|torch|"
                 r"classif|segment|weights|\.h5|\.pt|rag|embedding|vector)\b"),
    ("frontend", r"\b(frontend|front-end|ui|ux|page|component|css|style|layout|responsive|button|"
                 r"navbar|design|react|tailwind|html|screen|dashboard|tab|form)\b"),
    ("backend", r"\b(backend|api|endpoint|route|server|database|db|sql|auth|login|jwt|flask|fastapi|"
                r"django|express|schema|migration|invite|admin|org)\b"),
    ("debug", r"\b(error|bug|fix|not working|broken|crash|fail|traceback|exception)\b"),
    ("deploy", r"\b(deploy|vercel|render|docker|hosting|production|build|ci|env)\b"),
    ("testing", r"\b(test|tests|testing|verify|check|e2e|end to end)\b"),
]
WORD_RE = re.compile(r"[a-z][a-z0-9_]{2,}")
STOP = set("the and for that this with from have into what when where how are was were you your "
           "can will would should could its not but all any use then them they there here just "
           "also more some one two out about over like make want need".split())


def redact(text):
    return SECRET_RE.sub("[redacted]", text)


def encode_cwd(cwd):
    return re.sub(r"[^A-Za-z0-9]", "-", cwd)


def find_logs(project_dir=None):
    d = Path(project_dir) if project_dir else PROJECTS / encode_cwd(os.getcwd())
    if not d.is_dir():
        return d, []
    return d, sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)


def resolve_session(arg, project_dir):
    if arg:
        p = Path(arg).expanduser()
        if p.is_file():
            return p
        # a bare session id, in this project or any project
        d, logs = find_logs(project_dir)
        for lp in logs:
            if lp.stem.startswith(arg):
                return lp
        for lp in PROJECTS.glob(f"*/{arg}*.jsonl"):
            return lp
        sys.exit(f"No chat log found for '{arg}'. Try --list.")
    d, logs = find_logs(project_dir)
    if not logs:
        recent = sorted(PROJECTS.glob("*/*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
        hint = "\n".join(f"  {p.parent.name}  {p.stem}" for p in recent)
        sys.exit(f"No chat logs in {d}.\nThe shell's folder may differ from the chat's project folder. "
                 f"Pass --project-dir or --session. Newest chats anywhere:\n{hint}\n"
                 "(No logs at all? Use the fallback in SKILL.md.)")
    return logs[0]


def human_text(row):
    """Return (text, has_image) if this user row is a real typed prompt, else None."""
    if row.get("type") != "user" or row.get("isMeta") or row.get("isSidechain"):
        return None
    c = row.get("message", {}).get("content")
    if isinstance(c, str):
        text, img = c, False
    elif isinstance(c, list):
        if any(b.get("type") == "tool_result" for b in c):
            return None
        text = "\n".join(b.get("text", "") for b in c if b.get("type") == "text")
        img = any(b.get("type") == "image" for b in c)
        if not text.strip():
            return ("", True) if img else None
    else:
        return None
    s = text.strip()
    if not s or s.startswith(NOISE_PREFIXES) or INTERRUPT_RE.match(s):
        return None
    if s.startswith("This session is being continued from a previous conversation"):
        return None               # auto-summary after /compact, not something the user typed
    return s, img


def load(path):
    rows = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def parse_ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


COMMAND_RE = re.compile(r"<command-name>\s*(/?[^<\s]+)\s*</command-name>")
IDLE_CAP = 600      # seconds: a longer pause between two log rows counts as 10 minutes


def command_name(row):
    """Return '/name' if this user row is a slash command typed by the user (e.g. /prompt-receipt)."""
    if row.get("type") != "user" or row.get("isMeta") or row.get("isSidechain"):
        return None
    c = row.get("message", {}).get("content")
    if isinstance(c, list):
        c = "\n".join(b.get("text", "") for b in c if b.get("type") == "text")
    m = COMMAND_RE.search(c) if isinstance(c, str) else None
    return m.group(1) if m else None


def new_turn(n, text, img, ts, command=False):
    return {"n": n, "text": text, "has_image": img, "start": ts, "end": ts, "last": ts, "active": 0.0,
            "command": command, "gap_before": 0.0, "reqs": {}, "tools": Counter(), "tool_ids": set(), "tool_errors": 0,
            "reads": Counter(), "interrupted": False, "sidechain_reqs": 0}


def tick(turn, ts):
    """Mark the chat as active at ts, without counting long idle gaps."""
    if not ts:
        return
    if turn["last"]:
        turn["active"] += min((ts - turn["last"]).total_seconds(), IDLE_CAP)
    turn["last"] = turn["end"] = ts


def parse_session(path):
    rows = load(path)
    turns, cur = [], None
    cost_state, meta = None, {}
    last_ts = None
    for r in rows:
        t = r.get("type")
        ts = parse_ts(r.get("timestamp", "")) if r.get("timestamp") else None
        gap = 0.0                      # seconds of silence before this row (a break in the chat)
        if ts and t in ("user", "assistant"):
            gap = (ts - last_ts).total_seconds() if last_ts else 0.0
            last_ts = ts
        for k in ("sessionId", "cwd", "version", "entrypoint", "gitBranch"):
            if r.get(k) and k not in meta:
                meta[k] = r[k]
        if t == "cost-state":
            cost_state = r
            continue
        if t == "user":
            cmd = command_name(r)
            if cmd:       # a slash command starts its own turn, so its cost is not charged to the prompt before it
                cur = new_turn(len(turns) + 1, cmd, False, ts, command=True)
                cur["gap_before"] = gap
                turns.append(cur)
                continue
            h = human_text(r)
            if h is not None:
                text, img = h
                if text == "" and cur is not None:       # image-only follow-up: attach
                    cur["has_image"] = True
                    continue
                cur = new_turn(len(turns) + 1, text, img, ts)
                cur["gap_before"] = gap
                turns.append(cur)
                continue
            if cur is None:
                continue
            c = r.get("message", {}).get("content")
            if isinstance(c, str) and INTERRUPT_RE.match(c.strip()):
                cur["interrupted"] = True
            if isinstance(c, list):
                for b in c:
                    if b.get("type") == "tool_result" and b.get("is_error"):
                        cur["tool_errors"] += 1
                    elif b.get("type") == "text" and INTERRUPT_RE.match(b.get("text", "")):
                        cur["interrupted"] = True
                if r.get("isMeta") and any(b.get("type") == "image" for b in c):
                    cur["has_image"] = True
            tick(cur, ts)
        elif t == "assistant" and cur is not None:
            m = r.get("message", {})
            u = m.get("usage") or {}
            key = r.get("requestId") or m.get("id") or r.get("uuid")
            prev = cur["reqs"].get(key, {})
            od = u.get("output_tokens_details") or {}
            cur["reqs"][key] = {
                "in": max(prev.get("in", 0), u.get("input_tokens", 0)),
                "cw": max(prev.get("cw", 0), u.get("cache_creation_input_tokens", 0)),
                "cr": max(prev.get("cr", 0), u.get("cache_read_input_tokens", 0)),
                "out": max(prev.get("out", 0), u.get("output_tokens", 0)),
                "think": max(prev.get("think", 0), od.get("thinking_tokens", 0) or 0),
                "model": m.get("model") or prev.get("model"),
            }
            if r.get("isSidechain"):
                cur["sidechain_reqs"] += 1
            for b in m.get("content") or []:
                if b.get("type") == "tool_use" and b.get("id") not in cur["tool_ids"]:
                    cur["tool_ids"].add(b.get("id"))
                    cur["tools"][b.get("name", "?")] += 1
                    inp = b.get("input") or {}
                    if b.get("name") in ("Read", "Edit", "Write") and inp.get("file_path"):
                        cur["reads"][inp["file_path"]] += 1
            tick(cur, ts)
    return turns, cost_state, meta


def content_words(text):
    return {w for w in WORD_RE.findall(text.lower()) if w not in STOP}


def classify(text):
    s = text.strip()
    low = s.lower()
    if QUESTION_START_RE.match(low) or (s.endswith("?") and len(s) < 200 and not ACTION_RE.search(low[:25])):
        kind = "question"
    elif len(s.split()) <= 3 and not ACTION_RE.search(low):
        kind = "reply"            # "yes", "done", "go ahead" - answers to Claude
    elif APPROVAL_RE.match(low):
        kind = "reply"            # "Yes, push it" - Claude already proposed it, so the task is named above
    else:
        kind = "action"
    phase = "other"
    for name, rx in PHASES:
        if re.search(rx, low):
            phase = name
            break
    return kind, phase


def flag_prompt(text, kind, has_image):
    """Return (flags, score). Rules are deliberately transparent: see references/rubric.md."""
    flags, score = [], 100
    words = len(text.split())
    low = text.lower()
    targets = len(FILE_RE.findall(text)) + len(PATH_RE.findall(text)) + len(CODE_RE.findall(text))
    problem = bool(PROBLEM_RE.search(text))
    evidence = bool(ERROR_EVIDENCE_RE.search(text)) or has_image or (text.count("\n") >= 3 and len(text) > 300)
    if kind == "reply":
        return flags, None
    if kind == "action" and targets == 0 and len(text) < 500:
        flags.append("no_target"); score -= 25
    if problem and not evidence and kind == "action":
        flags.append("problem_without_evidence"); score -= 25
    if VAGUE_RE.search(text) and kind == "action":
        flags.append("vague_words"); score -= 10
    if kind == "action" and words < 8:
        flags.append("too_short"); score -= 15
    verbs = {m.group(0).lower() for m in ACTION_RE.finditer(text)}
    if kind == "action" and (len(verbs) >= 5 or len(re.findall(r"(?m)^\s*(?:\d+[.)]|[-*])\s", text)) >= 5
                             or low.count(" and also ") + low.count(" also ") >= 2):
        flags.append("multi_task"); score -= 15
    if kind == "action" and not problem and words >= 8 and not OUTCOME_RE.search(text):
        flags.append("no_expected_outcome"); score -= 10
    if len(text) > 4000:
        flags.append("huge_paste"); score -= 5
    return flags, max(score, 0)


def units(r):
    return (r["in"] * W_IN + r["cw"] * W_CACHE_WRITE + r["cr"] * W_CACHE_READ + r["out"] * W_OUT)


VERDICTS = {
    "A": "Clear prompts. Very little to fix.",
    "B": "Good prompts. A few easy wins.",
    "C": "Okay. Some prompts cost more than they needed to.",
    "D": "Costly habits. Fixing two or three prompts will help most.",
    "E": "Most prompts were too vague. Start with the first fix below.",
}
LEVEL_RANK = {"alert": 0, "warn": 1, "info": 2}


def ago(minutes):
    h = minutes / 60
    return f"{h / 24:.0f}-day" if h >= 48 else f"{h:.0f}-hour"


def build_warnings(res, auto_picked):
    """Plain-language heads-ups for the user. Each is {level, code, message}; level is alert, warn or info."""
    t, p = res["totals"], res["patterns"]
    out = []

    def add(level, code, msg):
        out.append({"level": level, "code": code, "message": msg})

    k = lambda n: f"{round(n / 1000):,}k"
    if t["context_peak"] >= 200_000:
        add("alert" if t["context_peak"] >= 500_000 else "warn", "long_chat",
            f"This chat grew to {k(t['context_peak'])} tokens. Claude re-reads all of it on every message, "
            "so each new message gets more expensive. Start a new chat when you change topic.")
    if t["commands"] and t["command_cost_share"] >= 0.15:
        add("warn", "review_cost",
            f"Running this review inside the chat used about {t['command_cost_share']:.0%} of its tokens. "
            "Next time, open a fresh chat and review the old one with --session <id>.")
    shown = 0
    for x in res["turns"][1:]:
        if x["break_before_min"] >= 60 and x["cache_write"] >= 50_000 and shown < 2:
            what = x["prompt"] if x["kind"] == "command" else f'"{x["prompt"][:30].strip()}"'
            add("info", "came_back_after_break",
                f"{what} came after a {ago(x['break_before_min'])} break. Claude had to re-read {k(x['cache_write'])} "
                "tokens at full price. Coming back to an old chat costs extra once; start fresh if you do not need the history.")
            shown += 1
    if p["rework_share"] >= 0.2:
        add("warn", "rework",
            f"About {p['rework_share']:.0%} of the cost went on redoing work after something did not work. "
            "Next time paste the exact error and say what you expected.")
    if p["tool_errors"] >= 5:
        add("info", "tool_errors",
            f"{p['tool_errors']} of Claude's steps failed. Putting your run commands in a CLAUDE.md file usually prevents this.")
    if p["secrets_masked"]:
        add("warn", "secrets",
            "Something in your prompts looked like a password or key, so it is hidden in this review. "
            "Never paste real secrets into a chat.")
    if t["prompts"] < 3:
        add("info", "few_prompts", f"Only {t['prompts']} prompt(s), too few to see a pattern. Treat the score as a rough guide.")
    if t["cost_usd"] is None:
        add("info", "no_cost", "This log has no cost counter, so you see tokens only, not dollars.")
    else:
        add("info", "estimate", "Dollar amounts per prompt are estimates: the log keeps one total for the chat, shared out by token weight.")
    if auto_picked:
        add("info", "picked_chat",
            f"Reviewed the newest chat in this folder ({res['session']['id'][:8]}). Not the right one? Run with --list to pick another.")
    return sorted(out, key=lambda w: LEVEL_RANK[w["level"]])


def analyze(path, top_n, auto_picked=False):
    turns, cost_state, meta = parse_session(path)
    if not any(not t["command"] for t in turns):
        sys.exit("That chat has no typed prompts to review.")
    total_units = 0.0
    out_turns = []
    prev_words = []
    for t in turns:
        reqs = list(t["reqs"].values())
        tin = sum(r["in"] for r in reqs); tcw = sum(r["cw"] for r in reqs)
        tcr = sum(r["cr"] for r in reqs); tout = sum(r["out"] for r in reqs)
        tthink = sum(r["think"] for r in reqs)
        ctx = [r["in"] + r["cw"] + r["cr"] for r in reqs]
        u = sum(units(r) for r in reqs)
        total_units += u
        kind, phase = classify(t["text"])
        flags, score = flag_prompt(t["text"], kind, t["has_image"])
        if not reqs and t["interrupted"]:     # stopped before Claude answered, usually re-sent; nothing to judge
            flags, score = [], None
        shift = False
        if t["command"]:                      # /prompt-receipt, /compact ...: counted in cost, never judged
            kind, phase, flags, score = "command", "other", [], None
        else:
            words = content_words(t["text"])
            recent = set().union(*prev_words[-3:]) if prev_words else set()
            shift = bool(prev_words and len(words) >= 5 and len(words & recent) / max(len(words | recent), 1) < 0.04)
            prev_words.append(words)
        secs = round(t["active"])
        reads = [(p, c) for p, c in t["reads"].items() if c >= 3]
        out_turns.append({
            "n": t["n"], "kind": kind, "phase": phase,
            "prompt": redact(t["text"])[:700], "chars": len(t["text"]), "words": len(t["text"].split()),
            "has_image": t["has_image"], "flags": flags, "score": score,
            "requests": len(reqs), "in": tin, "cache_write": tcw, "cache_read": tcr, "out": tout,
            "thinking": tthink, "units": round(u), "ctx_peak": max(ctx) if ctx else 0,
            "tools": dict(t["tools"]), "tool_errors": t["tool_errors"],
            "interrupted": t["interrupted"], "topic_shift": shift, "seconds": secs,
            "break_before_min": round(t["gap_before"] / 60),
            "reread_files": [{"file": p, "touches": c} for p, c in reads],
            "models": sorted({r["model"] for r in reqs if r["model"]}),
        })
    # correction chains: a prompt followed by a "that didn't work" prompt
    for i, t in enumerate(out_turns):
        t["share"] = t["units"] / total_units if total_units else 0
        t["led_to_correction"] = False
        t["is_correction"] = (i > 0 and t["kind"] != "command" and bool(CORRECTION_RE.search(t["prompt"][:200]))
                              and not ANSWER_NO_RE.match(t["prompt"].strip()))
        if t["is_correction"]:
            out_turns[i - 1]["led_to_correction"] = True
    # rework = the "that didn't work" turns plus the turns they were correcting
    rework_idx = {i for i, t in enumerate(out_turns) if t["is_correction"] or t["led_to_correction"]}
    rework_units = sum(out_turns[i]["units"] for i in rework_idx)
    # session totals
    sums = {k: sum(t[k] for t in out_turns) for k in ("in", "cache_write", "cache_read", "out", "thinking", "requests")}
    all_tok = sums["in"] + sums["cache_write"] + sums["cache_read"] + sums["out"]
    cost = cost_state.get("totalCostUSD") if cost_state else None
    for t in out_turns:
        t["cost_usd_est"] = round(cost * t["share"], 3) if cost is not None else None
    scored = [t for t in out_turns if t["score"] is not None]
    wsum = sum(max(t["share"], 0.01) for t in scored)
    overall = round(sum(t["score"] * max(t["share"], 0.01) for t in scored) / wsum) if scored else None
    fc = Counter(f for t in out_turns for f in t["flags"])
    flagged_units = defaultdict(int)
    for t in out_turns:
        for f in t["flags"]:
            flagged_units[f] += t["units"]
    # repeated file touches across whole session
    allreads = Counter()
    for t in turns:
        allreads.update(t["reads"])
    ctx_peak = max((t["ctx_peak"] for t in out_turns), default=0)
    first, last = turns[0]["start"], turns[-1]["end"]
    models = Counter(m for t in out_turns for m in t["models"] if not m.startswith("<"))
    # active time: time spent inside turns, so overnight gaps between prompts are not counted
    active = sum(t["active"] for t in turns)
    top = sorted((t for t in out_turns if t["kind"] != "command"), key=lambda t: t["units"], reverse=True)[:top_n]
    commands = [t for t in out_turns if t["kind"] == "command"]
    masked = sum(1 for t in turns if SECRET_RE.search(t["text"]))
    grade = None if overall is None else "A" if overall >= 90 else "B" if overall >= 80 else "C" if overall >= 70 else "D" if overall >= 55 else "E"
    res = {
        "session": {"id": meta.get("sessionId"), "path": str(path), "cwd": meta.get("cwd"),
                    "version": meta.get("version"), "entrypoint": meta.get("entrypoint"),
                    "start": first.isoformat() if first else None,
                    "wall_minutes": round((last - first).total_seconds() / 60) if first and last else None,
                    "active_minutes": round(active / 60),
                    "models": dict(models)},
        "totals": {"prompts": len(out_turns) - len(commands), "commands": len(commands),
                   "command_cost_share": round(sum(t["share"] for t in commands), 3),
                   "requests": sums["requests"], **{k: sums[k] for k in ("in", "cache_write", "cache_read", "out", "thinking")},
                   "all_tokens": all_tok, "cache_read_share": round(sums["cache_read"] / all_tok, 3) if all_tok else 0,
                   "context_peak": ctx_peak, "cost_usd": round(cost, 2) if cost is not None else None,
                   "cost_note": "from the chat's own cost counter" if cost is not None else "no cost counter in log; tokens only"},
        "score": {"overall": overall, "grade": grade,
                  "verdict": VERDICTS.get(grade, "Not enough prompts to give a grade."),
                  "note": "weighted by each prompt's share of cost; see references/rubric.md"},
        "patterns": {
            "flag_counts": dict(fc),
            "flag_cost_share": {f: round(u / total_units, 3) for f, u in flagged_units.items()} if total_units else {},
            "corrections": sum(1 for t in out_turns if t["is_correction"]),
            "rework_share": round(rework_units / total_units, 3) if total_units else 0,
            "topic_shifts": [{"turn": t["n"], "context_before": out_turns[i - 1]["ctx_peak"] if i else 0}
                             for i, t in enumerate(out_turns) if t["topic_shift"]],
            "files_touched_3plus": [{"file": p, "touches": c} for p, c in allreads.most_common(8) if c >= 3],
            "tool_errors": sum(t["tool_errors"] for t in out_turns),
            "secrets_masked": masked,
            "interrupted_turns": [t["n"] for t in out_turns if t["interrupted"]],
            "phases": dict(Counter(t["phase"] for t in out_turns)),
            "median_prompt_words": statistics.median([t["words"] for t in out_turns if t["kind"] not in ("reply", "command")] or [0]),
        },
        "top_cost_turns": [t["n"] for t in top],
        "turns": out_turns,
    }
    res["warnings"] = build_warnings(res, auto_picked)
    return res


def list_logs(project_dir, limit):
    d, logs = find_logs(project_dir)
    if not logs:
        print(f"No chat logs in {d}")
        return
    print(f"Chats in {d}\n")
    for p in logs[:limit]:
        first = ""
        n = 0
        for row in load(p):
            h = human_text(row)
            if h and h[0]:
                n += 1
                first = first or h[0]
        when = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"{p.stem}  {when}  {n:>3} prompts  {redact(first)[:70]!r}")


def print_table(res):
    s, t = res["session"], res["totals"]
    print(f"Chat {s['id']}  ({s['active_minutes']} min active, {s['wall_minutes']} min start to end)  models: {s['models']}")
    print(f"Prompts {t['prompts']} | requests {t['requests']} | all tokens {t['all_tokens']:,} "
          f"(cache-read {t['cache_read_share']:.0%}) | output {t['out']:,} | peak context {t['context_peak']:,} | "
          f"cost {'n/a' if t['cost_usd'] is None else '$' + str(t['cost_usd'])}")
    print(f"Prompt score {res['score']['overall']} ({res['score']['grade']}) | "
          f"corrections {res['patterns']['corrections']} | rework {res['patterns']['rework_share']:.0%} of cost")
    print(f"Verdict: {res['score']['verdict']}")
    for w in res["warnings"]:
        print(f"  [{w['level'].upper()}] {w['message']}")
    print()
    print(f"{'#':>3} {'share':>6} {'ctx':>8} {'score':>5}  {'kind':<8} {'flags':<40} prompt")
    for x in res["turns"]:
        sc = "-" if x["score"] is None else x["score"]
        flags = ",".join(x["flags"] + (["CORRECTION"] if x["is_correction"] else []))
        print(f"{x['n']:>3} {x['share']:>6.1%} {x['ctx_peak']:>8,} {sc:>5}  {x['kind']:<8} {flags:<40.40} "
              f"{x['prompt'][:60]!r}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session", help="session id (or prefix) or path to a .jsonl")
    ap.add_argument("--project-dir", help="folder holding the .jsonl logs (default: current folder's)")
    ap.add_argument("--list", action="store_true", help="list recent chats and exit")
    ap.add_argument("--limit", type=int, default=15, help="rows for --list")
    ap.add_argument("--top", type=int, default=5, help="how many costliest prompts to name")
    ap.add_argument("--format", choices=["json", "table"], default="json")
    a = ap.parse_args()
    if a.list:
        return list_logs(a.project_dir, a.limit)
    res = analyze(resolve_session(a.session, a.project_dir), a.top, auto_picked=not a.session)
    if a.format == "table":
        print_table(res)
    else:
        json.dump(res, sys.stdout, indent=1, default=str)
        print()


if __name__ == "__main__":
    main()
