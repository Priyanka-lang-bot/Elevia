"""Computer Science topics: predict-the-output questions on short Python programs.

The student only TYPES what they think the program prints; their input is never executed. Every expected
answer below is verified at build time by running the fixed snippet (scripts/build_curriculum.py)."""
from .common import TOPIC_IDS, Bank

TOPIC_IDS["VAR"] = "variables"
TOPIC_IDS["LOOP"] = "loops"
PROMPT = "What does this program print?"


def variables() -> dict:
    B = Bank("VAR")
    VA, VT = "variable_assignment", "variable_tracing"
    h1 = ["A variable is a labelled box holding ONE value at a time.", "A new assignment replaces the old value."]
    h2 = ["Trace line by line. Write down each variable's value after every line.",
          "`a = b` copies the value of b into a right now. It does not link them."]

    def keep(kind, a, b, role=None):
        B.add(kind, VA, "code_output", PROMPT, str(b), code=f"x = {a}\nx = {b}\nprint(x)",
              patterns={str(a): "CS_KEEPS_FIRST"}, role=role, hints=h1,
              solution=[f"x starts as {a}.", f"x = {b} replaces it, so x is {b}.", f"The program prints {b}."])

    def update(kind, a, b, role=None):
        B.add(kind, VA, "code_output", PROMPT, str(a + b), code=f"x = {a}\nx = x + {b}\nprint(x)",
              patterns={str(a): "CS_KEEPS_FIRST"}, role=role, hints=h1,
              solution=[f"x starts as {a}.", f"x + {b} is worked out first: {a} + {b} = {a + b}.",
                        f"That result is stored back in x, so it prints {a + b}."])

    def link(kind, p, q, role=None):
        B.add(kind, VT, "code_output", PROMPT, str(p), code=f"a = {p}\nb = a\na = {q}\nprint(b)",
              patterns={str(q): "CS_ASSIGN_LINK"}, role=role, hints=h2,
              solution=[f"b = a copies the value {p} into b.", f"Changing a to {q} later does not change b.",
                        f"The program prints {p}."])

    def swap(kind, p, q, role=None):
        B.add(kind, VT, "code_output", PROMPT + " (Type the two numbers with a space, like: 3 4)", f"{q} {q}",
              code=f"a = {p}\nb = {q}\na = b\nb = a\nprint(a, b)", patterns={f"{q} {p}": "CS_SWAP"}, role=role,
              hints=h2, solution=[f"a = b makes a equal to {q}. The {p} is now lost.",
                                  f"b = a copies {q} back into b.", f"Both are {q}: it prints {q} {q}."])

    keep("diagnostic:A", 3, 7); update("diagnostic:A", 4, 5); link("diagnostic:A", 5, 9); link("diagnostic:A", 2, 8); swap("diagnostic:A", 1, 2)
    keep("diagnostic:B", 6, 2); update("diagnostic:B", 10, 3); link("diagnostic:B", 4, 1); link("diagnostic:B", 7, 3); swap("diagnostic:B", 5, 8)
    keep("verification", 9, 4, "same_type"); keep("verification", 1, 6, "same_type")
    update("verification", 8, 2, "similar_concept"); update("verification", 3, 9, "similar_concept")
    link("verification", 6, 10, "same_type"); link("verification", 3, 12, "same_type")
    swap("verification", 4, 7, "similar_concept"); swap("verification", 9, 3, "similar_concept")
    keep("practice", 2, 5); update("practice", 7, 1); keep("practice", 8, 11); update("practice", 5, 5)
    link("practice", 1, 4); swap("practice", 2, 6); link("practice", 9, 2); swap("practice", 3, 5)
    for a, b in ((5, 12), (13, 4), (20, 1)):
        keep("retest", a, b)
    for a, b in ((6, 7), (12, 3), (0, 8)):
        update("retest", a, b)
    for p, q in ((8, 2), (11, 5), (4, 6)):
        link("retest", p, q)
    for p, q in ((6, 1), (7, 2), (3, 9)):
        swap("retest", p, q)

    lessons = {
        VA: {"title": "Variables and assignment",
             "big_idea": "A variable is like a labelled box that holds one value at a time. `x = 7` puts 7 in the "
                         "box and throws away whatever was there before.",
             "steps": ["Read `=` as 'becomes' or 'gets', not 'equals'.",
                       "Work out the right-hand side first, using the CURRENT values.",
                       "Store the result in the variable on the left, replacing the old value.",
                       "Only the latest value is kept."],
             "sense_check": "`x = x + 1` would be impossible in maths, but in code it just means: x gets (old x) + 1.",
             "worked_examples": [
                 {"prompt": PROMPT, "code": "x = 3\nx = 7\nprint(x)", "answer": "7",
                  "steps": ["x becomes 3.", "x becomes 7 (the 3 is replaced).", "Prints 7."]},
                 {"prompt": PROMPT, "code": "x = 4\nx = x + 5\nprint(x)", "answer": "9",
                  "steps": ["x becomes 4.", "x + 5 = 9, then x becomes 9.", "Prints 9."]}]},
        VT: {"title": "Tracing assignments step by step",
             "big_idea": "`b = a` copies a's value into b at that moment. The two variables are not linked, so "
                         "changing one later does not change the other.",
             "steps": ["Make a trace table with one column per variable.",
                       "Go line by line and update only the variable on the left of `=`.",
                       "When a value is overwritten, cross it out: it is gone.",
                       "At print, read the current values from the table."],
             "sense_check": "To swap two cups of juice you need a third, empty cup. Code needs a temporary variable too.",
             "worked_examples": [
                 {"prompt": PROMPT, "code": "a = 5\nb = a\na = 9\nprint(b)", "answer": "5",
                  "steps": ["a = 5.", "b = 5 (a copy).", "a = 9; b is still 5.", "Prints 5."]},
                 {"prompt": PROMPT, "code": "a = 1\nb = 2\na = b\nb = a\nprint(a, b)", "answer": "2 2",
                  "steps": ["a = 1, b = 2.", "a = b → a = 2 (the 1 is lost).", "b = a → b = 2.", "Prints 2 2."]}]},
    }
    return {
        "topic": {"id": "variables", "subject": "computer_science", "name": "Variables and assignment",
                  "unit": "Programming fundamentals", "grade_min": 6, "grade_max": 9,
                  "description": "What a variable holds, how assignment replaces values, and tracing short programs.",
                  "objectives": ["Predict the value of a variable after assignments", "Trace a short program line by line"],
                  "skills": [VA, VT]},
        "skills": [
            {"id": VA, "name": "Variables and assignment", "grade": 6, "prerequisites": [],
             "description": "A variable holds its latest value; the right-hand side is evaluated first."},
            {"id": VT, "name": "Tracing assignments", "grade": 7, "prerequisites": [VA],
             "description": "Copying values between variables; why a naive swap fails."}],
        "misconceptions": {
            "CS_KEEPS_FIRST": {"label": "Thinks a variable keeps its first value", "gap_skill": VA,
                               "explanation": "Predicts that after x = 3 then x = 7, x is still 3."},
            "CS_ASSIGN_LINK": {"label": "Thinks `b = a` links the two variables forever", "gap_skill": VT,
                               "explanation": "Predicts that changing a later also changes b."},
            "CS_SWAP": {"label": "Thinks `a = b` followed by `b = a` swaps two values", "gap_skill": VT,
                        "explanation": "Misses that the first assignment overwrites a's old value."}},
        "questions": B.items, "lessons": lessons}


