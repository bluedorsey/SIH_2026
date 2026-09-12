# Distilled data report

- dedupe / leak guard: {'exact_or_near_dups': 5220, 'leaks_vs_gold_ihm': 6, 'threshold': 0.7}
- train 3210 rows, dev 384, test 408 (seed-grouped, stratified by verdict x language)

## Train set vs plan

| verdict | rows | target | shortfall |
|---|---|---|---|
| EXPOSURE | 1003 | 3000 | 1997 |
| P_SIF | 682 | 2040 | 1358 |
| LOW_ENERGY | 466 | 2040 | 1574 |
| CAPACITY | 204 | 1800 | 1596 |
| SUCCESS | 249 | 840 | 591 |
| NON_EVENT | 240 | 720 | 480 |
| INSUFFICIENT | 81 | 720 | 639 |
| H_SIF | 167 | 480 | 313 |
| L_SIF | 118 | 360 | 242 |

- language share: {'english': 0.516, 'devanagari': 0.09, 'hinglish': 0.341, 'assamese_mix': 0.053} (plan: hinglish .45 / english .35 / devanagari .10 / assamese .05)
- post-injury share (H_SIF+L_SIF): 0.089 (cap 0.06)
- rows with spans: 3200 / 3210, avg spans per row 3.3
- roles: {'energy_cue': 2849, 'exposure_cue': 1770, 'control_absent': 1725, 'release_cue': 1383, 'negation_cue': 802, 'outcome_cue': 802, 'control_present': 567, 'no_release_cue': 245, 'pseudo_control': 227, 'control_ineffective': 108, 'statement_cue': 102}
- Life-Saving Rules: {'Line of Fire': 795, 'Energy Isolation': 437, 'Safe Mechanical Lifting': 430, 'Working at Height': 331, 'Driving': 232, 'Work Authorisation': 231, 'Hot Work': 231, 'Confined Space': 157, 'Bypassing Safety Controls': 154}
- traps: {'original': 461, 'rewind_A': 299, 'rewind_B': 292, 'low_energy_with_injury_word': 271, 'hinglish_plain': 258, 'rewind_C': 256, 'none': 211, 'historical': 126, 'positive_observation': 108, 'capacity': 97, 'hypothetical': 79, 'vague': 72, 'india_context': 66, 'corrective_completed': 66, 'multi_event': 60, 'negation': 53, 'condition_only': 52, 'sarcasm_minimising': 44, 'contradiction': 41, 'bypassing_safety_controls': 39, 'devanagari': 38, 'assamese_mix': 26, 'bypassing': 24, 'training_example': 23, 'driving': 21, 'low_energy_sif': 8, 'correction_completed': 7, 'duplicate_paraphrase': 6, 'correctional_completed': 5, 'negative_control': 3, 'bypassing_controls': 3, 'energy_isolation': 3, 'pit_smoker': 3, 'negative': 3, 'multiple_event': 3, 'no_trap': 3, 'success': 3, 'fire_safe_exit': 2, 'correction': 2, 'conditional': 2, 'line_of_fire': 2, 'Bypassing_Safety_Controls': 2, 'negative_observation': 2, 'hot_work': 2, 'pseudo_control': 2, 'conditional_control': 1, 'hot_work_authority': 1, 'hot_work_focus': 1, 'lifting_operations_absence': 1, 'evacuation': 1, 'rockfall': 1, 'hot_work_without_permit': 1, 'hot_work_permit_required': 1, 'scaffolding_trap_typo': 1, 'unmanned': 1, 'work_auth_focus': 1, 'pos_control': 1, 'no_injury': 1, 'unknown': 1, 'Line of Fire': 1, 'swinging_load_no_zone': 1, 'energy_released': 1, 'exposure': 1, 'conjugate': 1, 'work_authorisation': 1, 'lifting_plan_missing': 1, 'devanagari_trap': 1, 'india_context_mix': 1, 'duplication_paraphrase': 1, 'india_context_monsoon': 1, 'ergonomic': 1, 'smoldering': 1, 'low_energy': 1, 'control_ineffective': 1, 'reverse_bypassing': 1, 'incorrect_control_status': 1, 'conditional_bypass': 1, ' Driving': 1, 'energy_cue': 1, 'energy_isolation_absence': 1, 'hindi': 1, 'multiplexer': 1, 'bp_controls': 1, 'lifting_operations': 1, 'hot_work_permit': 1, 'lagitudinal_plain': 1, 'harness_not_clipped': 1, 'PPE_on_but_not_effective': 1, 'hot_work_no_hw': 1, 'contradiction (PPE on but not effective)': 1, 'typo_heavy': 1, 'exposure_focus': 1, 'mechanical_hazard': 1, 'electrical_no_loto': 1, 'bypass': 1, 'confined_space': 1, 'routine_adjustment': 1, 'safety_device': 1, 'routine_reset': 1, 'weather_outage': 1, 'planned_maintenance': 1, 'component_failure': 1, 'english': 1, 'correction (control worked)': 1, 'positive': 1, 'capacity_control_worked': 1}
- sources: {'generate': 1664, 'rewind': 1308, 'label': 235, 'exemplar': 3}

## Next

1. If a verdict shortfall is large, run more §1 batches (`--job generate --total-rows N`) - the prompt's VERDICT QUOTA will fill it.
2. Hand `test.jsonl` (or a 400-row sample of it) to two annotators -> silver test with kappa.
3. `python -m TRAINING.finetune.prepare_gliner_data` and `python -m TRAINING.finetune.prepare_setfit_data`.
