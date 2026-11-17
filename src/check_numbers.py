"""Number checker for the weekly CRO note (adapted from a release-commentary checker).

Every number in a draft must be traceable to the week's fact sheet with the right metric, segment, unit
(% vs percentage points vs EUR vs count), period (this week, week on week, vs the same week last year,
expected), basis (conversion per session vs per user; revenue gross vs net of returns) and sign.
One wrong number rejects the whole draft; each failure names the likely mistake and the right figure.

    python src/check_numbers.py weekly_notes/weekly_note_2026-03-16.md   (exit code 1 if rejected)
"""
from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

METRICS = [  # longest phrases first: "revenue per visit" must win over "revenue" and "visit"
    ("rpv", r"revenue per visit|rpv"),
    ("checkout_abandonment", r"checkout abandonment|abandon(?:ed|ment)? (?:at|in) checkout"),
    ("atc", r"add-to-cart rate|add-to-cart|add to cart"),
    ("payment_step", r"payment step|payment-step"),
    ("shipping_step", r"shipping step|shipping-step"),
    ("aov", r"average order value|aov|average basket"),
    ("conversion", r"conversion rate|conversion|converted"),
    ("return_rate", r"return rate|returned"),
    ("revenue", r"revenue"),
    ("orders", r"orders"),
    ("incidents", r"incidents?"),
    ("sessions", r"sessions|traffic|visits"),
]
SEGMENTS = [("analytics vs shop", r"analytics revenue"), ("mobile / Safari iOS", r"mobile / safari ios|safari ios"), ("mobile / Mattress", r"mobile / mattress"),
            ("mobile", r"\bmobile\b"), ("desktop", r"\bdesktop\b"), ("tablet", r"\btablet\b"),
            ("Paid social", r"paid social|paid-social")]
UP = r"rose|rise|up|increased|grew|higher|gained|improved"
DOWN = r"fell|fall|down|dropped|declined|decreased|lower|slipped|lost"
NUM = re.compile(r"(?P<sign>[-+−])?(?P<cur>€)?\s?(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
                 r"(?P<suf>\s?(?:%|pp\b|percentage points?\b|points?\b|€|EUR\b))?")
MONTHS = r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"


@dataclass
class Claim:
    raw: str
    value: float
    decimals: int
    unit: str
    metric: str | None
    segment: str
    period: str
    basis: str | None
    sentence: str


@dataclass
class Finding:
    claim: Claim
    ok: bool
    error: str = ""
    message: str = ""


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(f.ok for f in self.findings)

    def errors(self) -> list[Finding]:
        return [f for f in self.findings if not f.ok]

    def text(self) -> str:
        n = sum(f.ok for f in self.findings)
        out = [f"{n}/{len(self.findings)} numbers verified -> {'PASS' if self.passed else 'REJECTED'}"]
        for f in self.errors():
            out.append(f"  [{f.error}] '{f.claim.raw}' in: {f.claim.sentence.strip()[:100]}\n      {f.message}")
        return "\n".join(out)


def _ignored(text: str, m: re.Match) -> bool:
    a, b, n = m.start("num"), m.end(), m.group("num")
    before, after = text[max(0, a - 12):a], text[b:b + 10]
    if m.group("suf") or m.group("cur"):
        return False
    if re.fullmatch(r"(?:19|20)\d\d", n) or re.match(r"-\d\d", after) or re.search(r"\d-$", before):
        return True                                             # years and ISO dates 2026-03-10
    if n.isdigit() and int(n) <= 31 and (re.match(rf"\s(?:{MONTHS})", after) or re.search(rf"(?:{MONTHS})\w*\s$", before)):
        return True                                             # 16 Mar, March 16
    if re.match(r"\s?(?:days?|weeks?|months?|nights?)\b", after) or re.match(r"-(?:day|week|night)", after):
        return True                                             # durations: 7 days, 100-night
    if re.search(r"\b(?:test|step|week)\s$", before, flags=re.I):
        return True
    return False


