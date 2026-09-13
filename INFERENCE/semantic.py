"""Semantic hazard typing: which energy is this report about, decided by MEANING.

`knowledge.detect_hazard` is a regex over a finite word list. It cannot know that "methane gas",
"sulphur ki gas", "garam steam", "flowline me crude" or "गैस लीक" are the same energies it already
handles, and every one of those returned no hazard - so question 1 fell to "unknown" and the
verdict to INSUFFICIENT, or hung on a GLiNER span three-thousandths above its threshold.

This layer embeds the report with the multilingual sentence encoder the heads already hold and
compares it to a handful of PROTOTYPE sentences per hazard. Highest cosine similarity above a
floor wins. The prototypes are seeds written by hand, not training data; add one when a real
report is missed. Because the encoder is multilingual, Hindi and Assamese script work without
transliteration.

The trap, measured: raw similarity is dominated by REGISTER, not topic - "Mess me aaj paratha
nahi tha" scored 0.70 against mechanical entanglement because it is a Hinglish workplace sentence
like the prototypes. So the score that counts is the MARGIN over a set of style-matched negative
prototypes (canteen, IT, admin, trivia). On gold-180 + probe: hazard-sim >= 0.45 and margin >=
0.05 types 23 of the 24 precursors that have no regex hazard and fires on 4 of 72 junk rows.

Two honest limits. Similarity says WHICH energy the text is about, not that the energy exceeded
a threshold - the numeric gate in energy.py still decides that when a number is present. And it
offers no span to highlight: the response says `semantic(pressure_release@0.63)` and, when
GLiNER has a weak energy span that agrees, borrows that span as the evidence in the text.

Fault-tolerant like everything else: no encoder -> disabled -> nothing changes.
"""
from __future__ import annotations

import logging

from .config import SEMANTIC_ENABLED, SEMANTIC_MIN_MARGIN, SEMANTIC_MIN_SIM
from .knowledge import HAZARDS

log = logging.getLogger("inference.semantic")

