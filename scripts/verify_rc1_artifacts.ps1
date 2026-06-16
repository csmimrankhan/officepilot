<#
.SYNOPSIS
  Release artifact verification for OfficePilot AI v0.36.1-rc1.
.DESCRIPTION
  Checks all release artifacts exist, versions are correct, and key
  endpoints respond. Exit code = number of failed checks.
#>

$ErrorActionPreference = "Stop"
$rc = 0

Write-Host "=== OfficePilot AI v0.36.1-rc1 Artifact Verification ===" -ForegroundColor Cyan
Write-Host ""

# ── Config ──────────────────────────────────────────────────────────────────
$ROOT = Resolve-Path "$PSScriptRoot\.."
$RELEASES = "$ROOT\releases\0.36.1"
$TAURI_BIN = "$ROOT\desktop\tauri\src-tauri\binaries"
$FRONTEND_DIST = "$ROOT\frontend\dist"
$BACKEND = "$ROOT\backend"
$API_BASE = "http://127.0.0.1:8000"

function Check {
    param($Name, [ScriptBlock]$Block)
    try {
        $result = & $Block
        if ($result) {
            Write-Host "  [PASS] $Name" -ForegroundColor Green
            return $true
        } else {
            Write-Host "  [FAIL] $Name" -ForegroundColor Red
            $script:rc++
            return $false
        }
    } catch {
        Write-Host "  [FAIL] $Name — $_" -ForegroundColor Red
        $script:rc++
        return $false
    }
}

# ── 1. MSI exists ───────────────────────────────────────────────────────────
Write-Host "1. Installer Artifacts" -ForegroundColor Yellow
Check "MSI exists" { Test-Path -LiteralPath "$RELEASES\OfficePilot AI_0.36.1_x64_en-US.msi" }
Check "NSIS exists" { Test-Path -LiteralPath "$RELEASES\OfficePilot AI_0.36.1_x64-setup.exe" }
Check "Signature exists" { Test-Path -LiteralPath "$RELEASES\OfficePilot AI_0.36.1_x64_en-US.msi.sig" }
Write-Host ""

# ── 2. Sidecar EXE exists ──────────────────────────────────────────────────
Write-Host "2. Sidecar Binary" -ForegroundColor Yellow
$sidecarPath = "$TAURI_BIN\officepilot-agent-x86_64-pc-windows-msvc.exe"
Check "Sidecar EXE exists" { Test-Path -LiteralPath $sidecarPath }
if (Test-Path $sidecarPath) {
    $sidecar = Get-Item $sidecarPath
    Check "Sidecar size > 100 MB" { $sidecar.Length -gt 100MB }
}
Write-Host ""

# ── 3. Frontend dist exists ────────────────────────────────────────────────
Write-Host "3. Frontend Build" -ForegroundColor Yellow
Check "frontend/dist/index.html exists" { Test-Path -LiteralPath "$FRONTEND_DIST\index.html" }
Check "frontend/dist/assets has JS bundles" { (Get-ChildItem "$FRONTEND_DIST\assets\*.js").Count -gt 0 }
Write-Host ""

# ── 4. Version consistency ─────────────────────────────────────────────────
Write-Host "4. Version Consistency" -ForegroundColor Yellow
$expectedVersion = "0.36.1"

$backendInit = Get-Content "$BACKEND\app\__init__.py" | Select-String '__version__\s*=\s*"0\.36\.1"'
Check "backend/app/__init__.py version" { $backendInit -ne $null }

$frontendPkg = Get-Content "$ROOT\frontend\package.json" | ConvertFrom-Json
Check "frontend/package.json version" { $frontendPkg.version -eq $expectedVersion }

$tauriConf = Get-Content "$ROOT\desktop\tauri\src-tauri\tauri.conf.json" | ConvertFrom-Json
Check "tauri.conf.json version" { $tauriConf.version -eq $expectedVersion }

$cargoToml = Get-Content "$ROOT\desktop\tauri\src-tauri\Cargo.toml" | Select-String '^version\s*=\s*"0\.36\.1"'
Check "Cargo.toml version" { $cargoToml -ne $null }

$mainPy = Get-Content "$BACKEND\app\main.py" | Select-String 'version"\s*:\s*"0\.36\.1"'
Check "main.py version constant" { $mainPy -ne $null }

$cfgVersion = Get-Content "$BACKEND\app\config.py" | Select-String 'app_version\s*=\s*os\.environ\.get\("OFFICEPILOT_APP_VERSION",\s*"0\.36\.1"\)'
Check "config.py default version" { $cfgVersion -ne $null }

$sidecarVersion = (Get-Item "$ROOT\desktop\tauri\src-tauri\target\release\officepilot-desktop.exe").VersionInfo
Check "Tauri EXE FileVersion = 0.36.1" { $sidecarVersion.FileVersion -eq $expectedVersion }
Check "Tauri EXE ProductVersion = 0.36.1" { $sidecarVersion.ProductVersion -eq $expectedVersion }
Write-Host ""

# ── 5. Backend API health (requires running backend) ───────────────────────
Write-Host "5. Backend API (requires running server)" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "$API_BASE/api/health" -TimeoutSec 5 -ErrorAction Stop
    Check "/api/health returns ok" { $health.ok -eq $true }
    Check "/api/health version = 0.36.1" { $health.version -eq $expectedVersion }
} catch {
    Write-Host "  [SKIP] Backend not running ($($_.Exception.Message))" -ForegroundColor Yellow
}

try {
    $updater = Invoke-RestMethod -Uri "$API_BASE/api/app/updater/windows/stable" -TimeoutSec 5 -ErrorAction Stop
    Check "/api/app/updater/windows/stable returns 200" { $updater -ne $null }
    Check "Updater version present" { $updater.version -ne $null }
} catch {
    Write-Host "  [SKIP] Updater endpoint not reachable ($($_.Exception.Message))" -ForegroundColor Yellow
}
Write-Host ""

# ── 6. No stale artifacts ──────────────────────────────────────────────────
Write-Host "6. Stale Artifact Risk" -ForegroundColor Yellow
$oldMsi = Get-ChildItem "$RELEASES\*.msi" | Where-Object { $_.Name -notlike "*0.36.1*" }
Check "No old version MSI in releases" { $oldMsi.Count -eq 0 }
$oldNsis = Get-ChildItem "$RELEASES\*.exe" | Where-Object { $_.Name -notlike "*0.36.1*" }
Check "No old version NSIS in releases" { $oldNsis.Count -eq 0 }
$builtMsi = Get-ChildItem "$ROOT\desktop\tauri\src-tauri\target\release\bundle\msi\*.msi" | Where-Object { $_.Name -notlike "*0.36.1*" }
Check "No pre-clean MSI in build output" { $builtMsi.Count -eq 0 }
Write-Host ""

# ── Summary ─────────────────────────────────────────────────────────────────
Write-Host "=============================" -ForegroundColor Cyan
if ($rc -eq 0) {
    Write-Host "RESULT: ALL CHECKS PASSED ($rc failures)" -ForegroundColor Green
} else {
    Write-Host "RESULT: $rc CHECK(S) FAILED" -ForegroundColor Red
}
Write-Host "=============================" -ForegroundColor Cyan
exit $rc
