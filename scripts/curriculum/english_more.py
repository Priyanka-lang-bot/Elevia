"""English: parts of speech and apostrophes. Hand-written sentences; options are fixed and checked exactly."""
from .common import TOPIC_IDS, Bank

TOPIC_IDS["POS"] = "parts_of_speech"
TOPIC_IDS["APO"] = "apostrophes"
CLASSES = ["noun", "verb", "adjective", "adverb"]

# (sentence, word, answer). Adjectives and adverbs, including -ly adjectives (lovely, friendly) as traps.
ADJ_ADV = [
    ("The tortoise moved slowly across the road.", "slowly", "adverb"),
    ("The quiet library was nearly empty.", "quiet", "adjective"),
    ("Meera sang beautifully at the concert.", "beautifully", "adverb"),
    ("Her lovely painting won a prize.", "lovely", "adjective"),
    ("The children waited patiently for the bus.", "patiently", "adverb"),
    ("We climbed a steep hill.", "steep", "adjective"),
    ("He closed the door quietly.", "quietly", "adverb"),
    ("The friendly shopkeeper smiled at us.", "friendly", "adjective"),
    ("She answered the question correctly.", "correctly", "adverb"),
    ("The soup smells delicious.", "delicious", "adjective"),
    ("The baby slept soundly all night.", "soundly", "adverb"),
    ("It was a cold morning.", "cold", "adjective"),
    ("Rain fell heavily on the roof.", "heavily", "adverb"),
    ("The kitten looked sleepy.", "sleepy", "adjective"),
    ("The dog barked loudly at the postman.", "loudly", "adverb"),
    ("A bright light filled the room.", "bright", "adjective"),
    ("Arjun ran fast to catch the bus.", "fast", "adverb"),
    ("That was a silly mistake.", "silly", "adjective"),
    ("The team played well in the final.", "well", "adverb"),
    ("The old bridge creaked.", "old", "adjective"),
]
# The same word doing a different job.
CONTEXT = [
    ("We went for a run before school.", "run", "noun"),
    ("Please book a table for four.", "book", "verb"),
    ("Ravi gave the ball a hard kick.", "kick", "noun"),
    ("Water the plants every morning.", "water", "verb"),
    ("Let's take a walk after dinner.", "walk", "noun"),
    ("They will paint the fence on Sunday.", "paint", "verb"),
    ("The play at school was a success.", "play", "noun"),
    ("Can you hand me the scissors?", "hand", "verb"),
    ("She had a long drink of water.", "drink", "noun"),
    ("The birds nest in that tree.", "nest", "verb"),
    ("I heard a loud knock at the door.", "knock", "noun"),
    ("We fish in the lake every summer.", "fish", "verb"),
    ("Grandma gave me a warm hug.", "hug", "noun"),
    ("Please light the candles.", "light", "verb"),
    ("The swim made us hungry.", "swim", "noun"),
    ("Don't park your bike here.", "park", "verb"),
    ("There was a long wait at the station.", "wait", "noun"),
    ("I will email my teacher tonight.", "email", "verb"),
    ("He made a quick jump over the puddle.", "jump", "noun"),
    ("We plant seeds in the spring.", "plant", "verb"),
]


