# ---------------------------------------------------------------------------------------------
#  SIH26165 - teacher distillation, one-go launcher (Windows PowerShell)
#
#    .\TRAINING\distill_one_go.ps1 -Pilot     # 3 small requests, then read DATA\distilled\raw\*.rejects.jsonl
#    .\TRAINING\distill_one_go.ps1            # opens 5 windows, one per provider lane group; all jobs resume
#    .\TRAINING\distill_one_go.ps1 -Status    # progress of every job and lane
#
#  Every window can be closed and re-launched any time - finished batches are never redone.
#  If PowerShell refuses to run scripts:  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
# ---------------------------------------------------------------------------------------------
param([switch]$Pilot, [switch]$Status, [switch]$NoOpenRouter)

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

if (-not (Test-Path ".env")) { Write-Error ".env not found in $repo - copy .env.example to .env and paste the 7 keys"; exit 1 }
if (-not (Test-Path "DATA\Processed\unified\teacher_input.jsonl")) { Write-Error "teacher_input.jsonl missing - run  python -m CLEANING.run_pipeline  first"; exit 1 }

if ($Status) { python -m TRAINING.distill.run_distill --status; exit $LASTEXITCODE }

python -m TRAINING.distill.make_exemplars
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($Pilot) {
    Write-Host "`n=== PILOT: 1 generate batch on Sarvam, 1 rewind request on Gemini, 1 label batch on Groq ===" -ForegroundColor Cyan
    python -m TRAINING.distill.run_distill --job generate --backend sarvam --limit 1
    python -m TRAINING.distill.run_distill --job rewind   --backend gemini --limit 3
    python -m TRAINING.distill.run_distill --job label    --backend groq   --limit 5
    python -m TRAINING.distill.run_distill --status
    Write-Host "`nNow open DATA\distilled\raw\generate.jsonl (accepted rows) and *.rejects.jsonl (why rows were dropped)." -ForegroundColor Yellow
    Write-Host "If the accepted rows look right, run this script again WITHOUT -Pilot." -ForegroundColor Yellow
    exit 0
}

$jobs = @(
    @{ name = "1 generate - Sarvam (Indic-heavy, stops at Rs95 per key)"; args = "--job generate --backend sarvam" },
    @{ name = "2 generate - Gemini (reverse order)";                       args = "--job generate --backend gemini --reverse" },
    @{ name = "3 rewind - Gemini";                                         args = "--job rewind --backend gemini" },
    @{ name = "4 label - Groq";                                            args = "--job label --backend groq" }
)
if (-not $NoOpenRouter) {
    $jobs += @{ name = "5 rewind - OpenRouter (reverse order)"; args = "--job rewind --backend openrouter --reverse" }
}
# optional providers - a window is opened only when the key is present in .env
$envText = Get-Content .env -Raw
# (NVIDIA=, NVIDIA_API=, NVIDIA_API_1=, NVIDIA_KEY= ... are all accepted, same as the Python loader)
if ($envText -match '(?m)^NVIDIA[A-Z0-9_]*\s*=\s*\S{10,}') {
    # NVIDIA has no daily cap (40 req/min shared) -> three windows: rewind from both ends + label
    $jobs += @{ name = "6a rewind - NVIDIA NIM";                 args = "--job rewind --backend nvidia" }
    $jobs += @{ name = "6b rewind - NVIDIA NIM (reverse order)"; args = "--job rewind --backend nvidia --reverse" }
    $jobs += @{ name = "6c label - NVIDIA NIM (reverse order)";  args = "--job label --backend nvidia --reverse" }
}
if ($envText -match '(?m)^MISTRAL[A-Z0-9_]*\s*=\s*\S{10,}')  { $jobs += @{ name = "7 generate - Mistral (reverse order)";   args = "--job generate --backend mistral --reverse" } }
if ($envText -match '(?m)^CEREBRAS[A-Z0-9_]*\s*=\s*\S{10,}') { $jobs += @{ name = "8 label - Cerebras";                     args = "--job label --backend cerebras --reverse" } }

foreach ($j in $jobs) {
    $title = $j.name
    $cmd = "`$env:PYTHONUTF8='1'; `$env:PYTHONIOENCODING='utf-8'; Set-Location '$repo'; `$host.UI.RawUI.WindowTitle='$title'; " +
           "python -m TRAINING.distill.run_distill $($j.args); " +
           "Write-Host ''; Write-Host 'This window is finished (quota for today used, or list complete). Re-run distill_one_go.ps1 tomorrow to continue.' -ForegroundColor Green; Read-Host 'press Enter to close'"
    Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $cmd
    Start-Sleep -Seconds 3        # stagger so the windows do not all read the state file in the same instant
}

Write-Host "`n$($jobs.Count) windows launched. Check progress any time with:  .\TRAINING\distill_one_go.ps1 -Status" -ForegroundColor Green
Write-Host "When the rewind windows are done:  python -m TRAINING.distill.run_distill --job agree" -ForegroundColor Green
Write-Host "Then train:                        .\TRAINING\train_after_distill.ps1" -ForegroundColor Green
