"""Science topics: concept questions with carefully chosen options. Each wrong option that reflects a
well-documented misconception is mapped to it; other wrong options count as unclassified mistakes."""
from .common import TOPIC_IDS, Bank

TOPIC_IDS["FRC"] = "forces_motion"
TOPIC_IDS["MAT"] = "states_of_matter"

HF, MW, NF, RN = "SCI_HEAVIER_FASTER", "SCI_MASS_WEIGHT", "SCI_MOTION_NEEDS_FORCE", "SCI_REST_NO_FORCE"
PG, BA, DV, SM = "SCI_PARTICLES_GROW", "SCI_BUBBLES_AIR", "SCI_DISSOLVE_VANISH", "SCI_STATE_MASS"

# (prompt, correct, {wrong option: misconception or None}, explanation)
GRAVITY = [
    ("A heavy iron ball and a light iron ball are dropped from the same height at the same time. Ignoring air resistance, which reaches the ground first?",
     "They land at the same time", {"The heavy ball": HF, "The light ball": None},
     "Without air resistance, gravity makes all objects fall with the same acceleration, whatever their mass."),
    ("On the Moon, an astronaut's mass is ___ compared with on Earth.", "the same", {"smaller": MW, "zero": MW},
     "Mass is the amount of matter. It does not change from place to place; only weight changes."),
    ("A bowling ball and a tennis ball are dropped together from a balcony. Air resistance is very small for both. What happens?",
     "They hit the ground at about the same time", {"The bowling ball hits first because it is heavier": HF, "The tennis ball hits first because it is lighter": None},
     "When air resistance is small, objects of different mass fall together."),
    ("Which of these changes when you travel from Earth to the Moon?", "Your weight", {"Your mass": MW, "Both your mass and your weight": MW},
     "Weight is the pull of gravity, which is weaker on the Moon. Mass stays the same."),
    ("Weight is best described as…", "the force of gravity pulling on an object", {"the amount of matter in an object": MW, "how big an object is": None},
     "Weight is a force (measured in newtons). The amount of matter is mass."),
    ("In a vacuum tube with no air, a feather and a coin are dropped together. What happens?", "They land at the same time",
     {"The coin lands first because it is heavier": HF, "The feather floats in the tube": None},
     "With no air, there is no air resistance, so the feather and coin fall together."),
    ("Mass is measured in kilograms. Weight is measured in…", "newtons", {"kilograms": MW, "metres": None},
     "Weight is a force, so it is measured in newtons (N)."),
    ("A 2 kg rock and a 10 kg rock are dropped from a cliff at the same moment. Ignoring air resistance, how do their speeds compare after 1 second?",
     "They are falling at the same speed", {"The 10 kg rock is five times faster": HF, "The 2 kg rock is faster": None},
     "All objects speed up at the same rate under gravity when air resistance is ignored."),
    ("An object has a mass of 6 kg on Earth. What is its mass on the Moon?", "6 kg", {"1 kg": MW, "0 kg": MW},
     "Mass does not change. Its WEIGHT on the Moon is about one sixth of its weight on Earth."),
    ("Why does a crumpled sheet of paper fall faster than a flat sheet of the same paper?", "The flat sheet meets more air resistance",
     {"The crumpled sheet is heavier": HF, "Gravity is stronger on crumpled paper": None},
     "Both sheets have the same mass. The flat sheet has a larger surface, so air slows it more."),
    ("A bag of rice weighs less on the Moon than on Earth. This is because…", "the Moon's gravity is weaker",
     {"the rice has less mass on the Moon": MW, "there is no air on the Moon": None},
     "Weight depends on gravity. The rice's mass is unchanged."),
    ("Galileo is said to have dropped two balls of different mass from a tower. What did he find?", "They landed at almost the same time",
     {"The heavier ball landed much earlier": HF, "The lighter ball landed first": None},
     "Objects of different mass fall at the same rate when air resistance is small."),
    ("If you could stand on Jupiter, which would be true?", "Your weight would be greater and your mass the same",
     {"Your mass would be greater": MW, "Your weight and mass would both stay the same": None},
     "Jupiter's gravity is stronger, so your weight increases. Your mass does not change."),
    ("A hammer and a feather are dropped on the Moon, where there is no air. Which lands first?", "They land at the same time",
     {"The hammer": HF, "The feather": None}, "With no air resistance, both fall with the same acceleration."),
    ("Which quantity stays the same wherever you are in the universe?", "Mass", {"Weight": MW, "Neither": None},
     "Mass is the amount of matter in you, so it does not depend on where you are."),
    ("A big stone and a small stone are dropped off a bridge at the same moment. Ignoring air resistance, which splashes into the river first?",
     "Both at the same time", {"The big stone": HF, "The small stone": None}, "Mass does not change how fast objects fall without air resistance."),
    ("An astronaut weighs 600 N on Earth. Gravity on the Moon is about 1/6 as strong. What is the astronaut's weight on the Moon?",
     "About 100 N", {"600 N": MW, "About 3600 N": None}, "Weight = mass × gravity strength. With 1/6 the gravity, 600 N becomes about 100 N."),
]
FORCES = [
    ("A hockey puck slides across smooth ice after being hit. Why does it slowly stop?", "Friction from the ice slows it down",
     {"The force from the hit gets used up": NF, "Nothing is pushing it any more, so it has to stop": NF},
     "A moving object keeps moving unless a force acts on it. Friction is the force that slows the puck."),
    ("A book is resting on a table. Which is true?", "Gravity pulls it down and the table pushes it up",
     {"There are no forces on it because it is not moving": RN, "Only gravity acts on it": None},
     "Forces act on still objects too. Here they are balanced, so the book does not move."),
    ("In deep space, far from any planet, a moving rocket turns off its engines. What happens to it?",
     "It keeps moving at the same speed in a straight line", {"It slows down and stops": NF, "It starts falling": None},
     "With no friction or gravity, nothing changes its motion, so it keeps going (Newton's first law)."),
    ("A car moves along a straight road at a steady 50 km/h. What is true about the forces on it?",
     "The forward force balances friction and air resistance", {"The forward force must be bigger than the backward forces": NF, "There are no forces on it": None},
     "Steady speed means the forces are balanced. A bigger forward force would make the car speed up."),
    ("A ball rolls across a carpet and stops. What made it stop?", "Friction", {"It ran out of force": NF, "Gravity pulled it backwards": None},
     "A moving ball does not carry a supply of force. Friction from the carpet slows it down."),
    ("A lamp hangs from the ceiling and does not move. Which forces act on it?", "Gravity down and the pull of the cord up, balanced",
     {"No forces, because it is still": RN, "Only the pull of the cord": None}, "Two equal and opposite forces act on the lamp, so it stays still."),
    ("A trolley is pushed and let go on a perfectly frictionless track. Without any more pushing, it will…", "keep moving at the same speed",
     {"slow down and stop": NF, "speed up": None}, "With no friction, no force acts against it, so its speed does not change."),
    ("You are standing still on the floor. Which statement is correct?", "Gravity pulls you down and the floor pushes you up equally",
     {"No forces act on you because you are not moving": RN, "Only the floor pushes on you": None},
     "Being still means the forces are balanced, not that there are none."),
    ("Why does a bicycle slow down when you stop pedalling on a flat road?", "Friction and air resistance act against its motion",
     {"Motion always needs a push to continue": NF, "The bicycle gets heavier": None},
     "Without those backward forces the bicycle would keep rolling. Pedalling only balances them."),
    ("A box sits on the floor without moving. A student says 'There are no forces on the box.' Is the student right?",
     "No: gravity and the floor's push act on it and balance", {"Yes: objects that are still have no forces on them": RN, "No: only gravity acts on it": None},
     "Gravity pulls the box down and the floor pushes up. They balance."),
    ("A spacecraft coasts between planets with its engines off, far from any gravity. What does it need to keep moving at the same speed?",
     "Nothing; it keeps moving on its own", {"Its engines must stay on": NF, "It needs air to push against": None},
     "An object in motion stays in motion unless a force acts on it."),
    ("A puck on an air-hockey table (almost no friction) is tapped once. What happens?", "It glides at nearly constant speed until it hits something",
     {"It slows down quickly because the force of the tap runs out": NF, "It keeps speeding up": None},
     "Almost no friction means almost no force against its motion, so its speed barely changes."),
    ("A picture hangs on a wall without moving. The forces on it are…", "balanced", {"zero; there are no forces": RN, "unbalanced": None},
     "Gravity pulls it down and the nail or hook holds it up with an equal force."),
    ("When a moving object has balanced forces on it, it…", "keeps moving at the same speed in the same direction",
     {"slows down and stops": NF, "speeds up": None}, "Balanced forces do not change motion. Only unbalanced forces do."),
    ("A football rolls on a flat field and stops. If there were no friction or air at all, what would happen?",
     "It would keep rolling at the same speed", {"It would still stop, because the kick's force runs out": NF, "It would speed up": None},
     "Friction and air resistance stop the ball. Without them, nothing would slow it down."),
    ("A cup sits on a table. Why doesn't it fall through the table?", "The table pushes up on it with a force equal to its weight",
     {"There are no forces on it, so it stays still": RN, "Gravity does not act on things on tables": None},
     "The table's upward push balances the cup's weight."),
    ("Two teams pull a rope equally hard and the rope does not move. What is true?", "Two equal forces act in opposite directions",
     {"There are no forces on the rope": RN, "The rope has no weight": None}, "The forces are balanced, so the rope stays still."),
]
PARTICLES = [
    ("When a metal rod is heated, it gets slightly longer. Why?", "Its particles vibrate more and move slightly further apart",
     {"Its particles get bigger": PG, "New particles are made": None}, "Particles do not grow. They move more, so they take up more space."),
    ("What are the bubbles that form inside boiling water?", "Water vapour (water as a gas)", {"Air": BA, "Oxygen and hydrogen": BA},
     "At boiling point, liquid water turns into water vapour inside the liquid. The water is not split into other gases."),
    ("A balloon gets bigger when it is warmed. What happens to the gas particles inside?", "They move faster and push harder on the balloon",
     {"Each particle grows larger": PG, "More particles are created": None}, "Heating makes particles move faster, not grow."),
    ("In which state are particles packed closely in a fixed arrangement?", "Solid", {"Liquid": None, "Gas": None},
     "In a solid, particles are close together and only vibrate in place."),
    ("When water boils in a kettle, the bubbles rising through it contain…", "steam (water vapour)", {"air that was in the water": BA, "heat": None},
     "The big bubbles at boiling are water that has turned into a gas."),
    ("The liquid in a thermometer rises when it gets warmer because…", "its particles move further apart, so it takes up more space",
     {"its particles expand": PG, "more liquid is made": None}, "The liquid expands because its particles spread out, not because each particle gets bigger."),
    ("Compared with a liquid, the particles in a gas are…", "far apart and moving quickly", {"bigger": PG, "not moving at all": None},
     "Gas particles are the same size as in the liquid, but much further apart and faster."),
    ("Water is boiling in an open pan. What happens to the water particles that escape?", "They become a gas and spread into the air",
     {"They break up into oxygen and hydrogen": BA, "They stop existing": None}, "Boiling changes water's state, not what it is made of."),
    ("Railway tracks have small gaps between sections. This is because on hot days…", "the metal expands as its particles move further apart",
     {"the metal particles get bigger": PG, "the metal melts a little": None}, "The particles move more and spread out, so the rail gets longer."),
    ("What is inside the large bubbles in a pot of water at a rolling boil?", "Water in its gas state", {"Air from the room": BA, "Nothing; they are empty": None},
     "The bubbles are water vapour made from the liquid water."),
    ("Ice melts into water. What happens to the water particles?", "They stay the same particles but can now move past each other",
     {"They become smaller particles": PG, "They turn into different particles": None}, "Melting changes how particles are arranged, not their size."),
    ("When a gas is cooled, it takes up less space. This is because…", "its particles slow down and move closer together",
     {"its particles shrink": PG, "some particles are destroyed": None}, "Cooling slows particles down. Their size stays the same."),
    ("Just above the spout of a boiling kettle there is an invisible gas. It is…", "water vapour", {"hot air": BA, "smoke": None},
     "The invisible gas is water vapour. The white cloud further away is tiny droplets formed as it cools."),
    ("A drop of perfume spreads across a room. This shows that gas particles…", "move around and spread out",
     {"grow until they fill the room": PG, "are not moving": None}, "Gas particles move quickly in all directions and mix with the air."),
    ("Bubbles appear in a beaker of water at 100 °C at sea level. They are bubbles of…", "water vapour", {"oxygen": BA, "carbon dioxide": None},
     "At 100 °C water boils: liquid water turns into water vapour."),
    ("Why does a bicycle tyre feel harder on a hot day?", "The air particles inside move faster and hit the tyre walls harder",
     {"The air particles get bigger": PG, "The rubber gets thicker": None}, "Faster particles push harder on the walls, raising the pressure."),
    ("Liquid water and ice are both made of…", "the same water particles, arranged differently",
     {"different particles; ice particles are bigger": PG, "particles that cannot move at all": None},
     "Ice and water are the same substance. In ice the particles are fixed in place but still vibrate."),
]
MASS = [
    ("50 g of sugar is stirred into 200 g of water until it all dissolves. What is the mass of the sugar solution?", "250 g",
     {"200 g": DV, "Between 200 g and 250 g": DV}, "The sugar is still there, spread out as tiny particles. 200 g + 50 g = 250 g."),
    ("A 100 g ice cube melts completely in a closed bag. What is the mass of the water?", "100 g",
     {"More than 100 g": SM, "Less than 100 g": SM}, "Melting changes the state, not the amount of matter. The mass stays 100 g."),
    ("When salt dissolves in water, the salt…", "is still there, broken into tiny particles spread through the water",
     {"disappears and no longer exists": DV, "turns into water": None}, "Dissolving spreads the salt out. You can get it back by evaporating the water."),
    ("A sealed bottle of water is put in a freezer and the water freezes. Compared with before, its mass is…", "the same",
     {"greater, because ice is heavier": SM, "smaller": SM}, "Freezing does not add or remove particles, so mass stays the same."),
    ("Sugar dissolved in tea cannot be seen. How do you know it is still there?", "The tea tastes sweet",
     {"It isn't; dissolved sugar is gone": DV, "The tea changes colour": None}, "The sweet taste shows the sugar particles are still in the tea."),
    ("A 300 g block of chocolate is melted in a closed container. What does the melted chocolate weigh?", "300 g",
     {"Less than 300 g, because liquids weigh less": SM, "More than 300 g": SM}, "Melting does not change mass."),
    ("Seawater is left in a dish in the sun until all the water evaporates. What is left?", "Salt",
     {"Nothing, because the salt disappeared when it dissolved": DV, "Sand": None}, "The dissolved salt was there all along and is left behind."),
    ("20 g of salt is dissolved in 500 g of water. The mass of the salty water is…", "520 g", {"500 g": DV, "480 g": None},
     "Nothing is lost when salt dissolves: 500 g + 20 g = 520 g."),
    ("Ice in a sealed jar melts. What happens to the total mass of the jar and its contents?", "It stays the same",
     {"It increases": SM, "It decreases": SM}, "In a sealed jar nothing gets in or out, and melting does not change mass."),
    ("A spoon of sugar is dissolved in a glass of water. With an extremely powerful microscope, you would see…",
     "sugar particles mixed among the water particles", {"only water particles; the sugar has been destroyed": DV, "bigger water particles": None},
     "The sugar particles separate and spread among the water particles."),
    ("40 g of solid candle wax is melted (none of it burns). How much liquid wax is there?", "40 g",
     {"Less than 40 g": SM, "More than 40 g": SM}, "Changing state does not change mass."),
    ("Why is the mass of a solution equal to the mass of the water plus the mass of what dissolved?",
     "Particles are not created or destroyed when something dissolves", {"Dissolving always adds extra mass": None, "It isn't; the dissolved mass is lost": DV},
     "Every particle is still there, so the masses add up."),
    ("A 250 g bottle of water freezes solid inside a sealed container. What is the mass of the ice?", "250 g",
     {"More than 250 g": SM, "Less than 250 g": SM}, "Freezing changes the state but not the mass."),
    ("10 g of copper sulfate crystals dissolve in 90 g of water. What is the mass of the blue solution?", "100 g",
     {"90 g": DV, "80 g": None}, "90 g + 10 g = 100 g. The crystals are still there, dissolved."),
    ("Water is frozen into ice in a sealed tray. The ice takes up more space. Its mass…", "stays the same",
     {"increases, because it takes up more space": SM, "decreases": SM}, "Ice takes up more space than water but has exactly the same mass."),
    ("Lemonade powder dissolves completely in water. Where did the powder go?", "It is spread through the water as tiny particles",
     {"It vanished": DV, "It became part of the glass": None}, "Dissolved substances are still present, just too spread out to see."),
    ("A beaker of ice weighs 200 g altogether. It is covered so no water can escape and left to melt. Afterwards the scale reads…",
     "200 g", {"Less than 200 g": SM, "More than 200 g": SM}, "No matter got in or out, and melting does not change mass."),
]


