"""Mathematics topics beyond fractions. Every answer and every misconception answer is COMPUTED exactly."""
from fractions import Fraction

from .common import TOPIC_IDS, Bank, D, br, neg, num

# =====================================================================================  DECIMALS
TOPIC_IDS["DEC"] = "decimals"


def _misaligned_sum(a: str, b: str, sub=False) -> Fraction:
    """What a student gets by lining up the LAST digits instead of the decimal points."""
    da = len(a.split(".")[1]) if "." in a else 0
    db = len(b.split(".")[1]) if "." in b else 0
    ia, ib = int(a.replace(".", "")), int(b.replace(".", ""))
    places = max(da, db)
    return Fraction(ia - ib if sub else ia + ib, 10 ** places)


def decimals() -> dict:
    B = Bank("DEC")
    PV, AD = "decimal_place_value", "adding_decimals"
    cmp_hints = ["Line up the decimal points and compare the tenths digit first.",
                 "Add zeros so both have the same number of decimal places, e.g. 0.5 = 0.50."]

    def compare(kind, a, b, role=None):
        big = a if D(a) > D(b) else b
        small = b if big == a else a
        longer = a if len(a) > len(b) else b
        pats = {small: "DEC_LONGER_BIGGER"} if longer == small else None
        L = max(len(a.split(".")[1]), len(b.split(".")[1]))
        pa, pb = a.ljust(L + 2, "0"), b.ljust(L + 2, "0")
        B.add(kind, PV, "mcq", f"Which is larger: {a} or {b}?", big, options=[a, b], patterns=pats, role=role,
              hints=cmp_hints, solution=[f"Write both with {L} decimal places: {a} = {pa}, {b} = {pb}.",
                                         f"Compare digit by digit from the left: {big} is larger."])

    add_hints = ["Line up the decimal points, one under the other.",
                 "Fill empty places with 0 (2.5 = 2.50), then add as usual and keep the point in line."]

    def add(kind, a, b, sub=False, role=None):
        ans = D(a) - D(b) if sub else D(a) + D(b)
        wrong = _misaligned_sum(a, b, sub)
        L = max(len(x.split(".")[1]) if "." in x else 0 for x in (a, b))
        pa = format(D(a).numerator / D(a).denominator, f".{L}f")
        pb = format(D(b).numerator / D(b).denominator, f".{L}f")
        op = "−" if sub else "+"
        B.add(kind, AD, "numeric", f"{a} {op} {b} = ?", num(ans), patterns={num(wrong): "DEC_RIGHT_ALIGN"},
              role=role, hints=add_hints,
              solution=[f"Line up the points: {pa} {op} {pb}.", f"{pa} {op} {pb} = {num(ans)}."])

    # diagnostics
    compare("diagnostic:A", "0.5", "0.25"); compare("diagnostic:A", "0.7", "0.65")
    add("diagnostic:A", "2.5", "1.25"); add("diagnostic:A", "3.4", "1.15"); add("diagnostic:A", "0.3", "0.4")
    compare("diagnostic:B", "0.8", "0.75"); compare("diagnostic:B", "0.3", "0.125")
    add("diagnostic:B", "4.6", "2.35"); add("diagnostic:B", "1.5", "3.25"); add("diagnostic:B", "0.2", "0.6")
    # verification
    compare("verification", "0.4", "0.36", "same_type"); compare("verification", "0.6", "0.55", "same_type")
    compare("verification", "0.9", "0.875", "similar_concept"); compare("verification", "0.2", "0.15", "similar_concept")
    add("verification", "5.5", "1.25", role="same_type"); add("verification", "2.7", "3.15", role="same_type")
    add("verification", "6.75", "1.5", sub=True, role="similar_concept"); add("verification", "8.4", "2.25", role="similar_concept")
    # practice
    for a, b in (("0.6", "0.45"), ("0.35", "0.4"), ("0.09", "0.1"), ("1.2", "1.15")):
        compare("practice", a, b)
    for a, b in (("3.5", "2.25"), ("1.75", "0.5"), ("4.2", "1.05"), ("9.8", "0.15")):
        add("practice", a, b)
    # retest (two sets of three)
    for a, b in (("0.7", "0.69"), ("0.5", "0.45"), ("0.4", "0.375"), ("0.1", "0.08"), ("0.6", "0.525"), ("0.3", "0.25")):
        compare("retest", a, b)
    for a, b, s in (("6.5", "2.25", False), ("7.3", "1.45", False), ("5.75", "1.5", True),
                    ("2.4", "5.35", False), ("8.6", "0.15", False), ("9.25", "3.5", True)):
        add("retest", a, b, s)

    lessons = {
        PV: {"title": "Decimal place value",
             "big_idea": "After the decimal point the places are tenths, then hundredths, then thousandths. "
                         "More digits does not mean bigger: 0.5 is 5 tenths, and 0.25 is only 2 tenths and 5 hundredths.",
             "steps": ["Line up the two numbers by their decimal points.",
                       "If one has fewer digits, add zeros at the end: 0.5 becomes 0.50. This does not change its value.",
                       "Compare the tenths digits first. The bigger tenths digit wins.",
                       "Only if the tenths are equal, compare the hundredths, and so on."],
             "sense_check": "Think of money: 0.5 of a rupee is 50 paise, 0.25 of a rupee is 25 paise. 50 paise is more.",
             "worked_examples": [
                 {"prompt": "Which is larger: 0.5 or 0.25?", "answer": "0.5",
                  "steps": ["Write 0.5 as 0.50.", "Compare tenths: 5 tenths vs 2 tenths.", "5 > 2, so 0.5 is larger."]},
                 {"prompt": "Which is larger: 0.7 or 0.65?", "answer": "0.7",
                  "steps": ["Write 0.7 as 0.70.", "70 hundredths vs 65 hundredths.", "0.7 is larger."]}]},
        AD: {"title": "Adding and subtracting decimals",
             "big_idea": "You can only add digits that have the same place value. Lining up the decimal points "
                         "lines up tenths with tenths and hundredths with hundredths.",
             "steps": ["Write the numbers one under the other with the decimal points in a straight line.",
                       "Fill any empty places at the end with 0 so both have the same number of decimal places.",
                       "Add or subtract column by column from the right, carrying or borrowing as usual.",
                       "Put the decimal point in the answer directly under the other points."],
             "sense_check": "Estimate first: 2.5 + 1.25 is about 2 + 1 = 3, so an answer like 1.5 can't be right.",
             "worked_examples": [
                 {"prompt": "2.5 + 1.25 = ?", "answer": num(D("2.5") + D("1.25")),
                  "steps": ["Line up the points: 2.50 + 1.25.", "Add the columns: 3.75."]},
                 {"prompt": "4.6 − 1.25 = ?", "answer": num(D("4.6") - D("1.25")),
                  "steps": ["Line up the points: 4.60 − 1.25.", "Subtract the columns: 3.35."]}]},
    }
    return {
        "topic": {"id": "decimals", "subject": "mathematics", "name": "Decimals", "unit": "Number",
                  "grade_min": 4, "grade_max": 6,
                  "description": "Place value after the decimal point, comparing decimals, adding and subtracting.",
                  "objectives": ["Compare decimals using place value", "Add and subtract decimals by lining up the points"],
                  "skills": [PV, AD]},
        "skills": [
            {"id": PV, "name": "Decimal place value", "grade": 4, "prerequisites": [],
             "description": "Tenths and hundredths; comparing decimals by place value."},
            {"id": AD, "name": "Adding and subtracting decimals", "grade": 5, "prerequisites": [PV],
             "description": "Line up decimal points so digits of the same place value are added."}],
        "misconceptions": {
            "DEC_LONGER_BIGGER": {"label": "Thinks a decimal with more digits is larger", "gap_skill": PV,
                                  "explanation": "Compares the digits after the point like whole numbers, so 0.25 "
                                                 "seems bigger than 0.5 because 25 > 5."},
            "DEC_RIGHT_ALIGN": {"label": "Lines up the last digits instead of the decimal points", "gap_skill": AD,
                                "explanation": "Adds 2.5 + 1.25 as 25 + 125, giving 1.50 instead of 3.75."}},
        "questions": B.items, "lessons": lessons}


