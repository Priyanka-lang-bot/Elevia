"""More Computer Science topics: predict-the-output on short Python programs.
Student answers are only compared as text; every expected answer is verified by running the fixed snippet
at build time (scripts/build_curriculum.py)."""
from .common import TOPIC_IDS, Bank
from .math_more import _plan

PROMPT = "What does this program print?"


def _lesson(title, big, steps, sense, examples):
    return {"title": title, "big_idea": big, "steps": steps, "sense_check": sense,
            "worked_examples": [{"prompt": PROMPT, "code": c, "answer": a, "steps": s} for c, a, s in examples]}


def _topic(tid, name, unit, gmin, gmax, desc, objectives, skills, mis, qs, lessons):
    return {"topic": {"id": tid, "subject": "computer_science", "name": name, "unit": unit, "grade_min": gmin,
                      "grade_max": gmax, "description": desc, "objectives": objectives,
                      "skills": [s["id"] for s in skills]},
            "skills": skills, "misconceptions": mis, "questions": qs, "lessons": lessons}


# =====================================================================  DATA TYPES
TOPIC_IDS["TYP"] = "data_types"


def data_types():
    B = Bank("TYP")
    TN, CV = "text_vs_numbers", "type_conversion"
    h1 = ["Anything in quotes is text (a string), even if it looks like a number.",
          "+ joins two strings end to end; * repeats a string."]
    h2 = ["int(...) turns text into a whole number; str(...) turns a number into text.",
          "After converting, the normal rules for that type apply."]

    def join(kind, a, b, role=None):
        B.add(kind, TN, "code_output", PROMPT, f"{a}{b}", code=f'a = "{a}"\nb = "{b}"\nprint(a + b)',
              patterns={str(a + b): "CS_TEXT_AS_NUMBER"}, role=role, hints=h1,
              solution=[f'"{a}" and "{b}" are text, because they are in quotes.', f"+ joins text: {a}{b}."])

    def rep(kind, a, k, role=None):
        B.add(kind, TN, "code_output", PROMPT, f"{a}" * k, code=f'x = "{a}"\nprint(x * {k})',
              patterns={str(a * k): "CS_TEXT_AS_NUMBER"}, role=role, hints=h1,
              solution=[f'x is the text "{a}".', f"Text × {k} repeats it {k} times: {str(a) * k}."])

    def to_int(kind, a, k, role=None):
        B.add(kind, CV, "code_output", PROMPT, str(a * k), code=f'a = "{a}"\nb = int(a) * {k}\nprint(b)',
              patterns={str(a) * k: "CS_IGNORES_CONVERSION"}, role=role, hints=h2,
              solution=[f'int("{a}") turns the text into the number {a}.', f"{a} × {k} = {a * k}."])

    def to_str(kind, a, b, role=None):
        B.add(kind, CV, "code_output", PROMPT, f"{a}{b}", code=f'n = {a}\nprint(str(n) + "{b}")',
              patterns={str(a + b): "CS_IGNORES_CONVERSION"}, role=role, hints=h2,
              solution=[f"str(n) turns {a} into the text \"{a}\".", f'"{a}" + "{b}" joins them: {a}{b}.'])

    def gen_a(kind, a, b, role=None, rep_=False):
        (rep if rep_ else join)(kind, a, b, role)

    def gen_b(kind, a, b, role=None, s=False):
        (to_str if s else to_int)(kind, a, b, role)

    _plan(B, gen_a, gen_b,
          [("a", (3, 4)), ("a", (5, 2, None, True)), ("b", (6, 2)), ("b", (8, 1, None, True)), ("a", (2, 9))],
          [("a", (7, 1)), ("a", (4, 3, None, True)), ("b", (9, 3)), ("b", (5, 2, None, True)), ("a", (6, 6))],
          [(1, 8), (3, 3, None, True), (2, 5), (9, 2, None, True)],
          [(7, 2), (4, 5), (3, 7, None, True), (6, 4, None, True)],
          [(4, 6), (2, 4, None, True), (8, 8), (1, 3, None, True)],
          [(3, 4), (5, 3), (2, 6, None, True), (7, 9, None, True)],
          [(5, 5), (6, 2, None, True), (9, 1), (7, 3, None, True), (2, 2), (8, 2, None, True)],
          [(6, 3), (8, 2), (4, 1, None, True), (1, 5, None, True), (9, 4), (2, 8, None, True)])
    lessons = {
        TN: _lesson("Text versus numbers",
                    "Quotes make a value text (a string). Text that looks like a number still behaves like text: + "
                    "sticks strings together and * repeats them.",
                    ["Check each value: is it in quotes? Then it's text.", "text + text joins them end to end.",
                     "text * number repeats the text.", "Only real numbers (no quotes) add up arithmetically."],
                    'A phone number "98" + "76" makes "9876", not 174.',
                    [('a = "3"\nb = "4"\nprint(a + b)', "34", ['"3" and "4" are text.', "+ joins them: 34."]),
                     ('x = "5"\nprint(x * 2)', "55", ['x is text.', "* 2 repeats it: 55."])]),
        CV: _lesson("Converting between types",
                    "int() turns text into a whole number and str() turns a number into text. After converting, the "
                    "value follows the rules of its new type.",
                    ["Find each int(...) or str(...) and work out the converted value first.",
                     "Numbers: + and * do arithmetic.", "Text: + joins, * repeats."],
                    'int("6") * 2 is 12, because the 6 is now a real number.',
                    [('a = "6"\nb = int(a) * 2\nprint(b)', "12", ['int("6") is the number 6.', "6 × 2 = 12."]),
                     ('n = 8\nprint(str(n) + "1")', "81", ['str(8) is the text "8".', '"8" + "1" = 81.'])]),
    }
    return _topic("data_types", "Data types", "Programming fundamentals", 7, 10,
                  "Strings versus numbers, and converting with int() and str().",
                  ["Predict what + and * do with text and numbers", "Use int() and str() to convert"],
                  [{"id": TN, "name": "Text versus numbers", "grade": 7, "prerequisites": ["variable_assignment"],
                    "description": "Strings join and repeat; numbers add and multiply."},
                   {"id": CV, "name": "Converting between types", "grade": 8, "prerequisites": [TN],
                    "description": "int() and str()."}],
                  {"CS_TEXT_AS_NUMBER": {"label": "Treats text that looks like a number as a number", "gap_skill": TN,
                                         "explanation": 'Predicts "3" + "4" prints 7 instead of 34.'},
                   "CS_IGNORES_CONVERSION": {"label": "Ignores int() or str() conversions", "gap_skill": CV,
                                             "explanation": 'Predicts int("6") * 2 prints 66.'}},
                  B.items, lessons)


