"""
Central configuration for TRAINING (distillation + fine-tuning).

Paths resolve relative to the repo root (parent of this folder).  Secrets come
from `.env` at the repo root - the seven keys in `.env.example`:

    GEMINI_API, GROQ_API_1, GROQ_API_2, SARVAM_API_1, SARVAM_API_2, OPENROUTER_API_1, OPENROUTER_API_2

Every key becomes a "lane".  Extra keys are auto-discovered: add GEMINI_API_2, GROQ_API_3, SARVAM_API_4 ... to .env
and they are used in order when the previous one hits its daily cap / budget.  Lanes of the same provider share that
provider's rate limits *per account*; two keys only help if they belong to two accounts (identical values are merged).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

TRAINING_DIR = Path(__file__).resolve().parent
REPO_ROOT = TRAINING_DIR.parent
DATA_DIR = REPO_ROOT / "DATA"
PROCESSED_DIR = DATA_DIR / "Processed"
DISTILLED_DIR = DATA_DIR / "distilled"
DISTILLED_RAW_DIR = DISTILLED_DIR / "raw"          # one jsonl + state file per job
MODELS_DIR = REPO_ROOT / "SERVER" / "Classfication" / "Models"
# base (downloaded) models live in Models/RAW since 2026-09-07; older layout had them directly under Models/
BASE_MODELS_DIR = (MODELS_DIR / "RAW") if (MODELS_DIR / "RAW").is_dir() else MODELS_DIR
OUTPUT_MODELS_DIR = MODELS_DIR / "Tunned"            # fine-tuned models: Tunned/gliner_sif, Tunned/sif_heads (base models stay one level up)
CHECKPOINT_DIR = TRAINING_DIR / "checkpoints"
# the prompt spec ships with the runner; a prompts.md at the repo root overrides it if present
PROMPTS_MD = (REPO_ROOT / "prompts.md") if (REPO_ROOT / "prompts.md").is_file() else (TRAINING_DIR / "distill" / "prompts.md")
ENV_FILE = REPO_ROOT / ".env"

TEACHER_INPUT = PROCESSED_DIR / "unified" / "teacher_input.jsonl"
GOLD_JSONL = PROCESSED_DIR / "gold" / "gold.jsonl"
IHM_JSONL = PROCESSED_DIR / "ihm" / "ihm_eval.jsonl"
GLOSSARY_LOOKUP = PROCESSED_DIR / "terms" / "variant_lookup.json"
GLOSSARY_JSON = PROCESSED_DIR / "terms" / "glossary_clean.json"
REGISTER_DIR = PROCESSED_DIR / "register"
EXEMPLARS = TRAINING_DIR / "distill" / "exemplars.jsonl"

PROMPT_VERSION = "prompts.md@2026-09-09-balanced"   # serious-injury list, statement-type rule, Sarvam reasoning off

# --------------------------------------------------------------------------
# Label spec (mirror of prompts.md §0 - keep in sync)
# --------------------------------------------------------------------------
ROLES = [
    "energy_cue", "release_cue", "no_release_cue", "exposure_cue", "control_present", "control_absent",
    "control_ineffective", "pseudo_control", "negation_cue", "outcome_cue", "statement_cue",
]
# GLiNER matches label *names* semantically -> train with natural-language names, keep the mapping
ROLE_TO_GLINER_LABEL = {
    "energy_cue": "energy source",
    "release_cue": "energy released",
    "no_release_cue": "not released yet",
    "exposure_cue": "person exposed",
    "control_present": "control present",
    "control_absent": "control absent",
    "control_ineffective": "control ineffective",
    "pseudo_control": "pseudo control",
    "negation_cue": "negation word",
    "outcome_cue": "outcome",
    "statement_cue": "statement marker",
}
GLINER_LABEL_TO_ROLE = {v: k for k, v in ROLE_TO_GLINER_LABEL.items()}
QUESTIONS = ["high_energy_present", "energy_released", "serious_injury", "direct_control_present"]
BARRIERS = ["energy_isolation", "gas_test", "entry_permit", "fall_arrest", "tool_lanyard", "drop_zone_barricade",
            "exclusion_zone", "lifting_plan", "hot_work_permit", "machine_guard", "ptw", "ppe"]
BARRIER_STATUS = ["absent", "present_effective", "present_ineffective", "pseudo"]
VERDICTS = ["H_SIF", "L_SIF", "P_SIF", "EXPOSURE", "CAPACITY", "SUCCESS", "LOW_ENERGY", "NON_EVENT", "INSUFFICIENT"]
STATEMENT_TYPES = ["observed", "hypothetical", "historical", "training_example", "corrective_completed", "condition_only"]
ENERGY_TYPES = ["gravity", "motion", "electrical", "pressure", "thermal", "chemical", "mechanical", "radiation", "biological", "water"]
LSR_NAMES = ["Energy Isolation", "Hot Work", "Confined Space", "Line of Fire", "Working at Height",
             "Safe Mechanical Lifting", "Driving", "Bypassing Safety Controls", "Work Authorisation"]
TRAPS = ["negation", "hypothetical", "historical", "corrective_completed", "multi_event", "contradiction",
         "hinglish_plain", "low_energy_with_injury_word", "capacity", "vague", "devanagari", "assamese_mix",
         "india_context", "sarcasm_minimising", "duplicate_paraphrase", "positive_observation"]
MAX_SPAN_TOKENS = 12          # GLiNER max_width in gliner_config.json
MAX_TEXT_TOKENS = 380         # GLiNER max_len 384

# --------------------------------------------------------------------------
# Distillation quotas (v2 plan) - final train set of ~12k rows
# --------------------------------------------------------------------------
TARGET_TRAIN_ROWS = 12000
VERDICT_QUOTA = {"EXPOSURE": .25, "P_SIF": .17, "LOW_ENERGY": .17, "CAPACITY": .15, "SUCCESS": .07,
                 "NON_EVENT": .06, "INSUFFICIENT": .06, "H_SIF": .04, "L_SIF": .03}
LANG_MIXES = [  # rotated across §1 batches so the corpus lands near 45/35/10/5/5
    "45% romanized Hinglish, 45% Indian English, 10% Devanagari Hindi",
    "60% romanized Hinglish, 30% Indian English, 10% Devanagari Hindi",
    "40% romanized Hinglish, 30% Indian English, 20% Devanagari Hindi, 10% Assamese-English mix (romanized Assamese words like 'kora nohol', 'ase', 'cholise')",
    "30% romanized Hinglish, 55% Indian English with 20% typo-heavy rows, 15% Devanagari Hindi",
    "45% romanized Hinglish, 15% Indian English, 25% Devanagari Hindi, 15% Assamese-English mix (romanized Assamese words like 'kora nohol', 'ase', 'cholise', 'bhitorot')",
    "50% romanized Hinglish, 20% Indian English, 30% Devanagari Hindi",
]
# Life-Saving Rules that the seed pool barely mentions (relevance audit 2026-09-07) - every §1 batch is told to
# make at least GENERATE_LSR_FOCUS_MIN rows involve each of the two rules rotated in for that batch.
# Relevance audit 2026-09-07: IMCA seeds are offshore-vessel incidents (avg 460 words, 4 % oil&gas vocab) and MSHA label
# rows are mining vocabulary - both still teach energy/control patterns, but they must not dominate the corpus.
SEED_SOURCE_CAPS = {"alert_imca": 150, "msha": 600, "osha_sir": 1000}   # per-source cap on rewind / label seeds (shortest IMCA rows kept)
LSR_FOCUS_ROTATION = ["Energy Isolation", "Confined Space", "Hot Work", "Work Authorisation", "Bypassing Safety Controls", "Driving"]
GENERATE_LSR_FOCUS_MIN = 4
INDIC_HEAVY_MIXES = [2, 4, 5]        # indices into LANG_MIXES with Devanagari/Assamese; these batches are scheduled first so
                                     # the (small) Sarvam budget is spent where the Indic-tuned model matters most
GENERATE_ROWS_PER_BATCH = 20          # 40 blows past the 8k output limit on most free tiers
GENERATE_TOTAL_ROWS = 10000       # raised from 4500: Hinglish/Devanagari/Assamese rows come only from §1 + rewind B/A
REWIND_SEEDS_PER_REQUEST = 3          # 3 seeds -> 12 rows per call (1 on Groq: 6k TPM)
LABEL_ROWS_PER_BATCH = 20
NEAR_DUP_JACCARD = 0.70               # stricter than CLEANING (0.85): generated paraphrases must not leak into test

# OIL-specific context appended to the §1 system prompt
OIL_CONTEXT = """
OIL INDIA CONTEXT (use these, mixed with the generic lists above):
- Sites: Duliajan, Moran, Digboi, Naharkatiya, Kathalguri, Tengakhat, Jodhpur (Rajasthan), Kharsang (Arunachal), Rajasthan field, KG basin
- Installations: GGS (group gathering station), OCS (oil collecting station), CTF, ETP, QPS, gas compressor station, LPG recovery plant,
  crude tank farm, tank roof, pump house, flare pit, well plinth, cellar pit, workover rig, drilling rig, rig floor, monkey board,
  derrick, mud pit, pipeline ROW (Naharkatiya-Barauni crude line), SV station, pig launcher, water injection plant
