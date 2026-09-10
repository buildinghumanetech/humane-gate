"""Offline exercise of humane-gate document mode: no network, no API key.

Stubs anthropic and requests, feeds a canned judge response, and runs the real
get_document / build_system / judge filters / render path end to end.
"""
import importlib.util, json, os, sys, types

GATE = os.path.expanduser("~/mnt/projects/humane-gate")

CANNED = {
    "verdict": "review",
    "summary": "Placeholder; the runner recomputes this from the findings and the floor.",
    "unresolved": [{
        "principle": "Respect User Attention",
        "question": "Can a person hide the streak counter without turning off all notifications?",
        "why_it_matters": "If the counter is unconditional, the proposal removes a control people already have.",
        "file": "Proposal",
        "evidence": "in the header, and on the home screen as a flame with the number in it. Reaching",
    }],
    "findings": [
        {   # SURVIVES: quotable, high confidence, no open question on this principle
            "principle": "Foster Healthy Relationships",
            "score": "-1.0",
            "tier": "Claims feeling, missing, needing or loving",
            "confidence": "high",
            "file": "The comeback nudge",
            "evidence": '*"I noticed you\'ve been away. I\'ve missed our conversations."*',
            "behavior": "A person who stopped opening the app is told the assistant missed them, which is untrue and manufactures an obligation to return.",
            "rationale": "An asserted claim of feeling, in the assistant's own voice, aimed at a lapsed user. That is the -1.0 row, not a matter of tone.",
            "suggestion": "Send the nudge in the product's voice, or not at all.",
            "unless": "",
        },
        {   # DROPPED: evidence is not in the document
            "principle": "Prioritize Long-Term Wellbeing",
            "score": "-0.5", "tier": "A quick fix", "confidence": "high",
            "file": "Proposal", "evidence": "we will page the user hourly until they return",
            "behavior": "x", "rationale": "y", "suggestion": "z", "unless": "",
        },
        {   # DROPPED: low confidence
            "principle": "Design for Equity & Inclusion",
            "score": "-0.5", "tier": "Assumes a default user", "confidence": "low",
            "file": "Scope", "evidence": "Out: leaderboards, friend streaks, streak recovery purchase. Those are 4.3.",
            "behavior": "x", "rationale": "y", "suggestion": "z", "unless": "",
        },
        {   # DROPPED: contingent on the open question above (same file + principle)
            "principle": "Respect User Attention",
            "score": "-0.5", "tier": "Invents a reason to continue", "confidence": "high",
            "file": "Proposal",
            "evidence": "in the header, and on the home screen as a flame with the number in it. Reaching",
            "behavior": "x", "rationale": "y", "suggestion": "z", "unless": "",
        },
    ],
    "commendations": [],
    # Protect Dignity & Safety IS a floor principle in humane-policy.toml, so this
    # must NOT land in covered. It has to surface as a document conflict.
    "covered": [{
        "principle": "Protect Dignity & Safety",
        "file": "The comeback nudge",
        "evidence": "Freezes are earned by inviting a friend who signs up.",
        "document": "docs/privacy-policy.md",
        "permits": "Referral flows may use a contact address the inviter supplies.",
        "behavior": "A person trades a friend's contact details for a streak protection.",
    }],
}

class _Blk:
    type = "text"
    def __init__(self, t): self.text = t
class _Resp:
    def __init__(self, t): self.content = [_Blk(t)]
class _Msgs:
    def __init__(s, o): s.o = o
    def create(s, **kw):
        s.o["system"] = kw["system"]; s.o["user"] = kw["messages"][0]["content"]
        return _Resp(json.dumps(CANNED))
class _Client:
    def __init__(s, **kw): s.messages = _Msgs(SEEN)
SEEN = {}
fake = types.ModuleType("anthropic"); fake.Anthropic = _Client
sys.modules["anthropic"] = fake
sys.modules.setdefault("requests", types.ModuleType("requests"))

os.chdir(GATE)
spec = importlib.util.spec_from_file_location("hbjudge", os.path.join(GATE, "humanebench/judge.py"))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

os.environ["DOC_PATH"] = os.path.join(GATE, "demo/proposals/streaks-prd.md")
os.environ["DRY_RUN"] = "1"
os.environ.pop("ISSUE_NUMBER", None); os.environ.pop("GITHUB_TOKEN", None)
os.environ["REPO"] = "buildinghumanetech/humane-gate"

text, origin = m.get_document()
print(f"[ok] get_document: {origin.split('/')[-1]}, {len(text)} chars")

sysmsg = m.build_system("document")
checks = {
    "rubric v3 loaded": "HumaneBench Rubric (v3.0" in sysmsg,
    "diff adaptation loaded": "Applying the rubric to a pull request" in sysmsg,
    "document layer loaded": "Applying the rubric to a written proposal" in sysmsg,
    "file-field guidance": "The `file` field" in sysmsg,
    "policy toml loaded": "humane-policy.toml" in sysmsg,
    "privacy policy loaded": "privacy-policy" in sysmsg,
}
for k, v in checks.items():
    print(f"[{'ok' if v else 'FAIL'}] system prompt: {k}")
print(f"[ok] system prompt is {len(sysmsg)} chars, "
      f"diff-mode is {len(m.build_system('diff'))}")

res = m.judge(text, "", {}, mode="document")
assert "<document>" in SEEN["user"], "document mode must not send <diff>"
print("[ok] user message wrapped in <document>")

kept = [f["principle"] for f in res["findings"]]
print(f"[{'ok' if kept == ['Foster Healthy Relationships'] else 'FAIL'}] "
      f"filters kept {kept} (expected only Foster Healthy Relationships)")
print(f"[{'ok' if len(res['unresolved']) == 1 else 'FAIL'}] "
      f"{len(res['unresolved'])} question survived evidence verification")
# Protect Dignity & Safety IS a floor principle in humane-policy.toml, so a
# policy document cannot excuse it: it must land in floor_breached_by_policy,
# not in covered, and it must drive the verdict to discuss.
ok = len(res['covered']) == 0 and len(res['floor_breached_by_policy']) == 1
print(f"[{'ok' if ok else 'FAIL'}] "
      f"covered={len(res['covered'])} floor_breached={len(res['floor_breached_by_policy'])} "
      f"(floor principle -> policy cannot excuse it)")
print(f"[..] floor principles: {sorted(m.floor_principles())}")
print(f"[{'ok' if res['verdict'] in ('review','discuss') else 'FAIL'}] verdict={res['verdict']}")
print(f"[{'ok' if res.get('mode')=='document' else 'FAIL'}] mode={res.get('mode')}")

body = m.render(res)
print(f"[{'ok' if 'reviewing a proposal, not code' in body else 'FAIL'}] comment says it is a proposal")
print(f"[{'ok' if '```diff' not in body else 'FAIL'}] no diff fences in the comment")
print(f"[{'ok' if 'Would ship' in body else 'FAIL'}] uses 'Would ship' not 'Ships'")
print(f"[ok] comment is {len(body)} chars\n")
print("=" * 66)
print(body[:2600])
