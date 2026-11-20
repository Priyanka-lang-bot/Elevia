"""English topics. Answers are exact (typed words or chosen options); wrong forms map to misconceptions."""
from .common import TOPIC_IDS, Bank

TOPIC_IDS["PAST"] = "past_tense"
TOPIC_IDS["SVA"] = "subject_verb_agreement"

IRREGULAR = [("go", "went", "goed"), ("buy", "bought", "buyed"), ("catch", "caught", "catched"),
             ("teach", "taught", "teached"), ("think", "thought", "thinked"), ("run", "ran", "runned"),
             ("eat", "ate", "eated"), ("write", "wrote", "writed"), ("bring", "brought", "bringed"),
             ("sing", "sang", "singed"), ("drink", "drank", "drinked"), ("take", "took", "taked"),
             ("find", "found", "finded"), ("speak", "spoke", "speaked"), ("throw", "threw", "throwed"),
             ("sleep", "slept", "sleeped"), ("keep", "kept", "keeped"), ("feel", "felt", "feeled")]
DOUBLE = [("stop", "stopped", "stoped"), ("plan", "planned", "planed"), ("drop", "dropped", "droped"),
          ("clap", "clapped", "claped"), ("hug", "hugged", "huged"), ("jog", "jogged", "joged"),
          ("shop", "shopped", "shoped"), ("grab", "grabbed", "grabed"), ("nod", "nodded", "noded"),
          ("rub", "rubbed", "rubed"), ("skip", "skipped", "skiped"), ("beg", "begged", "beged")]
YIED = [("cry", "cried", "cryed"), ("try", "tried", "tryed"), ("study", "studied", "studyed"),
        ("carry", "carried", "carryed"), ("hurry", "hurried", "hurryed"), ("copy", "copied", "copyed"),
        ("worry", "worried", "worryed"), ("reply", "replied", "replyed"), ("dry", "dried", "dryed"),
        ("fry", "fried", "fryed"), ("tidy", "tidied", "tidyed")]


