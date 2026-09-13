"""Paths, thresholds and the pipeline version stamped into every response."""
from __future__ import annotations

import os
from pathlib import Path

PIPELINE_VERSION = "0.7.0"          # 0.7.0: normalise + semantic hazard typing + harm extraction (see README "Meaning, not strings")

REPO_ROOT = Path(os.getenv("SIF_REPO_ROOT", Path(__file__).resolve().parents[1]))
MODELS_DIR = REPO_ROOT / "SERVER" / "Classfication" / "Models"
BASE_MODELS_DIR = (MODELS_DIR / "RAW") if (MODELS_DIR / "RAW").is_dir() else MODELS_DIR
TUNED_MODELS_DIR = MODELS_DIR / "Tunned"

GLINER_TUNED = TUNED_MODELS_DIR / "gliner_sif"
GLINER_BASE = BASE_MODELS_DIR / "gliner_multi"
HEADS_DIR = TUNED_MODELS_DIR / "sif_heads"
SCOPE_DIR = TUNED_MODELS_DIR / "scope_gate"
ENCODER_DIR = BASE_MODELS_DIR / "sentance_encoder"

# EEI SIF energy thresholds (prompts.md section 0 - keep in step with the training spec)
THRESHOLDS = {
    "gravity_fall_m": 1.2,          # a person falling
    "dropped_object_j": 680.0,      # 500 ft-lb
    "electrical_v": 50.0,
    "temperature_c": 65.0,
    "excavation_depth_m": 1.5,
    "pressure_bar": 7.0,
}
GRAVITY = 9.81

# Routing: how sure the fast lane must be before a heavier layer is called.
FAST_LANE_MIN_CONFIDENCE = 0.75
REVIEW_MAX_CONFIDENCE = 0.55        # below this a human is asked to look
CONFORMAL_ALPHA = 0.10              # 90 % coverage target

# ---- scope gate -----------------------------------------------------------
# A logistic head on the frozen encoder, run BEFORE GLiNER. Rejects text that is not a safety
# observation at all (canteen, IT, payroll). Asymmetric on purpose: a false reject is a dead
# precursor, a false accept only costs review time.
SCOPE_THRESHOLD = 0.90              # reject only when P(out_of_scope) exceeds this
SCOPE_ENABLED = True                # kill switch; the gate never fires when False
# A hard rule span vetoes the gate no matter how confident it is: if the text literally says
# "barricading nahi tha", no classifier gets to throw it away.
SCOPE_VETO_ROLES = ("control_absent", "control_ineffective", "release_cue",
                    "outcome_cue", "pseudo_control")
# Only HAND-WRITTEN rule spans may veto. The corpus-mined lexicon (source "rules:mined") tags
# "housekeeping" as control_absent and "paper" as release_cue; letting those veto the gate is
# how "Room 214 ki cleaning nahi hui" was reaching the tree.
SCOPE_VETO_SOURCES = ("rules", "rules:hazard_lexicon")

# ---- evidence gate ----------------------------------------------------------
# Runs AFTER GLiNER and the heads, BEFORE the tree. The scope gate alone is weak below its hard
# threshold (at 0.95 it catches under half of the probe junk), and anything it lets through
# was reaching the EEI tree, where a single low-score GLiNER span ("AC" as an energy source)
# plus three safety defaults produced EXPOSURE at 0.48 -> human review. A row the gate could
# not reject outright is dismissed as OUT_OF_SCOPE when NOTHING downstream vouches for it:
# no safety-domain word (knowledge.SAFETY_VOCAB), no hard rule span, no numeric energy, no
# confident GLiNER span, and both sentence heads saying "not SIF". ONE corroborating signal
# keeps the row - the asymmetry is the scope gate's. Rows the gate itself vouches for (p_out
# below the soft threshold) are never dismissed here. Measured on the probe set without
# GLiNER: junk sent to review 51 -> 14 of 72, gold-180 precursors lost 0.
EVIDENCE_GATE_ENABLED = True        # kill switch; off -> every row the scope gate passes runs the tree
SCOPE_SOFT_THRESHOLD = 0.35         # p_out below this: the gate vouches, skip the evidence check
GLINER_STRONG_SCORE = 0.80          # a model span at/above this is evidence on its own
# ...but only in a role that says something about the domain. GLiNER will happily tag "remote"
# as a negation or statement marker at 0.9; that is not a reason to keep a row alive.
EVIDENCE_GLINER_ROLES = ("energy_cue", "release_cue", "exposure_cue", "control_present",
                         "control_absent", "control_ineffective", "outcome_cue")
# what a sentence head has to say for the row to count as corroborated. The verdict head is the
# weakest layer here (9 classes, macro_f1 0.47), so a SIF-like label it is not even 40 % sure of
# is noise, not corroboration - on the probe set that floor alone dismisses 3 more junk rows and
# costs nothing on gold-180. The prefilter head needs no floor: a positive prediction is rare
# enough to be worth keeping the row.
EVIDENCE_SIF_LIKE = ("H_SIF", "L_SIF", "P_SIF", "EXPOSURE", "CAPACITY")
EVIDENCE_HEAD_MIN_CONFIDENCE = 0.40
# For the REVIEW decision a head has to be at least this sure of "SIF" before its disagreement
# with a non-SIF tree verdict sends the row to a human. Same idea as above; the prefilter head is
# binary so its floor sits higher (0.5 is a coin flip).
REVIEW_PREFILTER_MIN_CONFIDENCE = 0.60

# ---- generalisation layers (0.7.0) ------------------------------------------
# Field text is misspelt Hinglish and the hazard vocabulary is finite. Three layers make the
# pipeline answer the four questions from MEANING rather than exact strings, each fault-tolerant:
# normalise.py  spelling / variant correction before every regex, with an offset map back
# semantic.py   hazard typing by cosine similarity to prototype sentences, on the encoder the
#               heads already hold - "methane gas", "sulphur ki gas", "garam steam" become an
#               energy without a word list, and in Devanagari too
# harm.py       body part + harm word -> serious_injury and an explanation span
NORMALISE_ENABLED = True
SEMANTIC_ENABLED = True
SEMANTIC_MIN_SIM = 0.45             # cosine floor for the best hazard prototype
SEMANTIC_MIN_MARGIN = 0.05          # ...and it must beat the best style-matched NEGATIVE by this much
SEMANTIC_GLINER_ASSIST_SCORE = 0.50 # a GLiNER energy span at/above this corroborates a semantic match (0.40 tagged "Darwaze")
HARM_ENABLED = True

SPAN_THRESHOLD = 0.60               # GLiNER decision threshold. 0.35 flooded the tree with
                                    # low-confidence control_present spans that flipped EXPOSURE
                                    # -> SUCCESS on gold-180. Recall is worth more than spans.
MAX_TEXT_CHARS = 8000

VERDICTS = ("H_SIF", "L_SIF", "P_SIF", "EXPOSURE", "CAPACITY", "SUCCESS",
            "LOW_ENERGY", "NON_EVENT", "INSUFFICIENT", "OUT_OF_SCOPE")
STATEMENT_TYPES = ("observed", "hypothetical", "historical", "training_example",
                   "corrective_completed", "condition_only")
LANGUAGES = ("english", "hinglish", "hindi", "assamese_mix")

SPAN_ROLES = ("energy_cue", "release_cue", "no_release_cue", "exposure_cue", "no_exposure_cue",
              "control_present", "control_absent", "control_ineffective", "pseudo_control",
              "negation_cue", "outcome_cue", "statement_cue")
