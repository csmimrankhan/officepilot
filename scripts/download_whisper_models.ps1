<#
.SYNOPSIS
    Download whisper.cpp model file for OfficePilot AI.

.DESCRIPTION
    Downloads ggml-base.en.bin (or specified model) from HuggingFace
    into desktop/tauri/src-tauri/binaries/models/.

    Models:
      ggml-tiny.en.bin    ~75MB  - Fast, lower accuracy
      ggml-base.en.bin    ~150MB - Balanced speed/accuracy (recommended)
      ggml-small.en.bin   ~500MB - Higher accuracy, slower

.EXAMPLE
    .\scripts\download_whisper_models.ps1
    .\scripts\download_whisper_models.ps1 -Model ggml-tiny.en.bin
#>

[CmdletBinding()]
param(
    [string]$Model = "ggml-base.en.bin",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

if (-not $OutputDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $RepoRoot  = Resolve-Path (Join-Path $ScriptDir "..")
    $OutputDir = Join-Path $RepoRoot "desktop\tauri\src-tauri\binaries\models"
}

# Ensure output dir exists
if (-not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$targetFile = Join-Path $OutputDir $Model
if (Test-Path -LiteralPath $targetFile) {
    Write-Host "Model '$Model' already exists at $targetFile"
    Write-Host "Size: $((Get-Item $targetFile).Length) bytes"
    Write-Host "Delete it first to force re-download."
    exit 0
}

# HuggingFace mirror for whisper.cpp models
$modelUrl = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$Model"
$modelSize = @{
    "ggml-tiny.en.bin"  = "~75 MB"
    "ggml-base.en.bin"  = "~150 MB"
    "ggml-small.en.bin" = "~500 MB"
}

Write-Host "Downloading whisper.cpp model: $Model"
Write-Host "  URL : $modelUrl"
Write-Host "  Size: $($modelSize[$Model] -or 'unknown')"
Write-Host "  OUT : $targetFile"
Write-Host ""
Write-Host "This may take a few minutes depending on your connection..."
Write-Host ""

try {
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($modelUrl, $targetFile)
    $fileInfo = Get-Item $targetFile
    Write-Host "Download complete: $($fileInfo.Length) bytes"
} catch {
    Write-Host "Download failed: $_"
    Write-Host ""
    Write-Host "Fallback: download manually from:"
    Write-Host "  $modelUrl"
    Write-Host "  Save to: $targetFile"
    exit 1
}

Write-Host ""
Write-Host "Model ready: $targetFile"
Write-Host ""
Write-Host "To verify, run:"
Write-Host "  whisper-cli.exe -m $targetFile -f test.wav"
