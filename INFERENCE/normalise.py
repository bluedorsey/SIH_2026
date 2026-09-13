"""Spelling and variant normalisation, run BEFORE every regex layer.

Field reports are typed on phones by people writing Hinglish with no fixed spelling: "permited",
"pipline", "leek", "wrkr", "jl gya". A pattern layer that only matches exact strings loses all of
them, and the loss is silent - "manager ko permission nahi thi, non permited area me chala gaya"
was hard-rejected as OUT OF SCOPE with no review, because `\\bpermit\\b` does not match "permited".

Two mechanisms, both deterministic and both explainable:

  1. a table of KNOWN variants (short tokens, where edit distance is meaningless): gya -> gaya,
     nhi -> nahi, pipline -> pipeline. Every entry is listed; nothing is learned.
  2. edit-distance correction of LONGER tokens against the safety vocabulary the pipeline already
     matches on: "barrikading" -> "barricading". Only against a curated list of core safety
     nouns, only for tokens of 7+ letters, distance 1 (2 for 10+), first letter must agree, and
     a stop-list of everyday words that must never be touched ("chala" is not "chota").

The output keeps a character map back to the original text, so every span the pipeline reports
still highlights the words the reporter actually typed. Nothing here can raise: a failure
returns the text unchanged.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import NORMALISE_ENABLED

# ---------------------------------------------------------------- 1. known variants
# short tokens and habitual phone spellings. Keys are matched as whole tokens, case-insensitive.
VARIANTS: dict[str, str] = {
    # Hinglish verbs / particles
    "gya": "gaya", "gyi": "gayi", "gye": "gaye", "gayaa": "gaya",
    "nhi": "nahi", "nai": "nahi", "nahin": "nahi", "nhin": "nahi",
    "rha": "raha", "rhi": "rahi", "rhe": "rahe",
    "hia": "hai", "hogya": "ho gaya", "hogyi": "ho gayi",
    "kam": "kaam",
    "kr": "kar", "krke": "karke", "krna": "karna",
    "chor": "chhod", "chod": "chhod",
    "jl": "jal", "jla": "jala",
    "kahrab": "kharab", "khrab": "kharab",
    "bhut": "bahut", "bht": "bahut",
    "wrkr": "worker", "wrker": "worker", "wroker": "worker",
    "hath": "haath", "haat": "haath",
    "ankh": "aankh", "ankhe": "aankhen", "ankhen": "aankhen", "ankho": "aankhon", "aankho": "aankhon",
    # equipment / hazards
    "pipline": "pipeline", "pipeine": "pipeline", "piplines": "pipeline",
    "gase": "gas", "gass": "gas",
    "leek": "leak", "lik": "leak", "leaking": "leak", "leakge": "leakage",
    "presure": "pressure", "pressur": "pressure",
    "electic": "electric", "eletric": "electric", "elec": "electric",
    "voltag": "voltage", "vlt": "volt",
    "scafolding": "scaffolding", "scafold": "scaffold",
    "harnes": "harness", "harnss": "harness",
    "barricad": "barricade", "baricade": "barricade", "barikade": "barricade", "barrikade": "barricade",
    "permited": "permitted", "permision": "permission", "permisson": "permission",
    "isoltn": "isolation", "isolatn": "isolation", "isoln": "isolation",
    "panl": "panel", "pannel": "panel",
    "crain": "crane", "cran": "crane",
    "vehical": "vehicle", "vechile": "vehicle", "vehcle": "vehicle",
    "weldng": "welding", "fractur": "fracture", "fractue": "fracture",
    "hight": "height", "hieght": "height", "heigth": "height",
    "injurd": "injured", "injry": "injury", "injuri": "injury",
    "bandge": "bandage",
    "safty": "safety", "saftey": "safety", "sefty": "safety",
    "exposd": "exposed", "expsure": "exposure",
    "temprature": "temperature", "temp": "temperature",
}

# ---------------------------------------------------------------- 2. words never corrected
# Everyday Hinglish / English tokens that sit one edit away from a safety word. "chala" must not
# become "chota", "women" must not become anything.
_STOP = set("""
chala chali chale chalo gaya gayi gaye raha rahi rahe kaha kahi kiya kiye liya liye diya diye
tha thi the hai hain mein karke wala wali wale bhi phir fir kuch koi sab aaj kal abhi apna apni
uska uski unka unki jab tab agar lekin magar aur par pe se ko ka ki ke me hua hui hue aaya aayi
aaye dekha dekhi mila mili bola boli laga lagi lage karna karte karta karti hota hoti hote jata
jati jate khana khane pani paani waha wahi yaha yahi kuchh bahut thoda zyada jyada pehle baad
andar bahar upar neeche niche saath sath bina sirf bilkul matlab kyunki isliye bataya batayi
kaam kaafi log logo logon admi aadmi banda bande ladka ladki aurat aadmi baith baithe baitha
subah shaam raat dopahar samay time wagera waise aise jaise kaise kabhi hamesha
women woman name what which where when first last about after before their there these those
other would could should have been were with from they them this that than then also only some
more most very into over under again still while until between because please thanks today
yesterday tomorrow morning evening night people person report reported request update change
""".split())

# ---------------------------------------------------------------- 3. correction targets
# A CURATED list of core safety nouns, not everything the regexes mention. The first version
# lifted targets from the pattern sources and corrected VALID words onto inflected fragments:
# "pichhe" (behind) -> "pichle" (previous) made a forklift near-miss "historical", and
# "discharge" -> "discharged" matched a degraded-control pattern and turned a pump spray into
# SUCCESS. Two gold precursors lost to a spell-checker. Targets are now nouns a reporter can
# only have meant one way, and only tokens of 7+ letters are ever corrected.
CORE_TERMS = """
barricade barricading barricaded exclusion harness lanyard lifeline scaffold scaffolding
ladder platform permitted permission isolation isolated energised energized switchgear
voltage electric electrical electrician confined manhole oxygen nitrogen welding grinding
cutting pressure pressurised pressurized hydraulic compressor separator wellhead manifold
pipeline flowline chemical corrosive hydrocarbon benzene ammonia chlorine methane sulphur
radiography radiation explosion flammable ignition extinguisher hydrogen generator
excavation trenching shoring vehicle forklift trailer reversing banksman collision
overspeed overspeeding lifting rigging shackle suspended conveyor rotating entanglement
machine guarding fracture fractured amputation unconscious hospital hospitalised injured
injury bleeding electrocuted temperature detector respirator goggles helmet gloves
""".split()
_VOCAB: set[str] | None = None


def _vocabulary() -> set[str]:
    global _VOCAB                                          # noqa: PLW0603
    if _VOCAB is None:
        _VOCAB = set(CORE_TERMS) - _STOP
    return _VOCAB


def _edit_distance(a: str, b: str, cap: int) -> int:
    """Damerau-Levenshtein with early exit above `cap`."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev2: list[int] | None = None
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if prev2 is not None and i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        if min(cur) > cap:
            return cap + 1
        prev2, prev = prev, cur
    return prev[-1]