# =====================================================================  CONDITIONALS
TOPIC_IDS["IFS"] = "conditionals"


def conditionals():
    B = Bank("IFS")
    IE, EL = "if_else", "elif_chains"
    h1 = ["Check the condition with the actual value. Only ONE of the if/else blocks runs.",
          "> means strictly greater: 5 > 5 is False."]
    h2 = ["Python checks the conditions from the top and runs the FIRST one that is True.",
          "After one branch runs, the rest are skipped."]

    def ifelse(kind, x, limit, role=None):
        ans = "big" if x > limit else "small"
        other = "small" if ans == "big" else "big"
        pats = {f"{ans} {other}" if ans == "big" else f"big small": "CS_BOTH_BRANCHES"}
        if x == limit:
            pats["big"] = "CS_GREATER_INCLUDES_EQUAL"
        B.add(kind, IE, "code_output", PROMPT, ans,
              code=f'x = {x}\nif x > {limit}:\n    print("big")\nelse:\n    print("small")',
              patterns=pats, role=role, hints=h1,
              solution=[f"Is {x} > {limit}? {'Yes' if x > limit else 'No'}.", f"So only the {'if' if x > limit else 'else'} part runs: {ans}."])

    def chain(kind, score, a, b, role=None):   # a > b thresholds, first check is the LOWER one (classic trap)
        ans = "pass" if score > b else ("merit" if score > a else "fail")
        code = f'score = {score}\nif score > {b}:\n    print("pass")\nelif score > {a}:\n    print("merit")\nelse:\n    print("fail")'
        pats = {}
        if score > a:
            pats = {"merit": "CS_ELIF_BEST_MATCH", "pass merit": "CS_ELIF_ALL_RUN"}
        B.add(kind, EL, "code_output", PROMPT, ans, code=code, patterns=pats, role=role, hints=h2,
              solution=[f"First check: is {score} > {b}? {'Yes' if score > b else 'No'}.",
                        "The first True branch runs and the rest are skipped." if score > b
                        else f"Is {score} > {a}? {'Yes' if score > a else 'No'}, so {'the elif' if score > a else 'the else'} block runs.",
                        f"It prints {ans}."])

    _plan(B, ifelse, chain,
          [("a", (7, 5)), ("b", (85, 80, 50)), ("a", (5, 5)), ("b", (92, 90, 40)), ("a", (12, 10))],
          [("a", (9, 4)), ("b", (88, 75, 50)), ("a", (6, 6)), ("b", (95, 85, 60)), ("a", (15, 3))],
          [(8, 2), (20, 11), (3, 3), (10, 10)],
          [(81, 80, 33), (99, 70, 45), (25, 60, 35), (90, 85, 50)],
          [(14, 9), (4, 4), (30, 25), (7, 7)],
          [(86, 80, 40), (97, 91, 55), (72, 65, 30), (83, 78, 50)],
          [(6, 1), (9, 9), (25, 20), (11, 11), (40, 39), (2, 2)],
          [(91, 90, 60), (87, 82, 45), (40, 70, 50), (94, 88, 35), (30, 60, 45), (98, 95, 70)])
    lessons = {
        IE: _lesson("if and else",
                    "An if/else is a fork in the road: Python checks the condition once and runs exactly one of the "
                    "two blocks, never both.",
                    ["Put the real value into the condition.", "Decide True or False (careful: > is strict).",
                     "True: run the if block. False: run the else block.", "Then carry on after both."],
                    "x = 5: is 5 > 5? No, they are equal, so the else block runs.",
                    [('x = 7\nif x > 5:\n    print("big")\nelse:\n    print("small")', "big", ["7 > 5 is True.", "Only the if block runs: big."]),
                     ('x = 5\nif x > 5:\n    print("big")\nelse:\n    print("small")', "small", ["5 > 5 is False.", "The else block runs: small."])]),
        EL: _lesson("elif chains",
                    "In an if/elif/else chain, Python runs the FIRST branch whose condition is True and skips the rest, "
                    "even if a later branch would match 'better'. So the order of the checks matters.",
                    ["Check the conditions from top to bottom.", "Stop at the first True one and run only that block.",
                     "If none are True, run the else block."],
                    "score = 85 with 'if score > 50' first: 85 > 50 is True, so it prints pass, and the merit check never happens.",
                    [('score = 85\nif score > 50:\n    print("pass")\nelif score > 80:\n    print("merit")\nelse:\n    print("fail")', "pass",
                      ["85 > 50 is True.", "That branch runs; the elif is skipped.", "pass."]),
                     ('score = 40\nif score > 50:\n    print("pass")\nelif score > 80:\n    print("merit")\nelse:\n    print("fail")', "fail",
                      ["40 > 50 is False.", "40 > 80 is False.", "else: fail."])]),
    }
    return _topic("conditionals", "Conditional statements", "Programming fundamentals", 7, 10,
                  "if/else decisions and if/elif/else chains, including boundary values.",
                  ["Predict which branch of an if/else runs", "Trace an if/elif/else chain"],
                  [{"id": IE, "name": "if and else", "grade": 7, "prerequisites": ["variable_assignment"],
                    "description": "Exactly one block runs; > is strict."},
                   {"id": EL, "name": "elif chains", "grade": 8, "prerequisites": [IE],
                    "description": "The first True branch runs."}],
                  {"CS_BOTH_BRANCHES": {"label": "Thinks both the if and the else blocks run", "gap_skill": IE,
                                        "explanation": "Predicts both lines are printed."},
                   "CS_GREATER_INCLUDES_EQUAL": {"label": "Treats > as 'greater than or equal'", "gap_skill": IE,
                                                 "explanation": "Thinks 5 > 5 is True."},
                   "CS_ELIF_BEST_MATCH": {"label": "Thinks Python picks the best-matching branch, not the first True one",
                                          "gap_skill": EL, "explanation": "Predicts 'merit' for 85 although 'score > 50' is checked first."},
                   "CS_ELIF_ALL_RUN": {"label": "Thinks every True branch of an elif chain runs", "gap_skill": EL,
                                       "explanation": "Predicts both 'pass' and 'merit'."}},
                  B.items, lessons)


