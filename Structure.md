# Project Structure

```
SIH_26/
├── CLIENT/                          # Frontend (empty for now)
├── DATA/
│   ├── Processed/                   # Cleaned/processed datasets
│   └── RAW/
│       ├── IOGP_HiPo fatal/         # IOGP HiPo & fatal incident report PDFs (2022–2025)
│       ├── OSHA Severe Injury Reports/
│       │   └── January2015toNovember2025.csv
│       ├── Register-style logs/
│       │   └── near_miss_report.csv
│       └── terms/
│           └── terms.json           # Domain terminology
├── SERVER/
│   ├── Classfication/
│   │   ├── Models/
│   │   │   ├── LLM/                 # Qwen3.5-4B-Q4_K_M.gguf
│   │   │   ├── gliner_multi/        # GLiNER NER model
│   │   │   └── sentance_encoder/    # Sentence embedding model
│   │   └── SIFp/
│   │       └── schema.py            # Classification schema
│   └── Prediction/                  # Prediction service (empty for now)
├── TRAINING/
│   ├── distrillation/               # Model distillation (empty for now)
│   └── preprocessing/
│       └── fetch_from_pdf.py        # PDF data extraction
├── .env / .env.example              # Environment config
├── data_set_instruction.md          # Dataset instructions
├── main.py                          # Entry point
├── prompts.md                       # LLM prompts
├── pyproject.toml / requirements.txt
└── Structure.md                     # This file
```