def _bank(prefix, items_a, skill_a, hints_a, items_b, skill_b, hints_b):
    B = Bank(prefix)
    its = {skill_a: iter(items_a), skill_b: iter(items_b)}
    hints = {skill_a: hints_a, skill_b: hints_b}
    counter = [0]

    def q(kind, skill, role=None):
        prompt, right, wrongs, expl = next(its[skill])
        opts = [right, *wrongs]
        k = counter[0] % len(opts)           # rotate so the right answer is not always first
        counter[0] += 1
        opts = opts[k:] + opts[:k]
        B.add(kind, skill, "mcq", prompt, right, options=opts,
              patterns={w: c for w, c in wrongs.items() if c}, role=role, hints=hints[skill],
              solution=[expl, f"Answer: {right}."])

    for kind, order in (("diagnostic:A", (skill_a, skill_b, skill_a, skill_b, skill_a)),
                        ("diagnostic:B", (skill_b, skill_a, skill_b, skill_a, skill_b))):
        for s in order:
            q(kind, s)
    for s in (skill_a, skill_b):
        q("verification", s, "same_type"); q("verification", s, "same_type"); q("verification", s, "similar_concept")
        for _ in range(3):
            q("practice", s)
        for _ in range(6):
            q("retest", s)
    return B.items