# =====================================================================  BOOLEAN LOGIC
TOPIC_IDS["BOO"] = "boolean_logic"


def boolean_logic():
    B = Bank("BOO")
    AO, NT = "and_or", "not_logic"
    h1 = ["and is True only if BOTH sides are True.", "or is True if AT LEAST ONE side is True."]
    h2 = ["Work out the part after not first, then flip it.", "Brackets are worked out first."]

    def andq(kind, v, lo, hi, role=None, use_or=False):
        if use_or:
            ans = v < lo or v > hi
            code = f"x = {v}\nprint(x < {lo} or x > {hi})"
            pats = {str(not ans): "CS_OR_NEEDS_BOTH"} if (v < lo) != (v > hi) else {}
        else:
            ans = v > lo and v < hi
            code = f"x = {v}\nprint(x > {lo} and x < {hi})"
            pats = {str(not ans): "CS_AND_EITHER"} if (v > lo) != (v < hi) else {}
        B.add(kind, AO, "code_output", PROMPT + " (True or False)", str(ans), code=code, patterns=pats, role=role,
              hints=h1, solution=[f"Check each side with x = {v}.", f"Combine them with {'or' if use_or else 'and'}: {ans}."])

    def notq(kind, v, t, role=None, compound=False):
        if compound:
            inner = v > t and v > 0
            ans = not inner
            code = f"x = {v}\nprint(not (x > {t} and x > 0))"
        else:
            inner = v > t
            ans = not inner
            code = f"x = {v}\nprint(not x > {t})"
        B.add(kind, NT, "code_output", PROMPT + " (True or False)", str(ans), code=code,
              patterns={str(inner): "CS_IGNORES_NOT"}, role=role, hints=h2,
              solution=[f"The part after not is {inner}.", f"not flips it: {ans}."])

    _plan(B, andq, notq,
          [("a", (12, 10, 12)), ("a", (3, 4, 9, None, True)), ("b", (4, 2)), ("b", (6, 2, None, True)), ("a", (15, 10, 12))],
          [("a", (20, 18, 20)), ("a", (2, 5, 9, None, True)), ("b", (7, 3)), ("b", (8, 5, None, True)), ("a", (25, 5, 9))],
          [(9, 3, 9), (14, 1, 10), (11, 15, 30, None, True), (40, 5, 30, None, True)],
          [(9, 4), (1, 6), (10, 3, None, True), (2, 8, None, True)],
          [(6, 2, 6), (30, 10, 20), (1, 3, 8, None, True), (12, 2, 10, None, True)],
          [(5, 1), (3, 7), (9, 4, None, True), (4, 6, None, True)],
          [(16, 15, 16), (50, 20, 40), (0, 4, 10, None, True), (25, 3, 20, None, True), (8, 8, 9), (7, 1, 6)],
          [(11, 2), (2, 9), (12, 6, None, True), (5, 1, None, True), (6, 6), (3, 10, None, True)])
    lessons = {
        AO: _lesson("and / or",
                    "and needs BOTH conditions to be True. or needs AT LEAST ONE to be True. That's different from how "
                    "we sometimes use 'or' in everyday speech.",
                    ["Work out each side separately as True or False.", "and: True only if both are True.",
                     "or: True if either one (or both) is True."],
                    "A ticket for ages over 10 AND under 12: a 12-year-old fails the second check, so it's False.",
                    [("x = 12\nprint(x > 10 and x < 12)", "False", ["12 > 10 is True.", "12 < 12 is False.", "True and False → False."]),
                     ("x = 3\nprint(x < 4 or x > 9)", "True", ["3 < 4 is True.", "3 > 9 is False.", "True or False → True."])]),
        NT: _lesson("not",
                    "not flips True to False and False to True. Work out what comes after it first (including anything "
                    "in brackets), then flip the result.",
                    ["Find what not applies to.", "Work that part out as True or False.", "Flip it."],
                    "not (4 > 2): 4 > 2 is True, so the answer is False.",
                    [("x = 4\nprint(not x > 2)", "False", ["4 > 2 is True.", "not True → False."]),
                     ("x = 6\nprint(not (x > 2 and x > 0))", "False", ["6 > 2 and 6 > 0 is True.", "not True → False."])]),
    }
    return _topic("boolean_logic", "Logical reasoning", "Computational thinking", 7, 10,
                  "and, or and not in Python conditions.",
                  ["Evaluate and / or expressions", "Evaluate expressions with not"],
                  [{"id": AO, "name": "and / or", "grade": 7, "prerequisites": [],
                    "description": "Both versus at least one."},
                   {"id": NT, "name": "not", "grade": 8, "prerequisites": [AO],
                    "description": "Flipping a True/False value."}],
                  {"CS_AND_EITHER": {"label": "Thinks `and` is True when either side is True", "gap_skill": AO,
                                     "explanation": "Treats and like or."},
                   "CS_OR_NEEDS_BOTH": {"label": "Thinks `or` needs both sides to be True", "gap_skill": AO,
                                        "explanation": "Treats or like and."},
                   "CS_IGNORES_NOT": {"label": "Ignores the `not`", "gap_skill": NT,
                                      "explanation": "Gives the value before it is flipped."}},
                  B.items, lessons)


