# SIF-Precursor — Teacher & Student Prompts

Four prompts. The first three run on the **teacher** (frontier model, offline, before demo)
and produce training data for SetFit + GLiNER. The fourth runs on the **on-device** Qwen 4B,
on demand, in the review UI.

Shared rules across all prompts are in §0. Copy that block into every system prompt.

---

## §0 — Shared label spec (paste into every teacher system prompt)

```
You are annotating oil-and-gas field safety observations for an ML training set.
Output ONLY valid JSON matching the schema. No prose, no markdown fences.

TOKEN ROLES (spans must be EXACT substrings of `text`, copied verbatim, case-preserved):
  energy_cue        - words showing an energy source or its size: "70 feet", "11 kV", "H2S", "excavator bucket", "6 m par"
  release_cue       - words showing energy was released / event happened: "dropped", "fell", "gir gaya", "slipped", "swung"
  no_release_cue    - words showing it had NOT happened yet: "not yet dropped", "about to", "abhi tak nahi gira"
  exposure_cue      - words placing a person in the line of fire: "below", "underneath", "standing near", "neeche khada", "inside tank"
  control_present   - a real barrier that was in place and worked: "lanyard caught it", "LOTO verified", "barricaded", "fall arrest engaged"
  control_absent    - a required barrier missing: "no lanyard", "LOTO nahi kiya", "gas test not done", "without harness"
  control_ineffective - barrier present but not working: "harness worn but not clipped", "lanyard not anchored", "isolation not verified"
  pseudo_control    - things people cite as protection that are NOT direct controls: "hard hat", "training given", "signage", "experienced worker", "cone placed"
  negation_cue      - the negation word itself: "no", "not", "nahi", "nahin", "bina", "without"
  outcome_cue       - what actually happened to a person: "no injury", "fracture", "koi chot nahi", "medevaced", "first aid"
  statement_cue     - words marking the statement type: "if", "could", "last month", "during drill", "pichle hafte", "has been rectified"

FOUR QUESTIONS (each is {"value": true|false|"unknown", "span": "<exact substring or null>"}):
  high_energy_present   - energy above SIF threshold present? (fall >= 1.2 m / 4 ft, dropped object >= 680 J (500 ft-lb),
                          >= 50 V, pressurised hydrocarbon line, suspended load, mobile plant near people on foot,
                          >= 65 C / steam, H2S / O2-deficient / LEL, excavation >= 1.5 m, rotating machinery)
  energy_released       - did the energy actually release / did the event happen?
  serious_injury        - did a person sustain a life-altering or fatal injury?  TRUE when the text states any of: fatality;
                          amputation (any, including a fingertip); fracture of any bone EXCEPT a single finger/toe; concussion or
                          loss of consciousness; hospital admission / surgery; 2nd-3rd degree burns; eye injury with vision loss;
                          crush injury to head, chest, abdomen or pelvis; electric shock with cardiac effect; asphyxiation.
                          FALSE for cuts, sprains, bruises, first aid, single finger/toe fracture, 'minor injury', 'no injury'.
                          Apply this list literally - a broken tibia/fibula, a fractured skull, a lost pinky ARE serious injuries.
  direct_control_present - was a DIRECT control (LOTO, guarding, hard barricade, fall arrest, tool lanyard, gas test + entry permit)
                           present AND effective for THIS energy source? PPE, signs, training, cones, experience NEVER count.

BARRIERS (list, one per barrier mentioned or clearly required):
  {"barrier": "<name from taxonomy>", "status": "absent"|"present_effective"|"present_ineffective"|"pseudo", "span": "<exact substring>"}
  taxonomy: energy_isolation, gas_test, entry_permit, fall_arrest, tool_lanyard, drop_zone_barricade, exclusion_zone,
            lifting_plan, hot_work_permit, machine_guard, ptw, ppe (ppe always -> pseudo)

VERDICT (exactly one):
  H_SIF        high energy + released + serious injury
  L_SIF        low energy + serious injury (rare; e.g. fall on same level with fracture)
  P_SIF        high energy + released + NO serious injury + NO effective direct control  (survived by luck)
  EXPOSURE     high energy + NOT released + NO effective direct control  (stop work)
  CAPACITY     high energy + released + effective direct control worked
  SUCCESS      high energy + NOT released + effective direct control present
  LOW_ENERGY   no energy above threshold; worst credible outcome <= medical case
  NON_EVENT    hypothetical / historical / training example / duplicate / no hazard described
  INSUFFICIENT a required question is "unknown" and cannot be safely defaulted

STATEMENT TYPE (exactly one): observed | hypothetical | historical | training_example | corrective_completed | condition_only
  observed        = a person's act or an event that the writer saw or that is in progress ('is being started without...',
                    'slinger standing under the load', 'worker climbing without harness') - MOST observations are this
  historical      = the text REFERS BACK to an earlier incident as background ('last year a man fell here', 'pichle saal',
                    'in 2019 we had a fatality') - NOT an incident report written in the past tense: a report of the
                    incident being described ('the helper was struck and hospitalised') is 'observed'
  condition_only  = a static unsafe condition with NOBODY acting or exposed right now ('open pit without barricade',
                    'guard missing on pump', 'corroded flowline') - if a person is doing something, it is 'observed'
ENERGY TYPES (list, may be empty): gravity | motion | electrical | pressure | thermal | chemical | mechanical | radiation
LIFE-SAVING RULES (list, IOGP names): Energy Isolation | Hot Work | Confined Space | Line of Fire | Working at Height |
  Lifting Operations | Driving | Safe Mechanical Lifting | Bypassing Safety Controls | Work Authorisation | (empty if none)

HARD RULES
- Every span MUST be a verbatim substring of `text`. If you cannot find one, use null. Never paraphrase a span.
- "no injury" is an outcome_cue, NOT a control.
- PPE worn is NEVER direct_control_present = true.
- A negated control ("no lanyard") is control_absent; also tag the negation word as negation_cue.
- "not yet dropped" / "abhi nahi gira" -> energy_released = false, but high_energy_present stays true.
- If the text is hypothetical/historical/training, verdict = NON_EVENT regardless of energy words.
- If corrective action is stated as completed before exposure, statement_type = corrective_completed and
  barriers list still records the original "absent" with span, but verdict considers exposure = unknown.
- Two distinct hazards in one text -> two objects in "events".
- Keep every span at most 12 words long.
```

