"""Exact fraction arithmetic, answer checking and mistake-pattern detection.

Every correctness decision in ELEVIA is made here, with Python's Fraction type.
The LLM is never asked whether an answer is right.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, asdict
from fractions import Fraction
from typing import Optional

_FRACTION_RE = re.compile(r"^\s*([+-]?\d+)\s*/\s*([+-]?\d+)\s*$")
_MIXED_RE = re.compile(r"^\s*([+-]?\d+)\s+(\d+)\s*/\s*(\d+)\s*$")
_INT_RE = re.compile(r"^\s*([+-]?\d+)\s*$")

MAX_INPUT_LEN = 20


class AnswerFormatError(ValueError):
    """Raised when a student's answer can't be read as a number."""


@dataclass
class ParsedAnswer:
    value: Fraction
    written_num: int  # numerator as the student wrote it (improper form)
    written_den: int  # denominator as the student wrote it


def parse_fraction(text: str) -> Fraction:
    """Parse trusted data like '3/4' from the question bank."""
    return Fraction(text)


def parse_answer(raw: str) -> ParsedAnswer:
    """Parse a student's answer: '5/6', '1 1/2' (mixed number), or '3'.

    Raises AnswerFormatError with a student-friendly message.
    """
    if raw is None:
        raise AnswerFormatError("Please type an answer.")
    text = str(raw).strip()
    if not text:
        raise AnswerFormatError("Please type an answer.")
    if len(text) > MAX_INPUT_LEN:
        raise AnswerFormatError("That answer is too long. Type a fraction like 3/4.")

    m = _MIXED_RE.match(text)
    if m:
        whole, num, den = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if den == 0:
            raise AnswerFormatError("A denominator can't be 0.")
        sign = -1 if whole < 0 or m.group(1).startswith("-") else 1
        improper_num = sign * (abs(whole) * den + num)
        return ParsedAnswer(Fraction(improper_num, den), improper_num, den)

    m = _FRACTION_RE.match(text)
    if m:
        num, den = int(m.group(1)), int(m.group(2))
        if den == 0:
            raise AnswerFormatError("A denominator can't be 0.")
        if den < 0:
            num, den = -num, -den
        return ParsedAnswer(Fraction(num, den), num, den)

    m = _INT_RE.match(text)
    if m:
        n = int(m.group(1))
        return ParsedAnswer(Fraction(n, 1), n, 1)

    raise AnswerFormatError("Type a whole number (like 4) or a fraction (like 3/4 or 1 1/2).")


def fmt(fr: Fraction) -> str:
    return str(fr.numerator) if fr.denominator == 1 else f"{fr.numerator}/{fr.denominator}"


def lcm(a: int, b: int) -> int:
    return a * b // math.gcd(a, b)


# --------------------------------------------------------------------------
# Question rendering and correct answers
# --------------------------------------------------------------------------

def render_prompt(q: dict) -> str:
    t = q["type"]
    if t == "add":
        return f"{q['a']} + {q['b']} = ?"
    if t == "sub":
        return f"{q['a']} − {q['b']} = ?"
    if t == "multiply":
        return f"{q['a']} × {q['b']} = ?"
    if t == "simplify":
        return f"Write {q['a']} in its simplest form."
    if t == "equivalent":
        return f"{q['a']} = ?/{q['target']}   (type the missing numerator)"
    if t == "compare":
        return f"Which is larger: {q['a']} or {q['b']}?"
    if t == "lcd":
        return f"What is the lowest common denominator of {q['a']} and {q['b']}?"
    raise ValueError(f"Unknown question type {t}")


def answer_input_kind(q: dict) -> str:
    """Tells the frontend which input widget to show."""
    if q["type"] == "compare":
        return "choice"
    if q["type"] in ("equivalent", "lcd"):
        return "integer"
    return "fraction"


def choices(q: dict) -> list[str]:
    return [q["a"], q["b"]] if q["type"] == "compare" else []


def correct_answer(q: dict) -> Fraction:
    t = q["type"]
    a = parse_fraction(q["a"])
    b = parse_fraction(q["b"]) if "b" in q else None
    if t == "add":
        return a + b
    if t == "sub":
        return a - b
    if t == "multiply":
        return a * b
    if t == "simplify":
        return a
    if t == "equivalent":
        target = int(q["target"])
        num = a * target
        if num.denominator != 1:
            raise ValueError(f"Question {q['id']}: {q['a']} has no equivalent over {target}")
        return Fraction(num.numerator)
    if t == "compare":
        if a == b:
            raise ValueError(f"Question {q['id']}: compare operands are equal")
        return max(a, b)
    if t == "lcd":
        return Fraction(lcm(a.denominator, b.denominator))
    raise ValueError(f"Unknown question type {t}")


def correct_answer_text(q: dict) -> str:
    return fmt(correct_answer(q))


# --------------------------------------------------------------------------
# Checking
# --------------------------------------------------------------------------

@dataclass
class CheckResult:
    valid: bool
    correct: bool = False
    error: Optional[str] = None
    expected: Optional[str] = None
    normalized: Optional[str] = None
    pattern: Optional[str] = None  # misconception code if a known pattern matched
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _same_written(p: ParsedAnswer, num: int, den: int) -> bool:
    return den != 0 and (p.written_num == num and p.written_den == den or p.value == Fraction(num, den))


def detect_pattern(q: dict, p: ParsedAnswer) -> Optional[str]:
    """Return a misconception code if a wrong answer matches a known pattern."""
    t = q["type"]
    a = parse_fraction(q["a"])
    b = parse_fraction(q["b"]) if "b" in q else None

    if t in ("add", "sub"):
        n1, d1, n2, d2 = a.numerator, a.denominator, b.numerator, b.denominator
        sign = 1 if t == "add" else -1
        n_comb = n1 + sign * n2
        if t == "add" and _same_written(p, n1 + n2, d1 + d2):
            return "ADD_ACROSS"
        if t == "sub" and d1 != d2 and (d1 - d2) != 0 and p.written_num == n1 - n2 and p.written_den == d1 - d2:
            return "SUB_ACROSS"
        if d1 != d2:
            if any(_same_written(p, n_comb, d) for d in (d1, d2, max(d1, d2))):
                return "KEEP_ONE_DENOMINATOR"
            if _same_written(p, n_comb, d1 * d2) or _same_written(p, n_comb, lcm(d1, d2)):
                return "NUMERATOR_NOT_SCALED"
        return None

    if t == "multiply":
        if _same_written(p, a.numerator * b.numerator, a.denominator + b.denominator):
            return "MULTIPLY_CROSS_ADD"
        if _same_written(p, a.numerator + b.numerator, a.denominator + b.denominator):
            return "ADD_ACROSS"
        return None

    if t == "simplify":
        if p.value == a:
            return "NOT_SIMPLIFIED"
        return None

    if t == "equivalent":
        target = int(q["target"])
        if p.value == a.numerator + (target - a.denominator):
            return "EQUIV_ADD_SAME"
        return None

    if t == "compare":
        chosen = p.value
        other = b if chosen == a else a
        chosen_den = chosen.denominator
        if chosen < other and chosen_den > other.denominator:
            return "BIGGER_DENOMINATOR_BIGGER"
        return None

    if t == "lcd":
        if p.value == a.denominator + b.denominator:
            return "ADD_ACROSS"
        return None
    return None


def check_answer(q: dict, raw: str) -> CheckResult:
    """Check a student's answer exactly. Never raises on bad student input."""
    expected = correct_answer(q)
    expected_text = fmt(expected)
    try:
        p = parse_answer(raw)
    except AnswerFormatError as e:
        return CheckResult(valid=False, error=str(e), expected=None)

    t = q["type"]
    res = CheckResult(valid=True, expected=expected_text, normalized=fmt(p.value))

    if t == "compare":
        opts = [parse_fraction(q["a"]), parse_fraction(q["b"])]
        if p.value not in opts:
            return CheckResult(valid=False, error=f"Choose one of {q['a']} or {q['b']}.")
        res.correct = p.value == expected
    elif t in ("equivalent", "lcd"):
        if p.value.denominator != 1 or p.written_den != 1:
            return CheckResult(valid=False, error="This question needs a whole number.")
        if t == "lcd" and p.value <= 0:
            return CheckResult(valid=False, error="A denominator must be a positive whole number.")
        res.correct = p.value == expected
        if t == "lcd" and not res.correct:
            a, b = parse_fraction(q["a"]), parse_fraction(q["b"])
            v = int(p.value)
            if v % a.denominator == 0 and v % b.denominator == 0:
                res.notes.append(
                    f"{v} is a common denominator, but not the lowest one. The lowest is {expected_text}."
                )
                res.pattern = "COMMON_NOT_LOWEST"
    elif t == "simplify":
        in_lowest = math.gcd(abs(p.written_num), p.written_den) == 1
        res.correct = p.value == expected and in_lowest
    else:  # add, sub, multiply: any equivalent value is correct
        res.correct = p.value == expected
        if res.correct and math.gcd(abs(p.written_num), p.written_den) != 1:
            res.notes.append(f"Correct. You can also simplify it to {expected_text}.")

    if not res.correct and res.pattern is None:
        res.pattern = detect_pattern(q, p)
    return res