# =====================================================================  BASIC ALGORITHMS
TOPIC_IDS["ALGO"] = "algorithms"


def algorithms():
    B = Bank("ALGO")
    MX, SC = "find_largest", "search_and_count"
    h1 = ["`best` keeps the largest value seen SO FAR; it only changes when a bigger one turns up.",
          "Trace the loop: write best after each item."]
    h2 = ["The loop looks at EVERY item; it doesn't stop at the first match.",
          "List positions start at 0: the first item is position 0."]

    def biggest(kind, nums, role=None, smallest=False):
        op = "<" if smallest else ">"
        ans = min(nums) if smallest else max(nums)
        code = f"nums = {nums}\nbest = nums[0]\nfor n in nums:\n    if n {op} best:\n        best = n\nprint(best)"
        pats = {str(nums[-1]): "CS_ALG_LAST_ITEM"}
        B.add(kind, MX, "code_output", PROMPT, str(ans), code=code, patterns=pats, role=role, hints=h1,
              solution=[f"best starts as {nums[0]}.", f"It is replaced whenever a {'smaller' if smallest else 'bigger'} number appears.",
                        f"The {'smallest' if smallest else 'largest'} value is {ans}."])

    def count(kind, nums, target, role=None, pos=False):
        if pos:
            ans = max(i for i, n in enumerate(nums) if n == target)
            first = nums.index(target)
            code = f"nums = {nums}\npos = -1\nfor i in range(len(nums)):\n    if nums[i] == {target}:\n        pos = i\nprint(pos)"
            pats = {str(first): "CS_ALG_STOPS_EARLY", str(ans + 1): "CS_ALG_ONE_BASED"}
            sol = [f"{target} is at positions {', '.join(str(i) for i, n in enumerate(nums) if n == target)} (counting from 0).",
                   "pos is overwritten each time, so it ends with the last match.", f"Prints {ans}."]
        else:
            ans = nums.count(target)
            code = f"nums = {nums}\ncount = 0\nfor n in nums:\n    if n == {target}:\n        count = count + 1\nprint(count)"
            pats = {"1": "CS_ALG_STOPS_EARLY"}
            sol = [f"The loop checks every item.", f"{target} appears {ans} times.", f"Prints {ans}."]
        B.add(kind, SC, "code_output", PROMPT, str(ans), code=code, patterns=pats, role=role, hints=h2, solution=sol)

    _plan(B, biggest, count,
          [("a", ([4, 9, 2, 7],)), ("b", ([3, 8, 5, 8, 1], 8)), ("a", ([6, 3, 1, 5], None, True)), ("b", ([5, 2, 9, 2], 2, None, True)), ("a", ([2, 11, 6, 8],))],
          [("a", ([5, 12, 3, 9],)), ("b", ([7, 4, 7, 7, 2], 7)), ("a", ([8, 4, 2, 6], None, True)), ("b", ([1, 6, 3, 6], 6, None, True)), ("a", ([3, 10, 7, 4],))],
          [([1, 14, 6, 9],), ([7, 20, 3, 11],), ([9, 5, 2, 7], None, True), ([12, 6, 4, 10], None, True)],
          [([2, 5, 2, 9, 2], 2), ([4, 4, 1, 4], 4), ([8, 3, 5, 3], 3, None, True), ([6, 9, 1, 9, 4], 9, None, True)],
          [([3, 15, 8, 10],), ([6, 13, 4, 9],), ([10, 7, 3, 8], None, True), ([11, 5, 1, 9], None, True)],
          [([1, 3, 1, 1, 6], 1), ([5, 8, 5, 2], 5), ([7, 2, 6, 2, 8], 2, None, True), ([4, 1, 4, 3], 4, None, True)],
          [([2, 17, 9, 12],), ([8, 16, 1, 5],), ([4, 19, 6, 13],), ([7, 3, 1, 4], None, True), ([9, 6, 2, 8], None, True), ([13, 9, 3, 11], None, True)],
          [([3, 7, 3, 3, 1], 3), ([9, 2, 9, 5], 9), ([6, 6, 4, 6], 6), ([5, 1, 8, 1, 7], 1, None, True), ([2, 9, 2, 4], 2, None, True), ([8, 3, 7, 3, 5], 3, None, True)])
    lessons = {
        MX: _lesson("Finding the largest value",
                    "To find the largest item, keep a 'best so far' and compare every item with it. best only changes "
                    "when a bigger value turns up, so it is NOT simply the last item in the list.",
                    ["Start best as the first item.", "For each item, if it's bigger than best, replace best.",
                     "After the loop, best holds the largest value."],
                    "For [4, 9, 2, 7] the answer can't be 7: 9 was bigger and nothing replaced it.",
                    [("nums = [4, 9, 2, 7]\nbest = nums[0]\nfor n in nums:\n    if n > best:\n        best = n\nprint(best)", "9",
                      ["best = 4.", "9 > 4: best = 9.", "2 and 7 are not bigger than 9.", "Prints 9."])]),
        SC: _lesson("Searching and counting",
                    "A for loop visits EVERY item, even after it finds a match, unless the code tells it to stop. List "
                    "positions start at 0.",
                    ["Trace the loop through every item.", "Update the count (or position) each time there's a match.",
                     "Remember: the first item is position 0."],
                    "In [3, 8, 5, 8, 1] there are two 8s, so the count is 2, not 1.",
                    [("nums = [3, 8, 5, 8, 1]\ncount = 0\nfor n in nums:\n    if n == 8:\n        count = count + 1\nprint(count)", "2",
                      ["8 at the 2nd item: count 1.", "8 again at the 4th item: count 2.", "Prints 2."])]),
    }
    return _topic("algorithms", "Basic algorithms", "Algorithms", 8, 10,
                  "Tracing simple algorithms: finding the largest value, counting and searching in a list.",
                  ["Trace a find-the-largest algorithm", "Trace counting and searching loops"],
                  [{"id": MX, "name": "Finding the largest value", "grade": 8, "prerequisites": ["loop_counting"],
                    "description": "Keeping a best-so-far value."},
                   {"id": SC, "name": "Searching and counting", "grade": 8, "prerequisites": [MX],
                    "description": "Loops visit every item; positions start at 0."}],
                  {"CS_ALG_LAST_ITEM": {"label": "Thinks the result is just the last item in the list", "gap_skill": MX,
                                        "explanation": "Misses that best only changes when a bigger value appears."},
                   "CS_ALG_STOPS_EARLY": {"label": "Thinks the loop stops at the first match", "gap_skill": SC,
                                          "explanation": "Counts only one match, or gives the first position."},
                   "CS_ALG_ONE_BASED": {"label": "Counts list positions from 1 instead of 0", "gap_skill": SC,
                                        "explanation": "Says the first item is at position 1."}},
                  B.items, lessons)


ALL = [data_types, conditionals, boolean_logic, algorithms]