def past_tense() -> dict:
    B = Bank("PAST")
    RP, IP = "regular_past", "irregular_past"
    reg_hints = ["Short verb ending consonant–vowel–consonant (stop)? Double the last letter, then add -ed.",
                 "Verb ending consonant + y (cry)? Change y to i, then add -ed."]
    irr_hints = ["This is an irregular verb: it does not take -ed.",
                 "Say it in a sentence: 'Yesterday I ...'. Which word sounds right?"]
    it = {"I": iter(IRREGULAR), "D": iter(DOUBLE), "Y": iter(YIED)}

    def q(kind, cat, role=None):
        base, past, wrong = next(it[cat])
        prompt = f'Type the past tense of the verb "{base}".'
        if cat == "I":
            B.add(kind, IP, "text", prompt, past, patterns={wrong: "ENG_OVERREGULARISE"}, role=role, hints=irr_hints,
                  solution=[f'"{base}" is irregular, so it does not add -ed.', f"Past tense: {past} (not {wrong})."])
        elif cat == "D":
            B.add(kind, RP, "text", prompt, past, patterns={wrong: "ENG_NO_DOUBLING"}, role=role, hints=reg_hints,
                  solution=[f'"{base}" ends consonant–vowel–consonant, so double the last letter.', f"{base} → {past}."])
        else:
            B.add(kind, RP, "text", prompt, past, patterns={wrong: "ENG_Y_TO_I"}, role=role, hints=reg_hints,
                  solution=[f'"{base}" ends with a consonant + y, so change y to i and add -ed.', f"{base} → {past}."])

    for k in ("diagnostic:A", "diagnostic:B"):
        q(k, "I"); q(k, "I"); q(k, "D"); q(k, "Y"); q(k, "D")
    q("verification", "D", "same_type"); q("verification", "Y", "same_type")
    q("verification", "D", "similar_concept"); q("verification", "Y", "similar_concept")
    q("verification", "I", "same_type"); q("verification", "I", "same_type")
    q("verification", "I", "similar_concept"); q("verification", "I", "similar_concept")
    q("practice", "D"); q("practice", "Y"); q("practice", "D"); q("practice", "Y")
    for _ in range(4):
        q("practice", "I")
    for c in ("D", "Y", "D", "Y", "D", "Y"):
        q("retest", c)
    for _ in range(6):
        q("retest", "I")

    lessons = {
        RP: {"title": "Regular past tense spelling",
             "big_idea": "Most verbs add -ed for the past tense, but two spelling rules change the word first: "
                         "double a final consonant after a short vowel, and change a final consonant + y to i.",
             "steps": ["Most verbs: just add -ed (walk → walked).",
                       "Short verb ending consonant–vowel–consonant (stop, plan): double the last letter, then add -ed.",
                       "Verb ending consonant + y (cry, study): change y to i, then add -ed.",
                       "Verb ending vowel + y (play): keep the y (played)."],
             "sense_check": "Without doubling, 'stoped' would rhyme with 'hoped'. The double letter keeps the vowel short.",
             "worked_examples": [
                 {"prompt": 'Past tense of "stop"', "answer": "stopped",
                  "steps": ["s-t-O-P: short vowel then one consonant.", "Double the p: stopp.", "Add -ed: stopped."]},
                 {"prompt": 'Past tense of "cry"', "answer": "cried",
                  "steps": ["Ends with consonant r + y.", "Change y to i: cri.", "Add -ed: cried."]}]},
        IP: {"title": "Irregular past tense verbs",
             "big_idea": "Some common verbs have their own past form and never take -ed: go → went, buy → bought, eat → ate.",
             "steps": ["Before adding -ed, ask: is this one of the irregular verbs?",
                       "Many irregular verbs change their vowel (sing → sang, drink → drank).",
                       "Some change completely (go → went, buy → bought).",
                       "Learn them in groups: think/bought/brought/caught/taught all end in -ought or -aught."],
             "sense_check": "Nobody says 'I goed to school' in a book or the news. If it sounds like baby talk, it's probably irregular.",
             "worked_examples": [
                 {"prompt": 'Past tense of "go"', "answer": "went", "steps": ["'go' is irregular.", "Its past form is 'went'."]},
                 {"prompt": 'Past tense of "catch"', "answer": "caught",
                  "steps": ["'catch' is irregular.", "It belongs to the -aught group, like teach → taught.", "caught."]}]},
    }
    return {
        "topic": {"id": "past_tense", "subject": "english", "name": "Past tense verbs", "unit": "Grammar",
                  "grade_min": 3, "grade_max": 6,
                  "description": "Spelling regular past tense forms and using common irregular verbs.",
                  "objectives": ["Apply doubling and y→i spelling rules", "Use common irregular past tense forms"],
                  "skills": [RP, IP]},
        "skills": [
            {"id": RP, "name": "Regular past tense spelling", "grade": 3, "prerequisites": [],
             "description": "Adding -ed with the doubling and y→i rules."},
            {"id": IP, "name": "Irregular past tense verbs", "grade": 4, "prerequisites": [RP],
             "description": "Common verbs that do not take -ed."}],
        "misconceptions": {
            "ENG_OVERREGULARISE": {"label": "Adds -ed to irregular verbs", "gap_skill": IP,
                                   "explanation": "Writes 'goed', 'buyed' or 'catched' instead of went, bought, caught."},
            "ENG_NO_DOUBLING": {"label": "Forgets to double the final consonant", "gap_skill": RP,
                                "explanation": "Writes 'stoped' or 'planed' instead of stopped, planned."},
            "ENG_Y_TO_I": {"label": "Keeps the y before adding -ed", "gap_skill": RP,
                           "explanation": "Writes 'cryed' or 'studyed' instead of cried, studied."}},
        "questions": B.items, "lessons": lessons}


