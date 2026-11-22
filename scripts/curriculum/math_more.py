"""More Mathematics topics. Every answer and every misconception answer is COMPUTED."""
from fractions import Fraction
from math import gcd

from .common import TOPIC_IDS, Bank, num


def _lesson(title, big, steps, sense, examples):
    return {"title": title, "big_idea": big, "steps": steps, "sense_check": sense,
            "worked_examples": [{"prompt": p, "answer": str(a), "steps": s} for p, a, s in examples]}


def _topic(tid, name, unit, gmin, gmax, desc, objectives, skills, mis, qs, lessons):
    return {"topic": {"id": tid, "subject": "mathematics", "name": name, "unit": unit, "grade_min": gmin,
                      "grade_max": gmax, "description": desc, "objectives": objectives,
                      "skills": [s["id"] for s in skills]},
            "skills": skills, "misconceptions": mis, "questions": qs, "lessons": lessons}


def _plan(B, gen_a, gen_b, diag_a, diag_b, ver_a, ver_b, prac_a, prac_b, ret_a, ret_b):
    """Lay out pools: diag A/B (5 each), 4 verification (2 same_type, 2 similar_concept), 4 practice, 6 retest."""
    for kind, items in (("diagnostic:A", diag_a), ("diagnostic:B", diag_b)):
        for which, args in items:
            (gen_a if which == "a" else gen_b)(kind, *args)
    for gen, ver, prac, ret in ((gen_a, ver_a, prac_a, ret_a), (gen_b, ver_b, prac_b, ret_b)):
        for i, args in enumerate(ver):
            role = "same_type" if i < 2 else "similar_concept"
            if None in args:                      # tuple already has a role slot (extra options follow it)
                args = list(args)
                args[args.index(None)] = role
                gen("verification", *args)
            else:
                gen("verification", *args, role=role)
        for args in prac:
            gen("practice", *args)
        for args in ret:
            gen("retest", *args)


# =====================================================================  ORDER OF OPERATIONS
TOPIC_IDS["OOP"] = "order_of_operations"


