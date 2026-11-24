"""Social Science (Class 9 geography: "India: size and location").

Two topics built from data tables, so every answer is computed rather than typed:
  * Latitude and longitude: what each one measures, and which hemispheres a place is in.
  * Time zones and Indian Standard Time: 4 minutes of time per degree of longitude, places to the east are ahead.
Coordinates are rounded to whole degrees and always introduced with "about".
"""
from .common import TOPIC_IDS, Bank

TOPIC_IDS["LATL"] = "latitude_longitude"
TOPIC_IDS["TZ"] = "time_zones"

SWAP, LETTER = "SS_LAT_LONG_SWAP", "SS_IGNORES_LETTER"
MIN15, EAST_BEHIND = "SS_15_MIN_PER_DEGREE", "SS_EAST_IS_BEHIND"

# (place, latitude, N/S, longitude, E/W), rounded to whole degrees
INDIA = [("Delhi", 29, "N", 77, "E"), ("Mumbai", 19, "N", 73, "E"), ("Chennai", 13, "N", 80, "E"),
         ("Kolkata", 23, "N", 88, "E"), ("Srinagar", 34, "N", 75, "E"), ("Kanyakumari", 8, "N", 78, "E"),
         ("Guwahati", 26, "N", 92, "E"), ("Jaipur", 27, "N", 76, "E"), ("Hyderabad", 17, "N", 78, "E"),
         ("Lucknow", 27, "N", 81, "E"), ("Pune", 18, "N", 74, "E"), ("Bhopal", 23, "N", 77, "E")]
WORLD = [("Rio de Janeiro", 23, "S", 43, "W"), ("Sydney", 34, "S", 151, "E"), ("Cape Town", 34, "S", 18, "E"),
         ("New York", 41, "N", 74, "W"), ("Lima", 12, "S", 77, "W"), ("Nairobi", 1, "S", 37, "E"),
         ("Buenos Aires", 35, "S", 58, "W"), ("Mexico City", 19, "N", 99, "W"), ("Jakarta", 6, "S", 107, "E"),
         ("Santiago", 33, "S", 71, "W"), ("Perth", 32, "S", 116, "E"), ("Havana", 23, "N", 82, "W")]
NS = {"N": "Northern", "S": "Southern"}
EW = {"E": "Eastern", "W": "Western"}
NORTH_OF, EAST_OF = "How far north or south of the Equator it is", "How far east or west of the Prime Meridian it is"
HEIGHT = "How high above sea level it is"


def _rot(o, k):
    k %= len(o)
    return o[k:] + o[:k]