def forces_motion() -> dict:
    G, F = "gravity_and_weight", "forces_and_motion"
    qs = _bank("FRC", GRAVITY, G, ["Is the question about how much matter (mass) or how hard gravity pulls (weight)?",
                                   "Without air resistance, mass does not change how fast things fall."],
               FORCES, F, ["Does something need a force to keep moving, or only to change its motion?",
                           "Still objects can have forces on them that balance."])
    lessons = {
        G: {"title": "Gravity, mass and weight",
            "big_idea": "Mass is how much matter something has and never changes from place to place. Weight is the "
                        "pull of gravity, measured in newtons. Without air resistance, heavy and light objects fall at the same rate.",
            "steps": ["Mass (kg) = amount of matter. Weight (N) = force of gravity on that matter.",
                      "On the Moon gravity is about 1/6 as strong, so weight drops to about 1/6. Mass stays the same.",
                      "Gravity pulls harder on a heavier object, but it is also harder to speed up, so both fall at the same rate.",
                      "In real life, air resistance can slow light or spread-out objects, like a feather or a flat sheet of paper."],
            "sense_check": "Astronauts on the Moon dropped a hammer and a feather: they landed together, because there is no air there.",
            "worked_examples": [
                {"prompt": "A heavy and a light ball are dropped together with no air resistance. Which lands first?",
                 "answer": "They land at the same time", "steps": ["No air resistance.", "All objects fall with the same acceleration.", "They land together."]},
                {"prompt": "An object's mass is 6 kg on Earth. What is its mass on the Moon?", "answer": "6 kg",
                 "steps": ["Mass is the amount of matter.", "Going to the Moon doesn't remove matter.", "Still 6 kg (only its weight changes)."]}]},
        F: {"title": "Forces and motion",
            "big_idea": "An object does not need a force to KEEP moving; it needs a force to start, stop, speed up, slow "
                        "down or turn. Things slow down on Earth because of friction and air resistance. Still objects usually "
                        "have forces on them that are balanced.",
            "steps": ["Ask: is the motion changing? Only unbalanced forces change motion.",
                      "Moving at a steady speed in a straight line means the forces are balanced.",
                      "Something slowing down has a force against its motion, usually friction or air resistance.",
                      "Something sitting still has balanced forces, like gravity down and a push up from the table."],
            "sense_check": "A puck on ice glides much further than on carpet. Same push, less friction: the push isn't 'used up'.",
            "worked_examples": [
                {"prompt": "A ball rolls across a carpet and stops. What stopped it?", "answer": "Friction",
                 "steps": ["The ball was moving, then slowed down.", "Slowing down needs a force against the motion.", "That force is friction from the carpet."]},
                {"prompt": "A book rests on a table. What forces act on it?", "answer": "Gravity down, the table pushing up",
                 "steps": ["Gravity always pulls the book down.", "The book isn't falling, so something pushes up.", "The table's push balances gravity."]}]},
    }
    return {
        "topic": {"id": "forces_motion", "subject": "science", "name": "Forces and motion", "unit": "Physics",
                  "grade_min": 6, "grade_max": 8,
                  "description": "Mass and weight, falling objects, and why things keep moving or slow down.",
                  "objectives": ["Tell mass and weight apart", "Explain motion with balanced and unbalanced forces"],
                  "skills": [G, F]},
        "skills": [
            {"id": G, "name": "Gravity, mass and weight", "grade": 6, "prerequisites": [],
             "description": "Mass vs weight; objects fall at the same rate without air resistance."},
            {"id": F, "name": "Forces and motion", "grade": 7, "prerequisites": [G],
             "description": "Balanced and unbalanced forces; friction; Newton's first law."}],
        "misconceptions": {
            HF: {"label": "Thinks heavier objects fall faster", "gap_skill": G,
                 "explanation": "Believes mass makes things fall faster, even when air resistance is not involved."},
            MW: {"label": "Confuses mass with weight", "gap_skill": G,
                 "explanation": "Thinks mass changes on the Moon, or that weight is measured in kilograms."},
            NF: {"label": "Thinks a moving object needs a constant force to keep moving", "gap_skill": F,
                 "explanation": "Believes the 'force of the push' gets used up, instead of friction slowing the object."},
            RN: {"label": "Thinks objects at rest have no forces on them", "gap_skill": F,
                 "explanation": "Misses balanced forces, like the table pushing up on a book."}},
        "questions": qs, "lessons": lessons}