def order_of_operations():
    B = Bank("OOP")
    MB, BR = "multiply_before_add", "brackets_first"
    h1 = ["Multiplication and division come before addition and subtraction.",
          "Then do + and − from left to right."]
    h2 = ["Work out what is inside the brackets first.", "Then multiply or divide, then add or subtract."]

    def mul(kind, a, b, c, role=None, form=0):
        if form == 0:   # a + b × c
            ans, wrong, p = a + b * c, (a + b) * c, f"{a} + {b} × {c}"
            sol = [f"Multiply first: {b} × {c} = {b * c}.", f"Then add: {a} + {b * c} = {ans}."]
            pats = {wrong: "ARITH_LEFT_TO_RIGHT"}
        elif form == 1:  # a − b + c (left to right)
            ans, wrong, p = a - b + c, a - (b + c), f"{a} − {b} + {c}"
            sol = ["+ and − have the same priority: go left to right.", f"{a} − {b} = {a - b}, then {a - b} + {c} = {ans}."]
            pats = {wrong: "ARITH_ADD_FIRST"}
        else:            # a × b − c... use a − b × c
            ans, wrong, p = a - b * c, (a - b) * c, f"{a} − {b} × {c}"
            sol = [f"Multiply first: {b} × {c} = {b * c}.", f"Then subtract: {a} − {b * c} = {ans}."]
            pats = {wrong: "ARITH_LEFT_TO_RIGHT"}
        B.add(kind, MB, "numeric", f"{p} = ?", str(ans), patterns=pats, role=role, hints=h1, solution=sol)

    def brk(kind, a, b, c, role=None, form=0):
        if form == 0:   # a × (b + c)
            ans, wrong, p = a * (b + c), a * b + c, f"{a} × ({b} + {c})"
            sol = [f"Brackets first: {b} + {c} = {b + c}.", f"Then multiply: {a} × {b + c} = {ans}."]
        else:           # (a + b) × c  ... wrong = a + b*c
            ans, wrong, p = (a + b) * c, a + b * c, f"({a} + {b}) × {c}"
            sol = [f"Brackets first: {a} + {b} = {a + b}.", f"Then multiply: {a + b} × {c} = {ans}."]
        B.add(kind, BR, "numeric", f"{p} = ?", str(ans), patterns={wrong: "ARITH_IGNORE_BRACKETS"}, role=role,
              hints=h2, solution=sol)

    _plan(B, mul, brk,
          [("a", (3, 4, 2)), ("a", (10, 3, 2, None, 1)), ("b", (2, 3, 4)), ("a", (5, 2, 6)), ("b", (3, 2, 5, None, 1))],
          [("a", (6, 2, 5)), ("a", (12, 4, 3, None, 1)), ("b", (4, 2, 3)), ("a", (2, 7, 3)), ("b", (1, 4, 6, None, 1))],
          [(8, 3, 2), (4, 5, 3), (20, 2, 3, None, 2), (15, 6, 4, None, 1)],
          [(5, 1, 4), (3, 6, 2), (2, 5, 3, None, 1), (6, 1, 3, None, 1)],
          [(7, 2, 4), (9, 3, 3), (18, 5, 2, None, 1), (30, 4, 5, None, 2)],
          [(2, 4, 5), (7, 1, 2), (3, 3, 4, None, 1), (5, 2, 6, None, 1)],
          [(6, 3, 4), (2, 8, 5), (11, 2, 3), (14, 5, 3, None, 1), (25, 3, 4, None, 2), (9, 6, 2, None, 1)],
          [(3, 2, 7), (4, 5, 1), (6, 2, 3), (2, 3, 8, None, 1), (5, 4, 2, None, 1), (8, 1, 4, None, 1)])
    lessons = {
        MB: _lesson("Multiply before you add",
                    "In a calculation with several operations, × and ÷ are done before + and −. Additions and "
                    "subtractions are then done from left to right.",
                    ["Look for × and ÷ first and work them out.", "Replace them with their answers.",
                     "Then do + and − in order from left to right."],
                    "3 + 4 × 2 means 3 plus two fours: 3 + 8 = 11, not 7 × 2 = 14.",
                    [("3 + 4 × 2 = ?", 11, ["Multiply first: 4 × 2 = 8.", "Then add: 3 + 8 = 11."]),
                     ("10 − 3 + 2 = ?", 9, ["Left to right: 10 − 3 = 7.", "7 + 2 = 9."])]),
        BR: _lesson("Brackets first",
                    "Brackets change the order: whatever is inside them is worked out before anything else.",
                    ["Work out the inside of each bracket first.", "Then multiply or divide.",
                     "Finally add or subtract."],
                    "2 × (3 + 4) means two lots of 7, which is 14. Without the brackets it would be 2 × 3 + 4 = 10.",
                    [("2 × (3 + 4) = ?", 14, ["Brackets: 3 + 4 = 7.", "2 × 7 = 14."]),
                     ("(3 + 2) × 5 = ?", 25, ["Brackets: 3 + 2 = 5.", "5 × 5 = 25."])]),
    }
    return _topic("order_of_operations", "Order of operations", "Arithmetic", 4, 7,
                  "Which part of a calculation to do first: × and ÷ before + and −, and brackets first.",
                  ["Apply × and ÷ before + and −", "Work out brackets first"],
                  [{"id": MB, "name": "Multiply before you add", "grade": 5, "prerequisites": [],
                    "description": "× and ÷ before + and −; + and − left to right."},
                   {"id": BR, "name": "Brackets first", "grade": 6, "prerequisites": [MB],
                    "description": "Brackets are worked out before anything else."}],
                  {"ARITH_LEFT_TO_RIGHT": {"label": "Works strictly left to right, ignoring that × and ÷ come first",
                                           "gap_skill": MB, "explanation": "Works out 3 + 4 × 2 as 7 × 2 = 14 instead of 11."},
                   "ARITH_ADD_FIRST": {"label": "Thinks addition must always be done before subtraction", "gap_skill": MB,
                                       "explanation": "Works out 10 − 3 + 2 as 10 − 5 = 5 instead of 9."},
                   "ARITH_IGNORE_BRACKETS": {"label": "Ignores the brackets", "gap_skill": BR,
                                             "explanation": "Works out 2 × (3 + 4) as 2 × 3 + 4 = 10 instead of 14."}},
                  B.items, lessons)


# =====================================================================  FACTORS AND MULTIPLES
TOPIC_IDS["FAM"] = "factors_multiples"


def _lcm(a, b):
    return a * b // gcd(a, b)