def parts_of_speech() -> dict:
    B = Bank("POS")
    WC, CT = "adjectives_and_adverbs", "word_class_in_context"
    ha = ["An adjective describes a noun (a quiet library). An adverb describes a verb (closed quietly).",
          "Not every -ly word is an adverb: lovely and friendly describe nouns."]
    hc = ["Look at what the word is doing in THIS sentence.",
          "After 'a', 'the' or 'my' it is usually a noun; if it's the action, it's a verb."]
    it = {WC: iter(ADJ_ADV), CT: iter(CONTEXT)}

    def q(kind, skill, role=None):
        sent, word, ans = next(it[skill])
        prompt = f'In the sentence "{sent}", what part of speech is "{word}"?'
        if skill == WC:
            wrong = "adjective" if ans == "adverb" else "adverb"
            B.add(kind, WC, "mcq", prompt, ans, options=CLASSES, patterns={wrong: "ENG_ADJ_ADV_MIX"}, role=role, hints=ha,
                  solution=[f'"{word}" describes {"how something is done (a verb)" if ans == "adverb" else "a noun"}.', f"So it is an {ans}."])
        else:
            wrong = "verb" if ans == "noun" else "noun"
            B.add(kind, CT, "mcq", prompt, ans, options=CLASSES, patterns={wrong: "ENG_FIXED_WORD_CLASS"}, role=role, hints=hc,
                  solution=[f'Here "{word}" is {"a thing (it comes after a/the)" if ans == "noun" else "the action"}.', f"So it is a {ans} in this sentence."])

    for k, order in (("diagnostic:A", (WC, CT, WC, CT, WC)), ("diagnostic:B", (CT, WC, CT, WC, CT))):
        for sk in order:
            q(k, sk)
    for sk in (WC, CT):
        q("verification", sk, "same_type"); q("verification", sk, "same_type")
        q("verification", sk, "similar_concept"); q("verification", sk, "similar_concept")
        for _ in range(4):
            q("practice", sk)
        for _ in range(6):
            q("retest", sk)
    lessons = {
        WC: {"title": "Adjectives and adverbs",
             "big_idea": "Adjectives describe nouns (a quiet library). Adverbs describe verbs: how, when or where something "
                         "happens (closed the door quietly). The -ly ending is a clue, not a rule: lovely and friendly are adjectives.",
             "steps": ["Find the word it is describing.", "If it describes a person, place or thing, it's an adjective.",
                       "If it describes an action (how, when, where), it's an adverb.",
                       "After verbs like is, looks, smells, feels, a describing word is usually an adjective (the soup smells delicious)."],
             "sense_check": "Try 'a lovely ___': a lovely painting works, so 'lovely' describes a noun.",
             "worked_examples": [
                 {"prompt": '"He closed the door quietly." What is "quietly"?', "answer": "adverb",
                  "steps": ["It tells us HOW he closed the door.", "It describes the verb 'closed'.", "Adverb."]},
                 {"prompt": '"Her lovely painting won a prize." What is "lovely"?', "answer": "adjective",
                  "steps": ["It describes the painting (a noun).", "Even though it ends in -ly, it's an adjective."]}]},
        CT: {"title": "Word class depends on the sentence",
             "big_idea": "Many words can be a noun in one sentence and a verb in another. You can only tell by looking at "
                         "the job the word does in that sentence.",
             "steps": ["Read the whole sentence.", "Is the word a thing (often after a, the, my)? Then it's a noun.",
                       "Is it the action someone does? Then it's a verb.", "Don't decide from the word alone."],
             "sense_check": "'I run' (verb) and 'a run' (noun): same word, different jobs.",
             "worked_examples": [
                 {"prompt": '"We went for a run." What is "run"?', "answer": "noun",
                  "steps": ["It comes after 'a'.", "It names a thing we went for.", "Noun."]},
                 {"prompt": '"Please book a table." What is "book"?', "answer": "verb",
                  "steps": ["It's what we are asked to do.", "It's the action.", "Verb."]}]},
    }
    return {
        "topic": {"id": "parts_of_speech", "subject": "english", "name": "Parts of speech", "unit": "Grammar",
                  "grade_min": 4, "grade_max": 7,
                  "description": "Telling adjectives from adverbs, and seeing that a word's class depends on the sentence.",
                  "objectives": ["Tell adjectives and adverbs apart", "Identify word class from how a word is used"],
                  "skills": [WC, CT]},
        "skills": [
            {"id": WC, "name": "Adjectives and adverbs", "grade": 4, "prerequisites": [],
             "description": "What each describes; -ly adjectives."},
            {"id": CT, "name": "Word class depends on the sentence", "grade": 5, "prerequisites": [WC],
             "description": "Nouns and verbs that share a spelling."}],
        "misconceptions": {
            "ENG_ADJ_ADV_MIX": {"label": "Mixes up adjectives and adverbs", "gap_skill": WC,
                                "explanation": "Calls 'quietly' an adjective, or every -ly word an adverb."},
            "ENG_FIXED_WORD_CLASS": {"label": "Thinks a word always has the same word class", "gap_skill": CT,
                                     "explanation": "Calls 'run' a verb even in 'we went for a run'."}},
        "questions": B.items, "lessons": lessons}


