"""Science: scientific reasoning (fair tests). Built from hand-checked experiment scenarios; each wrong option
reflects a documented misconception about variables and fair testing."""
from .common import TOPIC_IDS, Bank

TOPIC_IDS["FAIR"] = "fair_testing"
IV, CM, CI = "SCI_CHANGE_VS_MEASURE", "SCI_CHANGE_MANY", "SCI_KEEP_TESTED_SAME"

# (what is changed, what is measured (question form), what is measured (noun), two things to keep the same)
SCENARIOS = [
    ("the amount of water", "how tall a bean plant grows", "the height of the plant", ("the type of plant", "the amount of sunlight")),
    ("the temperature of the water", "how quickly sugar dissolves", "the time the sugar takes to dissolve", ("the amount of sugar", "the amount of water")),
    ("the height of the ramp", "how far a toy car rolls", "the distance the car rolls", ("the toy car used", "the floor surface")),
    ("the type of surface", "how far a ball rolls", "the distance the ball rolls", ("the ball used", "the height it is let go from")),
    ("the size of the parachute", "how long a parachute takes to fall", "the time it takes to fall", ("the height it is dropped from", "the weight hanging from it")),
    ("the colour of the cup", "how quickly an ice cube melts in the sun", "the time the ice takes to melt", ("the size of the ice cube", "the place it is left in the sun")),
    ("the number of batteries", "how bright a bulb is", "the brightness of the bulb", ("the type of bulb", "the length of the wires")),
    ("the amount of salt in the water", "how quickly water freezes", "the time the water takes to freeze", ("the amount of water", "the freezer used")),
    ("the length of the string", "how long one swing of a pendulum takes", "the time for one swing", ("the weight on the end", "the angle it is let go from")),
    ("the amount of light", "how tall cress seedlings grow", "the height of the seedlings", ("the amount of water", "the type of seed")),
    ("the thickness of the rubber band", "how far a rubber band stretches", "how far the band stretches", ("the weight hung on it", "the length of the band")),
    ("the material of the spoon", "how quickly a spoon gets hot in hot water", "the time until the handle feels warm", ("the temperature of the water", "the size of the spoon")),
]
NAMES = ["Priya", "Rahul", "Meena", "Kabir", "Sara", "Dev", "Anjali", "Vikram", "Zoya", "Arun", "Neha", "Imran"]