def validate_question(q: dict) -> None:
    """Raise if a question-bank entry is malformed or has no computable answer."""
    for k in ("id", "pool", "skill_id", "type", "a"):
        if k not in q:
            raise ValueError(f"Question missing '{k}': {q}")
    if q["type"] in ("add", "sub", "multiply", "compare", "lcd") and "b" not in q:
        raise ValueError(f"Question {q['id']} needs operand b")
    if q["type"] == "equivalent" and "target" not in q:
        raise ValueError(f"Question {q['id']} needs target")
    correct_answer(q)
    render_prompt(q)


# --------------------------------------------------------------------------
# Hints and worked examples (deterministic, so arithmetic is always right)
# --------------------------------------------------------------------------

def hints_for(q: dict) -> list[str]:
    t = q["type"]
    a = parse_fraction(q["a"])
    b = parse_fraction(q["b"]) if "b" in q else None
    if t in ("add", "sub"):
        d1, d2 = a.denominator, b.denominator
        if d1 == d2:
            return ["The denominators already match.", "Combine only the numerators; the denominator stays the same."]
        L = lcm(d1, d2)
        return [
            f"The denominators {d1} and {d2} are different, so you can't combine the fractions yet.",
            f"Find a number both {d1} and {d2} go into. The lowest is {L}.",
            f"Rewrite: {q['a']} = {a.numerator * (L // d1)}/{L} and {q['b']} = {b.numerator * (L // d2)}/{L}. "
            f"Now {'add' if t == 'add' else 'subtract'} the numerators.",
        ]
    if t == "lcd":
        d1, d2 = a.denominator, b.denominator
        return [
            f"List multiples of {max(d1, d2)}: {', '.join(str(max(d1, d2) * k) for k in range(1, 5))}…",
            f"Which is the first of those that {min(d1, d2)} also divides into?",
        ]
    if t == "equivalent":
        target = int(q["target"])
        factor = target // a.denominator
        return [
            f"What do you multiply {a.denominator} by to get {target}?",
            f"You multiply by {factor}. Do the same to the numerator {a.numerator}.",
        ]
    if t == "simplify":
        g = math.gcd(a.numerator, a.denominator)
        return [
            f"Find the biggest number that divides both {a.numerator} and {a.denominator}.",
            f"It's {g}. Divide the top and the bottom by {g}.",
        ]
    if t == "compare":
        L = lcm(a.denominator, b.denominator)
        return [
            "A bigger denominator means the whole is cut into more pieces, so each piece is smaller.",
            f"Rewrite both over {L}: {q['a']} = {a.numerator * (L // a.denominator)}/{L}, "
            f"{q['b']} = {b.numerator * (L // b.denominator)}/{L}. Now compare the numerators.",
        ]
    if t == "multiply":
        return [
            "To multiply fractions you don't need a common denominator.",
            f"Multiply the tops: {a.numerator} × {b.numerator}. Multiply the bottoms: {a.denominator} × {b.denominator}. Then simplify.",
        ]
    return []


