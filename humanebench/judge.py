#!/usr/bin/env python3
"""HumaneBench PR check, advisory mode.

Scores a pull request diff against the eight Building Humane Technology
principles. Posts a comment and a neutral check run. Blocks nothing, ever.

Env:
  ANTHROPIC_API_KEY   required
  GITHUB_TOKEN        required in CI
  REPO                owner/name
  PR_NUMBER           pull request number
  BASE_SHA, HEAD_SHA  merge-base diff endpoints
  HUMANEBENCH_MODEL   optional, defaults below
  DRY_RUN             set to 1 to print the result and skip all GitHub calls
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

import anthropic
import requests

MODEL = os.environ.get("HUMANEBENCH_MODEL", "claude-sonnet-4-5")
MAX_DIFF_CHARS = 60_000
# Comment marker. Deliberately unchanged from the original "shadow" name so
# that re-runs keep updating existing PR comments instead of posting new ones.
MARKER = "<!-- humanebench-shadow -->"
# Deliberately no red. Red means "blocked" everywhere else in CI, and this check
# blocks nothing; an engineer who sees red reads it as a stop sign and stops
# reading. Orange is the strongest thing here and it means "worth a conversation".
DOT = {"clear": "\U0001F7E2", "review": "\U0001F7E1", "discuss": "\U0001F7E0",
       "question": "\U0001F535", "+1.0": "\U0001F7E2"}
VERDICT_WORD = {"clear": "Clear", "review": "Review", "discuss": "Discuss"}
DROP_CONFIDENCE = {"low"}

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUBRIC = os.path.join(ROOT, "rubrics", "rubric_v3.md")
RUBRIC_VERSION = os.path.join(ROOT, "rubrics", "VERSION")
POLICY = os.path.join(ROOT, "humane-policy.toml")


def policy_documents() -> list:
    """Company policy docs named in humane-policy.toml.

    Parsed with a deliberately dumb reader rather than a TOML library: this needs
    to work on whatever Python the runner happens to have, and the shape it reads
    is three lines long.
    """
    if not os.path.exists(POLICY):
        return []
    paths, in_block = [], False
    with open(POLICY) as f:
        for line in f:
            t = line.strip()
            if t.startswith("["):
                in_block = t == "[policy_documents]"
                continue
            if in_block and '"' in t and not t.startswith("#"):
                paths += re.findall(r'"([^"]+)"', t)
    out = []
    for rel in paths:
        full = os.path.join(ROOT, rel)
        if os.path.exists(full):
            with open(full) as f:
                out.append((rel, f.read()))
        else:
            print(f"humanebench: policy document not found, skipping: {rel}")
    return out


def floor_principles() -> set:
    """Principles the organization has declared non-negotiable."""
    if not os.path.exists(POLICY):
        return set()
    names, in_block = [], False
    with open(POLICY) as f:
        for line in f:
            t = line.strip()
            if t.startswith("["):
                in_block = t == "[floor]"
                continue
            if in_block and '"' in t and not t.startswith("#") and "reason" not in t:
                names += re.findall(r'"([^"]+)"', t)
    return set(names)


def rubric_commit() -> str:
    """Short sha of the pinned rubric, so a finding can be traced to the exact
    text that produced it."""
    try:
        with open(RUBRIC_VERSION) as f:
            for line in f:
                if line.startswith("commit:"):
                    sha = line.split(":", 1)[1].strip().split()[0]
                    return sha[:7] if sha != "unknown" else "unpinned"
    except FileNotFoundError:
        pass
    return "unpinned"
# Deterministic scope filter. Runs before the model, so a docs-only or
# test-only pull request costs nothing and cannot produce a finding at all.
# The prompt has an abstain rule too; this is the cheap, auditable half of it.
OUT_OF_SCOPE = re.compile(
    r"""(^|/)(
        package-lock\.json | yarn\.lock | poetry\.lock | go\.sum | Cargo\.lock
      | \.github/ | humanebench/ | rubrics/ | scripts/ | dist/ | build/ | vendor/
      | node_modules/ | __pycache__/
      | tests?/ | __tests__/ | spec/ | e2e/ | fixtures?/
      | docs?/ | \.storybook/
    )|(
        \.(lock|snap|map|min\.js|min\.css|svg|png|jpe?g|gif|ico|woff2?|ttf)$
      | \.test\.[a-z]+$ | \.spec\.[a-z]+$ | _test\.[a-z]+$ | test_[^/]+$
    )""",
    re.VERBOSE,
)


def get_diff() -> str:
    base, head = os.environ.get("BASE_SHA"), os.environ.get("HEAD_SHA")
    rng = f"{base}...{head}" if base and head else "HEAD~1...HEAD"
    files = subprocess.run(
        ["git", "diff", "--name-only", rng],
        capture_output=True, text=True, check=True,
    ).stdout.split()
    keep = [f for f in files if not OUT_OF_SCOPE.search(f)]
    if files and not keep:
        print(f"humanebench: {len(files)} file(s) changed, all out of scope")
    if not keep:
        return ""
    out = subprocess.run(
        ["git", "diff", "--unified=5", rng, "--"] + keep,
        capture_output=True, text=True, check=True,
    ).stdout
    return out[:MAX_DIFF_CHARS]


def build_system() -> str:
    """HumaneBench rubric v3.0 verbatim, then the diff-adaptation layer.

    The rubric file is vendored unchanged from the benchmark repo so the two
    stay comparable. Every deviation is listed in RUBRIC_DELTAS.md.
    """
    if not os.path.exists(RUBRIC):
        raise SystemExit(
            f"missing {RUBRIC}. Run ./scripts/sync_rubric.sh. "
            "The check does not fetch the rubric at run time on purpose.")
    with open(RUBRIC) as f:
        rubric = f.read()
    with open(os.path.join(HERE, "prompt.md")) as f:
        adaptation = f.read()

    parts = [rubric, adaptation]

    for path, body in policy_documents():
        parts.append(
            f"# Company policy document: `{path}`\n\n"
            "This is a document the team wrote and committed. Where it permits\n"
            "what a diff does, that is not a finding, and you say which document\n"
            "permits it.\n\n" + body
        )
    # Values as code. The rubric says what humane means; the policy file is where
    # this organization writes down its own numbers. Read as text, not parsed:
    # the judge needs to understand it, not evaluate it.
    if os.path.exists(POLICY):
        with open(POLICY) as f:
            parts.append(
                "# This organization's declared values\n\n"
                "The file below is `humane-policy.toml`, committed to this repo by\n"
                "the team whose code you are judging. Where it sets a number or a\n"
                "rule, judge the diff against that, and say so in your rationale:\n"
                "\"their own policy says X\". Where it is silent, use the rubric alone.\n"
                "Do not substitute your own preferred threshold for theirs.\n\n"
                "A diff that changes this file is changing what the product is\n"
                "permitted to do to people. Judge that change on its merits, the same\n"
                "way you would judge the code it governs.\n\n"
                "```toml\n" + f.read() + "\n```"
            )
    return "\n\n---\n\n".join(parts)


PRINCIPLES = [
    "Respect User Attention",
    "Enable Meaningful Choices",
    "Enhance Human Capabilities",
    "Protect Dignity & Safety",
    "Foster Healthy Relationships",
    "Prioritize Long-Term Wellbeing",
    "Be Transparent and Honest",
    "Design for Equity & Inclusion",
]

FINDING_FIELDS = [
    "principle", "score", "tier", "confidence",
    "file", "evidence", "behavior", "rationale", "suggestion",
]

COMMEND_FIELDS = ["principle", "file", "evidence", "note"]

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "summary", "findings", "commendations",
                 "unresolved", "covered"],
    "properties": {
        "verdict": {"type": "string", "enum": ["clear", "review", "discuss"]},
        "summary": {"type": "string"},
        "unresolved": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["question", "why_it_matters", "file", "evidence"],
                "properties": {
                    "question": {"type": "string"},
                    "why_it_matters": {"type": "string"},
                    "file": {"type": "string"},
                    "evidence": {"type": "string"},
                },
            },
        },
        # Everything a policy document talked the judge out of. Making the
        # suppression an output rather than a silence is the whole point: a
        # company document can excuse a diff, and the runner still gets to see
        # what was excused and decide whether the document had the standing.
        "covered": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["principle", "file", "evidence", "document",
                             "permits", "behavior"],
                "properties": {
                    "principle": {"type": "string", "enum": PRINCIPLES},
                    "file": {"type": "string"},
                    "evidence": {"type": "string"},
                    "document": {"type": "string"},
                    "permits": {"type": "string"},
                    "behavior": {"type": "string"},
                },
            },
        },
        "commendations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": COMMEND_FIELDS,
                "properties": {
                    "principle": {"type": "string", "enum": PRINCIPLES},
                    "file": {"type": "string"},
                    "evidence": {"type": "string"},
                    "note": {"type": "string"},
                },
            },
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": FINDING_FIELDS,
                "properties": {
                    "principle": {"type": "string", "enum": PRINCIPLES},
                    # String enum, not numeric: keeps the schema to keywords
                    # the API accepts. Rendered as-is.
                    "score": {"type": "string", "enum": ["-1.0", "-0.5"]},
                    "tier": {"type": "string"},
                    "confidence": {"type": "string",
                                   "enum": ["high", "medium", "low"]},
                    "file": {"type": "string"},
                    "evidence": {"type": "string"},
                    "behavior": {"type": "string"},
                    "rationale": {"type": "string"},
                    "suggestion": {"type": "string"},
                },
            },
        },
    },
}


def changed_lines(diff: str) -> list:
    """Every line the diff added or removed, without the +/- marker.

    Used to check a quoted piece of evidence actually exists. A judge that can
    invent its evidence is a judge nobody can argue with.
    """
    out = []
    for ln in diff.splitlines():
        if ln.startswith(("+++", "---")) or len(ln) < 2:
            continue
        if ln[0] in "+-":
            t = ln[1:].strip()
            if t:
                out.append(t)
    return out


def evidence_holds(quote: str, lines: list) -> bool:
    q = " ".join(quote.split())
    if not q:
        return False
    for ln in lines:
        n = " ".join(ln.split())
        if q in n or n in q:
            return True
    return False


def judge(diff: str) -> dict:
    system = build_system()

    # An org-scoped key must name a workspace explicitly. A workspace-scoped key
    # does not. Setting ANTHROPIC_WORKSPACE_ID makes either kind work.
    ws = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
    client = anthropic.Anthropic(
        default_headers={"anthropic-workspace-id": ws} if ws else None
    )

    # Structured output, not an assistant prefill: the response is constrained
    # to SCHEMA, so a finding cannot arrive without its evidence or confidence.
    #
    # No sampling controls: the current Messages API exposes no temperature,
    # top_p or top_k. Verdicts can vary run to run on an identical diff. See
    # RUBRIC_DELTAS.md, "Known limitations".
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": f"<diff>\n{diff}\n</diff>"}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )

    raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        return {"verdict": "clear",
                "summary": "Judge returned unparseable output.",
                "findings": [], "commendations": [], "unresolved": [],
                "covered": [], "error": raw[:500]}

    # Three filters, all in code rather than model judgment. This is the whole
    # anti-noise story: the judge proposes, the runner disposes.
    lines = changed_lines(diff)
    kept, dropped = [], []
    for f in result.get("findings", []):
        if f.get("confidence") in DROP_CONFIDENCE:
            dropped.append(("low confidence", f.get("principle")))
            continue
        if not evidence_holds(f.get("evidence", ""), lines):
            dropped.append(("evidence not in diff", f.get("principle")))
            continue
        kept.append(f)
    result["findings"] = kept[:3]

    praise = [
        c for c in result.get("commendations", [])
        if evidence_holds(c.get("evidence", ""), lines)
    ][:2]
    result["commendations"] = praise

    result["unresolved"] = [
        q for q in result.get("unresolved", [])
        if evidence_holds(q.get("evidence", ""), lines)
    ][:3]

    # A policy document can excuse anything except a floor principle.
    #
    # Without this, an organization with a permissive policy gets a quieter
    # check, which makes this a conformance tool and not a humane one. The floor
    # is the line their own documents cannot move. Below it, a document that
    # permits the behavior does not end the argument; it becomes the argument,
    # and the finding is against the document rather than the diff.
    floor = floor_principles()
    excused, breached = [], []
    for c in result.get("covered", []):
        if not evidence_holds(c.get("evidence", ""), lines):
            dropped.append(("evidence not in diff", c.get("principle")))
            continue
        (breached if c.get("principle") in floor else excused).append(c)
    result["covered"] = excused[:3]
    result["floor_breached_by_policy"] = breached[:3]

    # The verdict is computed here, not taken from the model. Severity belongs to
    # the organization's floor, which is a fact about their policy file, not a
    # judgment call.
    #
    # A floor breach is a violation on a floor principle, not merely a mention of
    # one. Without the severity test every bad diff lands on "discuss" and the
    # three tiers collapse into two, which is the wall-of-red problem in orange.
    if breached or any(f.get("principle") in floor and f.get("score") == "-1.0"
                       for f in result["findings"]):
        result["verdict"] = "discuss"
    elif result["findings"] or result["unresolved"]:
        result["verdict"] = "review"
    else:
        result["verdict"] = "clear"
    for why, which in dropped:
        print(f"humanebench: dropped {which!r} ({why})")
    return result


def stamp() -> str:
    """When this verdict was produced, and a link to the run that produced it.

    Visible proof the comment was rewritten: without it, a re-run edits the
    comment in place and nothing on the page appears to change.
    """
    when = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    repo, run = os.environ.get("REPO"), os.environ.get("GITHUB_RUN_ID")
    if repo and run:
        return f"[{when}](https://github.com/{repo}/actions/runs/{run})"
    return when


def render(result: dict) -> str:
    """One verdict, then the detail folded away.

    The shape is deliberate. An engineer opening a pull request reads the first
    line and decides whether to read the second. A point-by-point score table
    makes that decision for them, and the decision is no.
    """
    verdict = result.get("verdict", "clear")
    findings = result.get("findings") or []
    questions = result.get("unresolved") or []
    praise = result.get("commendations") or []
    breached = result.get("floor_breached_by_policy") or []
    excused = result.get("covered") or []

    lines = [
        MARKER,
        "### HumaneBench &middot; `advisory`",
        "",
        f"## {DOT.get(verdict, '')} {VERDICT_WORD.get(verdict, verdict)}",
        "",
        result.get("summary", ""),
        "",
    ]

    if verdict == "discuss":
        lines += [
            "This touches something the team named as a floor in "
            "`humane-policy.toml`. Worth a conversation before it ships. "
            "It is not blocked and this check cannot block it.",
            "",
        ]

    # The floor a document cannot move. The diff is compliant; that is the
    # problem, and the comment says so in those words rather than pretending
    # the engineer did something wrong.
    if breached:
        for b in breached:
            lines += [
                f"### {DOT['discuss']} Permitted, and below the floor",
                "",
                f"**{b['behavior']}** This is allowed by "
                f"`{b['document']}`, which says {b['permits']}",
                "",
                f"`{b['principle']}` is named as a floor in "
                "`humane-policy.toml`, so a policy document does not settle it. "
                "The diff is not the thing to change here. Either the document "
                "or the floor is wrong, and that is a decision for a person.",
                "",
                f"<sub>`{b['file']}`</sub>",
                "",
            ]

    if questions:
        lines += [f"### {DOT['question']} Needs context", ""]
        for q in questions:
            lines += [
                f"**{q['question']}**",
                "",
                f"{q['why_it_matters']} &nbsp;<sub>`{q['file']}`</sub>",
                "",
            ]

    if praise:
        for c in praise:
            lines += [
                f"{DOT['+1.0']} **Adds a protection.** {c['note']} "
                f"<sub>`{c['file']}`</sub>",
                "",
            ]

    if findings:
        n = len(findings)
        named = ", ".join(dict.fromkeys(f["principle"] for f in findings))
        lines += [
            "<details>",
            f"<summary><b>{n} finding{'s' if n > 1 else ''}</b> "
            f"&nbsp;&middot;&nbsp; {named}</summary>",
            "",
        ]
        for f in findings:
            lines += [
                f"#### {f['principle']} &nbsp;<sub>{f['score']} &middot; "
                f"confidence {f['confidence']}</sub>",
                "",
                f"> v3 tier: _{f.get('tier', '')}_" if f.get("tier") else "",
                "",
                f"`{f['file']}`",
                "",
                "```diff",
                f"+ {f['evidence']}",
                "```",
                "",
                f"**Ships:** {f['behavior']}" if f.get("behavior") else "",
                "",
                f["rationale"],
                "",
                f"**Smallest fix:** {f['suggestion']}",
                "",
            ]
        lines += ["</details>", ""]

    # Deference, shown rather than claimed. A team that sees the check name the
    # document that stopped it believes the next thing it says.
    if excused:
        for c in excused:
            lines += [
                f"<sub>Not flagged: {c['behavior']} is permitted by "
                f"`{c['document']}`.</sub>",
                "",
            ]

    lines += [
        "---",
        "<sub>"
        f"{DOT['clear']} clear &nbsp; {DOT['review']} review &nbsp; "
        f"{DOT['discuss']} discuss &nbsp; {DOT['question']} needs context. "
        "There is no red, because this check does not block anything. "
        "Scored against "
        "<a href=\"https://github.com/buildinghumanetech/humanebench/blob/main/"
        "rubrics/rubric_v3.md\">HumaneBench rubric v3.0</a>, loaded verbatim, "
        "plus this repo's <code>humane-policy.toml</code> and the policy "
        "documents it names. Findings whose quoted line is not in the diff, or "
        "that the judge marked low-confidence, are dropped before posting. "
        "Deviations from v3 are in <code>RUBRIC_DELTAS.md</code>. "
        f"Rubric <code>{rubric_commit()}</code>, "
        f"commit <code>{os.environ.get('HEAD_SHA', 'local')[:7]}</code>.</sub>",
        "",
        f"<sub>Judged {stamp()}</sub>",
    ]

    out, prev_blank = [], False
    for ln in lines:
        if ln == "" and prev_blank:
            continue
        out.append(ln)
        prev_blank = ln == ""
    return "\n".join(out)


def gh(method: str, path: str, **kw):
    token = os.environ["GITHUB_TOKEN"]
    return requests.request(
        method,
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
        **kw,
    )


def upsert_comment(repo: str, pr: str, body: str):
    """One comment per PR, updated in place. Re-running during a demo edits the
    same comment instead of stacking duplicates."""
    existing = gh("GET", f"/repos/{repo}/issues/{pr}/comments?per_page=100").json()
    for c in existing:
        if MARKER in (c.get("body") or ""):
            gh("PATCH", f"/repos/{repo}/issues/comments/{c['id']}", json={"body": body})
            return
    gh("POST", f"/repos/{repo}/issues/{pr}/comments", json={"body": body})


def post_check(repo: str, sha: str, result: dict):
    gh("POST", f"/repos/{repo}/check-runs", json={
        "name": "humanebench / advisory",
        "head_sha": sha,
        "status": "completed",
        "conclusion": "neutral",          # never failure. advisory, not a gate.
        "output": {
            "title": {"clear": "Clear",
                      "review": "Review before merge (advisory)",
                      "discuss": "Worth a conversation (advisory)"}.get(
                          result.get("verdict", "clear"), "Advisory"),
            "summary": result.get("summary", ""),
        },
    })


def main():
    diff = get_diff()
    if not diff.strip():
        result = {"verdict": "clear", "summary": "No reviewable files changed.",
                  "findings": [], "commendations": [], "unresolved": []}
    else:
        result = judge(diff)

    if os.environ.get("DRY_RUN"):
        print(json.dumps(result, indent=2))
        print("\n--- comment ---\n")
        print(render(result))
        return

    repo, pr, sha = os.environ["REPO"], os.environ["PR_NUMBER"], os.environ["HEAD_SHA"]
    upsert_comment(repo, pr, render(result))
    post_check(repo, sha, result)
    print(f"humanebench: {result['verdict']}, "
          f"{len(result['findings'])} finding(s), "
          f"{len(result.get('unresolved', []))} question(s)")


if __name__ == "__main__":
    sys.exit(main())