def _period(before: str, after: str) -> str:
    """Period of a number: cues right after it win; otherwise cues earlier in the same clause."""
    if re.match(r"\s*\)?\s*vs expected", after):
        return "vs_expected"
    if re.match(r"[^\d]{0,14}?(?:year on year|vs the same week last year|vs last year)", after):
        return "yoy"
    if re.match(r"[^\d]{0,14}?(?:week on week|vs the previous week|vs last week|on the previous week)", after):
        return "wow"
    clause = re.split(r"[;,()]", before)[-1]
    if re.search(r"(?:an expected|expected at|expected value of|against)\s*$", clause):
        return "expected"
    if re.search(r"\b(?:was|were|is|at|to)\s*$", clause):
        return "current"
    if re.search(r"year on year|vs the same week last year", clause):
        return "yoy"
    if re.search(r"week on week|vs the previous week", clause):
        return "wow"
    if re.search(r"\bfrom\s*$", clause):
        return "previous"
    return "current"


def extract(text: str) -> list[Claim]:
    sentences = [(m.start(), m.group()) for m in re.finditer(r"(?:[^.!?\n]|\.(?=\d))+(?:[.!?](?!\d)|$)", text, flags=re.M)]
    matches = [m for m in NUM.finditer(text) if not _ignored(text, m)]
    claims = []
    for i, m in enumerate(matches):
        s0, sent = next(((s, t) for s, t in sentences if s <= m.start() < s + len(t)), (0, text))
        prev_end = max(s0, matches[i - 1].end() if i else 0)
        next_start = min(s0 + len(sent), matches[i + 1].start() if i + 1 < len(matches) else len(text))
        before, after = text[prev_end:m.start()], text[m.end():next_start]
        head = text[s0:m.start()].lower()                       # sentence up to the number
        suf = (m.group("suf") or "").strip().lower()
        unit = ("pct" if suf == "%" else "pp" if suf in ("pp", "percentage point", "percentage points", "point", "points")
                else "eur" if (m.group("cur") or suf in ("€", "eur")) else "count")
        value = float(m.group("num").replace(",", ""))
        dec = len(m.group("num").split(".")[1]) if "." in m.group("num") else 0
        # metric: last metric keyword before the number in the sentence, else the first one after it
        metric, best = None, -1
        for name, pat in METRICS:
            for km in re.finditer(pat, head):
                if km.start() > best:
                    metric, best = name, km.start()
        if metric is None:
            tail = text[m.end():s0 + len(sent)].lower()
            firsts = [(km.start(), name) for name, pat in METRICS for km in [re.search(pat, tail)] if km]
            metric = min(firsts)[1] if firsts else None
        # segment: the segment named closest before the number ("mobile ... while desktop ... 1.49%" -> desktop)
        segment, best = "All", -1
        for name, pat in SEGMENTS:
            for sm in re.finditer(pat, head):
                if sm.end() > best:
                    segment, best = name, sm.end()
        basis = None
        if metric == "conversion":  # the last basis named before the number, per session by default
            cues = re.findall(r"per (session|user)", head)
            basis = f"per_{cues[-1]}" if cues else "per_session"
        if metric in ("rpv", "revenue"):  # gross unless "net" is said in the clause or right after the number
            clause = re.split(r"[;,()]", before.lower())[-1]
            basis = "net" if re.search(r"\bnet\b", clause + " " + after.lower()[:25]) else "gross"
        sign = 1
        if m.group("sign") in ("-", "−"):
            sign = -1
        elif not re.search(r"\b(?:to|at|was|were|is)\s*$", before.lower()):
            verbs = re.findall(rf"\b(?:{UP}|{DOWN})\b", before.lower())
            if verbs and re.fullmatch(DOWN, verbs[-1]):
                sign = -1
        claims.append(Claim(raw=m.group().strip(), value=sign * value, decimals=dec, unit=unit, metric=metric,
                            segment=segment, period=_period(before.lower(), after.lower()), basis=basis, sentence=sent))
    return claims


def _value_ok(c: Claim, f: dict, signed: bool = True) -> bool:
    v = c.value if signed else abs(c.value)
    t = f["value"] if signed else abs(f["value"])
    return abs(v - t) <= 0.5 * 10 ** (-c.decimals) + 1e-9