# (sentence with ___, correct, wrong, misconception or None)
SVA_BASIC = [
    ("The dogs ___ loudly every night.", "bark", "barks"),
    ("My friends ___ cricket after school.", "play", "plays"),
    ("The birds ___ south in winter.", "fly", "flies"),
    ("Those girls ___ in the school choir.", "sing", "sings"),
    ("The teachers ___ in the staff room.", "meet", "meets"),
    ("My parents ___ tea every morning.", "drink", "drinks"),
    ("The children ___ to the park on Sundays.", "go", "goes"),
    ("Cats ___ a lot during the day.", "sleep", "sleeps"),
    ("The farmers ___ rice in July.", "plant", "plants"),
    ("These shoes ___ too tight.", "feel", "feels"),
    ("Monkeys ___ bananas.", "eat", "eats"),
    ("The students ___ their homework in the library.", "do", "does"),
    ("My brothers ___ comics at night.", "read", "reads"),
    ("Bees ___ honey from nectar.", "make", "makes"),
    ("The buses ___ late when it rains.", "arrive", "arrives"),
    ("Our neighbours ___ a big garden.", "have", "has"),
    ("The cows ___ grass in the field.", "eat", "eats"),
    ("My cousins ___ in Chennai.", "live", "lives"),
]
SVA_NEAR = [
    ("The box of pencils ___ on the desk.", "is", "are"),
    ("The leader of the players ___ ready.", "is", "are"),
    ("The pencils in the box ___ new.", "are", "is"),
    ("The colour of the flowers ___ bright yellow.", "is", "are"),
    ("A bunch of grapes ___ in the fridge.", "is", "are"),
    ("The books on the shelf ___ dusty.", "are", "is"),
    ("The sound of the drums ___ very loud.", "was", "were"),
    ("The keys to the cupboard ___ lost.", "were", "was"),
    ("The price of the tickets ___ too high.", "is", "are"),
    ("One of my friends ___ a cat.", "has", "have"),
    ("The girls in the photo ___ my cousins.", "are", "is"),
    ("The smell of the cakes ___ wonderful.", "was", "were"),
]
SVA_EACH = [
    ("Everyone in the class ___ a book.", "has", "have"),
    ("Each of the boys ___ a bat.", "has", "have"),
    ("Every student ___ a uniform.", "wears", "wear"),
    ("Everybody ___ the answer.", "knows", "know"),
    ("Each of the rooms ___ a fan.", "has", "have"),
    ("Every one of the apples ___ ripe.", "is", "are"),
    ("Everyone ___ invited to the party.", "is", "are"),
    ("Each child ___ a turn.", "gets", "get"),
    ("Nobody in the team ___ tired.", "is", "are"),
    ("Every dog in the street ___ at night.", "barks", "bark"),
]