def fair_testing() -> dict:
    B = Bank("FAIR")
    VR, FT = "variables_in_investigations", "fair_test"
    hv = ["The thing you CHANGE is the one in the question 'Does ___ affect …?'.",
          "The thing you MEASURE is the result you are interested in."]
    hf = ["In a fair test you change ONE thing and keep everything else the same.",
          "Never keep the thing you are testing the same: you have to change it to test it."]
    rot = [0]

    def opts(right, wrongs):
        o = [right, *wrongs]
        k = rot[0] % len(o)
        rot[0] += 1
        return o[k:] + o[:k]

    def change(kind, i, role=None):
        iv, dvq, dvn, ctl = SCENARIOS[i]
        who = NAMES[i]
        stem = f"{who} wants to find out whether {iv} affects {dvq}."
        both, measure = f"{iv[0].upper()}{iv[1:]} and {ctl[0]}", f"{dvn[0].upper()}{dvn[1:]}"
        right = f"{iv[0].upper()}{iv[1:]}"
        B.add(kind, VR, "mcq", f"{stem} What should {who} change?", right, options=opts(right, [both, measure]),
              patterns={both: CM, measure: IV}, role=role, hints=hv,
              solution=[f"The question asks whether {iv} makes a difference, so that is what changes.",
                        f"{dvn[0].upper()}{dvn[1:]} is what {who} measures. Everything else stays the same."])

    def measure(kind, i, role=None):
        iv, dvq, dvn, ctl = SCENARIOS[i]
        who = NAMES[i]
        right = f"{dvn[0].upper()}{dvn[1:]}"
        wrong_iv, wrong_c = f"{iv[0].upper()}{iv[1:]}", f"{ctl[1][0].upper()}{ctl[1][1:]}"
        B.add(kind, VR, "mcq", f"{who} wants to find out whether {iv} affects {dvq}. What should {who} measure?", right,
              options=opts(right, [wrong_iv, wrong_c]), patterns={wrong_iv: IV}, role=role, hints=hv,
              solution=[f"The result {who} cares about is {dvq}.", f"So {who} measures {dvn}."])

    def keep(kind, i, role=None, which=0):
        iv, dvq, dvn, ctl = SCENARIOS[i]
        who = NAMES[i]
        right = f"{ctl[which][0].upper()}{ctl[which][1:]}"
        w_iv, w_dv = f"{iv[0].upper()}{iv[1:]}", f"{dvn[0].upper()}{dvn[1:]}"
        B.add(kind, FT, "mcq", f"{who} is testing whether {iv} affects {dvq}. Which of these must stay the same to make it a fair test?",
              right, options=opts(right, [w_iv, w_dv]), patterns={w_iv: CI}, role=role, hints=hf,
              solution=[f"{iv[0].upper()}{iv[1:]} is being tested, so it must change.",
                        f"{ctl[which][0].upper()}{ctl[which][1:]} could also affect the result, so it stays the same."])

    def fair(kind, i, role=None):
        iv, dvq, dvn, ctl = SCENARIOS[i]
        who = NAMES[i]
        right = "No: two things changed, so you can't tell which one caused the difference"
        w1 = "Yes: changing more things gives more information"
        w2 = "Yes, as long as the measurements are careful"
        B.add(kind, FT, "mcq", f"{who} is testing whether {iv} affects {dvq}. Between trials, {who} changes {iv} and also {ctl[0]}. Is it a fair test?",
              right, options=opts(right, [w1, w2]), patterns={w1: CM, w2: CM}, role=role, hints=hf,
              solution=[f"{who} changed {iv} AND {ctl[0]}.", "If the result changes, we can't tell which one caused it, so it isn't fair."])

    # pools: diag A/B (5 each), 4 verification, 4 practice, 6 retest per skill; each scenario used for different questions
    plan_v = [("diagnostic:A", change, 0), ("diagnostic:A", measure, 1), ("diagnostic:A", change, 2),
              ("diagnostic:B", change, 3), ("diagnostic:B", measure, 4), ("diagnostic:B", change, 5),
              ("verification", change, 6, "same_type"), ("verification", change, 7, "same_type"),
              ("verification", measure, 8, "similar_concept"), ("verification", measure, 9, "similar_concept"),
              ("practice", change, 10), ("practice", measure, 11), ("practice", measure, 0), ("practice", change, 1),
              ("retest", change, 4), ("retest", measure, 2), ("retest", change, 8),
              ("retest", measure, 6), ("retest", change, 11), ("retest", measure, 3)]
    plan_f = [("diagnostic:A", keep, 3), ("diagnostic:A", fair, 4),
              ("diagnostic:B", keep, 0), ("diagnostic:B", fair, 1),
              ("verification", keep, 5, "same_type"), ("verification", keep, 9, "same_type"),
              ("verification", fair, 2, "similar_concept"), ("verification", fair, 7, "similar_concept"),
              ("practice", keep, 11), ("practice", fair, 10), ("practice", keep, 6), ("practice", fair, 8),
              ("retest", keep, 1, None, 1), ("retest", fair, 0), ("retest", keep, 7, None, 1),
              ("retest", fair, 3), ("retest", keep, 10, None, 1), ("retest", fair, 6)]
    for step in plan_v + plan_f:
        kind, fn, i, *rest = step
        role = rest[0] if rest else None
        if len(rest) > 1:
            fn(kind, i, role, rest[1])
        else:
            fn(kind, i, role)

    lessons = {
        VR: {"title": "What to change and what to measure",
             "big_idea": "Every investigation asks 'Does A affect B?'. A is the one thing you change on purpose. B is the "
                         "result you measure. Mixing them up means you can't answer the question.",
             "steps": ["Write the question as 'Does ___ affect ___?'.", "The first blank is what you change.",
                       "The second blank is what you measure.", "Everything else is kept the same."],
             "sense_check": "To find out if water affects plant growth, you give plants different amounts of water and measure their height, not the other way round.",
             "worked_examples": [
                 {"prompt": "Does the amount of water affect how tall a bean plant grows? What do you change?", "answer": "The amount of water",
                  "steps": ["The question names the amount of water as the possible cause.", "So that is what you change.", "You measure the plant's height."]}]},
        FT: {"title": "Fair tests",
             "big_idea": "A test is fair when only ONE thing changes, the thing being tested. Everything else that could "
                         "affect the result is kept the same, so any difference must be caused by that one thing.",
             "steps": ["Name the thing you are testing: it must change.", "List other things that could affect the result.",
                       "Keep all of those the same.", "If two things change at once, you can't tell which caused the result."],
             "sense_check": "If you change both the ramp height and the car, and the car goes further, was it the ramp or the car? You can't tell.",
             "worked_examples": [
                 {"prompt": "Testing whether ramp height affects how far a car rolls. Keep the same?", "answer": "The car and the floor surface",
                  "steps": ["Ramp height is tested, so it changes.", "The car and the floor could also change the distance.", "Keep them the same."]}]},
    }
    return {
        "topic": {"id": "fair_testing", "subject": "science", "name": "Scientific reasoning", "unit": "Working scientifically",
                  "grade_min": 4, "grade_max": 8,
                  "description": "Planning fair tests: what to change, what to measure and what to keep the same.",
                  "objectives": ["Identify what to change and what to measure", "Plan and judge fair tests"],
                  "skills": [VR, FT]},
        "skills": [
            {"id": VR, "name": "What to change and what to measure", "grade": 4, "prerequisites": [],
             "description": "Independent and dependent variables."},
            {"id": FT, "name": "Fair tests", "grade": 5, "prerequisites": [VR],
             "description": "Changing one thing and keeping the rest the same."}],
        "misconceptions": {
            IV: {"label": "Mixes up what you change and what you measure", "gap_skill": VR,
                 "explanation": "Chooses the result (e.g. plant height) as the thing to change."},
            CM: {"label": "Thinks changing more than one thing at once is fine", "gap_skill": FT,
                 "explanation": "Doesn't see that two changes make the result impossible to explain."},
            CI: {"label": "Keeps the thing being tested the same", "gap_skill": FT,
                 "explanation": "Lists the variable under test as something to control."}},
        "questions": B.items, "lessons": lessons}


ALL = [fair_testing]