def worked_solution(q: dict) -> list[str]:
    """Step-by-step solution, computed exactly."""
    t = q["type"]
    a = parse_fraction(q["a"])
    b = parse_fraction(q["b"]) if "b" in q else None
    ans = correct_answer(q)
    if t in ("add", "sub"):
        d1, d2 = a.denominator, b.denominator
        L = lcm(d1, d2)
        n1, n2 = a.numerator * (L // d1), b.numerator * (L // d2)
        op = "+" if t == "add" else "−"
        comb = n1 + n2 if t == "add" else n1 - n2
        steps = []
        if d1 != d2:
            steps.append(f"The lowest common denominator of {d1} and {d2} is {L}.")
            steps.append(f"{q['a']} = {n1}/{L} (multiply top and bottom by {L // d1}).")
            steps.append(f"{q['b']} = {n2}/{L} (multiply top and bottom by {L // d2}).")
        steps.append(f"{n1}/{L} {op} {n2}/{L} = {comb}/{L}.")
        if comb != 0 and math.gcd(abs(comb), L) != 1:
            steps.append(f"Simplify: {comb}/{L} = {fmt(ans)}.")
        return steps
    if t == "lcd":
        return [f"Multiples of {a.denominator} and {b.denominator} meet first at {fmt(ans)}."]
    if t == "equivalent":
        f = int(q["target"]) // a.denominator
        return [f"{a.denominator} × {f} = {q['target']}, so {a.numerator} × {f} = {fmt(ans)}."]
    if t == "simplify":
        g = math.gcd(a.numerator, a.denominator)
        return [f"Greatest common factor of {a.numerator} and {a.denominator} is {g}.", f"{q['a']} = {fmt(ans)}."]
    if t == "compare":
        L = lcm(a.denominator, b.denominator)
        return [
            f"{q['a']} = {a.numerator * (L // a.denominator)}/{L}, {q['b']} = {b.numerator * (L // b.denominator)}/{L}.",
            f"So {fmt(ans)} is larger.",
        ]
    if t == "multiply":
        raw = Fraction(a.numerator * b.numerator, a.denominator * b.denominator)
        return [
            f"{a.numerator}×{b.numerator} = {a.numerator * b.numerator}, {a.denominator}×{b.denominator} = {a.denominator * b.denominator}.",
            f"{a.numerator * b.numerator}/{a.denominator * b.denominator} = {fmt(raw)}.",
        ]
    return []