def factors_multiples():
    B = Bank("FAM")
    HC, LC = "highest_common_factor", "lowest_common_multiple"
    hh = ["A factor divides into a number exactly. List the factors of both numbers.",
          "The HCF is the biggest number in both lists. It can't be bigger than the smaller number."]
    hl = ["List the multiples of each number: 4, 8, 12, … and 6, 12, 18, …",
          "The LCM is the first number in both lists. It is often smaller than the two numbers multiplied."]

    def fac(n):
        return [d for d in range(1, n + 1) if n % d == 0]

    def hcf(kind, a, b, role=None):
        ans = gcd(a, b)
        pats = {_lcm(a, b): "FM_GAVE_LCM", min(a, b): "FM_HCF_IS_SMALLER"}
        B.add(kind, HC, "numeric", f"What is the highest common factor (HCF) of {a} and {b}?", str(ans),
              patterns={str(k): v for k, v in pats.items()}, role=role, hints=hh,
              solution=[f"Factors of {a}: {', '.join(map(str, fac(a)))}.", f"Factors of {b}: {', '.join(map(str, fac(b)))}.",
                        f"The biggest number in both lists is {ans}."])

    def lcm(kind, a, b, role=None):
        ans = _lcm(a, b)
        pats = {a * b: "FM_LCM_IS_PRODUCT", gcd(a, b): "FM_GAVE_HCF"}
        mult = lambda n: ", ".join(str(n * k) for k in range(1, ans // n + 1))  # noqa: E731
        B.add(kind, LC, "numeric", f"What is the lowest common multiple (LCM) of {a} and {b}?", str(ans),
              patterns={str(k): v for k, v in pats.items()}, role=role, hints=hl,
              solution=[f"Multiples of {a}: {mult(a)}.", f"Multiples of {b}: {mult(b)}.",
                        f"The first number in both lists is {ans}."])

    _plan(B, hcf, lcm,
          [("a", (12, 18)), ("b", (4, 6)), ("a", (8, 20)), ("b", (6, 9)), ("a", (15, 25))],
          [("a", (16, 24)), ("b", (6, 8)), ("a", (9, 15)), ("b", (10, 15)), ("a", (14, 21))],
          [(18, 24), (10, 25), (12, 30), (20, 28)],
          [(4, 10), (6, 15), (8, 12), (9, 12)],
          [(6, 15), (12, 16), (21, 28), (18, 27)],
          [(4, 14), (10, 12), (6, 10), (15, 20)],
          [(24, 36), (14, 35), (16, 40), (27, 36), (20, 30), (12, 42)],
          [(8, 10), (6, 21), (12, 15), (14, 21), (10, 25), (12, 18)])
    lessons = {
        HC: _lesson("Highest common factor",
                    "The HCF is the biggest number that divides into BOTH numbers exactly. It is never bigger than the "
                    "smaller number, and it is only the smaller number if that number divides into the other.",
                    ["List all the factors of the first number.", "List all the factors of the second number.",
                     "Circle the numbers in both lists.", "The biggest circled number is the HCF."],
                    "8 doesn't divide into 12 exactly, so the HCF of 8 and 12 can't be 8. It's 4.",
                    [("HCF of 12 and 18?", 6, ["Factors of 12: 1, 2, 3, 4, 6, 12.", "Factors of 18: 1, 2, 3, 6, 9, 18.",
                                               "Biggest in both: 6."]),
                     ("HCF of 8 and 20?", 4, ["Factors of 8: 1, 2, 4, 8.", "Factors of 20: 1, 2, 4, 5, 10, 20.",
                                              "Biggest in both: 4."])]),
        LC: _lesson("Lowest common multiple",
                    "The LCM is the SMALLEST number that both numbers divide into. Multiplying the two numbers always "
                    "gives a common multiple, but often not the lowest one.",
                    ["Write the first few multiples of each number.", "Find the first number that appears in both lists.",
                     "Check: both numbers divide into it exactly."],
                    "4 × 6 = 24 is a common multiple, but 12 comes first in both lists.",
                    [("LCM of 4 and 6?", 12, ["Multiples of 4: 4, 8, 12.", "Multiples of 6: 6, 12.", "First in both: 12."]),
                     ("LCM of 6 and 9?", 18, ["Multiples of 6: 6, 12, 18.", "Multiples of 9: 9, 18.", "First in both: 18."])]),
    }
    return _topic("factors_multiples", "Factors and multiples", "Number", 5, 7,
                  "Highest common factors and lowest common multiples, and how not to mix them up.",
                  ["Find the HCF of two numbers", "Find the LCM of two numbers"],
                  [{"id": HC, "name": "Highest common factor", "grade": 5, "prerequisites": [],
                    "description": "The biggest number dividing both numbers."},
                   {"id": LC, "name": "Lowest common multiple", "grade": 6, "prerequisites": [HC],
                    "description": "The smallest number both numbers divide into."}],
                  {"FM_GAVE_LCM": {"label": "Gives the LCM when asked for the HCF", "gap_skill": HC,
                                   "explanation": "Mixes up 'highest common factor' and 'lowest common multiple'."},
                   "FM_HCF_IS_SMALLER": {"label": "Thinks the HCF is always the smaller number", "gap_skill": HC,
                                         "explanation": "Says the HCF of 8 and 20 is 8, though 8 doesn't divide 20."},
                   "FM_LCM_IS_PRODUCT": {"label": "Thinks the LCM is always the two numbers multiplied", "gap_skill": LC,
                                         "explanation": "Says the LCM of 4 and 6 is 24 instead of 12."},
                   "FM_GAVE_HCF": {"label": "Gives the HCF when asked for the LCM", "gap_skill": LC,
                                   "explanation": "Mixes up the two: answers 2 for the LCM of 4 and 6."}},
                  B.items, lessons)


# =====================================================================  RATIO AND PROPORTION
TOPIC_IDS["RAT"] = "ratio_proportion"


def ratio_proportion():
    B = Bank("RAT")
    ER, SH = "equivalent_ratios", "sharing_in_ratio"
    he = ["A ratio stays the same when you MULTIPLY both parts by the same number.",
          "Find how many times bigger the new amount is, then multiply the other part by that."]
    hs = ["Add the parts of the ratio to find how many equal shares there are.",
          "Divide the total by the number of shares, then multiply by each part."]
    things = [("cups of flour", "cups of milk"), ("red beads", "blue beads"), ("boys", "girls"),
              ("spoons of sugar", "cups of water"), ("teachers", "students"), ("cars", "bikes")]

    def eq(kind, a, b, k, role=None, i=[0]):
        x, y = things[i[0] % len(things)]
        i[0] += 1
        c, ans = a * k, b * k
        additive = b + (c - a)
        B.add(kind, ER, "numeric", f"A recipe uses {a} {x} for every {b} {y}. How many {y} go with {c} {x}?", str(ans),
              patterns={str(additive): "RAT_ADDITIVE"}, role=role, hints=he,
              solution=[f"{c} is {k} times {a}.", f"So multiply {b} by {k}: {b} × {k} = {ans}."])

    def share(kind, total, p, q, role=None):
        parts = p + q
        each = Fraction(total, parts)
        ans = each * p
        pats = {num(Fraction(total, 2)): "RAT_SHARE_EQUAL", num(Fraction(total, p)): "RAT_DIVIDE_BY_PART"}
        B.add(kind, SH, "numeric", f"₹{total} is shared between Asha and Ben in the ratio {p} : {q}. How much does Asha get (in ₹)?",
              num(ans), patterns=pats, role=role, hints=hs,
              solution=[f"{p} + {q} = {parts} equal shares.", f"One share = {total} ÷ {parts} = {num(each)}.",
                        f"Asha gets {p} shares: {p} × {num(each)} = {num(ans)}."])

    _plan(B, eq, share,
          [("a", (2, 3, 3)), ("b", (30, 2, 3)), ("a", (4, 5, 2)), ("b", (40, 3, 5)), ("a", (3, 7, 4))],
          [("a", (3, 4, 3)), ("b", (35, 2, 5)), ("a", (5, 2, 3)), ("b", (24, 1, 3)), ("a", (2, 9, 4))],
          [(3, 5, 4), (2, 7, 3), (4, 3, 5), (5, 6, 2)],
          [(50, 2, 3), (42, 4, 3), (60, 1, 4), (36, 5, 4)],
          [(2, 5, 4), (3, 2, 5), (4, 7, 3), (6, 5, 2)],
          [(28, 3, 4), (45, 4, 5), (72, 5, 3), (20, 3, 2)],
          [(3, 8, 3), (2, 11, 5), (5, 4, 3), (4, 9, 2), (7, 3, 3), (6, 7, 2)],
          [(56, 3, 4), (63, 2, 5), (80, 3, 5), (48, 5, 3), (27, 4, 5), (90, 7, 3)])
    lessons = {
        ER: _lesson("Equivalent ratios",
                    "A ratio compares amounts by multiplication. To keep a recipe tasting the same, both amounts must be "
                    "multiplied by the same number, not increased by the same amount.",
                    ["Find the scale factor: new amount ÷ old amount.", "Multiply the other part by the same factor.",
                     "Check: the new ratio simplifies back to the old one."],
                    "2 flour : 3 milk. Tripling to 6 flour needs 9 milk. Adding 4 to both (6 : 7) would change the taste.",
                    [("2 flour for 3 milk. Milk for 6 flour?", 9, ["6 ÷ 2 = 3 times as much.", "3 × 3 = 9."]),
                     ("4 red : 5 blue. Blue for 8 red?", 10, ["8 ÷ 4 = 2.", "5 × 2 = 10."])]),
        SH: _lesson("Sharing in a ratio",
                    "In the ratio 2 : 3 the total is split into 2 + 3 = 5 equal shares. One person gets 2 of them, the "
                    "other 3. It is not split in half.",
                    ["Add the ratio parts to get the number of shares.", "Divide the total by the number of shares.",
                     "Multiply by each person's part.", "Check: the amounts add up to the total."],
                    "₹30 in 2 : 3 gives ₹12 and ₹18. They add to 30, and 12 : 18 simplifies to 2 : 3.",
                    [("₹30 shared 2 : 3. First share?", 12, ["2 + 3 = 5 shares.", "30 ÷ 5 = 6.", "2 × 6 = 12."]),
                     ("₹40 shared 3 : 5. First share?", 15, ["3 + 5 = 8 shares.", "40 ÷ 8 = 5.", "3 × 5 = 15."])]),
    }
    return _topic("ratio_proportion", "Ratio and proportion", "Ratio and proportion", 6, 8,
                  "Scaling ratios up and down, and sharing an amount in a given ratio.",
                  ["Find equivalent ratios by multiplying", "Share an amount in a ratio"],
                  [{"id": ER, "name": "Equivalent ratios", "grade": 6, "prerequisites": [],
                    "description": "Scaling both parts of a ratio by the same factor."},
                   {"id": SH, "name": "Sharing in a ratio", "grade": 7, "prerequisites": [ER],
                    "description": "Splitting a total into ratio shares."}],
                  {"RAT_ADDITIVE": {"label": "Adds the same amount to both parts instead of multiplying", "gap_skill": ER,
                                    "explanation": "Goes from 2 : 3 to 6 : 7 by adding 4 to both parts."},
                   "RAT_SHARE_EQUAL": {"label": "Splits the total in half instead of in the ratio", "gap_skill": SH,
                                       "explanation": "Gives each person ₹15 when ₹30 is shared 2 : 3."},
                   "RAT_DIVIDE_BY_PART": {"label": "Divides the total by one part of the ratio", "gap_skill": SH,
                                          "explanation": "Works out ₹30 ÷ 2 for a 2 : 3 share, forgetting there are 5 shares."}},
                  B.items, lessons)


# =====================================================================  PERIMETER AND AREA
TOPIC_IDS["PAR"] = "perimeter_area"


def perimeter_area():
    B = Bank("PAR")
    PE, AR = "perimeter", "area_rectangles"
    hp = ["Perimeter is the distance all the way round: add every side.",
          "A rectangle has two lengths and two widths."]
    ha = ["Area is the space inside, measured in squares.", "Area of a rectangle = length × width."]

    def per(kind, l, w, role=None):
        sq = l == w
        ans = 2 * (l + w)
        shape = f"A square has sides of {l} cm." if sq else f"A rectangle is {l} cm long and {w} cm wide."
        B.add(kind, PE, "numeric", f"{shape} What is its perimeter, in cm?", str(ans),
              patterns={str(l * w): "PA_AREA_FOR_PERIM", str(l + w): "PA_HALF_PERIM"}, role=role, hints=hp,
              solution=[f"Add all four sides: {l} + {w} + {l} + {w}.", f"Perimeter = {ans} cm."])

    def area(kind, l, w, role=None, missing=False):
        if missing:
            a = l * w
            B.add(kind, AR, "numeric", f"A rectangle has an area of {a} cm² and a length of {l} cm. How wide is it, in cm?",
                  str(w), patterns={str(a - l): "PA_SUBTRACT_SIDE", str(2 * (l + w)): "PA_PERIM_FOR_AREA"}, role=role,
                  hints=ha, solution=[f"Area = length × width, so {l} × ? = {a}.", f"{a} ÷ {l} = {w} cm."])
            return
        sq = l == w
        ans = l * w
        shape = f"A square has sides of {l} cm." if sq else f"A rectangle is {l} cm long and {w} cm wide."
        B.add(kind, AR, "numeric", f"{shape} What is its area, in cm²?", str(ans),
              patterns={str(2 * (l + w)): "PA_PERIM_FOR_AREA", str(l + w): "PA_ADD_SIDES"}, role=role, hints=ha,
              solution=[f"Area = length × width = {l} × {w}.", f"Area = {ans} cm²."])

    _plan(B, per, area,
          [("a", (7, 3)), ("b", (6, 4)), ("a", (5, 5)), ("b", (8, 2)), ("b", (9, 3))],
          [("a", (8, 5)), ("b", (7, 2)), ("a", (6, 6)), ("b", (5, 3)), ("b", (4, 4))],
          [(9, 4), (10, 3), (6, 2), (12, 5)],
          [(6, 5), (9, 2), (8, 3, None, True), (7, 4, None, True)],
          [(11, 4), (8, 8), (13, 2), (7, 7)],
          [(10, 4), (12, 3), (6, 4, None, True), (9, 5, None, True)],
          [(9, 6), (14, 3), (5, 2), (10, 10), (15, 4), (8, 7)],
          [(11, 3), (7, 6), (12, 2), (9, 4, None, True), (8, 5, None, True), (10, 6)])
    lessons = {
        PE: _lesson("Perimeter",
                    "Perimeter is the total length of the edge: imagine walking all the way round the shape. "
                    "For a rectangle that means adding all four sides, not just two.",
                    ["Mark each side's length, including the ones not written (opposite sides are equal).",
                     "Add all the sides.", "Write the unit: cm, m … (not cm²)."],
                    "A fence round a 7 m by 3 m garden needs 7 + 3 + 7 + 3 = 20 m of fencing.",
                    [("Perimeter of a 7 cm by 3 cm rectangle?", 20, ["7 + 3 + 7 + 3 = 20.", "20 cm."]),
                     ("Perimeter of a square with 5 cm sides?", 20, ["4 sides of 5 cm.", "5 × 4 = 20 cm."])]),
        AR: _lesson("Area of rectangles",
                    "Area is how many unit squares fit inside a shape. A 7 cm by 3 cm rectangle holds 3 rows of 7 "
                    "squares, so its area is 7 × 3 = 21 cm².",
                    ["Area of a rectangle = length × width.", "The answer is in square units: cm², m².",
                     "If you know the area and one side, divide to find the other side."],
                    "Adding the sides (7 + 3 = 10) measures a length, not the space inside.",
                    [("Area of a 7 cm by 3 cm rectangle?", 21, ["7 × 3 = 21.", "21 cm²."]),
                     ("Area 24 cm², length 6 cm. Width?", 4, ["6 × ? = 24.", "24 ÷ 6 = 4 cm."])]),
    }
    return _topic("perimeter_area", "Perimeter and area", "Mensuration", 4, 7,
                  "The distance round a shape versus the space inside it, for rectangles and squares.",
                  ["Find the perimeter of rectangles and squares", "Find and use the area of rectangles"],
                  [{"id": PE, "name": "Perimeter", "grade": 4, "prerequisites": [],
                    "description": "The total length of the boundary."},
                   {"id": AR, "name": "Area of rectangles", "grade": 5, "prerequisites": [PE],
                    "description": "Length × width, in square units."}],
                  {"PA_AREA_FOR_PERIM": {"label": "Works out the area when asked for the perimeter", "gap_skill": PE,
                                         "explanation": "Multiplies length and width for the distance round."},
                   "PA_HALF_PERIM": {"label": "Adds only two sides for the perimeter", "gap_skill": PE,
                                     "explanation": "Says a 7 by 3 rectangle has perimeter 10."},
                   "PA_PERIM_FOR_AREA": {"label": "Works out the perimeter when asked for the area", "gap_skill": AR,
                                         "explanation": "Adds all four sides for the space inside."},
                   "PA_ADD_SIDES": {"label": "Adds length and width to find the area", "gap_skill": AR,
                                    "explanation": "Says a 7 by 3 rectangle has area 10."},
                   "PA_SUBTRACT_SIDE": {"label": "Subtracts instead of dividing to find a missing side", "gap_skill": AR,
                                        "explanation": "Works out width = area − length."}},
                  B.items, lessons)


# =====================================================================  STATISTICS
TOPIC_IDS["STA"] = "statistics"


def statistics():
    B = Bank("STA")
    ME, MD = "calculating_mean", "finding_median"
    hm = ["Add all the values.", "Divide the total by HOW MANY values there are."]
    hd = ["First put the values in order from smallest to largest.", "The median is the middle value of the ordered list."]

    def mean(kind, vals, role=None):
        s, n = sum(vals), len(vals)
        ans = Fraction(s, n)
        mode = max(set(vals), key=vals.count)
        pats = {str(s): "STAT_TOTAL_ONLY"}
        if vals.count(mode) > 1:
            pats[str(mode)] = "STAT_MODE_FOR_MEAN"
        B.add(kind, ME, "numeric", f"Find the mean of: {', '.join(map(str, vals))}", num(ans), patterns=pats, role=role,
              hints=hm, solution=[f"Total = {' + '.join(map(str, vals))} = {s}.", f"{s} ÷ {n} = {num(ans)}."])

    def median(kind, vals, role=None):
        srt = sorted(vals)
        ans = srt[len(vals) // 2]
        pats = {str(vals[len(vals) // 2]): "STAT_MEDIAN_UNSORTED"}
        m = Fraction(sum(vals), len(vals))
        if m.denominator == 1:
            pats.setdefault(str(m), "STAT_MEAN_FOR_MEDIAN")
        B.add(kind, MD, "numeric", f"Find the median of: {', '.join(map(str, vals))}", str(ans), patterns=pats, role=role,
              hints=hd, solution=[f"In order: {', '.join(map(str, srt))}.", f"The middle value is {ans}."])

    _plan(B, mean, median,
          [("a", ([4, 6, 6, 8],)), ("b", ([7, 2, 9, 4, 3],)), ("a", ([5, 9, 10],)), ("b", ([12, 5, 8, 15, 1],)), ("a", ([3, 3, 9, 5],))],
          [("a", ([2, 8, 8, 6],)), ("b", ([9, 1, 6, 8, 2],)), ("a", ([6, 7, 11],)), ("b", ([10, 4, 13, 7, 2],)), ("a", ([5, 5, 11, 7],))],
          [([3, 7, 7, 11],), ([10, 2, 2, 6],), ([4, 8, 12],), ([1, 5, 9, 5],)],
          [([8, 3, 10, 6, 1],), ([14, 2, 9, 11, 4],), ([6, 15, 3, 9, 12],), ([20, 5, 11, 2, 7],)],
          [([2, 4, 4, 6],), ([9, 3, 3, 5],), ([7, 8, 12],), ([10, 6, 6, 2],)],
          [([5, 12, 3, 8, 2],), ([11, 4, 16, 6, 3],), ([9, 2, 14, 7, 1],), ([13, 6, 2, 10, 4],)],
          [([1, 9, 9, 5],), ([6, 2, 2, 10],), ([10, 14, 18],), ([4, 4, 12, 8],), ([3, 11, 11, 7],), ([8, 12, 16],)],
          [([7, 1, 12, 9, 3],), ([15, 5, 10, 2, 8],), ([4, 13, 1, 9, 6],), ([18, 7, 3, 12, 5],), ([2, 11, 6, 14, 4],), ([16, 3, 9, 1, 8],)])
    lessons = {
        ME: _lesson("The mean",
                    "The mean shares the total out equally. Add all the values, then divide by how many values there "
                    "are. The total on its own isn't an average, and neither is the most common value (the mode).",
                    ["Add all the values to get the total.", "Count how many values there are.",
                     "Divide the total by the count.", "Check: the mean lies between the smallest and largest values."],
                    "The mean of 4, 6, 6 and 8 can't be 24: that's bigger than every value.",
                    [("Mean of 4, 6, 6, 8?", 6, ["Total: 24.", "4 values: 24 ÷ 4 = 6."]),
                     ("Mean of 5, 9, 10?", 8, ["Total: 24.", "3 values: 24 ÷ 3 = 8."])]),
        MD: _lesson("The median",
                    "The median is the middle value once the list is IN ORDER. The middle of the unsorted list means "
                    "nothing, because the order the values were written in is just the order they were collected.",
                    ["Rewrite the list from smallest to largest.", "Cross off one from each end until one value is left.",
                     "That middle value is the median."],
                    "For 7, 2, 9, 4, 3 the third value written is 9, but sorted (2, 3, 4, 7, 9) the middle is 4.",
                    [("Median of 7, 2, 9, 4, 3?", 4, ["Sort: 2, 3, 4, 7, 9.", "Middle: 4."]),
                     ("Median of 12, 5, 8, 15, 1?", 8, ["Sort: 1, 5, 8, 12, 15.", "Middle: 8."])]),
    }
    return _topic("statistics", "Averages", "Statistics", 6, 8,
                  "Finding the mean and the median, and choosing the right steps for each.",
                  ["Calculate the mean", "Find the median of a list"],
                  [{"id": ME, "name": "The mean", "grade": 6, "prerequisites": [],
                    "description": "Total divided by how many."},
                   {"id": MD, "name": "The median", "grade": 6, "prerequisites": [],
                    "description": "The middle value of an ordered list."}],
                  {"STAT_TOTAL_ONLY": {"label": "Gives the total instead of dividing by how many", "gap_skill": ME,
                                       "explanation": "Adds the values but forgets to divide."},
                   "STAT_MODE_FOR_MEAN": {"label": "Gives the most common value when asked for the mean", "gap_skill": ME,
                                          "explanation": "Mixes up the mean and the mode."},
                   "STAT_MEDIAN_UNSORTED": {"label": "Takes the middle value without putting the list in order",
                                            "gap_skill": MD, "explanation": "Picks the middle of the list as written."},
                   "STAT_MEAN_FOR_MEDIAN": {"label": "Calculates the mean when asked for the median", "gap_skill": MD,
                                            "explanation": "Mixes up the two kinds of average."}},
                  B.items, lessons)


# =====================================================================  ANGLES
TOPIC_IDS["ANG"] = "angles"


def angles():
    B = Bank("ANG")
    SL, TR = "angles_on_a_line", "angles_in_a_triangle"
    hs = ["Angles on a straight line add up to 180°.", "Angles all the way round a point add up to 360°."]
    ht = ["The three angles inside any triangle add up to 180°.", "Add the two you know, then subtract from 180°."]

    def line(kind, a, role=None, around=None):
        if around:
            known = around
            ans = 360 - sum(known)
            pats = {str(180 - sum(known)): "GEO_POINT_180"} if 180 - sum(known) > 0 else {}
            B.add(kind, SL, "numeric", f"Three angles around a point are {', '.join(f'{k}°' for k in known)} and x. What is x, in degrees?",
                  str(ans), patterns=pats, role=role, hints=hs,
                  solution=["Angles around a point add up to 360°.", f"360 − {' − '.join(map(str, known))} = {ans}°."])
            return
        ans = 180 - a
        pats = {str(360 - a): "GEO_LINE_360"}
        if a < 90:
            pats[str(90 - a)] = "GEO_LINE_90"
        B.add(kind, SL, "numeric", f"Two angles sit together on a straight line. One is {a}°. What is the other, in degrees?",
              str(ans), patterns=pats, role=role, hints=hs,
              solution=["Angles on a straight line add up to 180°.", f"180 − {a} = {ans}°."])

    def tri(kind, a, b, role=None):
        ans = 180 - a - b
        B.add(kind, TR, "numeric", f"A triangle has angles of {a}° and {b}°. What is the third angle, in degrees?",
              str(ans), patterns={str(360 - a - b): "GEO_TRIANGLE_360"}, role=role, hints=ht,
              solution=["The angles in a triangle add up to 180°.", f"{a} + {b} = {a + b}; 180 − {a + b} = {ans}°."])

    _plan(B, line, tri,
          [("a", (130,)), ("b", (50, 60)), ("a", (65,)), ("b", (35, 85)), ("a", (110,))],
          [("a", (140,)), ("b", (40, 70)), ("a", (55,)), ("b", (25, 95)), ("a", (100,))],
          [(120,), (75,), (0, None, (100, 120)), (0, None, (90, 150))],
          [(45, 75), (30, 80), (60, 60), (20, 110)],
          [(150,), (35,), (125,), (80,)],
          [(55, 65), (35, 75), (50, 50), (15, 105)],
          [(115,), (45,), (160,), (0, None, (110, 130)), (70,), (0, None, (80, 140))],
          [(70, 40), (25, 85), (65, 65), (30, 100), (45, 90), (10, 120)])
    lessons = {
        SL: _lesson("Angles on a line and around a point",
                    "A straight line is half a turn: the angles on it add up to 180°. A full turn around a point is 360°.",
                    ["Decide: is it a straight line (180°) or all the way round a point (360°)?",
                     "Add up the angles you know.", "Subtract from 180° or 360°."],
                    "If one angle on a line is 130°, the other must be small, 50°. 230° would be bigger than the whole line.",
                    [("One angle on a straight line is 130°. The other?", 50, ["Straight line: 180°.", "180 − 130 = 50°."]),
                     ("Around a point: 100°, 120° and x. x?", 140, ["Full turn: 360°.", "360 − 100 − 120 = 140°."])]),
        TR: _lesson("Angles in a triangle",
                    "The three angles of any triangle add up to 180°: tear the corners off a paper triangle and they "
                    "make a straight line.",
                    ["Add the two angles you know.", "Subtract the total from 180°.", "Check: all three add to 180°."],
                    "A triangle's third angle can't be more than 180°, so 250° is impossible.",
                    [("Triangle angles 50° and 60°. Third?", 70, ["50 + 60 = 110.", "180 − 110 = 70°."]),
                     ("Triangle angles 35° and 85°. Third?", 60, ["35 + 85 = 120.", "180 − 120 = 60°."])]),
    }
    return _topic("angles", "Angles", "Geometry", 5, 8,
                  "Angle facts: straight lines, full turns and triangles.",
                  ["Find missing angles on a line and around a point", "Find the missing angle in a triangle"],
                  [{"id": SL, "name": "Angles on a line and around a point", "grade": 5, "prerequisites": [],
                    "description": "180° on a straight line, 360° around a point."},
                   {"id": TR, "name": "Angles in a triangle", "grade": 6, "prerequisites": [SL],
                    "description": "The three angles add up to 180°."}],
                  {"GEO_LINE_360": {"label": "Thinks angles on a straight line add up to 360°", "gap_skill": SL,
                                    "explanation": "Subtracts from 360° instead of 180° on a straight line."},
                   "GEO_LINE_90": {"label": "Subtracts from 90° instead of 180°", "gap_skill": SL,
                                   "explanation": "Treats a straight line like a right angle."},
                   "GEO_POINT_180": {"label": "Thinks angles around a point add up to 180°", "gap_skill": SL,
                                     "explanation": "Uses the straight-line total for a full turn."},
                   "GEO_TRIANGLE_360": {"label": "Thinks the angles in a triangle add up to 360°", "gap_skill": TR,
                                        "explanation": "Confuses the triangle total with a full turn."}},
                  B.items, lessons)


ALL = [order_of_operations, factors_multiples, ratio_proportion, perimeter_area, statistics, angles]