def subject_verb_agreement() -> dict:
    B = Bank("SVA")
    SB, ST = "sva_basic", "sva_tricky"
    hb = ["Find the subject. Is it one thing or more than one?",
          "With a plural subject (dogs, they), the verb has NO -s: the dogs bark."]
    ht = ["Cross out the extra phrase (of the..., in the...) and find the real subject.",
          "Each, every, everyone and nobody are singular."]
    it = {"B": iter(SVA_BASIC), "N": iter(SVA_NEAR), "E": iter(SVA_EACH)}

    def q(kind, cat, role=None):
        sent, right, wrong = next(it[cat])
        opts = sorted([right, wrong], key=len)
        prompt = f"Choose the word that completes the sentence:  {sent}"
        if cat == "B":
            B.add(kind, SB, "mcq", prompt, right, options=opts, patterns={wrong: "ENG_PLURAL_VERB_S"}, role=role,
                  hints=hb, solution=[f"The subject is plural, so the verb has no -s.", sent.replace("___", right)])
        elif cat == "N":
            B.add(kind, ST, "mcq", prompt, right, options=opts, patterns={wrong: "ENG_NEAREST_NOUN"}, role=role,
                  hints=ht, solution=["The verb agrees with the main subject, not the noun just before it.",
                                      sent.replace("___", right)])
        else:
            B.add(kind, ST, "mcq", prompt, right, options=opts, patterns={wrong: "ENG_EACH_PLURAL"}, role=role,
                  hints=ht, solution=["Each / every / everyone / nobody is singular, so use the singular verb.",
                                      sent.replace("___", right)])

    for k in ("diagnostic:A", "diagnostic:B"):
        q(k, "B"); q(k, "N"); q(k, "E"); q(k, "N"); q(k, "B")
    q("verification", "B", "same_type"); q("verification", "B", "same_type")
    q("verification", "B", "similar_concept"); q("verification", "B", "similar_concept")
    q("verification", "N", "same_type"); q("verification", "N", "same_type")
    q("verification", "E", "similar_concept"); q("verification", "E", "similar_concept")
    for c in ("B", "B", "B", "B", "N", "E", "N", "E"):
        q("practice", c)
    for c in ("B",) * 6 + ("N", "E", "N", "E", "N", "E"):
        q("retest", c)

    lessons = {
        SB: {"title": "Singular and plural subjects",
             "big_idea": "A verb must match its subject. One thing: add -s to the verb (the dog barks). More than "
                         "one: no -s on the verb (the dogs bark). The -s moves from the noun to the verb, never both.",
             "steps": ["Find the subject: who or what is doing the action?",
                       "Is it one (he, she, the dog) or more than one (they, the dogs)?",
                       "One: the verb takes -s or -es (barks, goes, has).",
                       "More than one: the verb has no -s (bark, go, have)."],
             "sense_check": "'The dogs barks' has two -s endings. Only one of the noun and the verb gets the -s.",
             "worked_examples": [
                 {"prompt": "The dogs ___ loudly. (bark / barks)", "answer": "bark",
                  "steps": ["Subject: the dogs, plural.", "Plural subject, so no -s: bark."]},
                 {"prompt": "My sister ___ to school by bus. (go / goes)", "answer": "goes",
                  "steps": ["Subject: my sister, one person.", "Singular, so add -es: goes."]}]},
        ST: {"title": "Agreement with tricky subjects",
             "big_idea": "Extra words between the subject and the verb do not change the subject. Words like "
                         "each, every, everyone and nobody are singular.",
             "steps": ["Cover up phrases like 'of the pencils' or 'in the box'.",
                       "What is left is the real subject: 'The box ... is'.",
                       "Each, every, everyone, everybody, nobody: treat them as ONE.",
                       "Read the sentence again with only the subject and verb."],
             "sense_check": "'The box of pencils are' becomes 'The box are' when you cover the middle. That sounds wrong.",
             "worked_examples": [
                 {"prompt": "The box of pencils ___ on the desk. (is / are)", "answer": "is",
                  "steps": ["Cover 'of pencils'.", "The box ___ on the desk.", "One box: is."]},
                 {"prompt": "Everyone in the class ___ a book. (has / have)", "answer": "has",
                  "steps": ["'Everyone' is singular.", "Everyone has."]}]},
    }
    return {
        "topic": {"id": "subject_verb_agreement", "subject": "english", "name": "Subject–verb agreement",
                  "unit": "Sentence construction", "grade_min": 3, "grade_max": 7,
                  "description": "Matching verbs to singular and plural subjects, including tricky subjects.",
                  "objectives": ["Match verbs to singular and plural subjects",
                                 "Find the real subject when other nouns get in the way"],
                  "skills": [SB, ST]},
        "skills": [
            {"id": SB, "name": "Singular and plural subjects", "grade": 3, "prerequisites": [],
             "description": "The verb takes -s with a singular subject, not with a plural one."},
            {"id": ST, "name": "Agreement with tricky subjects", "grade": 5, "prerequisites": [SB],
             "description": "Phrases between subject and verb; each/every/everyone."}],
        "misconceptions": {
            "ENG_PLURAL_VERB_S": {"label": "Adds -s to the verb when the subject is plural", "gap_skill": SB,
                                  "explanation": "Writes 'the dogs barks', putting -s on both noun and verb."},
            "ENG_NEAREST_NOUN": {"label": "Makes the verb agree with the nearest noun", "gap_skill": ST,
                                 "explanation": "Writes 'the box of pencils are' because 'pencils' is next to the verb."},
            "ENG_EACH_PLURAL": {"label": "Treats each / every / everyone as plural", "gap_skill": ST,
                                "explanation": "Writes 'everyone have' or 'each of the boys have'."}},
        "questions": B.items, "lessons": lessons}


ALL = [past_tense, subject_verb_agreement]