def _correct(token: str) -> str | None:
    """The vocabulary word this token is a misspelling of, or None."""
    low = token.lower()
    if low in VARIANTS:
        return VARIANTS[low]
    if len(low) < 7 or low in _STOP or not low.isalpha():
        return None
    vocab = _vocabulary()
    if low in vocab:
        return None
    # a stem match is not a misspelling ("barricadings" starts with "barricading")
    if any(low.startswith(v) for v in vocab if len(v) >= 6):
        return None
    cap = 1 if len(low) < 10 else 2
    best, best_d = None, cap + 1
    for v in vocab:
        if v[0] != low[0] or abs(len(v) - len(low)) > cap:
            continue
        d = _edit_distance(low, v, cap)
        if d < best_d:
            best, best_d = v, d
            if d == 1:
                break
    return best if best_d <= cap else None


# ---------------------------------------------------------------- the result
@dataclass
class NormText:
    original: str
    text: str
    # for every character of `text`: (start, end) of the original characters it stands for
    back: list[tuple[int, int]] = field(default_factory=list)
    changes: list[dict] = field(default_factory=list)

    def span(self, start: int, end: int) -> tuple[int, int]:
        """Normalised [start, end) -> original [start, end)."""
        if not self.back or start >= end:
            return start, end
        start = max(0, min(start, len(self.back) - 1))
        end = max(start + 1, min(end, len(self.back)))
        return self.back[start][0], self.back[end - 1][1]

    def restore(self, start: int, end: int) -> tuple[int, int, str]:
        s, e = self.span(start, end)
        return s, e, self.original[s:e]


_TOKEN = re.compile(r"[A-Za-zऀ-ॿ]+|\d+(?:[.,]\d+)?|\S", re.UNICODE)


def normalise(text: str) -> NormText:
    if not NORMALISE_ENABLED:
        return NormText(text, text, [(i, i + 1) for i in range(len(text))], [])
    try:
        out: list[str] = []
        back: list[tuple[int, int]] = []
        changes: list[dict] = []
        pos = 0
        for m in _TOKEN.finditer(text):
            # verbatim gap (whitespace / punctuation between tokens)
            for i in range(pos, m.start()):
                out.append(text[i]); back.append((i, i + 1))
            tok = m.group(0)
            fix = _correct(tok) if tok[0].isalpha() and tok.isascii() else None
            if fix and fix.lower() != tok.lower():
                if tok[0].isupper():
                    fix = fix[0].upper() + fix[1:]
                for ch in fix:
                    out.append(ch); back.append((m.start(), m.end()))
                changes.append({"from": tok, "to": fix, "start": m.start(), "end": m.end()})
            else:
                for i in range(m.start(), m.end()):
                    out.append(text[i]); back.append((i, i + 1))
            pos = m.end()
        for i in range(pos, len(text)):
            out.append(text[i]); back.append((i, i + 1))
        return NormText(text, "".join(out), back, changes)
    except Exception:                                       # noqa: BLE001
        return NormText(text, text, [(i, i + 1) for i in range(len(text))], [])
