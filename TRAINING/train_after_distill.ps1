# ---------------------------------------------------------------------------------------------
#  SIH26165 - fine-tuning after distillation (Windows PowerShell)
#
#    .\TRAINING\train_after_distill.ps1                 # filter -> models -> heads (CPU) -> GLiNER smoke -> Colab bundle -> eval
#    .\TRAINING\train_after_distill.ps1 -GlinerCpu      # also train GLiNER fully on this laptop's CPU (hours; overnight)
#    .\TRAINING\train_after_distill.ps1 -SkipAgree       # skip the teacher-agreement step (no API credit left)
#    .\TRAINING\train_after_distill.ps1 -SkipSetup       # models already verified by setup_models
#
#  Outputs:  SERVER\Classfication\Models\Tunned\sif_heads   (prefilter / verdict / statement_type / LSR heads)
#            SERVER\Classfication\Models\Tunned\gliner_sif  (from Colab, or from -GlinerCpu)
#            TRAINING\eval\reports\gold_eval.md
# ---------------------------------------------------------------------------------------------
param([switch]$SkipSetup, [switch]$SkipAgree, [switch]$GlinerCpu, [int]$GlinerEpochs = 3)

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

function Step($label, $cmd) {
    Write-Host "`n=== $label ===" -ForegroundColor Cyan
    Invoke-Expression $cmd
    if ($LASTEXITCODE -ne 0) { Write-Error "step failed: $label"; exit $LASTEXITCODE }
}

if (-not (Test-Path "DATA\distilled\raw\generate.jsonl") -and -not (Test-Path "DATA\distilled\raw\rewind.jsonl")) {
    Write-Error "no teacher rows yet - run .\TRAINING\distill_one_go.ps1 first"; exit 1
}

New-Item -ItemType Directory -Force -Path "SERVER\Classfication\Models\Tunned" | Out-Null

if ($SkipAgree) {
    Write-Host "`n=== 1/8 teacher agreement sample - SKIPPED (-SkipAgree) ===" -ForegroundColor DarkGray
} else {
    Step "1/8 teacher agreement sample (needs API keys; use -SkipAgree if spent)" "python -m TRAINING.distill.run_distill --job agree"
}
Step "2/8 filter, dedup, leakage guard, quotas, 80/10/10 split" "python -m TRAINING.distill.filter_distilled --enforce-quotas"
if (-not $SkipSetup) {
    Step "3/8 base model folders (encoder / NLI / GLiNER tokenizer)" "python -m TRAINING.setup_models"
}
Step "4/8 weak GLiNER rows from the glossary"                  "python -m TRAINING.weak_label_gliner"
Step "5/8 prepare GLiNER + sentence-task data"                  "python -m TRAINING.finetune.prepare_gliner_data --weak; python -m TRAINING.finetune.prepare_setfit_data"
Step "6/8 sentence heads on CPU -> Models\Tunned\sif_heads"     "python -m TRAINING.finetune.train_setfit --mode head"
if ($GlinerCpu) {
    Step "7/8 GLiNER full training on CPU -> Models\Tunned\gliner_sif (hours)" "python -m TRAINING.finetune.train_gliner --epochs $GlinerEpochs --batch 8 --device cpu --resume"
} else {
    Step "7/8 GLiNER smoke test + Colab bundle"                 "python -m TRAINING.finetune.train_gliner --smoke; python -m TRAINING.pack_for_colab"
    Write-Host "Upload sih_train_bundle.zip to Google Drive (SIH_26\) and run TRAINING\finetune\colab_train.ipynb on a GPU runtime." -ForegroundColor Yellow
    Write-Host "It returns sif_models.zip - unzip it at $repo to get Models\Tunned\gliner_sif." -ForegroundColor Yellow
}
Step "8/8 evaluate the heads on gold-180 + IHM"                 "python -m TRAINING.eval.evaluate_gold"

Write-Host "`nDone. Tuned models: SERVER\Classfication\Models\Tunned\   Report: TRAINING\eval\reports\gold_eval.md" -ForegroundColor Green