# =====================================================================================  PERCENTAGES
TOPIC_IDS["PCT"] = "percentages"


def percentages() -> dict:
    B = Bank("PCT")
    PM, PQ = "percent_meaning", "percent_of_quantity"
    m_hints = ["Per cent means 'out of 100'.", "To turn a percentage into a decimal, divide by 100: move the point two places left."]

    def to_dec(kind, p, role=None):
        ans = Fraction(p, 100)
        B.add(kind, PM, "numeric", f"Write {p}% as a decimal.", num(ans),
              patterns={num(Fraction(p, 10)): "PCT_DECIMAL_SHIFT"}, role=role, hints=m_hints,
              solution=[f"{p}% means {p} out of 100.", f"{p} ÷ 100 = {num(ans)}."])

    def to_pct(kind, dec, role=None):
        v = D(dec)
        ans = v * 100
        B.add(kind, PM, "numeric", f"Write {dec} as a percentage. (Type the number, e.g. 40 for 40%.)", num(ans),
              percent=True, patterns={num(v * 10): "PCT_DECIMAL_SHIFT"}, role=role,
              hints=["Multiply by 100 to turn a decimal into a percentage.", "Move the point two places right."],
              solution=[f"{dec} × 100 = {num(ans)}.", f"So {dec} = {num(ans)}%."])

    q_hints = ["Find 10% or 1% first, then build up.", "p% of n means (p ÷ 100) × n."]

    def of(kind, p, n, role=None):
        ans = Fraction(p * n, 100)
        pats = {num(n - p): "PCT_SUBTRACT", num(Fraction(n, p)): "PCT_DIVIDE"}
        B.add(kind, PQ, "numeric", f"What is {p}% of {n}?", num(ans), patterns=pats, role=role, hints=q_hints,
              solution=[f"{p}% = {p}/100.", f"{p}/100 × {n} = {p * n}/100 = {num(ans)}."])

    to_dec("diagnostic:A", 7); to_pct("diagnostic:A", "0.4"); of("diagnostic:A", 20, 50); of("diagnostic:A", 25, 80); of("diagnostic:A", 10, 70)
    to_dec("diagnostic:B", 3); to_pct("diagnostic:B", "0.6"); of("diagnostic:B", 30, 60); of("diagnostic:B", 75, 40); of("diagnostic:B", 15, 60)
    to_dec("verification", 9, "same_type"); to_dec("verification", 5, "same_type")
    to_pct("verification", "0.3", "similar_concept"); to_pct("verification", "0.8", "similar_concept")
    of("verification", 40, 25, "same_type"); of("verification", 20, 35, "same_type")
    of("verification", 50, 36, "similar_concept"); of("verification", 30, 90, "similar_concept")
    to_dec("practice", 4); to_dec("practice", 8); to_pct("practice", "0.2"); to_pct("practice", "0.9")
    of("practice", 10, 90); of("practice", 25, 40); of("practice", 60, 30); of("practice", 5, 80)
    for p in (2, 6, 1):
        to_dec("retest", p)
    for d in ("0.7", "0.5", "0.1"):
        to_pct("retest", d)
    for p, n in ((20, 45), (40, 15), (75, 12), (30, 50), (25, 60), (60, 45)):
        of("retest", p, n)

    lessons = {
        PM: {"title": "What a percentage means",
             "big_idea": "Per cent means 'out of 100'. 7% is 7 out of 100, which is 0.07, not 0.7.",
             "steps": ["Read p% as p out of 100, or p/100.",
                       "To change a percentage to a decimal, divide by 100: move the decimal point two places left.",
                       "7% → 7.0 → 0.07. Add a zero if you run out of digits.",
                       "To change a decimal to a percentage, multiply by 100: 0.4 → 40%."],
             "sense_check": "0.7 is more than half, but 7% is a tiny part of the whole. They can't be equal.",
             "worked_examples": [
                 {"prompt": "Write 7% as a decimal.", "answer": "0.07", "steps": ["7% = 7/100.", "7 ÷ 100 = 0.07."]},
                 {"prompt": "Write 0.4 as a percentage.", "answer": "40", "steps": ["0.4 × 100 = 40.", "0.4 = 40%."]}]},
        PQ: {"title": "Finding a percentage of an amount",
             "big_idea": "p% of an amount means p hundredths of it: multiply the amount by p and divide by 100.",
             "steps": ["Write the percentage as a fraction over 100.",
                       "Multiply that fraction by the amount.",
                       "A shortcut: 10% is the amount ÷ 10, then scale up (20% is double 10%).",
                       "Check the size: 20% is less than half, so the answer must be less than half the amount."],
             "sense_check": "20% of 50 is a small part of 50. 30 is more than half of 50, so it can't be 20% of it.",
             "worked_examples": [
                 {"prompt": "What is 20% of 50?", "answer": "10",
                  "steps": ["10% of 50 = 5.", "20% = 2 × 10%, so 2 × 5 = 10."]},
                 {"prompt": "What is 25% of 80?", "answer": "20", "steps": ["25% = 1/4.", "80 ÷ 4 = 20."]}]},
    }
    return {
        "topic": {"id": "percentages", "subject": "mathematics", "name": "Percentages", "unit": "Ratio and proportion",
                  "grade_min": 6, "grade_max": 8,
                  "description": "What per cent means, converting to decimals, and finding a percentage of an amount.",
                  "objectives": ["Convert between percentages and decimals", "Find a percentage of a quantity"],
                  "skills": [PM, PQ]},
        "skills": [
            {"id": PM, "name": "What a percentage means", "grade": 6, "prerequisites": ["decimal_place_value"],
             "description": "Per cent as 'out of 100'; converting percentages and decimals."},
            {"id": PQ, "name": "Percentage of an amount", "grade": 6, "prerequisites": [PM],
             "description": "Finding p% of a quantity."}],
        "misconceptions": {
            "PCT_DECIMAL_SHIFT": {"label": "Moves the decimal point only one place when converting percentages",
                                  "gap_skill": PM, "explanation": "Writes 7% as 0.7 (or 0.4 as 4%), forgetting that per cent means out of 100."},
            "PCT_SUBTRACT": {"label": "Subtracts the percentage number from the amount", "gap_skill": PQ,
                             "explanation": "Works out 20% of 50 as 50 − 20 = 30."},
            "PCT_DIVIDE": {"label": "Divides the amount by the percentage number", "gap_skill": PQ,
                           "explanation": "Works out 20% of 50 as 50 ÷ 20 = 2.5."}},
        "questions": B.items, "lessons": lessons}


