# Data quality report

Generated 2026-09-06 13:10 · 91s · Python 3.10.12

## IOGP fatal / HiPo / permanent-impairment PDFs

| file | type | year | pages | records | with warnings |
|---|---|---|---|---|---|
| 2022sf.pdf | fatal | 2022 | 32 | 29 | 4 |
| 2022sh.pdf | hipo | 2022 | 86 | 105 | 17 |
| 2023fpi.pdf | permanent_impairment | 2023 | 56 | 47 | 8 |
| 2023sf.pdf | fatal | 2023 | 22 | 17 | 4 |
| 2023sh.pdf | hipo | 2023 | 112 | 131 | 49 |
| 2024fpi.pdf | permanent_impairment | 2024 | 42 | 34 | 1 |
| 2024sf.pdf | fatal | 2024 | 28 | 21 | 5 |
| 2024sh.pdf | hipo | 2024 | 120 | 150 | 13 |
| 2025sf.pdf | fatal | 2025 | 46 | 40 | 8 |
| 2025sh.pdf | hipo | 2025 | 92 | 98 | 6 |

Skipped: `2023f.pdf` (not a narrative report (statistics / summary)); `2023fe.pdf` (not a narrative report (statistics / summary)); `2023s.pdf` (not a narrative report (statistics / summary)); `2024f.pdf` (not a narrative report (statistics / summary)); `2024fe.pdf` (not a narrative report (statistics / summary)); `2024s.pdf` (not a narrative report (statistics / summary)); `2024sf (1).pdf` (byte-identical duplicate of 2024sf.pdf); `2024sh (1).pdf` (byte-identical duplicate of 2024sh.pdf); `2025ae.pdf` (not a narrative report (statistics / summary)); `2025s.pdf` (not a narrative report (statistics / summary))

- **672 records** - fatal: 107, hipo: 484, permanent_impairment: 81
- narrative length: min 2 / median 57 / p90 128 / max 340 words
- records with a Life-Saving Rule: 573 (99 say 'no applicable rule' / unspecified)
- LSR distribution: Line of Fire: 362, Safe Mechanical Lifting: 122, Energy Isolation: 81, Bypassing Safety Controls: 81, Work Authorisation: 65, Working at Height: 60, Driving: 33, Hot Work: 23, Confined Space: 7
- records with parsed causal factors: 591
- warnings: no_lsr: 99, very_short_narrative: 25

## OSHA Severe Injury Reports

- raw rows: 105996 (dropped 1 with empty/short narrative)
- **oil & gas subset: 2902 rows**, 2901 unique after de-duplication (1 exact + 0 near duplicates)
- by sector: support_activities_oil_gas: 1896, drilling_oil_gas_wells: 663, oil_gas_extraction: 191, petroleum_refineries: 152
- by year: 2015: 336, 2016: 246, 2017: 385, 2018: 408, 2019: 370, 2020: 158, 2021: 161, 2022: 229, 2023: 213, 2024: 202, 2025: 194
- actual severity: hospitalized: 2062, amputation: 837, loss_of_eye: 3
- narrative length: min 5 / median 35 / p90 63 / max 207 words
- unparsed dates: 0, missing NAICS: 2

## Register-style logs

### near_miss_report.csv
- rows: 56 (raw 56, dropped 0)
- column mapping: `S/No.` → sno, `Date Raised` → date, `Shift` → shift, `Time (Day/Night)` → time_of_day, `Near miss description (Observation)` → description, `Category` → category, `Near miss Observation` → sub_category, `Area(Location)` → area, `Raised By(Observer)` → observer, `Status` → status, `Corrective action/Follow up` → corrective_action, `Comments` → comments
- unmapped columns: none
- category: UC: 42, UA: 14; sub-category: SLIPS AND TRIPS: 31, NARROW ESCAPE: 12, FALL RISK: 7, EQUIPMENT OPERATION AND MAINTENANCE: 2, FALLING OBJECTS: 2, RISKY BEHAVIOR: 2
- areas: PIN LONG: 13, 5 PA: 10, 9 PA: 10, 9 PB: 7, CORRUGATOR: 6, 6 PAN: 2, DISPATCH: 2, 9 PB STRAPPING AREA: 1, CCD BALING MACHINE: 1, ENGINEERING STORES: 1, PPO LAMINATOR MACHIN: 1, REEL GODOWN: 1, STERIO ROOM: 1
- dates unparsed: 0 (year assumed for 56) - pass `--register-year YYYY` if the register omits the year
- description words min/median/max: [2, 9, 25]
- duplicates: 0 exact, 0 near

## terms.json glossary

- 155 raw entries → **149 unique terms**, 972 variants
- duplicate terms merged: 6 (6 with conflicting fields - see `merge_conflicts`)
- by category: abbreviation: 91, equipment: 47, barrier: 11
- by safety_signal (GLiNER role): energy_cue: 60, control_present: 26, None: 20, pseudo_control: 17, exposure_cue: 15, statement_cue: 7, outcome_cue: 3, release_cue: 1
- by Life-Saving Rule: None: 68, Line of Fire: 14, Safe Mechanical Lifting: 13, Bypassing Safety Controls: 12, Energy Isolation: 11, Hot Work: 8, Driving: 6, Work Authorisation: 6, Working at Height: 6, Confined Space: 5
- variants shared by two terms (first wins in lookup): 21
- schema problems: 0

## Unified corpus

- **3630 rows, 3620 unique** (7 exact + 3 near duplicates flagged, not removed)
- by source: osha_sir: 2902, iogp: 672, register: 56
- by record type: severe_injury: 2902, hipo: 484, fatal: 107, permanent_impairment: 81, near_miss: 56
- by teacher prompt: label: 2958, rewind: 672 (rewind = prompts.md §2, label = §3)
- `teacher_input.jsonl` has 3620 de-duplicated rows ready for the teacher LLM

## Output files

- `iogp/parse_log.json` (4 KB)
- `iogp/records.csv` (1722 KB)
- `iogp/records.jsonl` (2244 KB)
- `manifest.json` (13 KB)
- `osha/osha_oilgas.csv` (2228 KB)
- `osha/osha_oilgas.jsonl` (3601 KB)
- `osha/osha_stats.json` (1 KB)
- `register/near_miss_report_clean.csv` (19 KB)
- `register/near_miss_report_clean.jsonl` (45 KB)
- `register/register_stats.json` (1 KB)
- `terms/glossary_clean.csv` (59 KB)
- `terms/glossary_clean.json` (104 KB)
- `terms/terms_stats.json` (3 KB)
- `terms/variant_lookup.json` (27 KB)
- `unified/corpus.csv` (1261 KB)
- `unified/corpus.jsonl` (4817 KB)
- `unified/teacher_input.jsonl` (3958 KB)