def states_of_matter() -> dict:
    P, C = "particle_model", "conservation_of_mass"
    qs = _bank("MAT", PARTICLES, P, ["Think about the particles: do they change size, or do they move and spread out?",
                                     "Boiling changes water into a gas; it does not split water into other substances."],
               MASS, C, ["Were any particles added or taken away?",
                         "Dissolving and changing state don't create or destroy particles."])
    lessons = {
        P: {"title": "States of matter and particles",
            "big_idea": "Everything is made of tiny particles. Heating makes them move faster and spread further apart; "
                        "the particles themselves never get bigger. When water boils, the bubbles are water vapour.",
            "steps": ["Solid: particles close together, vibrating in place.",
                      "Liquid: particles close together but able to slide past each other.",
                      "Gas: particles far apart, moving fast in all directions.",
                      "Heating: particles move faster and spread out, so things expand. Each particle stays the same size.",
                      "Boiling: liquid turns into gas inside the liquid, making bubbles of vapour."],
            "sense_check": "If particles grew when heated, a hot spoon would be made of bigger atoms than a cold one. Atoms don't change size like that.",
            "worked_examples": [
                {"prompt": "Why does a metal rod get longer when heated?", "answer": "Its particles move more and spread apart",
                 "steps": ["Heat gives particles more energy.", "They vibrate more and push slightly apart.", "The rod gets longer; the particles are the same size."]},
                {"prompt": "What is inside the bubbles in boiling water?", "answer": "Water vapour",
                 "steps": ["At 100 °C some liquid water turns into gas.", "That gas forms bubbles that rise.", "The bubbles are water vapour, not air."]}]},
        C: {"title": "Mass is conserved",
            "big_idea": "When something dissolves, melts or freezes, no particles are created or destroyed, so the total "
                        "mass stays the same. Dissolved sugar or salt is still there, just spread out too small to see.",
            "steps": ["List everything you started with and its mass.",
                      "Ask: did anything escape (like a gas) or get added? If not, the total mass stays the same.",
                      "Dissolving: mass of solution = mass of liquid + mass of what dissolved.",
                      "Melting or freezing: the mass does not change, even if the volume does."],
            "sense_check": "Evaporate salty water and salt is left behind. It must have been there the whole time.",
            "worked_examples": [
                {"prompt": "50 g of sugar dissolves in 200 g of water. Mass of the solution?", "answer": "250 g",
                 "steps": ["Nothing escapes.", "The sugar is still there, spread out.", "200 g + 50 g = 250 g."]},
                {"prompt": "A 100 g ice cube melts in a closed bag. Mass of the water?", "answer": "100 g",
                 "steps": ["Melting changes state only.", "No particles are added or lost.", "100 g."]}]},
    }
    return {
        "topic": {"id": "states_of_matter", "subject": "science", "name": "States of matter", "unit": "Chemistry",
                  "grade_min": 5, "grade_max": 8,
                  "description": "The particle model of solids, liquids and gases, and why mass is conserved.",
                  "objectives": ["Explain expansion and boiling with the particle model",
                                 "Explain why mass is conserved when dissolving or changing state"],
                  "skills": [P, C]},
        "skills": [
            {"id": P, "name": "States of matter and particles", "grade": 5, "prerequisites": [],
             "description": "Particle arrangement and movement in solids, liquids and gases."},
            {"id": C, "name": "Mass is conserved", "grade": 7, "prerequisites": [P],
             "description": "Mass stays the same when dissolving, melting or freezing."}],
        "misconceptions": {
            PG: {"label": "Thinks particles themselves grow or shrink", "gap_skill": P,
                 "explanation": "Explains expansion by particles getting bigger instead of moving further apart."},
            BA: {"label": "Thinks the bubbles in boiling water are air or other gases", "gap_skill": P,
                 "explanation": "Believes boiling bubbles are air, or that water splits into oxygen and hydrogen."},
            DV: {"label": "Thinks a dissolved substance disappears", "gap_skill": C,
                 "explanation": "Believes dissolved sugar or salt is gone, so the solution weighs less."},
            SM: {"label": "Thinks mass changes when something melts or freezes", "gap_skill": C,
                 "explanation": "Believes ice weighs more (or less) than the water it melts into."}},
        "questions": qs, "lessons": lessons}


ALL = [forces_motion, states_of_matter]
