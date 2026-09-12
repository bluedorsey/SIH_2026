# Training readiness — 2026-09-07T04:47:14

**Seeds and evaluation sets are valid and sufficient; NO model can be fine-tuned yet because zero rows carry span labels or 9-class verdicts - the teacher-LLM run (prompts §1/§2/§3) is the gating step, and it can start now on 4045 seeds.**

## 1. Validity of each source

| source | rows | empty | <8 words | dups | label coverage | language guess | status | issues |
|---|---|---|---|---|---|---|---|---|
| IOGP fatal/HiPo/PI | 672 | 0 | 8 | 0 | life_saving_rules 85 %, what_went_wrong 100 %, causal_factors 88 % | english 667, hinglish 5 | VALID | - |
| OSHA SIR oil&gas | 2902 | 0 | 6 | 1 | event_type 100 %, nature 100 % | english 2885, hinglish 17 | VALID | - |
| OSHA accident abstracts (16k) | 16323 | 0 | 358 | 365 | keywords 100 % | english 16009, hinglish 314 | VALID | - |
| OSHA abstracts oil&gas subset | 928 | 0 | 13 | 13 | keywords 100 % | english 922, hinglish 6 | VALID | - |
| MSHA selected | 6759 | 0 | 152 | 57 | classification 100 %, accident_type 100 % | english 6690, hinglish 69 | VALID | - |
| Safety alerts (IADC/IMCA/StepChange/OISD) | 3157 | 0 | 0 | 52 | life_saving_rules 0 %, what_went_wrong 46 % | english 3036, hinglish 121 | VALID_WITH_WARNINGS | life_saving_rules filled for only 0 %; what_went_wrong filled for only 46 % |
| Register template | 56 | 0 | 19 | 0 | category 100 % | english 56 | VALID_WITH_WARNINGS | 34 % texts under 8 words |
| Gold-180 | 180 | 0 | 17 | 0 | sif_potential 100 %, statement_type 100 % | hinglish 144, english 33, assamese_roman 3 | VALID | - |
| Kaggle IHM (eval) | 425 | 0 | 0 | 15 | potential_level 100 % | english 422, hinglish 3 | VALID | - |

## 2. Seed pool for §2 Rewind

- seeds: **4045** unique rows (566 with a Life-Saving Rule; 452 tagged onshore) → ≈ 16180 rewound rows at 4 variants each
- by source: msha 1300, osha_abstracts 915, alert_iadc 748, iogp 663, alert_imca 406, alert_oisd 13
- post-injury seeds: 2016 (0.498) — post-injury originals may be at most 6 % of the final train set (= 720 rows of 12000); 2016 are available, so the surplus becomes evaluation / seeds-only.
- verdict quota targets for a 12000-row train set: EXPOSURE 3000, P_SIF 2040, LOW_ENERGY 2040, CAPACITY 1800, SUCCESS 840, NON_EVENT 720, INSUFFICIENT 720, H_SIF 480, L_SIF 360
- language targets: hinglish 45 %, english 35 %, devanagari 10 %, assamese 5 % - gold-180 actual: {'hinglish': 144, 'english': 33, 'assamese_roman': 3}
- gold-180 has 0 Devanagari and 0 Assamese-script rows; training data must add them (10 % + 5 %) and gold v2 needs 30 + 20 rows

## 3. Can each model be trained?

**GLiNER (span roles)** — NOT_READY: 0 span-annotated rows of 1500 needed. 0 span-annotated rows. Nothing downloadable has the 11 roles; they must come from the teacher LLM (prompts §1/§2/§3) or, as a smoke-test only, glossary weak labels (variant_lookup.json).

**SetFit / MiniLM prefilter** — EVAL_ONLY: 180 labelled rows (per class {'YES': 90, 'NO': 37, 'UNCERTAIN': 53}). Only gold-180 carries verdict labels (3-class YES/NO/UNCERTAIN, not the 9-class verdict) and it is the test set. Training rows with §0 verdicts: 0 of the 12000 target. Teacher output required.

**LSR mapper** — SEEDS_THIN_FOR:Bypassing Safety Controls,Confined Space,Driving,Energy Isolation,Hot Work,Work Authorisation,Working at Height: seeds per rule {'Bypassing Safety Controls': 81, 'Confined Space': 7, 'Driving': 33, 'Energy Isolation': 77, 'Hot Work': 23, 'Line of Fire': 355, 'Safe Mechanical Lifting': 121, 'Work Authorisation': 65, 'Working at Height': 59}; below 100 seeds: {'Bypassing Safety Controls': 19, 'Confined Space': 93, 'Driving': 67, 'Energy Isolation': 23, 'Hot Work': 77, 'Work Authorisation': 35, 'Working at Height': 41}; expected after ×4 rewind: {'Bypassing Safety Controls': 324, 'Confined Space': 28, 'Driving': 132, 'Energy Isolation': 308, 'Hot Work': 92, 'Line of Fire': 1420, 'Safe Mechanical Lifting': 484, 'Work Authorisation': 260, 'Working at Height': 236}

**Actual-vs-potential contrast/eval set** — READY: 1001 rows

## 4. What unblocks training

1. Put a teacher key in `.env` (Gemini free tier for synthetic/public text) and run prompts §2 on `unified/teacher_input.jsonl` (rewind) and §1 (generate) — every output row carries the 11 span roles and the 9-class verdict.
2. Run the sources still marked MISSING above through `python -m CLEANING.fetch.fetch_all` on the laptop, then re-run the pipeline.
3. Keep gold-180 as the test set; the pipeline already removes any training row that near-duplicates it.