# =====================================================================================  INTEGERS
TOPIC_IDS["INT"] = "integers"


def integers() -> dict:
    B = Bank("INT")
    AI, MI = "adding_integers", "multiplying_integers"
    a_hints = ["Picture a number line. Adding a negative number moves you LEFT.",
               "Subtracting a negative number is the same as adding the positive number."]

    def add(kind, a, b, role=None):
        ans = a + b
        pats = {}
        if a < 0 and b < 0:
            pats[str(abs(a) + abs(b))] = "INT_TWO_NEG_POS"
        else:
            pats[str(abs(a) + abs(b))] = "INT_IGNORE_SIGNS"
            pats[str(-(abs(a) + abs(b)))] = "INT_IGNORE_SIGNS"
            pats[str(-ans)] = "INT_IGNORE_SIGNS"
        B.add(kind, AI, "numeric", f"{neg(a)} + {br(b)} = ?", str(ans), patterns=pats, role=role, hints=a_hints,
              solution=[f"Start at {neg(a)} on the number line.",
                        f"{'Move left' if b < 0 else 'Move right'} {abs(b)} steps.", f"You land on {neg(ans)}."])

    def sub(kind, a, b, role=None):  # a - (negative b)
        ans = a - b
        B.add(kind, AI, "numeric", f"{neg(a)} − {br(b)} = ?", str(ans), patterns={str(a + b): "INT_SUB_NEG"},
              role=role, hints=a_hints,
              solution=[f"Subtracting {br(b)} is the same as adding {abs(b)}.", f"{neg(a)} + {abs(b)} = {neg(ans)}."])

    m_hints = ["Multiply the sizes first, then decide the sign.",
               "Same signs give a positive answer. Different signs give a negative answer."]

    def mul(kind, a, b, role=None):
        ans = a * b
        B.add(kind, MI, "numeric", f"{neg(a)} × {br(b)} = ?", str(ans), patterns={str(-ans): "INT_MUL_SIGN"},
              role=role, hints=m_hints,
              solution=[f"{abs(a)} × {abs(b)} = {abs(ans)}.",
                        f"The signs are {'the same' if (a < 0) == (b < 0) else 'different'}, so the answer is "
                        f"{'positive' if ans > 0 else 'negative'}: {neg(ans)}."])

    add("diagnostic:A", -3, -4); add("diagnostic:A", -5, 3); sub("diagnostic:A", 7, -2); mul("diagnostic:A", -3, -4); mul("diagnostic:A", 5, -2)
    add("diagnostic:B", -6, -2); add("diagnostic:B", 4, -9); sub("diagnostic:B", 3, -5); mul("diagnostic:B", -2, -6); mul("diagnostic:B", -4, 3)
    add("verification", -2, -5, "same_type"); add("verification", -7, -1, "same_type")
    add("verification", -8, 3, "similar_concept"); sub("verification", 6, -4, "similar_concept")
    mul("verification", -5, -3, "same_type"); mul("verification", -6, -2, "same_type")
    mul("verification", 7, -3, "similar_concept"); mul("verification", -9, 2, "similar_concept")
    add("practice", -4, -4); add("practice", -9, 5); sub("practice", 2, -6); add("practice", 6, -8)
    mul("practice", -7, -2); mul("practice", 3, -8); mul("practice", -4, -5); mul("practice", -6, 4)
    for a, b in ((-5, -6), (-9, 4), (-3, -8), (-2, 7), (-10, -5), (8, -12)):
        add("retest", a, b)
    for a, b in ((-8, -3), (6, -7), (-9, -4), (-5, 8), (-7, -7), (4, -11)):
        mul("retest", a, b)

    lessons = {
        AI: {"title": "Adding and subtracting negative numbers",
             "big_idea": "On a number line, adding a negative number moves you left. Two negatives added together "
                         "make a MORE negative number. 'Two negatives make a positive' is a rule for multiplying, not adding.",
             "steps": ["Find the first number on the number line.",
                       "Adding a positive number: move right. Adding a negative number: move left.",
                       "Subtracting a negative number is the same as adding its positive: 7 − (−2) = 7 + 2.",
                       "Read off where you land."],
             "sense_check": "If you owe ₹3 and borrow ₹4 more, you owe ₹7: −3 + (−4) = −7, not +7.",
             "worked_examples": [
                 {"prompt": "−3 + (−4) = ?", "answer": "-7", "steps": ["Start at −3.", "Move 4 left.", "You land on −7."]},
                 {"prompt": "7 − (−2) = ?", "answer": "9", "steps": ["Subtracting −2 means adding 2.", "7 + 2 = 9."]}]},
        MI: {"title": "Multiplying negative numbers",
             "big_idea": "Multiply the sizes, then use the sign rule: same signs give a positive answer, different signs give a negative answer.",
             "steps": ["Ignore the signs and multiply the sizes.",
                       "Look at the signs: both negative, or both positive, gives a positive answer.",
                       "One negative and one positive gives a negative answer.",
                       "Write the sign in front of your answer."],
             "sense_check": "3 × (−4) means three lots of −4: −4 −4 −4 = −12. So positive × negative is negative.",
             "worked_examples": [
                 {"prompt": "−3 × (−4) = ?", "answer": "12", "steps": ["3 × 4 = 12.", "Same signs, so positive: 12."]},
                 {"prompt": "5 × (−2) = ?", "answer": "-10", "steps": ["5 × 2 = 10.", "Different signs, so negative: −10."]}]},
    }
    return {
        "topic": {"id": "integers", "subject": "mathematics", "name": "Integers", "unit": "Number systems",
                  "grade_min": 6, "grade_max": 8,
                  "description": "Adding, subtracting and multiplying positive and negative numbers.",
                  "objectives": ["Add and subtract negative numbers", "Multiply integers using the sign rules"],
                  "skills": [AI, MI]},
        "skills": [
            {"id": AI, "name": "Adding and subtracting negative numbers", "grade": 6, "prerequisites": [],
             "description": "Number-line model for adding and subtracting integers."},
            {"id": MI, "name": "Multiplying negative numbers", "grade": 7, "prerequisites": [AI],
             "description": "Sign rules for multiplying integers."}],
        "misconceptions": {
            "INT_TWO_NEG_POS": {"label": "Uses 'two negatives make a positive' when adding", "gap_skill": AI,
                                "explanation": "Works out −3 + (−4) as 7, borrowing the multiplication sign rule."},
            "INT_IGNORE_SIGNS": {"label": "Ignores or mixes up the signs when adding", "gap_skill": AI,
                                 "explanation": "Works out −5 + 3 as 8, −8 or 2 instead of −2."},
            "INT_SUB_NEG": {"label": "Thinks subtracting a negative number makes the answer smaller", "gap_skill": AI,
                            "explanation": "Works out 7 − (−2) as 5 instead of 9."},
            "INT_MUL_SIGN": {"label": "Gets the sign wrong when multiplying negative numbers", "gap_skill": MI,
                             "explanation": "Works out −3 × (−4) as −12, or 5 × (−2) as 10."}},
        "questions": B.items, "lessons": lessons}


