# scripts/sign_installers.ps1
#
# Phase 9 - code-sign the installers produced by
# ``cargo tauri build`` (or any subset of them). Designed to be
# invoked either by the build script (``tauri.conf.json ->
# bundle.windows.code-signing.signCommand``) or directly by a
# developer on a CI agent.
#
# Required env / args:
#   OFFICEPILOT_CERT_THUMBPRINT  SHA1 thumbprint of the code-signing
#                                certificate in the CurrentUser\My
#                                store. The build host must have the
#                                private key available.
#
# Optional:
#   OFFICEPILOT_TIMESTAMP_URL   RFC 3161 timestamp server. Default:
#                               http://timestamp.sectigo.com
#   OFFICEPILOT_SIGN_DESCRIPTION  Description embedded in the signature.
#                               Default: "OfficePilot AI"
#   Input paths (positional)     One or more .exe / .msi files to
#                               sign. If none are given, the script
#                               signs every installer under
#                               target/release/bundle/{msi,nsis}/.

[CmdletBinding()]
param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$InputPaths
)

$ErrorActionPreference = "Stop"

# ---- Validation -------------------------------------------------------------

if (-not $env:OFFICEPILOT_CERT_THUMBPRINT) {
    Write-Host "OFFICEPILOT_CERT_THUMBPRINT is not set; skipping code sign." -ForegroundColor Yellow
    Write-Host "  Export the SHA1 thumbprint of your code-signing cert and re-run." -ForegroundColor Yellow
    exit 0
}

$thumb = $env:OFFICEPILOT_CERT_THUMBPRINT
$timestampUrl = if ($env:OFFICEPILOT_TIMESTAMP_URL) { $env:OFFICEPILOT_TIMESTAMP_URL } else { "http://timestamp.sectigo.com" }
$description = if ($env:OFFICEPILOT_SIGN_DESCRIPTION) { $env:OFFICEPILOT_SIGN_DESCRIPTION } else { "OfficePilot AI" }

$signtool = Get-Command signtool.exe -ErrorAction SilentlyContinue
if (-not $signtool) {
    $sdkPaths = @(
        "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe"
        "C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
        "C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe"
    )
    foreach ($p in $sdkPaths) {
        $resolved = Get-Item $p -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($resolved) { $signtool = $resolved; break }
    }
}
if (-not $signtool) {
    Write-Error "signtool.exe not found. Install the Windows SDK or add it to PATH."
    exit 1
}

# ---- Discover inputs --------------------------------------------------------

if (-not $InputPaths -or $InputPaths.Count -eq 0) {
    $repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
    $candidates = @()
    foreach ($sub in @("msi", "nsis")) {
        $dir = Join-Path $repoRoot "desktop\tauri\src-tauri\target\release\bundle\$sub"
        if (Test-Path -LiteralPath $dir) {
            $candidates += Get-ChildItem -LiteralPath $dir -File -Include "*.exe", "*.msi"
        }
    }
    $InputPaths = $candidates | ForEach-Object { $_.FullName }
}

if (-not $InputPaths -or $InputPaths.Count -eq 0) {
    Write-Host "No installer files found to sign." -ForegroundColor Yellow
    exit 0
}

Write-Host "Signing $($InputPaths.Count) file(s) with thumbprint $thumb (timestamp: $timestampUrl)" -ForegroundColor Cyan

# ---- Sign -------------------------------------------------------------------

$failed = @()
foreach ($file in $InputPaths) {
    if (-not (Test-Path -LiteralPath $file)) {
        Write-Warning "Skipping missing file: $file"
        continue
    }
    Write-Host "  -> $file" -ForegroundColor Gray
    & $signtool sign `
        /sha1 $thumb `
        /tr $timestampUrl `
        /td sha256 `
        /fd sha256 `
        /d $description `
        /du "https://officepilot.local" `
        $file
    if ($LASTEXITCODE -ne 0) {
        $failed += $file
    }
}

if ($failed.Count -gt 0) {
    Write-Error "Failed to sign: $($failed -join ', ')"
    exit 1
}

Write-Host "All installers signed successfully." -ForegroundColor Green