def latitude_longitude() -> dict:
    B = Bank("LATL")
    MEAN, HEMI = "lat_long_meaning", "hemispheres"
    hm = ["Latitude (°N or °S) is distance north or south of the Equator.",
          "Longitude (°E or °W) is distance east or west of the Prime Meridian."]
    hh = ["Look at the letters: N or S gives the north–south hemisphere, E or W the east–west one.",
          "S means south of the Equator; W means west of the Prime Meridian."]
    n = [0]

    def meaning(kind, place, which, role=None):
        name, la, ns, lo, ew = place
        n[0] += 1
        if which == "lat":
            part, right, swap = f"{la}°{ns}", NORTH_OF, EAST_OF
            why = f"{la}°{ns} is a latitude: it says the place is {la}° {'north' if ns == 'N' else 'south'} of the Equator."
        else:
            part, right, swap = f"{lo}°{ew}", EAST_OF, NORTH_OF
            why = f"{lo}°{ew} is a longitude: it says the place is {lo}° {'east' if ew == 'E' else 'west'} of the Prime Meridian."
        B.add(kind, MEAN, "mcq", f"{name} is at about {la}°{ns}, {lo}°{ew}. What does {part} tell you?", right,
              options=_rot([right, swap, HEIGHT], n[0]), patterns={swap: SWAP}, role=role, hints=hm,
              solution=[why, "Coordinates are always written latitude first, then longitude."])

    def hemi(kind, place, role=None):
        name, la, ns, lo, ew = place
        n[0] += 1
        right = f"{NS[ns]} and {EW[ew]}"
        assumed = "Northern and Eastern"                       # what you get if you ignore the S/W letters
        # the third option keeps one letter right and gets the other wrong, so it is a plausible plain mistake
        combos = [f"{x} and {y}" for x in NS.values() for y in EW.values()]
        other = next(c for c in [f"{NS[ns]} and {EW['W' if ew == 'E' else 'E']}",
                                 f"{NS['S' if ns == 'N' else 'N']} and {EW[ew]}", *combos] if c not in (right, assumed))
        B.add(kind, HEMI, "mcq", f"{name} is at about {la}°{ns}, {lo}°{ew}. Which two hemispheres is it in?", right,
              options=_rot([right, assumed, other], n[0]), patterns={assumed: LETTER}, role=role, hints=hh,
              solution=[f"{ns} = {NS[ns].lower()} of the Equator, so the {NS[ns]} Hemisphere.",
                        f"{ew} = {EW[ew].lower()} of the Prime Meridian, so the {EW[ew]} Hemisphere."])

    I, W = INDIA, [p for p in WORLD if p[2] == "S" or p[4] == "W"]       # world places that test the letters
    plan = [("diagnostic:A", meaning, I[0], "lat"), ("diagnostic:A", meaning, I[1], "long"),
            ("diagnostic:A", meaning, I[2], "lat"), ("diagnostic:A", hemi, W[0]), ("diagnostic:A", hemi, W[1]),
            ("diagnostic:B", meaning, I[3], "long"), ("diagnostic:B", meaning, I[4], "lat"),
            ("diagnostic:B", meaning, I[5], "long"), ("diagnostic:B", hemi, W[2]), ("diagnostic:B", hemi, W[3]),
            ("verification", meaning, I[6], "lat", "same_type"), ("verification", meaning, I[7], "long", "same_type"),
            ("verification", meaning, I[8], "long", "similar_concept"), ("verification", meaning, I[9], "lat", "similar_concept"),
            ("practice", meaning, I[10], "lat"), ("practice", meaning, I[11], "long"),
            ("practice", meaning, I[0], "long"), ("practice", meaning, I[1], "lat"),
            ("retest", meaning, I[2], "long"), ("retest", meaning, I[3], "lat"), ("retest", meaning, I[4], "long"),
            ("retest", meaning, I[5], "lat"), ("retest", meaning, I[6], "long"), ("retest", meaning, I[7], "lat"),
            ("verification", hemi, W[4], "same_type"), ("verification", hemi, W[5], "same_type"),
            ("verification", hemi, W[6], "similar_concept"), ("verification", hemi, W[7], "similar_concept"),
            ("practice", hemi, W[8]), ("practice", hemi, W[9]), ("practice", hemi, W[0]), ("practice", hemi, W[2]),
            ("retest", hemi, W[1]), ("retest", hemi, W[3]), ("retest", hemi, W[5]),
            ("retest", hemi, W[7]), ("retest", hemi, W[9]), ("retest", hemi, W[4])]
    for kind, fn, place, *rest in plan:
        if fn is meaning:
            meaning(kind, place, rest[0], rest[1] if len(rest) > 1 else None)
        else:
            hemi(kind, place, rest[0] if rest else None)

    lessons = {
        MEAN: {"title": "What latitude and longitude tell you",
               "big_idea": "A position has two parts. Latitude says how far north or south of the Equator a place is. "
                           "Longitude says how far east or west of the Prime Meridian it is. Mixing them up puts you on "
                           "the wrong side of the world.",
               "steps": ["Coordinates are written latitude first: 29°N, 77°E.", "The number with N or S is the latitude.",
                         "The number with E or W is the longitude.", "Latitude lines (parallels) run east–west; "
                         "longitude lines (meridians) run north–south from pole to pole."],
               "sense_check": "India is north of the Equator and east of the Prime Meridian, so Indian places have °N and °E.",
               "worked_examples": [
                   {"prompt": "Delhi is at about 29°N, 77°E. What does 29°N tell you?",
                    "answer": NORTH_OF,
                    "steps": ["29°N has the letter N, so it is a latitude.", "It says Delhi is 29° north of the Equator."]}]},
        HEMI: {"title": "Which hemispheres a place is in",
               "big_idea": "The Equator splits the Earth into Northern and Southern Hemispheres; the Prime Meridian splits "
                           "it into Eastern and Western. The letters in a place's coordinates tell you which halves it is in.",
               "steps": ["Find the latitude letter: N → Northern, S → Southern.",
                         "Find the longitude letter: E → Eastern, W → Western.", "Put the two together.",
                         "Don't assume north and east just because India is: always read the letters."],
               "sense_check": "Sydney is at about 34°S, 151°E: south of the Equator but east of the Prime Meridian.",
               "worked_examples": [
                   {"prompt": "Rio de Janeiro is at about 23°S, 43°W. Which hemispheres?",
                    "answer": "Southern and Western",
                    "steps": ["S → Southern Hemisphere.", "W → Western Hemisphere."]}]},
    }
    return {
        "topic": {"id": "latitude_longitude", "subject": "social_science", "name": "Latitude and longitude",
                  "unit": "India: size and location", "grade_min": 6, "grade_max": 9,
                  "description": "Reading coordinates: what latitude and longitude measure, and which hemispheres a place is in.",
                  "objectives": ["Say what latitude and longitude each measure", "Work out a place's hemispheres from its coordinates"],
                  "skills": [MEAN, HEMI]},
        "skills": [
            {"id": MEAN, "name": "What latitude and longitude measure", "grade": 6, "prerequisites": [],
             "description": "Latitude: north–south of the Equator. Longitude: east–west of the Prime Meridian."},
            {"id": HEMI, "name": "Hemispheres from coordinates", "grade": 6, "prerequisites": [MEAN],
             "description": "Using the N/S and E/W letters to find a place's hemispheres."}],
        "misconceptions": {
            SWAP: {"label": "Mixes up latitude and longitude", "gap_skill": MEAN,
                   "explanation": "Reads a latitude as a distance east–west (or the other way round)."},
            LETTER: {"label": "Assumes every place is north and east", "gap_skill": HEMI,
                     "explanation": "Ignores the S or W letter and puts the place in the Northern and Eastern Hemispheres."}},
        "questions": B.items, "lessons": lessons}