---

## §1 — GENERATE: write raw-style observations from scratch (teacher)

System = §0 + this:

```
TASK: Write {N} NEW safety observations as an Oil India Limited field supervisor would file them,
then annotate each one with the full schema.

REGISTER STYLE (this is the target distribution — match it, do not "improve" it):
- 8 to 60 words. Median ~25. One or two sentences. Often no full stop.
- {LANG_MIX}: e.g. 45% romanized Hinglish, 10% Devanagari Hindi, 45% Indian English.
- Abbreviations used raw: PTW, LOTO, JSA, SCBA, HSE, BOP, WO, MPT, ESD, PPE, TBT.
- Typos and regional spellings ~15% of rows: "isolaton", "energised", "harnes", "scafolding".
- Outcome usually NOT stated (it's an observation, not an incident).
- Sometimes wrong or missing categorical fields.
- Locations: drill site, rig floor, monkey board, derrick, GGS (group gathering station), OCS, tank farm,
  pump house, pipeline ROW, workshop, well head, mud pit, flare area, ETP, workover rig, crude tank roof.
- Equipment: tong, elevator, slips, kelly, drill collar, hydra crane, Hyva tipper, chain pulley block,
  welding set, grinder, hot tapping machine, MCC panel, 11 kV line, compressor, separator, flowline.

TRAP QUOTA for this batch (each row gets ONE primary trap; distribute evenly):
  negation | hypothetical | historical | corrective_completed | multi_event | contradiction (PPE on but not effective) |
  hinglish_plain | low_energy_with_injury_word | capacity (control worked) | vague (insufficient info) |
  devanagari (row written in Devanagari script) | assamese_mix | india_context (monsoon, wildlife, lightning, road, pilferage) |
  sarcasm_minimising | duplicate_paraphrase (a second wording of another row in this batch) | positive_observation (control worked, SUCCESS)

VERDICT QUOTA: at least 15% each of P_SIF, EXPOSURE, CAPACITY, LOW_ENERGY; at least 5% each of SUCCESS, NON_EVENT, INSUFFICIENT; H_SIF <= 3%.

OUTPUT: JSON array. Each element:
{
  "text": "...",
  "meta": {"site": "...", "location": "...", "activity": "...", "shift": "day|night", "lang": "hinglish|hindi|english|assamese_mix", "trap": "<from quota>"},
  "events": [
    {
      "roles": [{"role": "<role>", "span": "<exact substring>"}],
      "questions": {
        "high_energy_present": {"value": ..., "span": ...},
        "energy_released": {"value": ..., "span": ...},
        "serious_injury": {"value": ..., "span": ...},
        "direct_control_present": {"value": ..., "span": ...}
      },
      "barriers": [...],
      "energy_types": [...],
      "life_saving_rules": [...],
      "statement_type": "...",
      "verdict": "...",
      "rationale_one_line": "<= 25 words, must reference at least one span verbatim"
    }
  ]
}
```

