# Offline Teacher Cheatsheet

## Exact output JSON field structure

Each output row is an object:

```json
{
  "text": "...",
  "meta": {"site": "...", "location": "...", "activity": "...", "shift": "day|night", "lang": "hinglish|hindi|english|assamese_mix", "trap": "..."},
  "events": [
    {
      "roles": [{"role": "<role>", "span": "<exact substring>"}],
      "questions": {
        "high_energy_present": {"value": true, "span": "<exact substring or null>"},
        "energy_released": {"value": true, "span": "<exact substring or null>"},
        "serious_injury": {"value": true, "span": "<exact substring or null>"},
        "direct_control_present": {"value": true, "span": "<exact substring or null>"}
      },
      "barriers": [{"barrier": "<taxonomy>", "status": "absent|present_effective|present_ineffective|pseudo", "span": "<exact substring>"}],
      "energy_types": ["gravity|motion|electrical|pressure|thermal|chemical|mechanical|radiation"],
      "life_saving_rules": ["<IOGP name>"],
      "statement_type": "observed|hypothetical|historical|training_example|corrective_completed|condition_only",
      "verdict": "<verdict>",
      "rationale_one_line": "<= 25 words, references at least one span verbatim"
    }
  ]
}
```

## Verdicts

- `H_SIF`: high energy + released + serious injury.
- `L_SIF`: low energy + serious injury.
- `P_SIF`: high energy + released + no serious injury + no effective direct control.
- `EXPOSURE`: high energy + not released + no effective direct control.
- `CAPACITY`: high energy + released + effective direct control worked.
- `SUCCESS`: high energy + not released + effective direct control present.
- `LOW_ENERGY`: no energy above threshold; worst credible outcome <= medical case.
- `NON_EVENT`: hypothetical, historical, training example, duplicate, or no hazard described.
- `INSUFFICIENT`: a required question is unknown and cannot be safely defaulted.

## Span roles

- `energy_cue`: words showing an energy source or its size.
- `release_cue`: words showing energy was released or an event happened.
- `no_release_cue`: words showing it had not happened yet.
- `exposure_cue`: words placing a person in the line of fire.
- `control_present`: a real barrier that was in place and worked.
- `control_absent`: a required barrier missing.
- `control_ineffective`: a barrier present but not working.
- `pseudo_control`: claimed protection that is not a direct control.
- `negation_cue`: the negation word itself.
- `outcome_cue`: what actually happened to a person.
- `statement_cue`: words marking the statement type.

## Statement types

- `observed`: a person's act or an event the writer saw or that is in progress.
- `hypothetical`: a conditional or imagined scenario.
- `historical`: refers back to an earlier incident as background.
- `training_example`: a training, mock, drill, toolbox, or example scenario.
- `corrective_completed`: corrective action is stated as completed before exposure; record the original absent barrier, and exposure is unknown.
- `condition_only`: a static unsafe condition with nobody acting or exposed right now.

## Serious injury

TRUE: fatality; amputation including a fingertip; fracture of any bone except a single finger/toe; concussion or loss of consciousness; hospital admission or surgery; second- or third-degree burns; eye injury with vision loss; crush injury to head, chest, abdomen, or pelvis; electric shock with cardiac effect; asphyxiation.

FALSE: cuts; sprains; bruises; first aid; single finger/toe fracture; minor injury; no injury.

## Hard-reject rules from schema.py

- Every span MUST be a verbatim substring of `text`. If you cannot find one, use null. Never paraphrase a span.
- Keep every span at most 12 words long.
- Barrier aliases are canonicalised as follows: `work_authorisation`, `work_authorization`, `permit`, `permit_to_work`, `sop`, `procedure`, `jsa`, `risk_assessment` -> `ptw`; `toolbox_talk`, `training`, `supervision`, `competent_person` -> `ppe`; `banksman`, `spotter` -> `exclusion_zone`; `harness`, `fall_protection`, `lifeline`, `guardrail`, `edge_protection`, `scaffold_tagging` -> `fall_arrest`; `barricade`, `barrication`, `hard_barricade`, `drop_zone` -> `drop_zone_barricade`; `cordon`, `exclusion` -> `exclusion_zone`; `loto`, `lockout`, `isolation`, `lock_out_tag_out` -> `energy_isolation`; `guard`, `guarding`, `interlock` -> `machine_guard`; `gas_testing`, `gas_detector`, `gas_monitoring` -> `gas_test`; `confined_space_permit`, `confined_space_entry_permit` -> `entry_permit`; `lift_plan`, `lifting_plan_and_rigging`, `rigging`, `sling_inspection` -> `lifting_plan`; `hot_work`, `fire_watch` -> `hot_work_permit`; `tool_tether`, `lanyard` -> `tool_lanyard`.
- A `statement_cue` must contain a marker word for hypothetical, historical, training, or closed-action signals; otherwise it is dropped.
- An `energy_cue` cannot overlap a control span; an energy cue on a control span is dropped.
- A stated serious injury while `serious_injury=false` is a hard reject, except a single finger/toe fracture.
- A verdict recomputed from the four questions by the EEI rules must agree with the teacher's verdict; a mismatch is a hard reject.
- A non-exempt event with no valid role spans is a hard reject.