# =====================================================================================  LINEAR EQUATIONS
TOPIC_IDS["ALG"] = "linear_equations"


def linear_equations() -> dict:
    B = Bank("ALG")
    O1, O2 = "one_step_equations", "two_step_equations"
    h1 = ["Ask: what was done to x? Then do the OPPOSITE to both sides.",
          "The opposite of + is −, and the opposite of × is ÷."]

    def plus(kind, k, r, role=None):  # x + k = r
        ans = r - k
        B.add(kind, O1, "numeric", f"Solve for x:  x + {k} = {r}", num(ans), patterns={num(r + k): "ALG_SAME_OP"},
              role=role, hints=h1, solution=[f"x has {k} added, so subtract {k} from both sides.", f"x = {r} − {k} = {num(ans)}."])

    def minus(kind, k, r, role=None):
        ans = r + k
        B.add(kind, O1, "numeric", f"Solve for x:  x − {k} = {r}", num(ans), patterns={num(r - k): "ALG_SAME_OP"},
              role=role, hints=h1, solution=[f"x has {k} taken away, so add {k} to both sides.", f"x = {r} + {k} = {num(ans)}."])

    def times(kind, a, r, role=None):
        ans = Fraction(r, a)
        B.add(kind, O1, "numeric", f"Solve for x:  {a}x = {r}", num(ans),
              patterns={num(r - a): "ALG_COEFF_SUB", num(r * a): "ALG_SAME_OP"}, role=role, hints=h1,
              solution=[f"{a}x means {a} × x, so divide both sides by {a}.", f"x = {r} ÷ {a} = {num(ans)}."])

    h2 = ["Undo the steps in reverse order: first undo the + or −, then undo the ×.",
          "Do the same thing to both sides at every step."]

    def two(kind, a, k, r, role=None):  # ax + k = r
        ans = Fraction(r - k, a)
        B.add(kind, O2, "numeric", f"Solve for x:  {a}x + {k} = {r}", num(ans),
              patterns={num(Fraction(r, a) - k): "ALG_ORDER", num(Fraction(r + k, a)): "ALG_SAME_OP"}, role=role,
              hints=h2, solution=[f"Subtract {k} from both sides: {a}x = {r - k}.",
                                  f"Divide both sides by {a}: x = {num(ans)}."])

    plus("diagnostic:A", 5, 12); times("diagnostic:A", 3, 12); two("diagnostic:A", 2, 3, 11); two("diagnostic:A", 4, 1, 21); minus("diagnostic:A", 4, 9)
    plus("diagnostic:B", 8, 15); times("diagnostic:B", 4, 20); two("diagnostic:B", 2, 5, 17); two("diagnostic:B", 3, 2, 14); minus("diagnostic:B", 6, 3)
    plus("verification", 7, 19, "same_type"); times("verification", 5, 30, "same_type")
    minus("verification", 9, 4, "similar_concept"); times("verification", 6, 42, "similar_concept")
    two("verification", 2, 7, 15, "same_type"); two("verification", 5, 3, 23, "same_type")
    two("verification", 4, 6, 26, "similar_concept"); two("verification", 3, 4, 19, "similar_concept")
    plus("practice", 3, 10); minus("practice", 5, 8); times("practice", 2, 18); times("practice", 7, 35)
    two("practice", 2, 1, 9); two("practice", 3, 5, 20); two("practice", 4, 2, 18); two("practice", 5, 1, 26)
    plus("retest", 9, 20); times("retest", 8, 48); minus("retest", 7, 5); plus("retest", 6, 13); times("retest", 9, 54); minus("retest", 3, 12)
    for a, k, r in ((2, 9, 21), (3, 1, 16), (5, 4, 29), (4, 3, 27), (2, 11, 25), (6, 5, 41)):
        two("retest", a, k, r)

    lessons = {
        O1: {"title": "Solving one-step equations",
             "big_idea": "An equation is a balance. To get x on its own, undo what was done to it by doing the "
                         "OPPOSITE operation to both sides.",
             "steps": ["Look at what is happening to x: is something added, subtracted or multiplied?",
                       "Choose the opposite: + ↔ −, × ↔ ÷.",
                       "Do that opposite to BOTH sides so the balance stays level.",
                       "Check: put your answer back into the equation."],
             "sense_check": "If x + 5 = 12 and you said x = 17, check it: 17 + 5 = 22, not 12. So x must be smaller than 12.",
             "worked_examples": [
                 {"prompt": "Solve for x:  x + 5 = 12", "answer": "7", "steps": ["Subtract 5 from both sides.", "x = 12 − 5 = 7.", "Check: 7 + 5 = 12 ✓"]},
                 {"prompt": "Solve for x:  3x = 12", "answer": "4", "steps": ["3x means 3 × x.", "Divide both sides by 3: x = 4.", "Check: 3 × 4 = 12 ✓"]}]},
        O2: {"title": "Solving two-step equations",
             "big_idea": "In 2x + 3 = 11, x was first multiplied by 2, then 3 was added. Undo them in REVERSE "
                         "order: subtract 3 first, then divide by 2.",
             "steps": ["Undo the adding or subtracting first.",
                       "Then undo the multiplying by dividing.",
                       "Do each step to both sides.",
                       "Check by substituting your answer."],
             "sense_check": "Getting dressed: socks then shoes. Undressing: shoes first, then socks. Undo in reverse order.",
             "worked_examples": [
                 {"prompt": "Solve for x:  2x + 3 = 11", "answer": "4",
                  "steps": ["Subtract 3: 2x = 8.", "Divide by 2: x = 4.", "Check: 2 × 4 + 3 = 11 ✓"]},
                 {"prompt": "Solve for x:  4x + 1 = 21", "answer": "5",
                  "steps": ["Subtract 1: 4x = 20.", "Divide by 4: x = 5.", "Check: 4 × 5 + 1 = 21 ✓"]}]},
    }
    return {
        "topic": {"id": "linear_equations", "subject": "mathematics", "name": "Linear equations", "unit": "Algebra",
                  "grade_min": 6, "grade_max": 8,
                  "description": "Solving one-step and two-step equations with inverse operations.",
                  "objectives": ["Solve one-step equations", "Solve two-step equations by undoing in reverse order"],
                  "skills": [O1, O2]},
        "skills": [
            {"id": O1, "name": "Solving one-step equations", "grade": 6, "prerequisites": [],
             "description": "Use the inverse operation on both sides."},
            {"id": O2, "name": "Solving two-step equations", "grade": 7, "prerequisites": [O1],
             "description": "Undo operations in reverse order."}],
        "misconceptions": {
            "ALG_SAME_OP": {"label": "Does the same operation instead of the opposite one", "gap_skill": O1,
                            "explanation": "Solves x + 5 = 12 as x = 17 by adding 5 again instead of subtracting."},
            "ALG_COEFF_SUB": {"label": "Subtracts the number in front of x instead of dividing", "gap_skill": O1,
                              "explanation": "Solves 3x = 12 as x = 9."},
            "ALG_ORDER": {"label": "Undoes the steps in the wrong order", "gap_skill": O2,
                          "explanation": "Solves 2x + 3 = 11 by dividing first: 11 ÷ 2 − 3 = 2.5 instead of 4."}},
        "questions": B.items, "lessons": lessons}


ALL = [decimals, percentages, integers, linear_equations]
