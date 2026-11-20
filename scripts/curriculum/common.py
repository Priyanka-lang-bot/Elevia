"""Small helpers shared by the curriculum authoring modules."""
from decimal import Decimal
from fractions import Fraction


def num(v) -> str:
    """Exact number -> short text (0.5, -3, 7/3)."""
    v = Fraction(v) if not isinstance(v, Fraction) else v
    if v.denominator == 1:
        return str(v.numerator)
    d = v.denominator
    for p in (2, 5):
        while d % p == 0:
            d //= p
    if d == 1:
        s = format(Decimal(v.numerator) / Decimal(v.denominator), "f")
        return s.rstrip("0").rstrip(".")
    return f"{v.numerator}/{v.denominator}"


def D(s: str) -> Fraction:
    return Fraction(Decimal(s))


def neg(n) -> str:
    """Display a number with a proper minus sign; negative numbers in brackets when they follow an operator."""
    return f"−{abs(n)}" if n < 0 else str(n)


def br(n) -> str:
    return f"(−{abs(n)})" if n < 0 else str(n)


class Bank:
    """Collects questions for one topic and assigns ids."""

    def __init__(self, prefix: str):
        self.prefix, self.items, self.n = prefix, [], {}

    def add(self, pool_kind: str, skill: str, qtype: str, prompt: str, answer: str, *, hints, solution,
            patterns=None, options=None, accept=None, code=None, role=None, percent=False, gap=None):
        tag = {"diagnostic:A": "DA", "diagnostic:B": "DB", "verification": "V", "practice": "P",
               "retest": "R"}[pool_kind]
        key = (tag, skill if tag in ("V", "P", "R") else "")
        self.n[key] = self.n.get(key, 0) + 1
        sk = "".join(w[0] for w in skill.split("_")).upper() if tag in ("V", "P", "R") else ""
        qid = f"{self.prefix}-{tag}{sk}{self.n[key]}"
        topic = self.prefix.lower()
        pool = {"DA": f"diagnostic:{TOPIC_IDS[self.prefix]}:A", "DB": f"diagnostic:{TOPIC_IDS[self.prefix]}:B"}.get(
            tag, f"{pool_kind}:{skill}")
        q = {"id": qid, "pool": pool, "skill_id": skill, "type": qtype, "gap_targets": [gap or skill],
             "prompt": prompt, "answer": str(answer), "hints": list(hints), "solution": list(solution)}
        if patterns:
            q["patterns"] = {str(k): v for k, v in patterns.items() if str(k) != str(answer)}
        if options:
            q["options"] = list(options)
        if accept:
            q["accept"] = list(accept)
        if code:
            q["code"] = code
        if role:
            q["check_role"] = role
        if percent:
            q["percent"] = True
        self.items.append(q)
        return q


TOPIC_IDS = {}  # prefix -> topic id, filled by each module