# (sentence with ___, correct, {wrong: misconception or None})
POSSESSION = [
    ("The ___ tail was wagging. (one dog)", "dog's", {"dogs'": "ENG_APOS_PLACE", "dogs": None}),
    ("The ___ coats were on the pegs. (several girls)", "girls'", {"girl's": "ENG_APOS_PLACE", "girls": None}),
    ("We bought six ___ at the market.", "apples", {"apple's": "ENG_APOS_PLURAL", "apples'": "ENG_APOS_PLURAL"}),
    ("The ___ desk was very tidy. (one teacher)", "teacher's", {"teachers'": "ENG_APOS_PLACE", "teachers": None}),
    ("All the ___ shirts were muddy. (many players)", "players'", {"player's": "ENG_APOS_PLACE", "players": None}),
    ("There are ten ___ on the shelf.", "books", {"book's": "ENG_APOS_PLURAL", "books'": "ENG_APOS_PLURAL"}),
    ("The ___ bag was left on the bus. (one boy)", "boy's", {"boys'": "ENG_APOS_PLACE", "boys": None}),
    ("The ___ staff room is upstairs. (all the teachers)", "teachers'", {"teacher's": "ENG_APOS_PLACE", "teachers": None}),
    ("My aunt has two ___.", "cats", {"cat's": "ENG_APOS_PLURAL", "cats'": "ENG_APOS_PLURAL"}),
    ("The ___ bowl was empty. (one cat)", "cat's", {"cats'": "ENG_APOS_PLACE", "cats": None}),
    ("The ___ nests were high in the tree. (several birds)", "birds'", {"bird's": "ENG_APOS_PLACE", "birds": None}),
    ("Please sharpen your ___.", "pencils", {"pencil's": "ENG_APOS_PLURAL", "pencils'": "ENG_APOS_PLURAL"}),
    ("The ___ wings were bright blue. (one butterfly)", "butterfly's", {"butterflies'": "ENG_APOS_PLACE", "butterflys": None}),
    ("The ___ projects are on the wall. (all the students)", "students'", {"student's": "ENG_APOS_PLACE", "students": None}),
    ("We need four ___ for the salad.", "tomatoes", {"tomato's": "ENG_APOS_PLURAL", "tomatoes'": "ENG_APOS_PLURAL"}),
    ("The ___ door was painted red. (one house)", "house's", {"houses'": "ENG_APOS_PLACE", "houses": None}),
    ("The ___ fields were flooded. (several farmers)", "farmers'", {"farmer's": "ENG_APOS_PLACE", "farmers": None}),
    ("The shop sells fresh ___ every day.", "bananas", {"banana's": "ENG_APOS_PLURAL", "bananas'": "ENG_APOS_PLURAL"}),
    ("The ___ roar was loud. (one lion)", "lion's", {"lions'": "ENG_APOS_PLACE", "lions": None}),
    ("Both ___ bikes were new. (two brothers)", "brothers'", {"brother's": "ENG_APOS_PLACE", "brothers": None}),
]
CONTRACTIONS = [
    ("The cat licked ___ paw.", "its", {"it's": "ENG_CONTRACTION_MIX"}),
    ("___ raining again today.", "It's", {"Its": "ENG_CONTRACTION_MIX"}),
    ("Is this ___ jacket?", "your", {"you're": "ENG_CONTRACTION_MIX"}),
    ("___ going to love this book.", "You're", {"Your": "ENG_CONTRACTION_MIX"}),
    ("The children packed ___ bags.", "their", {"they're": "ENG_CONTRACTION_MIX", "there": None}),
    ("___ coming to the party later.", "They're", {"Their": "ENG_CONTRACTION_MIX", "There": None}),
    ("The tree lost ___ leaves in autumn.", "its", {"it's": "ENG_CONTRACTION_MIX"}),
    ("I think ___ time for lunch.", "it's", {"its": "ENG_CONTRACTION_MIX"}),
    ("Don't forget ___ water bottle.", "your", {"you're": "ENG_CONTRACTION_MIX"}),
    ("Tell me when ___ ready to go.", "you're", {"your": "ENG_CONTRACTION_MIX"}),
    ("My cousins sold ___ old car.", "their", {"they're": "ENG_CONTRACTION_MIX", "there": None}),
    ("I hope ___ not late again.", "they're", {"their": "ENG_CONTRACTION_MIX", "there": None}),
    ("The company changed ___ logo.", "its", {"it's": "ENG_CONTRACTION_MIX"}),
    ("___ a beautiful day.", "It's", {"Its": "ENG_CONTRACTION_MIX"}),
    ("Please wash ___ hands before dinner.", "your", {"you're": "ENG_CONTRACTION_MIX"}),
    ("If ___ tired, have a rest.", "you're", {"your": "ENG_CONTRACTION_MIX"}),
    ("The players thanked ___ coach.", "their", {"they're": "ENG_CONTRACTION_MIX", "there": None}),
    ("Ask them if ___ hungry.", "they're", {"their": "ENG_CONTRACTION_MIX", "there": None}),
    ("The dog wagged ___ tail.", "its", {"it's": "ENG_CONTRACTION_MIX"}),
    ("___ too cold to swim.", "It's", {"Its": "ENG_CONTRACTION_MIX"}),
]