# ---------------------------------------------------------------- prototypes
# Written to sound like the reports, not like a textbook: Hinglish, English, Devanagari, and
# the misspellings that survive normalisation. Keys are HAZARDS keys plus the energies the tree
# had no regex for. The extra keys carry their own knowledge-base entry below.
PROTOTYPES: dict[str, list[str]] = {
    "pressure_release": [
        "pipeline se high pressure gas leak ho raha tha",
        "hydraulic hose phat gaya aur oil pressure se bahar aaya",
        "line depressurise kiye bina flange khola, pressure release hua",
        "compressor discharge line me leakage, pressure 40 kg tha",
        "mud pump ka hose burst ho gaya, high pressure fluid spray hua",
        "pressurised line was opened without isolation and fluid sprayed out",
        "पाइपलाइन में प्रेशर था और वाल्व खोलते ही गैस निकल गई",
    ],
    "chemical_exposure": [
        "methane gas leakage se worker ki aankhon me jalan ho gayi",
        "H2S gas ki smell aayi aur do worker ko chakkar aa gaya",
        "sulphur ki gas se helper ko ulti hone lagi",
        "acid transfer karte waqt chemical splash ho gaya",
        "toxic fumes se worker ko saans lene me dikkat hui",
        "chlorine gas leak, operators evacuated the area",
        "hydrocarbon vapour release near the separator",
        "गैस लीक होने से मज़दूर को सांस लेने में दिक्कत हुई",
        "क्रूड ऑयल का रिसाव हो रहा था और गंध आ रही थी",
    ],
    "electrical_contact": [
        "live panel pe kaam ho raha tha bina isolation ke",
        "worker ko current laga, 440 volt line energised thi",
        "distribution box ki wiring exposed thi aur paani pada tha",
        "welding machine ka cable kata hua tha, worker ne chhua",
        "electrician did LOTO nahi kiya and switchgear was energised",
        "बिजली की लाइन चालू थी और मज़दूर ने तार छू लिया",
    ],
    "fire_explosion": [
        "flare ke paas ghaas me aag lag gayi",
        "battery room me hydrogen jama tha, exhaust fan band tha",
        "diesel tank ke paas smoking kar raha tha worker",
        "generator se dhuan nikal raha tha aur aag lag sakti thi",
        "gas cylinder ke paas welding ki chingari gir rahi thi",
        "fire broke out at the pump house, extinguisher was empty",
        "जनरेटर के पास आग लग गई थी",
    ],
    "hot_work": [
        "bina hot work permit ke welding shuru kar di",
        "grinding ki chingari flammable material pe gir rahi thi",
        "gas cutting near the tank without fire watch",
        "steam line bahut garam thi aur insulation nahi tha, worker ka haath jal gaya",
        "garam surface se contact ho gaya, thermal burn",
    ],
    "dropped_object": [
        "monkey board se tool box neeche gir gaya",
        "derrick se spanner gira, neeche log khade the",
        "crane se load ka ek hissa gir gaya",
        "scaffold se pipe neeche aa gaya, koi barricading nahi thi",
        "an object fell from height onto the rig floor",
        "ऊपर से हथौड़ा गिरा और नीचे मज़दूर खड़ा था",
    ],
    "fall_from_height": [
        "worker 5 meter height pe bina harness ke kaam kar raha tha",
        "scaffold pe guard rail nahi thi, worker edge pe khada tha",
        "ladder se worker neeche gir gaya",
        "roof pe kaam ho raha tha bina fall protection ke",
        "मज़दूर बिना हार्नेस के ऊंचाई पर काम कर रहा था",
    ],
    "confined_space": [
        "tank ke andar entry ki bina gas test ke",
        "vessel me worker gaya, oxygen level check nahi kiya",
        "manhole ke andar kaam, koi standby nahi tha",
        "confined space entry without permit and without BA set",
        "टैंक के अंदर बिना गैस टेस्ट के मज़दूर घुस गया",
    ],
    "mechanical_entanglement": [
        "rotating shaft ka guard nahi tha, worker ka kapda fas gaya",
        "belt aur pulley khule the, haath aa sakta tha",
        "draw works chal raha tha aur worker paas khada tha",
        "conveyor belt me haath fas gaya",
        "घूमती हुई मशीन में मज़दूर का हाथ फंस गया",
    ],
    "vehicle_or_mobile_plant": [
        "truck reverse ho raha tha bina banksman ke, worker peeche khada tha",
        "kohre me convoy tez speed se chal raha tha",
        "forklift ne worker ko takkar maar di",
        "driver ne seat belt nahi lagayi thi, gaadi palat gayi",
        "vehicle skid ho gayi geeli road pe",
        "गाड़ी तेज़ रफ़्तार से आ रही थी और मज़दूर सड़क पर था",
    ],
    "lifting_operation": [
        "crane se load utha rahe the, neeche worker khada tha",
        "sling damaged thi aur 2 ton pipe lift ho raha tha",
        "suspended load ke neeche se worker nikla",
        "winch wire rope fray ho gaya tha lifting ke dauran",
        "क्रेन से लोड उठाते समय नीचे मज़दूर खड़ा था",
    ],
    "excavation": [
        "trench 2 meter gehri thi aur shoring nahi thi",
        "excavation ke andar worker tha, wall collapse ho sakti thi",
        "khudai ke dauran mitti dhah gayi",
        "pit ke kinare pe barricade nahi tha",
    ],
}

# Style-matched NEGATIVES. Same register as the prototypes, no hazard. The margin over the best
# of these is what cancels "this sounds like a Hinglish workplace sentence". None of these rows
# is in the probe set the layer is measured against.
NEGATIVE_PROTOTYPES: list[str] = [
    "Mess me aaj khana late mila, shift walon ko wait karna pada",
    "Printer kharab hai, admin ko bata do",
    "Salary slip portal pe nahi dikh raha",
    "WiFi baar baar disconnect ho raha hai office me",
    "Room ki cleaning aaj nahi hui, housekeeping ko bolna hai",
    "Pantry me chai ke cup khatam ho gaye",
    "Attendance galat absent dikha rahi hai, correct karwa do",
    "Laundry pickup kal nahi hua",
    "Bus ka timing change hua tha, driver ko pata nahi tha",
    "Reimbursement claim abhi tak pending hai",
    "Water dispenser empty hai, refill karwana hai",
    "Meeting room ka projector connect nahi ho raha",
    "Guest house ka AC remote nahi mil raha",
    "ID card ke liye photo submit karni hai",
    "Canteen ka menu board update nahi hua",
    "Leave balance portal pe galat dikha raha hai",
    "what is the name of first women",
    "please send me the report by tomorrow",
    "monthly meeting shifted to Friday afternoon",
    "vehicle allocation list me mera naam update karo",
    "stationery ka stock khatam ho gaya, order karna hai",
    "AC ka remote kharab ho gaya naya lana hoga",
    "कैंटीन में आज खाना देर से मिला",
    "प्रिंटर खराब है, एडमिन को बताना है",
]

