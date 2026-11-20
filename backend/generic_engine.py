"""Deterministic answer checking for non-fraction subjects.

Question types (all graded by rules, never by an AI model):

  mcq          Multiple choice. Each wrong option can be mapped to a known misconception code, so a wrong
               choice is evidence for a specific gap (e.g. "heavier objects fall faster").
  numeric      An exact number (integer, decimal, fraction or percentage). Compared with Python's Fraction,
               so 0.5, .50 and 1/2 are the same value and nothing is rounded.
  text         A short word or phrase with a list of accepted spellings (e.g. a verb form). Compared after
               normalising case, spaces and end punctuation. Known wrong answers can map to misconceptions.
  code_output  "What does this program print?" The student predicts the output; their answer is compared like
               `text`. Student code is never executed. The expected output is checked at build time by
               running the (fixed, author-written) snippet: see scripts/build_curriculum.py.

Question fields: id, pool, skill_id, type, gap_targets, prompt, answer, [options], [accept], [code],
[patterns: {wrong answer: misconception code}], hints: [...], solution: [...], [check_role].
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Optional

TYPES = ("mcq", "numeric", "text", "code_output")
_NUM_RE = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)$")


@dataclass
class CheckResult:  # same shape as fractions_engine.CheckResult
    valid: bool
    correct: bool = False
    error: Optional[str] = None
    expected: Optional[str] = None
    normalized: Optional[str] = None
    pattern: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- normalising

def norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.strip("\"'“”‘’`")
    s = re.sub(r"[.!?;:]+$", "", s).strip()
    return " ".join(s.split())


def parse_number(raw: str, percent: bool = False) -> Fraction:
    """Exact value of '12', '-3', '0.75', '.5', '3/4', '-1/2', '25%'. Raises ValueError on anything else."""
    s = (raw or "").strip().replace(" ", "").replace("−", "-").replace(",", "")
    if percent and s.endswith("%"):
        s = s[:-1]
    if not s:
        raise ValueError("Please type a number.")
    if "/" in s:
        n, _, d = s.partition("/")
        if not re.fullmatch(r"[+-]?\d+", n) or not re.fullmatch(r"\d+", d):
            raise ValueError("Write a fraction like 3/4.")
        if int(d) == 0:
            raise ValueError("The bottom number of a fraction can't be 0.")
        return Fraction(int(n), int(d))
    if not _NUM_RE.match(s):
        raise ValueError("Please type a number, like 12, -3 or 0.75.")
    try:
        return Fraction(Decimal(s))
    except InvalidOperation:  # pragma: no cover - regex already guards
        raise ValueError("Please type a number.")


def fmt_number(v: Fraction) -> str:
    if v.denominator == 1:
        return str(v.numerator)
    # finite decimal? (denominator only has factors 2 and 5)
    d = v.denominator
    while d % 2 == 0:
        d //= 2
    while d % 5 == 0:
        d //= 5
    if d == 1:
        s = format(Decimal(v.numerator) / Decimal(v.denominator), "f")
        return s.rstrip("0").rstrip(".") if "." in s else s
    return f"{v.numerator}/{v.denominator}"


# ---------------------------------------------------------------- public API (mirrors fractions_engine)

def render_prompt(q: dict) -> str:
    return q["prompt"]


def answer_input_kind(q: dict) -> str:
    return {"mcq": "choice", "numeric": "number", "text": "text", "code_output": "text"}[q["type"]]


def choices(q: dict) -> list[str]:
    return list(q.get("options", [])) if q["type"] == "mcq" else []


def correct_answer_text(q: dict) -> str:
    return q["answer"]


def hints_for(q: dict) -> list[str]:
    return list(q.get("hints", []))


def worked_solution(q: dict) -> list[str]:
    return list(q.get("solution", []))


def check_answer(q: dict, raw: str) -> CheckResult:
    t = q["type"]
    expected = q["answer"]
    patterns = q.get("patterns", {})
    if t == "mcq":
        pick = (raw or "").strip()
        if pick not in q["options"]:
            return CheckResult(valid=False, error="Please choose one of the options.")
        ok = pick == expected
        return CheckResult(valid=True, correct=ok, expected=expected, normalized=pick,
                           pattern=None if ok else patterns.get(pick))
    if t == "numeric":
        percent = bool(q.get("percent"))
        try:
            v = parse_number(raw, percent)
        except ValueError as e:
            return CheckResult(valid=False, error=str(e))
        target = parse_number(expected, percent)
        ok = v == target
        pat = None
        if not ok:
            for wrong, code in patterns.items():
                if parse_number(wrong, percent) == v:
                    pat = code
                    break
        return CheckResult(valid=True, correct=ok, expected=expected, normalized=fmt_number(v), pattern=pat)
    if t in ("text", "code_output"):
        if not (raw or "").strip():
            return CheckResult(valid=False, error="Please type an answer first.")
        if len(raw) > 60:
            return CheckResult(valid=False, error="That answer is too long. Keep it short.")
        n = norm_text(raw)
        accepted = {norm_text(a) for a in [expected, *q.get("accept", [])]}
        ok = n in accepted
        pat = None if ok else next((c for w, c in patterns.items() if norm_text(w) == n), None)
        return CheckResult(valid=True, correct=ok, expected=expected, normalized=n, pattern=pat)
    raise ValueError(f"Unknown question type {t}")


def validate_question(q: dict) -> None:
    t = q["type"]
    qid = q.get("id", "?")
    for k in ("prompt", "answer"):
        if not str(q.get(k, "")).strip():
            raise ValueError(f"Question {qid}: missing {k}")
    if not q.get("hints") or not q.get("solution"):
        raise ValueError(f"Question {qid}: needs hints and a worked solution")
    pats = q.get("patterns", {})
    if t == "mcq":
        opts = q.get("options") or []
        if len(opts) < 2 or len(set(opts)) != len(opts) or q["answer"] not in opts:
            raise ValueError(f"Question {qid}: options must be unique and include the answer")
        for w in pats:
            if w not in opts or w == q["answer"]:
                raise ValueError(f"Question {qid}: pattern key '{w}' must be a wrong option")
    elif t == "numeric":
        target = parse_number(q["answer"], bool(q.get("percent")))
        for w in pats:
            if parse_number(w, bool(q.get("percent"))) == target:
                raise ValueError(f"Question {qid}: pattern '{w}' equals the answer")
    elif t in ("text", "code_output"):
        accepted = {norm_text(a) for a in [q["answer"], *q.get("accept", [])]}
        for w in pats:
            if norm_text(w) in accepted:
                raise ValueError(f"Question {qid}: pattern '{w}' is an accepted answer")
        if t == "code_output" and not q.get("code"):
            raise ValueError(f"Question {qid}: code_output needs code")
    else:
        raise ValueError(f"Question {qid}: unknown type {t}")
