param(
  [Parameter(Mandatory=$true)][string]$CorpusDir,
  [string]$Model = 'qwen3:8b',
  [string]$OutDir = 'output'
)

$ErrorActionPreference = 'Stop'

# Run from the ScriptLab project root so `python -m scriptlab` resolves locally.
Write-Host "Checking local Ollama model: $Model"
python -m scriptlab check-ollama --model $Model
if ($LASTEXITCODE -ne 0) { throw 'Ollama/model preflight did not pass' }

Write-Host "Parsing Buffy corpus from $CorpusDir"
python -m scriptlab parse --series buffy $CorpusDir --out $OutDir
if ($LASTEXITCODE -ne 0) { throw 'Parsing failed; examine the report before proceeding' }

$ParsedFile = Join-Path (Join-Path $OutDir 'buffy') 'S03E15.json'
if (-not (Test-Path $ParsedFile)) { throw 'S03E15.json was not found; the pilot requires Consequences (3x15.htm)' }

$ResultDir = Join-Path $OutDir 'verification'
New-Item -ItemType Directory -Force -Path $ResultDir | Out-Null
$ResultPrefix = Join-Path $ResultDir 'S03E15_pilot'
Write-Host 'Running a bounded comparison on normalized lines 525-570'
python -m scriptlab compare --parsed $ParsedFile --model $Model --line-start 525 --line-end 570 --chunk-size 16 --out $ResultPrefix
if ($LASTEXITCODE -ne 0) { Write-Warning 'LLM returned missing/malformed labels; review failure report and retry with a smaller chunk size' }
Write-Host "Open $ResultPrefix.comparison.md for human review"
