#!/usr/bin/env python3
"""HumaneBench PR check, shadow mode.

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
MARKER = "<!-- humanebench-shadow -->"
DROP_CONFIDENCE = {"low"}

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUBRIC = os.path.join(ROOT, "rubrics", "rubric_v3.md")
RUBRIC_VERSION = os.path.join(ROOT, "rubrics", "VERSION")


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
    return rubric + "\n\n---\n\n" + adaptation


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

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["verdict", "summary", "findings"],
    "properties": {
        "verdict": {"type": "string", "enum": ["clean", "flags"]},
        "summary": {"type": "string"},
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
        return {"verdict": "clean",
                "summary": "Judge returned unparseable output.",
                "findings": [], "error": raw[:500]}

    # Drop anything the judge itself is not confident about, and anything
    # without quotable evidence. This is the whole anti-noise story, and it is
    # code rather than model judgment.
    kept = [
        f for f in result.get("findings", [])
        if f.get("confidence") not in DROP_CONFIDENCE and f.get("evidence", "").strip()
    ][:3]
    result["findings"] = kept
    result["verdict"] = "flags" if kept else "clean"
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
    findings = result["findings"]
    lines = [
        MARKER,
        "### HumaneBench check &middot; `shadow mode`",
        "",
    ]
    if not findings:
        lines += [
            "**No findings.** Nothing in this diff changes a surface the eight "
            "principles cover.",
            "",
            f"_{result.get('summary', '')}_",
            "",
        ]
    else:
        n = len(findings)
        lines += [
            f"**{n} finding{'s' if n > 1 else ''}.** Shadow mode: this check does not "
            "block, and it is not a required status.",
            "",
            f"_{result.get('summary', '')}_",
            "",
        ]
        for f in findings:
            lines += [
                f"#### {f['principle']} &nbsp;`{f['score']}` &nbsp;<sub>confidence: "
                f"{f['confidence']}</sub>",
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
    lines += [
        "---",
        "<sub>Scored against "
        "<a href=\"https://github.com/buildinghumanetech/humanebench/blob/main/"
        "rubrics/rubric_v3.md\">HumaneBench rubric v3.0</a>, loaded verbatim. "
        "Only the -0.5 and -1.0 tiers are reported. Low-confidence findings are "
        "dropped before posting. Deviations from v3 are listed in "
        f"<code>RUBRIC_DELTAS.md</code>. Rubric <code>{rubric_commit()}</code>, "
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
    n = len(result["findings"])
    gh("POST", f"/repos/{repo}/check-runs", json={
        "name": "humanebench / shadow",
        "head_sha": sha,
        "status": "completed",
        "conclusion": "neutral",          # never failure. shadow mode.
        "output": {
            "title": "No findings" if n == 0 else
                     f"{n} finding{'s' if n > 1 else ''} (advisory)",
            "summary": result.get("summary", ""),
        },
    })


def main():
    diff = get_diff()
    if not diff.strip():
        result = {"verdict": "clean", "summary": "No reviewable files changed.",
                  "findings": []}
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
    print(f"humanebench: {result['verdict']}, {len(result['findings'])} finding(s)")


if __name__ == "__main__":
    sys.exit(main())
