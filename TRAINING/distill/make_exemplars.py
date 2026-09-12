"""
Hand-written exemplar rows (§1 element format) -> TRAINING/distill/exemplars.jsonl

They are the few-shot / seed anchors for §1 Generate (rotated into every batch as SEED EXAMPLES) and they
also enter the training set through filter_distilled (source = "exemplar").  Every row is validated with
schema.py before it is written, so a typo in a span fails loudly here instead of silently at training time.

    python -m TRAINING.distill.make_exemplars
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "TRAINING.distill"  # noqa: A001

from ..config import EXEMPLARS  # noqa: E402
from .schema import validate_element  # noqa: E402


def q(he, rel, inj, ctl, he_s=None, rel_s=None, inj_s=None, ctl_s=None):
    return {"high_energy_present": {"value": he, "span": he_s}, "energy_released": {"value": rel, "span": rel_s},
            "serious_injury": {"value": inj, "span": inj_s}, "direct_control_present": {"value": ctl, "span": ctl_s}}


def ev(roles, questions, barriers, energy, lsr, st, verdict, rationale):
    return {"roles": [{"role": r, "span": s} for r, s in roles], "questions": questions,
            "barriers": [{"barrier": b, "status": s, "span": sp} for b, s, sp in barriers],
            "energy_types": energy, "life_saving_rules": lsr, "statement_type": st, "verdict": verdict, "rationale_one_line": rationale}


def row(text, site, location, activity, shift, lang, trap, events):
    return {"text": text, "meta": {"site": site, "location": location, "activity": activity, "shift": shift, "lang": lang, "trap": trap}, "events": events}


EXEMPLARS_LIST = [
    # 1 hinglish_plain / EXPOSURE - rig floor dropped object
    row("Rig floor pe tong ka 5 kg die 8 m upar rakha tha, neeche 2 roustabout kaam kar rahe the, koi lanyard nahi",
        "Duliajan", "rig floor", "tripping", "day", "hinglish", "hinglish_plain",
        [ev([("energy_cue", "5 kg die 8 m upar"), ("exposure_cue", "neeche 2 roustabout kaam kar rahe the"), ("control_absent", "koi lanyard nahi"), ("negation_cue", "nahi")],
            q(True, False, False, False, "5 kg die 8 m upar", "rakha tha", None, "koi lanyard nahi"),
            [("tool_lanyard", "absent", "koi lanyard nahi"), ("drop_zone_barricade", "absent", "neeche 2 roustabout kaam kar rahe the")],
            ["gravity"], ["Line of Fire"], "condition_only", "EXPOSURE", "5 kg at 8 m over two workers with \"koi lanyard nahi\"; stop work.")]),
    # 2 contradiction (PPE on, not effective) / EXPOSURE
    row("Worker was wearing full body harness during scaffold work at 6 m but lanyard was not hooked to lifeline. No fall occurred.",
        "GGS-4", "scaffold", "scaffolding", "day", "english", "contradiction",
        [ev([("energy_cue", "6 m"), ("pseudo_control", "wearing full body harness"), ("control_ineffective", "lanyard was not hooked to lifeline"), ("negation_cue", "not"), ("no_release_cue", "No fall occurred"), ("outcome_cue", "No fall occurred")],
            q(True, False, False, False, "6 m", "No fall occurred", "No fall occurred", "lanyard was not hooked to lifeline"),
            [("fall_arrest", "present_ineffective", "lanyard was not hooked to lifeline")],
            ["gravity"], ["Working at Height"], "observed", "EXPOSURE", "Harness worn is not protection when \"lanyard was not hooked to lifeline\" at 6 m.")]),
    # 3 negation / SUCCESS - confined space entry done right
    row("Tank cleaning at CTF: gas test done, entry permit signed by EIC, attendant standing at manhole, nobody entered without SCBA.",
        "Moran CTF", "crude tank", "tank cleaning", "day", "english", "positive_observation",
        [ev([("energy_cue", "Tank cleaning"), ("control_present", "gas test done"), ("control_present", "entry permit signed by EIC"), ("control_present", "attendant standing at manhole"), ("negation_cue", "nobody")],
            q(True, False, False, True, "Tank cleaning", None, None, "gas test done"),
            [("gas_test", "present_effective", "gas test done"), ("entry_permit", "present_effective", "entry permit signed by EIC")],
            ["chemical"], ["Confined Space"], "observed", "SUCCESS", "Confined space with \"gas test done\" and a signed permit - controls in place.")]),
    # 4 negation trap / LOW_ENERGY -> NON_EVENT style: explicit no exposure
    row("Koi bhi worker confined space me nahi gaya aur na hi koi exposure hua, tank ka kaam kal ke liye postpone.",
        "OCS-2", "tank area", "maintenance", "day", "hinglish", "negation",
        [ev([("negation_cue", "nahi"), ("no_release_cue", "nahi gaya"), ("statement_cue", "postpone"), ("outcome_cue", "na hi koi exposure hua")],
            q(False, False, False, "unknown", None, "nahi gaya", None, None),
            [],
            [], [], "observed", "LOW_ENERGY", "Nobody entered - \"nahi gaya\" - so no exposure to the tank atmosphere.")]),
    # 5 hypothetical / NON_EVENT
    row("Agar separator ka PSV fail ho jaye to operator toxic gas ke exposure me aa sakta hai, isliye PSV testing schedule banana chahiye.",
        "GGS-7", "separator", "operations", "day", "hinglish", "hypothetical",
        [ev([("statement_cue", "Agar"), ("statement_cue", "aa sakta hai"), ("energy_cue", "toxic gas")],
            q(True, False, "unknown", "unknown", "toxic gas", "Agar", None, None),
            [],
            ["chemical", "pressure"], [], "hypothetical", "NON_EVENT", "\"Agar\" marks a hypothetical - no observed event.")]),
    # 6 historical / NON_EVENT
    row("Pichle mahine ek helper bina harness ke monkey board pe chala gaya tha, ab derrickman ko double lanyard issue kar diya gaya hai.",
        "Rig 12", "monkey board", "tripping", "night", "hinglish", "historical",
        [ev([("statement_cue", "Pichle mahine"), ("energy_cue", "monkey board"), ("control_absent", "bina harness"), ("negation_cue", "bina"), ("statement_cue", "kar diya gaya hai")],
            q(True, False, False, False, "monkey board", None, None, "bina harness"),
            [("fall_arrest", "absent", "bina harness")],
            ["gravity"], ["Working at Height"], "historical", "NON_EVENT", "\"Pichle mahine\" - a past event already actioned, not a current observation.")]),
    # 7 corrective_completed / EXPOSURE (initial absent, fixed before work)
    row("LOTO initially not applied on MCC panel feeder; isolation completed and verified by electrician before the mechanic started work.",
        "Duliajan pump house", "MCC panel", "maintenance", "day", "english", "corrective_completed",
        [ev([("energy_cue", "MCC panel feeder"), ("control_absent", "LOTO initially not applied"), ("negation_cue", "not"), ("control_present", "isolation completed and verified"), ("statement_cue", "before the mechanic started work")],
            q(True, False, False, "unknown", "MCC panel feeder", None, None, "isolation completed and verified"),
            [("energy_isolation", "absent", "LOTO initially not applied"), ("energy_isolation", "present_effective", "isolation completed and verified")],
            ["electrical"], ["Energy Isolation"], "corrective_completed", "EXPOSURE", "\"LOTO initially not applied\" then corrected before exposure - record the gap, exposure unknown.")]),
    # 8 multi_event / two events
    row("During hot work at GGS-3 the panel was not isolated and a contract welder entered the restricted zone without HWP while grinding was going on nearby.",
        "GGS-3", "GGS", "hot work", "day", "english", "multi_event",
        [ev([("energy_cue", "panel"), ("control_absent", "not isolated"), ("negation_cue", "not")],
            q(True, False, False, False, "panel", None, None, "not isolated"),
            [("energy_isolation", "absent", "not isolated")],
            ["electrical"], ["Energy Isolation"], "observed", "EXPOSURE", "Panel \"not isolated\" during work - electrical exposure."),
         ev([("energy_cue", "grinding"), ("exposure_cue", "entered the restricted zone"), ("control_absent", "without HWP"), ("negation_cue", "without")],
            q(True, False, False, False, "grinding", None, None, "without HWP"),
            [("hot_work_permit", "absent", "without HWP"), ("exclusion_zone", "absent", "entered the restricted zone")],
            ["thermal"], ["Hot Work", "Work Authorisation"], "observed", "EXPOSURE", "Hot work \"without HWP\" in a hydrocarbon area.")]),
    # 9 low_energy_with_injury_word / LOW_ENERGY
    row("Store keeper cut his finger while opening a carton with a blade, first aid given, back to work.",
        "Engineering stores", "store", "material handling", "day", "english", "low_energy_with_injury_word",
        [ev([("release_cue", "cut his finger"), ("outcome_cue", "first aid given"), ("energy_cue", "blade")],
            q(False, True, False, "unknown", "blade", "cut his finger", "first aid given", None),
            [],
            ["mechanical"], [], "observed", "LOW_ENERGY", "A blade cut with \"first aid given\" - no lethal energy.")]),
    # 10 capacity / CAPACITY - control worked after release
    row("Scaffold pole slipped from the helper's hand at 7 m but the tool lanyard held it, drop zone below was barricaded.",
        "Rig 7", "derrick", "scaffolding", "day", "english", "capacity",
        [ev([("energy_cue", "7 m"), ("release_cue", "slipped from the helper's hand"), ("control_present", "tool lanyard held it"), ("control_present", "drop zone below was barricaded")],
            q(True, True, False, True, "7 m", "slipped from the helper's hand", None, "tool lanyard held it"),
            [("tool_lanyard", "present_effective", "tool lanyard held it"), ("drop_zone_barricade", "present_effective", "drop zone below was barricaded")],
            ["gravity"], ["Line of Fire", "Working at Height"], "observed", "CAPACITY", "Energy released but \"tool lanyard held it\" - control worked.")]),
    # 11 vague / INSUFFICIENT
    row("Isolation ka issue dekha gaya maintenance ke dauran.",
        None, None, "maintenance", None, "hinglish", "vague",
        [ev([("energy_cue", "Isolation ka issue")],
            q("unknown", "unknown", "unknown", "unknown", None, None, None, None),
            [],
            [], ["Energy Isolation"], "observed", "INSUFFICIENT", "\"Isolation ka issue\" gives no energy source, exposure or control detail.")]),
    # 12 devanagari / EXPOSURE
    row("पैनल का LOTO नहीं किया गया था और मेंटेनेंस चालू था, 415 V सिस्टम पर मिस्त्री काम कर रहा था।",
        "Duliajan", "MCC panel", "maintenance", "day", "hindi", "devanagari",
        [ev([("energy_cue", "415 V सिस्टम"), ("control_absent", "LOTO नहीं किया गया था"), ("negation_cue", "नहीं"), ("exposure_cue", "मिस्त्री काम कर रहा था")],
            q(True, False, False, False, "415 V सिस्टम", "काम कर रहा था", None, "LOTO नहीं किया गया था"),
            [("energy_isolation", "absent", "LOTO नहीं किया गया था")],
            ["electrical"], ["Energy Isolation"], "observed", "EXPOSURE", "\"LOTO नहीं किया गया था\" on a live 415 V panel with a person working.")]),
    # 13 devanagari / P_SIF - release without injury
    row("हाइड्रा क्रेन से केसिंग पाइप उठाते समय स्लिंग टूट गई, पाइप जमीन पर गिरा, पास खड़ा हेल्पर बाल-बाल बचा, कोई चोट नहीं।",
        "Rig 9", "pipe rack", "lifting", "day", "hindi", "devanagari",
        [ev([("energy_cue", "केसिंग पाइप"), ("release_cue", "स्लिंग टूट गई"), ("release_cue", "पाइप जमीन पर गिरा"), ("exposure_cue", "पास खड़ा हेल्पर"), ("outcome_cue", "कोई चोट नहीं"), ("negation_cue", "नहीं")],
            q(True, True, False, False, "केसिंग पाइप", "स्लिंग टूट गई", "कोई चोट नहीं", None),
            [("lifting_plan", "absent", "पास खड़ा हेल्पर"), ("exclusion_zone", "absent", "पास खड़ा हेल्पर")],
            ["gravity", "mechanical"], ["Safe Mechanical Lifting", "Line of Fire"], "observed", "P_SIF", "\"स्लिंग टूट गई\" with a helper in the drop zone - survived by luck.")]),
    # 14 assamese_mix / EXPOSURE
    row("Gas test kora hoy ni, tank er bhitore duta lok dhuke geche, attendant bahire nai.",
        "OCS-1", "tank", "tank cleaning", "day", "assamese_mix", "assamese_mix",
        [ev([("control_absent", "Gas test kora hoy ni"), ("negation_cue", "ni"), ("exposure_cue", "tank er bhitore duta lok dhuke geche"), ("control_absent", "attendant bahire nai"), ("negation_cue", "nai")],
            q(True, False, False, False, "tank er bhitore", "dhuke geche", None, "Gas test kora hoy ni"),
            [("gas_test", "absent", "Gas test kora hoy ni"), ("entry_permit", "absent", "attendant bahire nai")],
            ["chemical"], ["Confined Space"], "observed", "EXPOSURE", "Two people inside a tank with \"Gas test kora hoy ni\".")]),
    # 15 assamese_mix / LOW_ENERGY
    row("Pani baradhi ase cellar pit ot, slip hobo pare, barricade lagabo lage.",
        "Kathalguri", "cellar pit", "housekeeping", "day", "assamese_mix", "assamese_mix",
        [ev([("energy_cue", "Pani baradhi ase cellar pit ot"), ("statement_cue", "hobo pare"), ("control_absent", "barricade lagabo lage")],
            q(False, False, False, False, "Pani baradhi ase cellar pit ot", None, None, "barricade lagabo lage"),
            [("exclusion_zone", "absent", "barricade lagabo lage")],
            [], [], "condition_only", "LOW_ENERGY", "Water in the cellar pit - slip hazard, \"barricade lagabo lage\" but no lethal energy.")]),
    # 16 india_context monsoon + vehicle / EXPOSURE
    row("Monsoon me approach road slushy tha, Hyva tipper loaded casing leke rig site ja raha tha without escort, road ke kinare 5 labour paidal chal rahe the.",
        "Tengakhat", "approach road", "transport", "day", "hinglish", "india_context",
        [ev([("energy_cue", "Hyva tipper loaded casing"), ("energy_cue", "approach road slushy tha"), ("control_absent", "without escort"), ("negation_cue", "without"), ("exposure_cue", "road ke kinare 5 labour paidal chal rahe the")],
            q(True, False, False, False, "Hyva tipper loaded casing", None, None, "without escort"),
            [("exclusion_zone", "absent", "road ke kinare 5 labour paidal chal rahe the")],
            ["motion"], ["Driving", "Line of Fire"], "observed", "EXPOSURE", "Loaded tipper on a slushy road \"without escort\" next to 5 workers on foot.")]),
    # 17 india_context wildlife / INSUFFICIENT (biological, no threshold)
    row("Night duty pe GGS-5 ke pump house ke paas cobra dikha, operator ne torch se dekha aur peeche hat gaya, snake catcher ko call kiya.",
        "GGS-5", "pump house", "night operations", "night", "hinglish", "india_context",
        [ev([("energy_cue", "cobra dikha"), ("exposure_cue", "operator ne torch se dekha"), ("control_present", "peeche hat gaya"), ("control_present", "snake catcher ko call kiya")],
            q("unknown", False, False, "unknown", "cobra dikha", None, None, None),
            [],
            ["biological"], [], "observed", "INSUFFICIENT", "Snake near the pump house - \"cobra dikha\" - severity threshold not defined for biological hazards.")]),
    # 18 india_context pilferage / EXPOSURE (hot tapping on ROW)
    row("Pipeline ROW ke paas Ch 21 pe illegal tapping ki koshish mili, live crude line pe fresh clamp aur drill mark, aas paas gaon ke log maujud the.",
        "Naharkatiya-Barauni ROW", "pipeline ROW", "patrol", "day", "hinglish", "india_context",
        [ev([("energy_cue", "live crude line"), ("release_cue", "fresh clamp aur drill mark"), ("exposure_cue", "aas paas gaon ke log maujud the"), ("control_absent", "illegal tapping ki koshish")],
            q(True, False, False, False, "live crude line", None, None, None),
            [("exclusion_zone", "absent", "aas paas gaon ke log maujud the")],
            ["pressure", "thermal"], ["Line of Fire", "Bypassing Safety Controls"], "observed", "EXPOSURE", "Drilled \"live crude line\" with the public around - fire and release potential.")]),
    # 19 sarcasm_minimising / EXPOSURE
    row("Sab kuch 'perfect' tha, sirf ek chhoti si baat thi ki 11 kV line ke neeche hydra ka boom uthaya ja raha tha.",
        "Jodhpur", "well site", "lifting", "day", "hinglish", "sarcasm_minimising",
        [ev([("statement_cue", "sirf ek chhoti si baat thi"), ("energy_cue", "11 kV line"), ("exposure_cue", "11 kV line ke neeche hydra ka boom uthaya ja raha tha")],
            q(True, False, False, False, "11 kV line", None, None, None),
            [("exclusion_zone", "absent", "11 kV line ke neeche hydra ka boom uthaya ja raha tha")],
            ["electrical", "mechanical"], ["Safe Mechanical Lifting", "Line of Fire"], "observed", "EXPOSURE", "\"sirf ek chhoti si baat\" minimises a crane boom under an \"11 kV line\".")]),
    # 20 H_SIF original narrative style (post-investigation, English)
    row("The IP was cleaning the tail pulley of a running conveyor at the ETP without LOTO; his glove was caught and two fingers were amputated.",
        "ETP", "conveyor", "maintenance", "day", "english", "hinglish_plain",
        [ev([("energy_cue", "running conveyor"), ("control_absent", "without LOTO"), ("negation_cue", "without"), ("release_cue", "his glove was caught"), ("outcome_cue", "two fingers were amputated")],
            q(True, True, True, False, "running conveyor", "his glove was caught", "two fingers were amputated", "without LOTO"),
            [("energy_isolation", "absent", "without LOTO"), ("machine_guard", "absent", "running conveyor")],
            ["mechanical"], ["Energy Isolation"], "observed", "H_SIF", "Rotating machinery \"without LOTO\" and \"two fingers were amputated\".")]),
    # 21 L_SIF - same level fall with fracture
    row("Operator slipped on oil spillage near 5 PA and fractured his wrist, no height involved.",
        "5 PA", "shop floor", "walking", "night", "english", "low_energy_with_injury_word",
        [ev([("release_cue", "slipped on oil spillage"), ("outcome_cue", "fractured his wrist"), ("no_release_cue", "no height involved"), ("negation_cue", "no")],
            q(False, True, True, "unknown", None, "slipped on oil spillage", "fractured his wrist", None),
            [],
            ["gravity"], [], "observed", "L_SIF", "Same-level slip with \"fractured his wrist\" - low energy, serious injury.")]),
    # 22 typo-heavy english / EXPOSURE
    row("Emplyee entered excvation 2m dep no shorng, soil was wet after rain, supervisr not present.",
        "Kharsang", "excavation", "civil work", "day", "english", "hinglish_plain",
        [ev([("energy_cue", "excvation 2m dep"), ("exposure_cue", "Emplyee entered excvation"), ("control_absent", "no shorng"), ("negation_cue", "no"), ("pseudo_control", "supervisr not present"), ("negation_cue", "not")],
            q(True, False, False, False, "excvation 2m dep", None, None, "no shorng"),
            [("exclusion_zone", "absent", "no shorng")],
            ["gravity"], ["Line of Fire"], "observed", "EXPOSURE", "Person inside a 2 m wet excavation with \"no shorng\".")]),
    # 23 duplicate_paraphrase pair (a)
    row("Rig 7 pe crane operation ke dauran load swing hua, ek helper kareeb khada tha, tag line use nahi ki.",
        "Rig 7", "pipe rack", "lifting", "day", "hinglish", "duplicate_paraphrase",
        [ev([("energy_cue", "load swing hua"), ("release_cue", "load swing hua"), ("exposure_cue", "ek helper kareeb khada tha"), ("control_absent", "tag line use nahi ki"), ("negation_cue", "nahi")],
            q(True, True, False, False, "load swing hua", "load swing hua", None, "tag line use nahi ki"),
            [("lifting_plan", "absent", "tag line use nahi ki"), ("exclusion_zone", "absent", "ek helper kareeb khada tha")],
            ["gravity", "mechanical"], ["Safe Mechanical Lifting", "Line of Fire"], "observed", "P_SIF", "Swinging load next to a helper with \"tag line use nahi ki\".")]),
    # 24 duplicate_paraphrase pair (b)
    row("Crane se suspended load hilne ki wajah se helper ko hatna pada, Rig 7 morning shift, tagline nahi thi.",
        "Rig 7", "pipe rack", "lifting", "day", "hinglish", "duplicate_paraphrase",
        [ev([("energy_cue", "suspended load"), ("release_cue", "load hilne"), ("exposure_cue", "helper ko hatna pada"), ("control_absent", "tagline nahi thi"), ("negation_cue", "nahi")],
            q(True, True, False, False, "suspended load", "load hilne", None, "tagline nahi thi"),
            [("lifting_plan", "absent", "tagline nahi thi")],
            ["gravity", "mechanical"], ["Safe Mechanical Lifting", "Line of Fire"], "observed", "P_SIF", "\"suspended load\" moved with a helper close by and \"tagline nahi thi\".")]),
    # 25 positive observation SUCCESS with hot work permit
    row("Grinding job at test separator: HWP issued, gas test 0% LEL recorded, fire watch with DCP extinguisher present throughout.",
        "GGS-7", "separator", "hot work", "day", "english", "positive_observation",
        [ev([("energy_cue", "Grinding job at test separator"), ("control_present", "HWP issued"), ("control_present", "gas test 0% LEL recorded"), ("control_present", "fire watch with DCP extinguisher present")],
            q(True, False, False, True, "Grinding job at test separator", None, None, "gas test 0% LEL recorded"),
            [("hot_work_permit", "present_effective", "HWP issued"), ("gas_test", "present_effective", "gas test 0% LEL recorded")],
            ["thermal"], ["Hot Work"], "observed", "SUCCESS", "Hot work with \"HWP issued\" and \"gas test 0% LEL recorded\" - controls present.")]),
    # 26 training example / NON_EVENT
    row("During TBT the safety officer explained a case where a worker entered a tank without gas test and collapsed; this is a training example.",
        "OCS-2", "training room", "toolbox talk", "day", "english", "hypothetical",
        [ev([("statement_cue", "During TBT"), ("statement_cue", "this is a training example"), ("energy_cue", "tank without gas test")],
            q(True, True, True, False, "tank without gas test", "collapsed", "collapsed", "without gas test"),
            [("gas_test", "absent", "without gas test")],
            ["chemical"], ["Confined Space"], "training_example", "NON_EVENT", "\"this is a training example\" - not a field observation.")]),
]


def main() -> int:
    ok, bad = [], []
    for i, el in enumerate(EXEMPLARS_LIST, start=1):
        rowv, probs = validate_element(el, source="exemplar", teacher="claude", model="claude", batch_id="exemplars")
        if rowv:
            ok.append(el)
        else:
            bad.append((i, el["text"][:60], probs))
    for b in bad:
        print("REJECTED", b)
    EXEMPLARS.parent.mkdir(parents=True, exist_ok=True)
    with open(EXEMPLARS, "w", encoding="utf-8") as fh:
        for el in ok:
            fh.write(json.dumps(el, ensure_ascii=False) + "\n")
    print(f"wrote {len(ok)} exemplars -> {EXEMPLARS} ({len(bad)} rejected)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