- Equipment: hydra crane, Hyva tipper, poclain/JCB, bolero, bowser, chain pulley block, tirfor, web sling, D-shackle, welding set,
  grinder, gas cutting set, DB box, ELCB, extension board, scaffolding, jhoola, SCBA, gas detector, fire monitor, BOP, tong, elevator, slips
- Environment: monsoon flooding, slushy approach road, NH-37 road transport at night, lightning, snakes/elephants/bees, remote night duty,
  public interference / hot-tapping pilferage on ROW, bandh, high humidity
- People: EIC, I/C, shift in-charge, TP, contractor party, mistri, helper, roustabout, derrickman, driller, operator, security (CISF)
- Abbreviations used raw: PTW, HWP, CSE, JSA, HIRA, TBT, SOP, PPE, LOTO, MSDS, SWL, TPI, ESD, PSV, NRV, H2S, LEL, GGS, OCS, ROW, HSE, OISD
"""

# --------------------------------------------------------------------------
# Backends - every entry that finds its key in .env becomes a lane
# OpenAI-style chat/completions everywhere so one client serves all of them.
# --------------------------------------------------------------------------
BACKENDS = {
    "sarvam": {
        "env_keys": ["SARVAM_API_1", "SARVAM_API_2"],
        "base_url": "https://api.sarvam.ai/v1",
        "auth": "sarvam",                          # header: api-subscription-key
        "model": "sarvam-105b",
        "rpm": 40, "tpm": 400_000,
        "budget_inr": 95,                          # per key: Rs 100 free signup credit, keep a Rs 5 margin
        "max_output_tokens": 8192,
        "rows_per_batch": 12, "seeds_per_request": 2,
        "supports_json_mode": False,
        # sarvam-105b "thinks" by default and the thinking counts against max_tokens (the pilot burned all 8192 tokens
        # on reasoning and returned no JSON) -> reasoning off; 12 rows per batch keeps the visible answer well inside the cap
        "extra_body": {"reasoning_effort": None},
        "notes": "tuned for Indian languages; Rs 29.28/73.2 per 1M in/out -> ~Rs 0.6 per 20-row batch, ~150 batches per Rs 100 key; "
                 "the lane parks itself when the estimated spend reaches budget_inr",
    },
    "gemini": {
        "env_keys": ["GEMINI_API"],
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "auth": "bearer",
        "model": "gemini-2.5-flash",
        "fallback_models": ["gemini-2.5-flash-lite", "gemini-3-flash-preview", "gemini-3.1-flash", "gemini-3-flash", "gemini-3.1-flash-lite"],
        # each Gemini model has its OWN free-tier daily bucket -> one key becomes one lane per model.
        # 2026-09: 2.0-flash is retired and accounts created recently get "2.5-flash is no longer available to new
        # users" -> backends.py lists /models with each key and keeps only the flash models that key can actually use
        "split_model_lanes": True,
        "discover_models": True,
        "model_limits": {"gemini-2.5-flash": {"rpm": 9, "rpd": 250, "tpm": 240_000},
                         "gemini-2.5-flash-lite": {"rpm": 14, "rpd": 1000, "tpm": 240_000}},
        "rpm": 9, "tpm": 240_000, "rpd": 250,
        "max_output_tokens": 16384,
        "rows_per_batch": 20, "seeds_per_request": 3,
        "supports_json_mode": True,
        "notes": "free tier 2.5-flash ~10 RPM / 250-500 RPD / 250k TPM (check AI Studio dashboard); the 429 handler "
                 "learns the real cap; prompts may be used for training - synthetic/public text only",
    },
    "openrouter": {
        "env_keys": ["OPENROUTER_API_1", "OPENROUTER_API_2"],
        "base_url": "https://openrouter.ai/api/v1",
        "auth": "bearer",
        # the ':free' roster rotates - backends.py re-discovers live ids at start-up; these are the 2026-09 defaults
        "model": "inclusionai/ling-3.0-flash-sante:free",
        "fallback_models": ["dots-studio/dots-3-note-preview:free", "nvidia/nemotron-3.5-lightning:free", "thinkingmachines/inkling-small:free"],
        "extra_body": {"reasoning": {"enabled": False}},   # nemotron answered with "Here's a thinking process:" and ran out of tokens
        "timeout": 300,
        "rpm": 15, "tpm": 200_000, "rpd": 50,
        "max_output_tokens": 8192,
        "rows_per_batch": 10, "seeds_per_request": 2,
        "supports_json_mode": False,
        "notes": ":free models = 50 requests/day per account without credits (1000/day once $10 credits were ever bought); "
                 "safety net + Rs0 pilot",
    },
    "groq": {
        "env_keys": ["GROQ_API_1", "GROQ_API_2"],
        "base_url": "https://api.groq.com/openai/v1",
        "auth": "bearer",
        "model": "openai/gpt-oss-120b",
        "fallback_models": ["openai/gpt-oss-20b", "llama-3.3-70b-versatile", "moonshotai/kimi-k2-instruct", "qwen/qwen3-32b"],
        "discover_models": True,
        # tokens-per-DAY buckets are per model -> one key becomes three lanes (200k + 500k + 100k tokens/day)
        "split_model_lanes": True,
        "model_limits": {"openai/gpt-oss-120b": {"rpm": 25, "tpm": 8_000, "rpd": 900, "tpd": 200_000},
                         "openai/gpt-oss-20b": {"rpm": 25, "tpm": 8_000, "rpd": 900, "tpd": 200_000},
                         "moonshotai/kimi-k2-instruct": {"rpm": 25, "tpm": 10_000, "rpd": 900, "tpd": 300_000},
                         "qwen/qwen3-32b": {"rpm": 50, "tpm": 6_000, "rpd": 900, "tpd": 500_000},
                         "llama-3.3-70b-versatile": {"rpm": 25, "tpm": 12_000, "rpd": 900, "tpd": 100_000}},
        "rpm": 25, "tpm": 6_000, "rpd": 900, "tpd": 200_000,
        "max_output_tokens": 4096,
        "rows_per_batch": 5, "seeds_per_request": 1,
        "supports_json_mode": True,
        "notes": "free tier is capped per DAY in tokens (gpt-oss-120b 200k, qwen3-32b 500k, llama-3.3-70b only 100k) -> "
                 "tiny batches, ~40-100 small requests/day per key; second-teacher / agreement sample",
    },
}

# ---- optional extra free tiers (only used when a key is present in .env) -------------------------------------
BACKENDS.update({
    "nvidia": {   # build.nvidia.com - 40 RPM, no daily token cap, ~80 models, no card (phone verification at signup)
        "env_keys": ["NVIDIA_API_1"],
        "base_url": "https://integrate.api.nvidia.com/v1",
        "auth": "bearer",
        "model": "deepseek-ai/deepseek-v4-flash-0731",
        "fallback_models": ["mistralai/mistral-large-2-instruct", "moonshotai/kimi-k3",
                            "meta/llama-3.3-70b-instruct", "nvidia/llama-3.3-nemotron-super-49b-v1"],
        "discover_models": True,               # ids rotate: backends.py lists /v1/models at start-up and keeps live ones
        "rotate_models": True,                 # one 40-RPM quota for ALL models -> round-robin them for teacher diversity
        "rpm": 30, "tpm": 400_000,
        "timeout": 600,                        # kimi-k3 needs 3-5 min for a batch; the first run timed out at 180 s
        "max_output_tokens": 5000,
        "rows_per_batch": 8, "seeds_per_request": 1,
        "supports_json_mode": False,
        "notes": "best free volume lane for rewind/label - 40 RPM shared across models, no daily cap",
    },
    "mistral": {  # api.mistral.ai Experiment plan - 1 req/s, 500k tokens/min, 1B tokens/month, all free-tier models
        "env_keys": ["MISTRAL_API_1"],
        "base_url": "https://api.mistral.ai/v1",
        "auth": "bearer",
        "model": "mistral-small-latest",
        "fallback_models": ["mistral-medium-latest", "magistral-small-latest", "open-mistral-nemo"],
        "discover_models": True,
        "rpm": 40, "tpm": 450_000,
        "max_output_tokens": 8192,
        "rows_per_batch": 12, "seeds_per_request": 2,
        "supports_json_mode": False,
        "notes": "1B tokens/month free - second workhorse next to Gemini",
    },
    "cerebras": { # api.cerebras.ai free - ~5 RPM, 30k TPM, 1M tokens/day, whole request capped at 8k tokens -> tiny batches
        "env_keys": ["CEREBRAS_API_1"],
        "base_url": "https://api.cerebras.ai/v1",
        "auth": "bearer",
        "model": "gpt-oss-120b",
        "fallback_models": ["zai-glm-4.7", "llama-3.3-70b", "qwen-3-235b-a22b-instruct-2507"],
        "discover_models": True,
        "rpm": 4, "tpm": 28_000, "tpd": 950_000,
        "max_output_tokens": 2500,
        "rows_per_batch": 4, "seeds_per_request": 1,
        "supports_json_mode": False,
        "notes": "8k-token request cap -> 4-row batches; good for label / agree",
    },
})

# preferred backend chain per job (first that has a key and is not exhausted wins; failover down the list)
JOB_CHAINS = {
    "generate": ["sarvam", "gemini", "mistral", "nvidia", "openrouter", "groq"],
    "rewind": ["gemini", "nvidia", "mistral", "sarvam", "openrouter", "groq", "cerebras"],
    "label": ["gemini", "nvidia", "mistral", "groq", "cerebras", "sarvam", "openrouter"],
    "agree": ["groq", "cerebras", "openrouter", "nvidia", "mistral", "gemini"],
}


def load_env(path: Path = ENV_FILE) -> dict[str, str]:
    """Tiny .env reader (no python-dotenv dependency). Environment variables override the file."""
    out: dict[str, str] = {}
    if path.is_file():
        for ln in path.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln:
                continue
            k, v = ln.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    known = {k for b in BACKENDS.values() for k in b["env_keys"]}
    for k in list(out) + sorted(known) + [k for k in os.environ if _KEY_RE.match(k)]:
        if os.environ.get(k):
            out[k] = os.environ[k]
    out = {k: v for k, v in out.items() if v}
    for k, v in list(out.items()):
        m = _KEY_RE.match(k)
        pre = _KEY_PREFIX.get(m.group(1).lower()) if m else None
        if pre and not v.startswith(pre) and not v.lower().startswith("bearer"):
            out[k] = pre + v                       # "GQ5zz..." pasted without the nvapi- prefix
        elif v.lower().startswith("bearer "):
            out[k] = v[7:].strip()                 # "Bearer nvapi-..." pasted from a curl example
    return out


_KEY_RE = re.compile(r"^(GEMINI|GROQ|SARVAM|OPENROUTER|NVIDIA|MISTRAL|CEREBRAS)(?:_API|_KEY|_API_KEY)?(?:_(\d+))?$")
_KEY_PREFIX = {"nvidia": "nvapi-"}     # provider keys that always start with a fixed prefix (pasted without it -> added back)


def env_keys_for(backend: str, env: dict[str, str]) -> list[str]:
    """Every key in .env for this provider, in order: PROVIDER_API, PROVIDER_API_1, _2, _3 ...  (add as many as you like).
    Two entries holding the SAME value are one account - the duplicate is dropped so its quota is not counted twice."""
    found = []
    for k, v in env.items():
        m = _KEY_RE.match(k)
        if m and m.group(1).lower() == backend and v:
            found.append((int(m.group(2)) if m.group(2) else 0, k))
    keys, seen = [], set()
    for _, k in sorted(found):
        if env[k] in seen:
            continue
        seen.add(env[k])
        keys.append(k)
    return keys


def available_lanes(env: dict[str, str] | None = None) -> list[dict]:
    """[{backend, lane, key, ...backend config}] for every key present (auto-discovered from .env, not just env_keys)."""
    env = env or load_env()
    lanes = []
    for name, cfg in BACKENDS.items():
        for i, ek in enumerate(env_keys_for(name, env), start=1):
            base = {"backend": name, "lane": f"{name}#{i}", "env_key": ek, "key": env[ek], **cfg}
            if cfg.get("split_model_lanes"):
                # one lane per model, each with its own rpm/rpd/tpd counters (the quotas are per model)
                for m in [cfg["model"], *cfg.get("fallback_models", [])]:
                    lane = dict(base, model=m, fallback_models=[], lane=f"{name}#{i}:{m.split('/')[-1]}")
                    lane.update(cfg.get("model_limits", {}).get(m, {}))
                    lanes.append(lane)
            else:
                lanes.append(base)
    return lanes