User message (fill the placeholders per batch):

```
N = 40
LANG_MIX = 45% romanized Hinglish, 10% Devanagari, 45% Indian English
SEED EXAMPLES (imitate register, never copy):
{{3-5 gold rows, text only}}
Write and annotate now.
```

Run in batches of 40, ~120 batches for 5k rows. Rotate the seed examples every batch.

---

## §2 — REWIND: turn an IOGP investigation record into the observation filed *before* it (teacher)

System = §0 + this:

```
TASK: You will receive a POST-INVESTIGATION fatal or high-potential incident record (IOGP format).
Rewrite it as the UNSAFE-ACT / UNSAFE-CONDITION observation a field supervisor would have filed
THE MORNING BEFORE the event, when the hazard existed but nothing had happened yet.
Then produce THREE variants and annotate all three.

RULES
- Remove every outcome word (injury, death, medevac, hospital, fatality). The event has NOT happened.
- Keep the same energy source, same missing/failed barrier, same location type, same activity.
- Do NOT reveal the investigation findings ("inadequate supervision" etc.). The observer sees a scene, not a root cause.
- Variant A: terse Indian English, 10-25 words.
- Variant B: romanized Hinglish, 15-40 words.
- Variant C: fuller English, 30-60 words, includes one categorical field wrong or missing.
- Verdict for rewound rows will almost always be EXPOSURE (condition present, not released, control absent)
  or P_SIF if the narrative describes a release that happened without injury. Decide per variant.
- Carry over: life_saving_rule from the record; energy_types inferred from `cause`; barriers inferred from `what_went_wrong`.
- Also emit the ORIGINAL narrative as a fourth annotated row with verdict H_SIF (if number_of_deaths) or P_SIF/CAPACITY (if HiPo).

OUTPUT: JSON object {"source_id": "...", "rows": [<4 annotated rows in the §1 element format>]}
```

User message:

```
IOGP RECORD:
{{one JSON row from fetch_iogp.py}}
Rewind and annotate.
```

---

## §3 — LABEL: annotate existing raw text you did not write (teacher)

Use for: OSHA SIR narratives, register rows you scraped, and any real rows OIL gives you.
System = §0 + this:

```
TASK: Annotate the given safety observation(s). Do NOT rewrite or correct the text.
If the text is too vague to answer a question, use "unknown" and verdict INSUFFICIENT — do not guess.
If the text describes an actual injury, set serious_injury from the text only (do not infer severity).
OUTPUT: JSON array of §1 elements, one per input row, in the same order, each including "input_id".
```

User message:

```
ROWS:
[{"input_id": "...", "text": "..."}, ...]   (batch of 20)
Annotate.
```

---

## §4 — RATIONALE: on-device, on demand (Qwen 4B, llama.cpp)

This is the only prompt that runs on the PSU box. It receives the verdict card the rules already produced;
it must not change anything, only phrase it. Every sentence is checked against the spans afterwards.

System:

```
You write a short plain-language explanation of a safety classification for an HSE officer.
You are given the classification and the exact evidence spans. You MUST NOT add facts, numbers,
hazards, barriers, or outcomes that are not in the evidence. Every sentence must reuse at least one
evidence span verbatim inside double quotes. Write in the same language mix as the report
(Hinglish report -> Hinglish explanation). 3 to 5 sentences. No headings, no bullets, no JSON.
If evidence is marked "inferred", say so ("estimated from ..."). If a question is "unknown", say what is missing.
```

User:

```
REPORT: "{{text}}"
VERDICT: {{verdict}} ({{verdict_plain_name}})
EVIDENCE:
  energy: "{{span}}" -> {{energy_type}}, ~{{joules_range}} J ({{basis}})
  released: "{{span}}" -> {{true/false}}
  injury: "{{span}}" -> {{true/false/unknown}}
  control: "{{span}}" -> {{status}}
  barrier that would change the verdict: {{barrier}} -> would become {{counterfactual_verdict}}
Write the explanation.
```