def loops() -> dict:
    B = Bank("LOOP")
    LC, LA = "loop_counting", "loop_accumulator"
    h1 = ["range(a, b) starts at a and stops BEFORE b.", "range(n) gives 0, 1, ..., n − 1: that is n numbers."]
    h2 = ["The total keeps growing: each time round it adds to what it already had.",
          "Write the total after every pass of the loop."]

    def count(kind, a, b, role=None):
        n = b - a
        B.add(kind, LC, "code_output", PROMPT, str(n),
              code=f"count = 0\nfor i in range({a}, {b}):\n    count = count + 1\nprint(count)",
              patterns={str(n + 1): "CS_RANGE_OFF_BY_ONE"}, role=role, hints=h1,
              solution=[f"range({a}, {b}) gives {', '.join(map(str, range(a, b)))}.", f"That is {n} numbers, so count is {n}."])

    def last(kind, n, role=None):
        B.add(kind, LC, "code_output", PROMPT, str(n - 1), code=f"for i in range({n}):\n    last = i\nprint(last)",
              patterns={str(n): "CS_RANGE_OFF_BY_ONE"}, role=role, hints=h1,
              solution=[f"range({n}) gives 0 to {n - 1}.", f"The last value i takes is {n - 1}."])

    def total(kind, n, role=None):
        s = sum(range(1, n))
        B.add(kind, LA, "code_output", PROMPT, str(s),
              code=f"total = 0\nfor i in range(1, {n}):\n    total = total + i\nprint(total)",
              patterns={str(n - 1): "CS_ACC_LAST", str(s + n): "CS_RANGE_OFF_BY_ONE"}, role=role, hints=h2,
              solution=[f"i takes the values {', '.join(map(str, range(1, n)))}.",
                        f"total adds each one: {' + '.join(map(str, range(1, n)))} = {s}."])

    def repeat(kind, n, k, role=None):
        B.add(kind, LA, "code_output", PROMPT, str(n * k),
              code=f"total = 0\nfor i in range({n}):\n    total = total + {k}\nprint(total)",
              patterns={str(k): "CS_ACC_LAST", str((n + 1) * k): "CS_RANGE_OFF_BY_ONE"}, role=role, hints=h2,
              solution=[f"The loop runs {n} times.", f"Each time it adds {k}: {n} × {k} = {n * k}."])

    count("diagnostic:A", 1, 5); last("diagnostic:A", 4); total("diagnostic:A", 4); repeat("diagnostic:A", 3, 5); total("diagnostic:A", 5)
    count("diagnostic:B", 2, 7); last("diagnostic:B", 6); total("diagnostic:B", 6); repeat("diagnostic:B", 4, 3); repeat("diagnostic:B", 5, 2)
    count("verification", 3, 8, "same_type"); last("verification", 5, "same_type")
    count("verification", 0, 6, "similar_concept"); last("verification", 9, "similar_concept")
    total("verification", 7, "same_type"); repeat("verification", 6, 4, "same_type")
    repeat("verification", 2, 9, "similar_concept"); total("verification", 3, "similar_concept")
    count("practice", 1, 4); last("practice", 3); count("practice", 5, 10); last("practice", 7)
    total("practice", 3); repeat("practice", 2, 6); total("practice", 8); repeat("practice", 5, 5)
    for a, b in ((1, 6), (4, 9), (0, 3)):
        count("retest", a, b)
    for n in (8, 2, 10):
        last("retest", n)
    for n in (6, 9):
        total("retest", n)
    for n, k in ((4, 7), (3, 8), (7, 2), (6, 3)):
        repeat("retest", n, k)

    lessons = {
        LC: {"title": "How many times a loop runs",
             "big_idea": "range(a, b) starts at a and stops just BEFORE b. So range(1, 5) gives 1, 2, 3, 4: four numbers, not five.",
             "steps": ["Write out the numbers range gives, starting at the first value.",
                       "Stop one before the end value; the end value itself is never used.",
                       "range(n) is the same as range(0, n): it runs exactly n times.",
                       "Count how many numbers you wrote."],
             "sense_check": "The count from range(a, b) is always b − a. range(1, 5): 5 − 1 = 4.",
             "worked_examples": [
                 {"prompt": PROMPT, "code": "count = 0\nfor i in range(1, 5):\n    count = count + 1\nprint(count)",
                  "answer": "4", "steps": ["i = 1, 2, 3, 4 (stops before 5).", "count goes up 4 times.", "Prints 4."]},
                 {"prompt": PROMPT, "code": "for i in range(4):\n    last = i\nprint(last)", "answer": "3",
                  "steps": ["i = 0, 1, 2, 3.", "The last value stored is 3.", "Prints 3."]}]},
        LA: {"title": "Running totals in loops",
             "big_idea": "`total = total + i` adds i to what total ALREADY holds. The total builds up each time round, it is not replaced.",
             "steps": ["Start with total = 0 (or whatever it starts as).",
                       "Each pass: new total = old total + the value added.",
                       "Keep a trace table: pass number, i, total.",
                       "The printed value is the total after the last pass."],
             "sense_check": "Saving ₹1, then ₹2, then ₹3 in a piggy bank gives ₹6, not ₹3.",
             "worked_examples": [
                 {"prompt": PROMPT, "code": "total = 0\nfor i in range(1, 4):\n    total = total + i\nprint(total)",
                  "answer": "6", "steps": ["i = 1: total 1.", "i = 2: total 3.", "i = 3: total 6.", "Prints 6."]},
                 {"prompt": PROMPT, "code": "total = 0\nfor i in range(3):\n    total = total + 5\nprint(total)",
                  "answer": "15", "steps": ["The loop runs 3 times.", "5 + 5 + 5 = 15.", "Prints 15."]}]},
    }
    return {
        "topic": {"id": "loops", "subject": "computer_science", "name": "Loops", "unit": "Programming fundamentals",
                  "grade_min": 7, "grade_max": 10,
                  "description": "How many times a for-loop runs with range(), and building running totals.",
                  "objectives": ["Predict how many times a loop runs", "Trace a running total through a loop"],
                  "skills": [LC, LA]},
        "skills": [
            {"id": LC, "name": "How many times a loop runs", "grade": 7, "prerequisites": ["variable_assignment"],
             "description": "range(a, b) stops before b."},
            {"id": LA, "name": "Running totals in loops", "grade": 8, "prerequisites": [LC],
             "description": "Accumulating a value across loop passes."}],
        "misconceptions": {
            "CS_RANGE_OFF_BY_ONE": {"label": "Thinks range() includes the end value (one extra pass)", "gap_skill": LC,
                                    "explanation": "Predicts range(1, 5) runs 5 times, or that range(4) ends at 4."},
            "CS_ACC_LAST": {"label": "Thinks a running total only keeps the last value added", "gap_skill": LA,
                            "explanation": "Predicts total = total + i ends with just the final i."}},
        "questions": B.items, "lessons": lessons}


ALL = [variables, loops]
