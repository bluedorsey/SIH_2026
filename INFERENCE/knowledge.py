"""Safety knowledge base: hazard -> barrier -> consequence, LSR mapping, mass/height defaults.

These are LOOKUPS, not model outputs. `potential_consequence` and `precursor_cluster` in the
response come from here so the pipeline never invents them.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------- hazards
# each hazard: the cues that identify it, the barrier that should be in place,
# what it can do to a person, and the precursor cluster it belongs to.
HAZARDS: dict[str, dict] = {
    "dropped_object": {
        "cues": r"\b(gir(a|i|e)|dropp?ed|fell|falling|neeche gir|upar se|monkey board|derrick|"
                r"tool ?box|spanner|hammer|pipe|casing|elevator|block)\b",
        "energy_type": "gravity",
        "barrier": "exclusion_zone_barricading",
        "consequence": "fatal_head_injury",
        "cluster": "DROPPED_OBJECT_NO_EXCLUSION_ZONE",
        "lsr": ["line_of_fire", "work_at_height"],
    },
    "fall_from_height": {
        "cues": r"\b(harness|lanyard|fall arrest|scaffold|ladder|platform|height|uncha|"
                r"chhat|roof|edge|opening|floor opening)\b",
        "energy_type": "gravity",
        "barrier": "fall_protection",
        "consequence": "fatal_fall",
        "cluster": "WORK_AT_HEIGHT_NO_FALL_ARREST",
        "lsr": ["work_at_height"],
    },
    "electrical_contact": {
        "cues": r"\b(live|kV|volt|电|panel|panl|switchgear|LOTO|lock ?out|isolation|energis\w*|energiz\w*|"
                r"bijli|current|earthing|breaker)\b",
        "energy_type": "electrical",
        "barrier": "energy_isolation",
        "consequence": "electrocution",
        "cluster": "LIVE_WORK_NO_ISOLATION",
        "lsr": ["energy_isolation"],
    },
    "confined_space": {
        "cues": r"\b(confined space|vessel entry|tank entry|manhole|H2S|oxygen|O2|gas test|"
                r"SCBA|BA set|purge|nitrogen)\b",
        "energy_type": "chemical",
        "barrier": "gas_test_and_permit",
        "consequence": "asphyxiation",
        "cluster": "CONFINED_SPACE_NO_GAS_TEST",
        "lsr": ["confined_space"],
    },
    "hot_work": {
        "cues": r"\b(welding|grinding|cutting torch|hot work|spark|flame|naked light|gas cutting)\b",
        "energy_type": "thermal",
        "barrier": "hot_work_permit",
        "consequence": "fire_or_burns",
        "cluster": "HOT_WORK_NO_PERMIT",
        "lsr": ["hot_work"],
    },
    "pressure_release": {
        "cues": r"\b(pressure|psi|bar|kg/cm2|hydro ?test|blow ?out|kick|choke|relief valve|"
                r"pressuris|pressuriz|line break)\b",
        "energy_type": "pressure",
        "barrier": "depressurisation_and_isolation",
        "consequence": "impact_or_fluid_injection",
        "cluster": "PRESSURISED_LINE_NOT_ISOLATED",
        "lsr": ["line_of_fire", "energy_isolation"],
    },
    "mechanical_entanglement": {
        "cues": r"\b(rotating|drum|belt|pulley|auger|tong|spinner|guard|nip point|shaft|"
                r"draw ?works|pump jack)\b",
        "energy_type": "mechanical",
        "barrier": "machine_guarding",
        "consequence": "amputation_or_crush",
        "cluster": "ROTATING_EQUIPMENT_NO_GUARD",
        "lsr": ["safe_mechanical_lifting"],
    },
    "vehicle_or_mobile_plant": {
        "cues": r"\b(vehicle|truck|trailer|forklift|crane|excavator|reversing|banksman|"
                r"gaadi|dumper|loader|convoy|overspeed\w*|speeding|seat ?belt|collision|"
                r"overtak\w*|skid\w*|tyre burst|brake fail\w*)\b",
        "energy_type": "motion",
        "barrier": "traffic_management",
        "consequence": "struck_by_vehicle",
        "cluster": "MOBILE_PLANT_NO_SEGREGATION",
        "lsr": ["driving", "line_of_fire"],
    },
    "lifting_operation": {
        "cues": r"\b(sling|shackle|hook|lifting|suspended load|load ke neeche|rigging|"
                r"crane lift|winch|hoist)\b",
        "energy_type": "gravity",
        "barrier": "lift_plan_and_exclusion_zone",
        "consequence": "struck_by_falling_load",
        "cluster": "SUSPENDED_LOAD_PERSON_UNDERNEATH",
        "lsr": ["safe_mechanical_lifting", "line_of_fire"],
    },
    "excavation": {
        "cues": r"\b(excavat|trench|shoring|pit|digging|khudai|bench(ing)?)\b",
        "energy_type": "gravity",
        "barrier": "shoring_and_benching",
        "consequence": "burial_or_crush",
        "cluster": "EXCAVATION_NO_SHORING",
        "lsr": ["excavation"],
    },
}

# ------------------------------------------------- safety-domain vocabulary
# Words that make a text a SAFETY observation even when no hazard above matches: hazards the
# EEI tree has no energy model for yet, barriers and PPE, emergency infrastructure, site
# vocabulary, and the meta-words people use when they are reporting safety ("unsafe", "khatra",
# "near miss"). The scope and evidence gates use this as the deterministic layer a classifier
# cannot overrule. It is deliberately NOT part of HAZARDS: adding "hathi" or "garmi" there
# would make the tree answer question 1 with "high energy" and turn every UNCERTAIN gold row
# into EXPOSURE. Here it only keeps the row alive; the tree still decides. The corpus-mined
# lexicon is NOT part of it either, because it fires on "paper", "kaam" and "housekeeping".
# (Gold-180 precursors that had NO word in the vocabulary above before 2026-09-12: acid
# transfer without goggles, radiography barricade breach, hydrocarbon smell, battery-room
# ventilation, convoy in fog, DG-set exhaust indoors.)
_HAZARD_VOCAB = (
    # chemical / hydrocarbon
    r"acid|alkali|caustic|corrosive|chemical|solvent|fumes|vapou?rs?|toxic|hydrocarbon|"
    r"benzene|ammonia|chlorine|mercury|crude|condensate|"
    r"(?:gas|hydrocarbon|chemical|diesel|fuel) (?:smell|leak\w*|odou?r)|smell (?:aa|report)|"
    # radiation
    r"radiograph\w*|radiation|radioactive|isotope|gamma|x-?ray|NDT source|"
    # fire / explosion / ventilation
    r"fire|aag|jal (?:rah[ai]|gay[ai]|raha)|flare|explosion|blast|flammable|ignition|smoke|"
    r"dhuan|dhua|burning|hydrogen|battery room|LPG|exhaust|ventilation|DG set|generator|"
    # electrical odds and ends the electrical_contact cues miss
    r"wiring|distribution box|DB box|junction box|live wire|exposed wire|cable|MCB|"
    # process equipment
    r"pump|gland|flange|gasket|hose|compressor|separator|wellhead|manifold|pipeline|seepage|"
    # environment
    r"heat stress|garmi|chakkar|dehydrat\w*|sun ?stroke|lightning|storm|toofan|flood\w*|"
    r"baadh|fog|kohra|kohre|visibility|cyclone|monsoon|"
    # wildlife
    r"hathi|elephant|saanp|snake|jaanwar|janwar|wild animal|leopard|tendua|bees?|wasp|"
    r"madhumakkhi|scorpion|bichhu|dog bite|kutta"
)
_BARRIER_VOCAB = (
    r"harness|lanyard|lifeline|fall arrest|barricad\w*|exclusion zone|permi(?:t|ts|tted|ssion)|PTW|"
    r"unauthori[sz]ed|restricted area|prohibited area|no[- ]entry|non[- ]?permitted|"
    r"authori[sz]ation|trespass\w*|LOTO|"
    r"lock ?out|tag ?out|isolat\w+|gas ?test\w*|SCBA|BA set|guard(?:ing|s|ed)?|banksman|"
    r"spotter|flagman|shoring|earthing|interlock|scaffold\w*|railing|handrail|guardrail|"
    r"toe ?board|helmet|hard ?hat|safety shoes|goggles|face ?shield|gloves|dastane|apron|"
    r"respirator|ear ?plugs?|ear ?muffs?|PPE|reflective jacket|hi-?vis|safety shower|"
    r"eye ?wash|extinguisher|hydrant|gas detector|smoke detector|siren|muster|evacuat\w*|"
    r"ambulance|first ?aid\w*|rescue|emergency|toolbox talk|TBT|JSA|risk assessment|"
    r"work authori[sz]ation|journey management|calibrat\w*|hot work|confined space|induction|"
    r"line of fire|work at height"
)
_SITE_VOCAB = (
    r"rig|drilling|well ?site|wellhead|GGS|OCS|plant area|workshop|substation|refinery|"
    r"tank farm|process area|derrick|monkey ?board|crane|excavation"
)
_META_VOCAB = (
    r"safety|surakshit|suraksha|unsafe|hazard\w*|khatra|khatarnak|incident|accident|"
    r"near ?miss|injur\w+|chot|HSE|behosh|unconscious|bleeding|khoon|jhatka|electric shock|"
    r"current laga|fracture|burn\w*|jal gaya"
)
def _inner(cues: str) -> str:
    """'\\b(a|b)\\b' -> 'a|b' so the hazard cues can be OR-ed into one alternation."""
    cues = cues.strip()
    if cues.startswith(r"\b("):
        cues = cues[3:]
    if cues.endswith(r")\b"):
        cues = cues[:-3]
    return cues


SAFETY_VOCAB = re.compile(
    r"\b(" + "|".join(_inner(h["cues"]) for h in HAZARDS.values())
    + "|" + _HAZARD_VOCAB + "|" + _BARRIER_VOCAB + "|" + _SITE_VOCAB + "|" + _META_VOCAB
    + r")\b", re.I)


def safety_vocab_hit(text: str) -> str | None:
    """The first safety-domain word in the text, or None when there is none."""
    m = SAFETY_VOCAB.search(text)
    return m.group(0) if m else None

_COMPILED = {k: re.compile(v["cues"], re.I) for k, v in HAZARDS.items()}

# ------------------------------------------------- default masses / heights
# Used ONLY when the text gives no number. Every default is reported in the response
# with basis="default_<name>" so a reviewer can see the estimate was not measured.
DEFAULT_MASS_KG = {
    "tool ?box": ("default_toolbox", 4.5),
    "spanner|wrench": ("default_hand_tool", 1.2),
    "hammer": ("default_hammer", 1.5),
    "drill (pipe|collar)": ("default_drill_pipe", 95.0),
    "casing": ("default_casing_joint", 120.0),
    "elevator": ("default_elevator", 180.0),
    "scaffold (pipe|tube)|scaffolding": ("default_scaffold_tube", 12.0),
    "grating": ("default_grating_panel", 25.0),
    "drum|barrel": ("default_drum_200l", 200.0),
    "cargo net": ("default_cargo_net", 750.0),
}
DEFAULT_HEIGHT_M = {
    "monkey ?board": ("default_monkey_board", 20.2),
    "derrick|mast": ("default_derrick", 30.0),
    "rig floor": ("default_rig_floor", 6.0),
    "scaffold": ("default_scaffold", 4.0),
    "platform": ("default_platform", 3.0),
    "ladder": ("default_ladder", 3.0),
    "roof|chhat": ("default_roof", 5.0),
    "first (floor|storey)": ("default_first_floor", 3.5),
}


def detect_hazard(text: str) -> tuple[str | None, dict]:
    """Best-matching hazard by cue count (ties -> the one whose cue appears earliest)."""
    best, best_score, best_pos = None, 0, 10 ** 9
    for name, rx in _COMPILED.items():
        hits = list(rx.finditer(text))
        if not hits:
            continue
        score, pos = len(hits), hits[0].start()
        if score > best_score or (score == best_score and pos < best_pos):
            best, best_score, best_pos = name, score, pos
    return best, (HAZARDS[best] if best else {})


def default_for(text: str, table: dict) -> tuple[str, float] | None:
    for pattern, (basis, value) in table.items():
        if re.search(pattern, text, re.I):
            return basis, value
    return None