Post-check in `explain/grounding_check.py`: drop any sentence with no quoted substring that appears in the report
or in the evidence list; if fewer than 2 sentences survive, show the template card instead of the prose.

---

## Two examples of the §1 element format (put these in the system prompt as few-shot)

```json
{
  "text": "Rig floor pe tong ka 5 kg die 8 m upar rakha tha, neeche 2 roustabout kaam kar rahe the, koi lanyard nahi",
  "meta": {"site": "Duliajan", "location": "rig floor", "activity": "tripping", "shift": "day", "lang": "hinglish", "trap": "hinglish_plain"},
  "events": [{
    "roles": [
      {"role": "energy_cue", "span": "5 kg die 8 m upar"},
      {"role": "exposure_cue", "span": "neeche 2 roustabout kaam kar rahe the"},
      {"role": "control_absent", "span": "koi lanyard nahi"},
      {"role": "negation_cue", "span": "nahi"}
    ],
    "questions": {
      "high_energy_present": {"value": true, "span": "5 kg die 8 m upar"},
      "energy_released": {"value": false, "span": "rakha tha"},
      "serious_injury": {"value": false, "span": null},
      "direct_control_present": {"value": false, "span": "koi lanyard nahi"}
    },
    "barriers": [
      {"barrier": "tool_lanyard", "status": "absent", "span": "koi lanyard nahi"},
      {"barrier": "drop_zone_barricade", "status": "absent", "span": "neeche 2 roustabout kaam kar rahe the"}
    ],
    "energy_types": ["gravity"],
    "life_saving_rules": ["Line of Fire"],
    "statement_type": "condition_only",
    "verdict": "EXPOSURE",
    "rationale_one_line": "5 kg at 8 m is ~390 J over two workers with \"koi lanyard nahi\"; stop work."
  }]
}
```

```json
{
  "text": "Worker was wearing full body harness during scaffold work at 6 m but lanyard was not hooked to lifeline. No fall occurred.",
  "meta": {"site": "GGS-4", "location": "scaffold", "activity": "scaffolding", "shift": "day", "lang": "english", "trap": "contradiction"},
  "events": [{
    "roles": [
      {"role": "energy_cue", "span": "6 m"},
      {"role": "pseudo_control", "span": "wearing full body harness"},
      {"role": "control_ineffective", "span": "lanyard was not hooked to lifeline"},
      {"role": "negation_cue", "span": "not"},
      {"role": "no_release_cue", "span": "No fall occurred"},
      {"role": "outcome_cue", "span": "No fall occurred"}
    ],
    "questions": {
      "high_energy_present": {"value": true, "span": "6 m"},
      "energy_released": {"value": false, "span": "No fall occurred"},
      "serious_injury": {"value": false, "span": "No fall occurred"},
      "direct_control_present": {"value": false, "span": "lanyard was not hooked to lifeline"}
    },
    "barriers": [
      {"barrier": "fall_arrest", "status": "present_ineffective", "span": "lanyard was not hooked to lifeline"}
    ],
    "energy_types": ["gravity"],
    "life_saving_rules": ["Working at Height"],
    "statement_type": "observed",
    "verdict": "EXPOSURE",
    "rationale_one_line": "Harness worn is not protection when \"lanyard was not hooked to lifeline\" at 6 m."
  }]
}
```

---

## How the outputs feed the two fine-tunes

| Field in the JSON | Trains |
|---|---|
| `text` + `verdict` (+ `statement_type`) | **SetFit** prefilter (binary: LOW_ENERGY/NON_EVENT vs rest) and statement-type head |
| `text` + `roles[]` spans | **GLiNER** span model (label set = the 11 roles) |
| `questions`, `barriers`, `energy_types`, `life_saving_rules` | **Not trained** — used as gold to unit-test the rules layer (`decide/`) and the LSR mapper |
| `rationale_one_line` | Held out; used to evaluate the on-device rationale against grounding |

`filter_distilled.py` must: verify every span is a substring of `text`; recompute char offsets; drop rows where
the rules layer's verdict from the teacher's own `questions` disagrees with the teacher's `verdict`; enforce trap
and verdict quotas; MinHash-dedupe against gold and test sets.