def _fmt(f: dict) -> str:
    v, u = f["value"], f["unit"]
    return {"pct": f"{v:+.2f}%" if f["period"] in ("wow", "yoy", "vs_expected") else f"{v:.2f}%",
            "pp": f"{v:+.2f} pp", "eur": f"EUR {v:,.2f}", "count": f"{v:,.0f}"}[u]


def check(text: str, sheet: dict) -> Report:
    facts = sheet["facts"]
    rep = Report()
    for c in extract(text):
        def find(**kw):
            for f in facts:
                if all((f.get(k) if k != "value" else None) == v for k, v in kw.items() if k != "test") and kw.get("test", lambda f: True)(f):
                    return f
            return None
        same = [f for f in facts if f["metric"] == c.metric and f["segment"] == c.segment]
        exact = [f for f in same if f["unit"] == c.unit and f["period"] == c.period
                 and f.get("basis") in (None, c.basis) and _value_ok(c, f)]
        if exact:
            rep.findings.append(Finding(c, True))
            continue
        rep.findings.append(diagnose(c, same, facts))
    return rep


def diagnose(c: Claim, same: list[dict], facts: list[dict]) -> Finding:
    """Test the usual traps one by one and name the first one that explains the number."""
    def first(pool, cond, signed=True):
        return next((f for f in pool if cond(f) and _value_ok(c, f, signed)), None)

    f = first(same, lambda f: f["unit"] in ("pp", "pct") and f["unit"] != c.unit and f["period"] == c.period)
    if f and c.unit in ("pp", "pct"):
        right = next((g for g in same if g["unit"] == c.unit and g["period"] == c.period and g.get("basis") == f.get("basis")), None)
        return Finding(c, False, "pp_vs_pct", f"{c.raw} is the change in {'percentage points' if f['unit'] == 'pp' else 'percent'}, "
                       f"but the text writes it as {'%' if c.unit == 'pct' else 'pp'}" + (f"; the {c.unit} change is {_fmt(right)}." if right else "."))
    f = first(same, lambda f: f["unit"] == c.unit and f["period"] != c.period and f.get("basis") in (None, c.basis))
    if f:
        names = {"current": "this week's value", "wow": "the week-on-week change", "yoy": "the change vs the same week last year",
                 "previous": "last week's value", "expected": "the expected value", "vs_expected": "the gap to the expected value"}
        return Finding(c, False, "wrong_period", f"{c.raw} is {names[f['period']]}, but the text presents it as {names[c.period]}.")
    f = first(same, lambda f: f["unit"] == c.unit and f["period"] == c.period and f.get("basis") not in (None, c.basis))
    if f:
        err = "per_session_vs_per_user" if c.metric == "conversion" else "gross_vs_net"
        right = next((g for g in same if g["unit"] == c.unit and g["period"] == c.period and g.get("basis") == c.basis), None)
        return Finding(c, False, err, f"{c.raw} is the {f['basis'].replace('_', ' ')} figure, but the text says "
                       f"{c.basis.replace('_', ' ')}" + (f"; the {c.basis.replace('_', ' ')} figure is {_fmt(right)}." if right else "."))
    f = first(same, lambda f: f["unit"] == c.unit and f["period"] == c.period, signed=False)
    if f and f["value"] != 0:
        return Finding(c, False, "sign", f"{f['label']} was {_fmt(f)}: the text gives the opposite direction.")
    f = first(facts, lambda f: f["unit"] == c.unit)
    if f:
        return Finding(c, False, "wrong_metric", f"{c.raw} matches '{f['label']}', not the {c.metric} of {c.segment} named in the sentence.")
    return Finding(c, False, "not_in_data", f"{c.raw} cannot be traced to the week's data ({c.metric}, {c.segment}, {c.period}).")


def main(argv: list[str]) -> int:
    bad = 0
    for p in map(Path, argv):
        sheet = json.loads(p.with_suffix(".facts.json").read_text(encoding="utf-8"))
        body = "\n".join(l for l in p.read_text(encoding="utf-8").splitlines() if not l.startswith(("#", ">")))
        rep = check(body, sheet)
        print(f"{p.name}: {rep.text()}")
        bad += not rep.passed
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