def _hm(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    parts = ([f"{h} hour{'s' if h != 1 else ''}"] if h else []) + ([f"{m} minutes"] if m else [])
    return " ".join(parts)


def _clock(minutes: int) -> str:
    minutes %= 24 * 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def time_zones() -> dict:
    B = Bank("TZ")
    LT, EWT = "longitude_and_time", "east_west_time"
    hl = ["The Earth turns 360° in 24 hours, so 15° every hour.", "That makes 4 minutes of time for each degree."]
    he = ["The Sun rises in the east, so places to the east reach noon first.",
          "East of you: add time. West of you: take time away."]
    n = [0]

    def gap(kind, deg, role=None):
        n[0] += 1
        right, wrong15 = _hm(4 * deg), _hm(15 * deg)
        plain = _hm(deg) if deg < 60 else _hm(60 * (deg // 15))   # 1 minute per degree / or hours per 15° mixed up
        if plain in (right, wrong15):
            plain = _hm(4 * deg + 60)
        B.add(kind, LT, "mcq", f"Two places are {deg}° of longitude apart. How far apart are their local times?", right,
              options=_rot([right, wrong15, plain], n[0]), patterns={wrong15: MIN15}, role=role, hints=hl,
              solution=[f"Each degree of longitude is 4 minutes of time.", f"{deg} × 4 = {4 * deg} minutes = {right}."])

    def local(kind, lon, ew, base=12 * 60, role=None):
        n[0] += 1
        sign = 1 if ew == "E" else -1
        right = _clock(base + sign * 4 * lon)
        flipped = _clock(base - sign * 4 * lon)
        plain = _clock(base + sign * lon)                      # adds the degrees as minutes
        if plain in (right, flipped):
            plain = _clock(base)
        B.add(kind, EWT, "mcq", f"When it is {_clock(base)} at Greenwich (0°), what is the local time at {lon}°{ew}?", right,
              options=_rot([right, flipped, plain], n[0]), patterns={flipped: EAST_BEHIND}, role=role, hints=he,
              solution=[f"{lon}° × 4 minutes = {_hm(4 * lon)}.",
                        f"{lon}°{ew} is {'east' if ew == 'E' else 'west'} of Greenwich, so {'add' if ew == 'E' else 'take away'} "
                        f"{_hm(4 * lon)}: {right}."])

    def ist(kind, gmt, role=None):
        n[0] += 1
        right, flipped, plain = _clock(gmt + 330), _clock(gmt - 330), _clock(gmt + 82)
        B.add(kind, EWT, "mcq", f"India's Standard Time is set by the meridian at 82°30′E. When it is {_clock(gmt)} at "
                                f"Greenwich, what time is it in India?", right,
              options=_rot([right, flipped, plain], n[0]), patterns={flipped: EAST_BEHIND}, role=role, hints=he,
              solution=["82.5° × 4 minutes = 330 minutes = 5 hours 30 minutes.",
                        f"India is east of Greenwich, so add it: {right}."])

    plan = [("diagnostic:A", gap, 30), ("diagnostic:A", gap, 45), ("diagnostic:A", local, 45, "E"),
            ("diagnostic:A", local, 30, "W"), ("diagnostic:A", gap, 10),
            ("diagnostic:B", gap, 60), ("diagnostic:B", gap, 20), ("diagnostic:B", local, 60, "E"),
            ("diagnostic:B", local, 15, "W"), ("diagnostic:B", gap, 75),
            ("verification", gap, 15, "same_type"), ("verification", gap, 90, "same_type"),
            ("verification", gap, 25, "similar_concept"), ("verification", gap, 105, "similar_concept"),
            ("practice", gap, 5), ("practice", gap, 40), ("practice", gap, 120), ("practice", gap, 35),
            ("retest", gap, 50), ("retest", gap, 70), ("retest", gap, 12), ("retest", gap, 80),
            ("retest", gap, 55), ("retest", gap, 100),
            ("verification", local, 90, "E", "same_type"), ("verification", local, 45, "W", "same_type"),
            ("verification", local, 75, "E", "similar_concept"), ("verification", local, 60, "W", "similar_concept"),
            ("practice", local, 30, "E"), ("practice", local, 75, "W"), ("practice", local, 15, "E"),
            ("practice", local, 90, "W"),
            ("retest", local, 120, "E"), ("retest", local, 105, "W"), ("retest", local, 135, "E"),
            ("retest", local, 50, "W"), ("ist", 6 * 60), ("ist", 15 * 60)]
    for step in plan:
        kind, fn = step[0], step[1]
        if kind == "ist":
            ist("retest", fn)
        elif fn is gap:
            gap(kind, step[2], step[3] if len(step) > 3 else None)
        else:
            local(kind, step[2], step[3], role=step[4] if len(step) > 4 else None)

    lessons = {
        LT: {"title": "Four minutes for every degree",
             "big_idea": "The Earth turns a full 360° in 24 hours. That is 15° every hour, or 4 minutes for every degree "
                         "of longitude. A common slip is to use 15 minutes per degree, which makes every answer far too big.",
             "steps": ["Find how many degrees of longitude apart the places are.", "Multiply by 4 to get minutes.",
                       "Turn the minutes into hours and minutes.", "Check: 15° should always come out as exactly 1 hour."],
             "sense_check": "India spans about 30° of longitude, so the Sun rises about 2 hours earlier in Arunachal "
                            "Pradesh than in Gujarat, not 7½ hours.",
             "worked_examples": [
                 {"prompt": "Two places are 30° of longitude apart. How far apart are their local times?",
                  "answer": "2 hours", "steps": ["30 × 4 = 120 minutes.", "120 minutes = 2 hours."]}]},
        EWT: {"title": "East is ahead, west is behind",
              "big_idea": "The Sun rises in the east, so places to the east of Greenwich have reached later in the day. "
                          "Going east you add time; going west you take time away.",
              "steps": ["Work out the time difference (4 minutes per degree).", "Is the place east (E) or west (W) of Greenwich?",
                        "East: add the difference. West: subtract it.", "India (82°30′E) is 5 hours 30 minutes ahead of Greenwich."],
              "sense_check": "When it is noon in London, offices in India are already open for the afternoon.",
              "worked_examples": [
                  {"prompt": "When it is 12:00 at Greenwich, what is the local time at 45°E?", "answer": "15:00",
                   "steps": ["45 × 4 = 180 minutes = 3 hours.", "45°E is east, so add: 12:00 + 3 hours = 15:00."]}]},
    }
    return {
        "topic": {"id": "time_zones", "subject": "social_science", "name": "Time zones and Indian Standard Time",
                  "unit": "India: size and location", "grade_min": 8, "grade_max": 10,
                  "description": "Working out local times from longitude, and why India uses one standard time.",
                  "objectives": ["Use 4 minutes per degree of longitude", "Add time going east and subtract going west",
                                 "Explain Indian Standard Time (82°30′E)"],
                  "skills": [LT, EWT]},
        "skills": [
            {"id": LT, "name": "Longitude and time difference", "grade": 8, "prerequisites": ["lat_long_meaning"],
             "description": "4 minutes of time for each degree of longitude."},
            {"id": EWT, "name": "East is ahead, west is behind", "grade": 8, "prerequisites": [LT],
             "description": "Adding time to the east and subtracting to the west; IST."}],
        "misconceptions": {
            MIN15: {"label": "Uses 15 minutes per degree instead of 4", "gap_skill": LT,
                    "explanation": "Mixes up 15° per hour with 15 minutes per degree."},
            EAST_BEHIND: {"label": "Thinks places to the east are behind in time", "gap_skill": EWT,
                          "explanation": "Subtracts time when moving east (and adds when moving west)."}},
        "questions": B.items, "lessons": lessons}


ALL = [latitude_longitude, time_zones]
