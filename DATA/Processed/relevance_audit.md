# Seed-pool relevance & sufficiency audit

**Status: ENOUGH_WITH_GAPS**

- only 33% of seed rows use explicit oil & gas vocabulary - the rest are generic industrial (MSHA mining, OSHA construction/manufacturing). The ENERGY types transfer (gravity, motion, mechanical, electrical, pressure); the vocabulary does not. Rewind prompt already re-sets each seed at an Oil India site, and §1 generate adds site-specific text - keep that, and prefer oil&gas / OISD / IADC seeds when quota is short.
- India context in seeds is 0% - it must come from OIL_CONTEXT in the prompts and the india_context trap quota; gold-180 is the only India-flavoured eval. Adding more OISD archive PDFs is the cheapest fix.
- seeds are 98% English; Hinglish / Devanagari / Assamese rows come entirely from generation - expected 7600 vs needed 7200 (OK).
- few seeds even mention these Life-Saving Rules: Confined Space, Bypassing Safety Controls - set a generate quota for them.
- only 13% of seeds read as near-miss / no-injury; most are post-injury reports. §2 rewind (variants A/B/C stop the event before injury) is what converts them into precursors - so the rewind job is NOT optional.

## 1. Is it enough?

- seeds after per-source caps {'alert_imca': 150, 'msha': 600, 'osha_sir': 1000}: 2489 rewind + 1600 label rows; generate target 10000
- expected accepted teacher rows: generate 8000 + rewind 7467 + label 1360 = 16827 → after dedup ≈ **15481** vs target 12000 → OK
- GLiNER span rows: every accepted row carries spans → 15481 ≥ 1500 → OK
- Indic-language rows (Hinglish+Devanagari+Assamese target 60 %): expected ≈ 7600 vs needed 7200 → OK
- API requests: generate 500, rewind 830, label 80
- eval: gold-180 (180 rows) + IHM 425 + contrast set — held out, never seeds

## 2. Is it relevant?  (per source)

| source | rows | job | oil&gas vocab | energy cue | India ctx | near-miss-like | severe outcome | avg words | >300 w | top domains | language |
|---|---|---|---|---|---|---|---|---|---|---|---|
| msha | 1300 | label | 4% | 69% | 0% | 12% | 11% | 39 | 0% | construction_projects 325, mining 244, transport_driving 140, electrical 118 | english 1290, hinglish 10 |
| osha_sir | 1000 | label | 26% | 88% | 0% | 0% | 78% | 42 | 0% | drilling_well 441, transport_driving 143, mining 88, production_process 80 | english 990, hinglish 10 |
| osha_abstracts | 915 | rewind | 84% | 94% | 1% | 2% | 81% | 126 | 5% | drilling_well 562, transport_driving 224, construction_projects 207, electrical 121 | english 909, hinglish 6 |
| alert_iadc | 748 | rewind | 56% | 95% | 0% | 29% | 38% | 135 | 4% | drilling_well 504, construction_projects 207, marine_offshore 160, transport_driving 67 | english 709, hinglish 39 |
| iogp | 663 | rewind | 24% | 90% | 0% | 12% | 22% | 69 | 0% | drilling_well 178, construction_projects 158, marine_offshore 140, transport_driving 95 | english 658, hinglish 5 |
| alert_imca | 406 | rewind | 4% | 96% | 0% | 43% | 47% | 463 | 50% | marine_offshore 350, marketing_lpg_pol 231, construction_projects 143, electrical 77 | english 387, hinglish 19 |
| alert_oisd | 13 | rewind | 31% | 100% | 23% | 8% | 62% | 327 | 38% | construction_projects 11, transport_driving 4, marine_offshore 4, pipeline 3 | english 13 |

Totals: oil&gas vocab 33% · energy cue 86% · India 0% · near-miss-like 13% · severe 45% · English 98% · >300 words 6%

## 3. Coverage across the seed pool (keyword-implied, not labels)

| Life-Saving Rule | seeds mentioning it |
|---|---|
| Working at Height | 550 |
| Line of Fire | 948 |
| Energy Isolation | 251 |
| Confined Space | 53 |
| Hot Work | 283 |
| Driving | 486 |
| Safe Mechanical Lifting | 1620 |
| Work Authorisation | 505 |
| Bypassing Safety Controls | 63 |

| energy type | seeds |
|---|---|
| gravity | 1810 |
| temperature_fire | 1459 |
| motion | 1413 |
| mechanical | 1277 |
| pressure | 981 |
| electrical | 476 |
| chemical | 282 |
| sound_radiation_bio | 73 |

| work domain | seeds |
|---|---|
| drilling_well | 1794 |
| construction_projects | 1118 |
| marine_offshore | 781 |
| transport_driving | 717 |
| mining | 563 |
| electrical | 476 |
| marketing_lpg_pol | 358 |
| production_process | 353 |
| pipeline | 103 |
| refinery_petrochem | 75 |

## 4. Verdict quota the teacher must fill

| verdict | rows | mainly from |
|---|---|---|
| EXPOSURE | 3000 | rewind A/B (event stopped before release) |
| P_SIF | 2040 | rewind + generate |
| LOW_ENERGY | 2040 | generate + label (OSHA SIR low severity, MSHA no-injury) |
| CAPACITY | 1800 | rewind C (control present but weak) + generate |
| SUCCESS | 840 | generate + rewind (control worked) |
| NON_EVENT | 720 | generate (observations, training, hypotheticals) |
| INSUFFICIENT | 720 | generate (vague one-liners) + register |
| H_SIF | 480 | original fatal seeds (IOGP, OISD, MSHA fatal) |
| L_SIF | 360 | original LTI/RWC seeds (OSHA SIR, IADC) |
