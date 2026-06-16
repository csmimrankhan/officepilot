<#
.SYNOPSIS
    Download whisper.cpp Windows binary (whisper-cli.exe) for OfficePilot AI.

.DESCRIPTION
    Downloads the latest whisper.cpp release from GitHub and extracts
    whisper-cli.exe into desktop/tauri/src-tauri/binaries/.

    Uses the official ggml-org/whisper.cpp releases.

.EXAMPLE
    .\scripts\download_whisper_cpp.ps1
#>

[CmdletBinding()]
param(
    [string]$Version = "1.8.6",
    [string]$OutputDir = ""
)

$ErrorActionPreference = "Stop"

if (-not $OutputDir) {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $RepoRoot  = Resolve-Path (Join-Path $ScriptDir "..")
    $OutputDir = Join-Path $RepoRoot "desktop\tauri\src-tauri\binaries"
}

# Ensure output dir exists
if (-not (Test-Path -LiteralPath $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$targetFile = Join-Path $OutputDir "whisper-cli.exe"
if (Test-Path -LiteralPath $targetFile) {
    Write-Host "whisper-cli.exe already exists at $targetFile"
    Write-Host "Delete it first to force re-download."
    exit 0
}

# Whisper.cpp releases provide a ZIP with the binary
$releaseUrl = "https://github.com/ggml-org/whisper.cpp/releases/download/v$Version/whisper-bin-x64.zip"
$zipPath = Join-Path $env:TEMP "whisper-bin-x64.zip"

Write-Host "Downloading whisper.cpp v$Version (Windows x64)..."
Write-Host "  URL : $releaseUrl"
Write-Host "  ZIP : $zipPath"
Write-Host "  OUT : $OutputDir"

try {
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($releaseUrl, $zipPath)
    Write-Host "Downloaded $((Get-Item $zipPath).Length) bytes."
} catch {
    Write-Host "Download failed: $_"
    Write-Host ""
    Write-Host "Falling back to manual instructions:"
    Write-Host "  1. Download from: https://github.com/ggml-org/whisper.cpp/releases"
    Write-Host "  2. Extract whisper-cli.exe from whisper-bin-x64.zip"
    Write-Host "  3. Copy to: $targetFile"
    exit 1
}

try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
    $entry = $zip.Entries | Where-Object { $_.Name -eq "whisper-cli.exe" } | Select-Object -First 1
    if ($entry) {
        [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $targetFile, $true)
        Write-Host "Extracted whisper-cli.exe to $targetFile"
    } else {
        # Try to find it in subdirectories
        $entry = $zip.Entries | Where-Object { $_.Name -like "*.exe" -and $_.FullName -like "*whisper*" } | Select-Object -First 1
        if ($entry) {
            [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $targetFile, $true)
            Write-Host "Extracted $($entry.Name) to $targetFile"
        } else {
            Write-Host "Could not find whisper-cli.exe in the ZIP."
            Write-Host "Extracting all files to $OutputDir for manual inspection..."
            [System.IO.Compression.ZipFileExtensions]::ExtractToDirectory($zip, $OutputDir)
        }
    }
    $zip.Dispose()
} catch {
    Write-Host "Extraction failed: $_"
    exit 1
}

if (Test-Path -LiteralPath $targetFile) {
    $fileInfo = Get-Item $targetFile
    Write-Host "whisper-cli.exe ready: $($fileInfo.Length) bytes"
} else {
    Write-Host "WARNING: whisper-cli.exe not found at expected path after extraction."
}

# Cleanup
Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Next step: run download_whisper_models.ps1 to get the model file."