# knowledge for the energies HAZARDS has no regex entry for. Same shape as HAZARDS.
EXTRA_HAZARDS: dict[str, dict] = {
    "chemical_exposure": {
        "energy_type": "chemical",
        "barrier": "containment_and_chemical_ppe",
        "consequence": "chemical_burns_or_poisoning",
        "cluster": "CHEMICAL_RELEASE_NO_PPE",
        "lsr": [],
    },
    "fire_explosion": {
        "energy_type": "thermal",
        "barrier": "fire_prevention_and_ventilation",
        "consequence": "fire_or_explosion",
        "cluster": "FIRE_EXPLOSION_NO_CONTROL",
        "lsr": ["hot_work"],
    },
}


def hazard_entry(name: str) -> dict:
    return HAZARDS.get(name) or EXTRA_HAZARDS.get(name) or {}


class SemanticHazard:
    def __init__(self) -> None:
        self.encoder = None
        self.available = False
        self._names: list[str] = []
        self._protos: list[str] = []
        self._matrix = None
        self._neg = None

    def load(self, encoder=None) -> "SemanticHazard":
        if self._matrix is not None or not SEMANTIC_ENABLED:
            return self
        try:
            self.encoder = encoder
            if self.encoder is None:
                from sentence_transformers import SentenceTransformer  # noqa: WPS433
                from .config import ENCODER_DIR  # noqa: WPS433
                self.encoder = SentenceTransformer(str(ENCODER_DIR), device="cpu")
            for name, sents in PROTOTYPES.items():
                for s in sents:
                    self._names.append(name)
                    self._protos.append(s)
            self._matrix = self.encoder.encode(self._protos, normalize_embeddings=True)
            self._neg = self.encoder.encode(NEGATIVE_PROTOTYPES, normalize_embeddings=True)
            self.available = True
            log.info("semantic hazard layer: %d prototypes, %d hazards", len(self._protos), len(PROTOTYPES))
        except Exception as exc:                            # noqa: BLE001
            log.warning("semantic hazard layer not loadable: %s", str(exc)[:160])
            self._matrix = None
        return self

    def match(self, text: str) -> dict | None:
        """Best hazard by cosine similarity, or None when it is below the floor or does not
        clear the style-matched negatives by the margin.
        {'hazard', 'energy_type', 'score', 'margin', 'prototype', 'runner_up'}"""
        if not self.available:
            return None
        try:
            import numpy as np                              # noqa: WPS433
            v = self.encoder.encode([text], normalize_embeddings=True)[0]
            sims = self._matrix @ v
            best: dict[str, tuple[float, str]] = {}
            for name, proto, s in zip(self._names, self._protos, sims):
                if name not in best or s > best[name][0]:
                    best[name] = (float(s), proto)
            ranked = sorted(best.items(), key=lambda kv: kv[1][0], reverse=True)
            (name, (score, proto)), runner = ranked[0], ranked[1] if len(ranked) > 1 else None
            neg = float((self._neg @ v).max())
            margin = score - neg
            if score < SEMANTIC_MIN_SIM or margin < SEMANTIC_MIN_MARGIN:
                return None
            return {"hazard": name, "energy_type": hazard_entry(name).get("energy_type"),
                    "score": round(score, 3), "margin": round(margin, 3), "prototype": proto,
                    "runner_up": ({"hazard": runner[0], "score": round(runner[1][0], 3)} if runner else None)}
        except Exception as exc:                            # noqa: BLE001
            log.warning("semantic hazard inference failed: %s", str(exc)[:140])
            return None


_SEM: SemanticHazard | None = None


def get_semantic(encoder=None) -> SemanticHazard:
    global _SEM                                             # noqa: PLW0603
    if _SEM is None:
        _SEM = SemanticHazard().load(encoder)
    return _SEM