def apostrophes() -> dict:
    B = Bank("APO")
    PO, CO = "apostrophes_for_possession", "contractions_vs_possessives"
    hp = ["An apostrophe shows that something belongs to someone. It is NOT used just to make a plural.",
          "One owner: add 's (the dog's tail). Several owners ending in s: add ' after the s (the girls' coats)."]
    hc = ["Try expanding it: it's = it is, you're = you are, they're = they are.",
          "If the expanded version makes sense, use the apostrophe. If not, use its / your / their."]
    it = {PO: iter(POSSESSION), CO: iter(CONTRACTIONS)}
    rot = [0]

    def q(kind, skill, role=None):
        sent, right, wrongs = next(it[skill])
        o = [right, *wrongs]
        k = rot[0] % len(o)
        rot[0] += 1
        o = o[k:] + o[:k]
        prompt = f"Choose the word that completes the sentence:  {sent}"
        if skill == PO:
            sol = ["A plural with no owner needs no apostrophe." if all(c == "ENG_APOS_PLURAL" for c in wrongs.values() if c)
                   else ("One owner: add 's." if right.endswith("'s") else "Several owners ending in s: add ' after the s."),
                   sent.split(" (")[0].replace("___", right)]
            B.add(kind, PO, "mcq", prompt, right, options=o, patterns={w: c for w, c in wrongs.items() if c}, role=role,
                  hints=hp, solution=sol)
        else:
            full = {"it's": "it is", "you're": "you are", "they're": "they are"}
            exp = full.get(right.lower())
            sol = [f"{right} = {exp}: it makes sense here." if exp else f"'{right}' shows belonging (no letters are missing).",
                   sent.replace("___", right)]
            B.add(kind, CO, "mcq", prompt, right, options=o, patterns={w: c for w, c in wrongs.items() if c}, role=role,
                  hints=hc, solution=sol)

    for k, order in (("diagnostic:A", (PO, CO, PO, CO, PO)), ("diagnostic:B", (CO, PO, CO, PO, CO))):
        for sk in order:
            q(k, sk)
    for sk in (PO, CO):
        q("verification", sk, "same_type"); q("verification", sk, "same_type")
        q("verification", sk, "similar_concept"); q("verification", sk, "similar_concept")
        for _ in range(4):
            q("practice", sk)
        for _ in range(6):
            q("retest", sk)
    lessons = {
        PO: {"title": "Apostrophes for belonging",
             "big_idea": "An apostrophe shows that something belongs to someone. It never makes a word plural: six apples, "
                         "not six apple's. Where it goes depends on whether there is one owner or several.",
             "steps": ["Ask: does something belong to someone? If not, no apostrophe.",
                       "One owner: write the owner, then 's (the dog's tail).",
                       "Several owners and the plural ends in s: write the plural, then ' (the girls' coats).",
                       "Check by saying 'the tail of the dog' or 'the coats of the girls'."],
             "sense_check": "'The teachers' room' is shared by all the teachers; 'the teacher's desk' belongs to one.",
             "worked_examples": [
                 {"prompt": "The ___ tail was wagging. (one dog)", "answer": "dog's", "steps": ["One owner: dog.", "Add 's: dog's."]},
                 {"prompt": "The ___ coats were on the pegs. (several girls)", "answer": "girls'",
                  "steps": ["Several owners: girls.", "Already ends in s, so add ': girls'."]}]},
        CO: {"title": "its / it's, your / you're, their / they're",
             "big_idea": "In it's, you're and they're the apostrophe shows missing letters (it is, you are, they are). "
                         "Its, your and their show belonging and never have an apostrophe.",
             "steps": ["Try replacing the word with it is / you are / they are.",
                       "If the sentence still makes sense, use the apostrophe form.",
                       "If it doesn't, use its / your / their."],
             "sense_check": "'The cat licked it is paw' makes no sense, so it's 'its paw'.",
             "worked_examples": [
                 {"prompt": "The cat licked ___ paw. (its / it's)", "answer": "its",
                  "steps": ["Try 'it is': the cat licked it is paw. No.", "So: its."]},
                 {"prompt": "___ going to love this book. (Your / You're)", "answer": "You're",
                  "steps": ["Try 'you are': You are going to love this book. Yes.", "So: You're."]}]},
    }
    return {
        "topic": {"id": "apostrophes", "subject": "english", "name": "Punctuation: apostrophes", "unit": "Punctuation",
                  "grade_min": 4, "grade_max": 7,
                  "description": "Apostrophes for belonging (one or many owners) and telling contractions from possessive words.",
                  "objectives": ["Use apostrophes for one and several owners", "Choose between its/it's, your/you're, their/they're"],
                  "skills": [PO, CO]},
        "skills": [
            {"id": PO, "name": "Apostrophes for belonging", "grade": 4, "prerequisites": [],
             "description": "'s for one owner, s' for several; never for plurals."},
            {"id": CO, "name": "its / it's, your / you're, their / they're", "grade": 5, "prerequisites": [PO],
             "description": "Contractions versus possessive words."}],
        "misconceptions": {
            "ENG_APOS_PLURAL": {"label": "Uses an apostrophe just to make a word plural", "gap_skill": PO,
                                "explanation": "Writes 'six apple's' or 'two cat's'."},
            "ENG_APOS_PLACE": {"label": "Puts the apostrophe in the wrong place for one or several owners", "gap_skill": PO,
                               "explanation": "Writes 'the girl's coats' for several girls, or 'the dogs' tail' for one dog."},
            "ENG_CONTRACTION_MIX": {"label": "Confuses it's / you're / they're with its / your / their", "gap_skill": CO,
                                    "explanation": "Writes 'the cat licked it's paw' or 'your going to love it'."}},
        "questions": B.items, "lessons": lessons}


ALL = [parts_of_speech, apostrophes]
