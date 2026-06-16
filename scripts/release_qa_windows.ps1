<#
.SYNOPSIS
  OfficePilot AI — Release QA Script for Windows
.DESCRIPTION
  Runs backend tests, frontend tests, frontend build, sidecar build,
  Tauri build, artifact timestamp checks, version consistency checks,
  and optional API smoke checks.

  Output: PASS/FAIL summary with artifact paths and app version.

  Usage:
    .\scripts\release_qa_windows.ps1 [-SkipBuild] [-SkipTauri] [-ApiBaseUrl ""]
#>

param(
  [switch]$SkipBuild,
  [switch]$SkipTauri,
  [string]$ApiBaseUrl = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$startTime = Get-Date

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Pass($msg) { Write-Host "  [PASS] $msg" -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red; $script:hasFailures = $true }
function Write-Skip($msg) { Write-Host "  [SKIP] $msg" -ForegroundColor Yellow }

$results = @()
$hasFailures = $false

# ── App Version ─────────────────────────────────────────────────────────
Write-Step "1. Checking version consistency"
$versions = @{}

# frontend
$fePkg = Get-Content "$RepoRoot/frontend/package.json" | ConvertFrom-Json
$versions["frontend/package.json"] = $fePkg.version

# Tauri config
$tauriConf = Get-Content "$RepoRoot/desktop/tauri/src-tauri/tauri.conf.json" | ConvertFrom-Json
$versions["tauri.conf.json"] = $tauriConf.version

# Cargo.toml
$cargoMatch = Select-String -Path "$RepoRoot/desktop/tauri/src-tauri/Cargo.toml" -Pattern '^version = "(.+)"'
if ($cargoMatch) { $versions["Cargo.toml"] = $cargoMatch.Matches.Groups[1].Value }

# Backend config
$configMatch = Select-String -Path "$RepoRoot/backend/app/config.py" -Pattern 'app_version=os\.environ\.get\("OFFICEPILOT_APP_VERSION", "(.+)"\)'
if ($configMatch) { $versions["config.py"] = $configMatch.Matches.Groups[1].Value }

# Backend health endpoint
$healthMatch = Select-String -Path "$RepoRoot/backend/app/main.py" -Pattern '"version": "(.+)"' | Select-Object -First 1
if ($healthMatch) { $versions["main.py"] = $healthMatch.Matches.Groups[1].Value }

# Backend __init__.py
$initMatch = Select-String -Path "$RepoRoot/backend/app/__init__.py" -Pattern '__version__ = "(.+)"'
if ($initMatch) { $versions["__init__.py"] = $initMatch.Matches.Groups[1].Value }

$allSame = $versions.Values | Select-Object -Unique
if ($allSame.Count -eq 1) {
  Write-Pass "All version sources match: $($allSame[0])"
} else {
  Write-Fail "Version mismatch: $($versions | ConvertTo-Json -Compress)"
  Write-Host "Versions found:" -ForegroundColor Yellow
  $versions.Keys | ForEach-Object { Write-Host "  $_ = $($versions[$_])" }
}
$results += @{ task = "Version consistency"; status = if ($allSame.Count -eq 1) { "PASS" } else { "FAIL" }; detail = "$($versions.Values | Select-Object -Unique)" }

# ── Backend Tests ───────────────────────────────────────────────────────
Write-Step "2. Running backend tests"
$bkStart = Get-Date
try {
  $bkOutput = & python -m pytest -q --tb=short 2>&1
  $bkDuration = (Get-Date) - $bkStart
  if ($LASTEXITCODE -eq 0) {
    $bkPassed = ($bkOutput | Select-String -Pattern "passed" | Select-Object -Last 1).ToString()
    $bkFailed = ($bkOutput | Select-String -Pattern "failed" | Select-Object -Last 1).ToString()
    if (-not $bkFailed) { $bkFailed = "0 failed" }
    Write-Pass "Backend tests: $bkPassed in $($bkDuration.TotalSeconds.ToString('F1'))s"
    $results += @{ task = "Backend tests"; status = "PASS"; detail = "$bkPassed $bkFailed" }
  } else {
    Write-Fail "Backend tests failed (exit code $LASTEXITCODE)"
    $results += @{ task = "Backend tests"; status = "FAIL"; detail = "exit code $LASTEXITCODE" }
  }
} catch {
  Write-Fail "Backend tests error: $_"
  $results += @{ task = "Backend tests"; status = "ERROR"; detail = "$_" }
}

# ── Frontend Tests ──────────────────────────────────────────────────────
Write-Step "3. Running frontend tests"
$feStart = Get-Date
try {
  Push-Location "$RepoRoot/frontend"
  $feOutput = & npm test -- --run 2>&1
  Pop-Location
  $feDuration = (Get-Date) - $feStart
  if ($LASTEXITCODE -eq 0) {
    $fePassed = ($feOutput | Select-String -Pattern "Tests:" | Select-Object -Last 1).ToString()
    Write-Pass "Frontend tests: $fePassed in $($feDuration.TotalSeconds.ToString('F1'))s"
    $results += @{ task = "Frontend tests"; status = "PASS"; detail = "$fePassed" }
  } else {
    Write-Fail "Frontend tests failed (exit code $LASTEXITCODE)"
    $results += @{ task = "Frontend tests"; status = "FAIL"; detail = "exit code $LASTEXITCODE" }
  }
} catch {
  Write-Fail "Frontend tests error: $_"
  $results += @{ task = "Frontend tests"; status = "ERROR"; detail = "$_" }
}

# ── Frontend Build ──────────────────────────────────────────────────────
Write-Step "4. Building frontend"
if (-not $SkipBuild) {
  $feBuildStart = Get-Date
  try {
    Push-Location "$RepoRoot/frontend"
    $feBuildOutput = & npm run build 2>&1
    Pop-Location
    $feBuildDuration = (Get-Date) - $feBuildStart
    if ($LASTEXITCODE -eq 0) {
      Write-Pass "Frontend build succeeded in $($feBuildDuration.TotalSeconds.ToString('F1'))s"
      $results += @{ task = "Frontend build"; status = "PASS"; detail = "$($feBuildDuration.TotalSeconds.ToString('F1'))s" }
    } else {
      Write-Fail "Frontend build failed"
      $results += @{ task = "Frontend build"; status = "FAIL" }
    }
  } catch {
    Write-Fail "Frontend build error: $_"
    $results += @{ task = "Frontend build"; status = "ERROR" }
  }
} else {
  Write-Skip "Skipping frontend build"
  $results += @{ task = "Frontend build"; status = "SKIP" }
}

# ── Sidecar Build ──────────────────────────────────────────────────────
Write-Step "5. Building sidecar binary"
if (-not $SkipBuild) {
  $scStart = Get-Date
  try {
    & "$RepoRoot/scripts/build_sidecar_windows.ps1" 2>&1
    $scDuration = (Get-Date) - $scStart
    $sidecarExe = Get-ChildItem "$RepoRoot/desktop/tauri/src-tauri/binaries/officepilot-agent-*.exe" | Select-Object -First 1
    if ($sidecarExe) {
      Write-Pass "Sidecar built: $($sidecarExe.Name) ($($sidecarExe.Length/1MB|% {[math]::Round($_,1)}) MB) in $($scDuration.TotalMinutes.ToString('F1'))m"
      $results += @{ task = "Sidecar build"; status = "PASS"; detail = "$($sidecarExe.Name) $($sidecarExe.Length) bytes" }
    } else {
      Write-Fail "Sidecar binary not found after build"
      $results += @{ task = "Sidecar build"; status = "FAIL" }
    }
  } catch {
    Write-Fail "Sidecar build error: $_"
    $results += @{ task = "Sidecar build"; status = "ERROR" }
  }
} else {
  Write-Skip "Skipping sidecar build"
  $results += @{ task = "Sidecar build"; status = "SKIP" }
}

# ── Tauri Build ─────────────────────────────────────────────────────────
Write-Step "6. Building Tauri installer"
if (-not $SkipTauri) {
  $tauriStart = Get-Date
  try {
    Push-Location "$RepoRoot/desktop/tauri"
    $tauriOutput = & npx tauri build 2>&1
    Pop-Location
    $tauriDuration = (Get-Date) - $tauriStart

    $msiFiles = Get-ChildItem "$RepoRoot/desktop/tauri/src-tauri/target/release/bundle/msi/*.msi" -ErrorAction SilentlyContinue
    $nsisFiles = Get-ChildItem "$RepoRoot/desktop/tauri/src-tauri/target/release/bundle/nsis/*.exe" -ErrorAction SilentlyContinue

    if ($msiFiles -or $nsisFiles) {
      foreach ($msi in $msiFiles) {
        Write-Pass "MSI: $($msi.Name) ($([math]::Round($msi.Length/1MB,1)) MB, modified $($msi.LastWriteTime))"
      }
      foreach ($nsis in $nsisFiles) {
        Write-Pass "NSIS: $($nsis.Name) ($([math]::Round($nsis.Length/1MB,1)) MB, modified $($nsis.LastWriteTime))"
      }
      $results += @{ task = "Tauri build"; status = "PASS"; detail = "$($msiFiles.Count) MSI, $($nsisFiles.Count) NSIS in $($tauriDuration.TotalMinutes.ToString('F1'))m" }
    } else {
      Write-Fail "No installer artifacts found"
      $results += @{ task = "Tauri build"; status = "FAIL" }
    }
  } catch {
    Write-Fail "Tauri build error: $_"
    $results += @{ task = "Tauri build"; status = "ERROR" }
  }
} else {
  Write-Skip "Skipping Tauri build"
  $results += @{ task = "Tauri build"; status = "SKIP" }
}

# ── Artifact Timestamp Check ────────────────────────────────────────────
Write-Step "7. Checking artifact timestamps"
try {
  $sidecarExe = Get-ChildItem "$RepoRoot/desktop/tauri/src-tauri/binaries/officepilot-agent-*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
  $desktopExe = Get-Item "$RepoRoot/desktop/tauri/src-tauri/target/release/officepilot-desktop.exe" -ErrorAction SilentlyContinue

  if ($sidecarExe) {
    Write-Pass "Sidecar: $($sidecarExe.Name) — $($sidecarExe.LastWriteTime)"
  } else {
    Write-Skip "Sidecar binary not found"
  }
  if ($desktopExe) {
    Write-Pass "Desktop EXE: $($desktopExe.Length/1MB|% {[math]::Round($_,1)}) MB — $($desktopExe.LastWriteTime)"
  } else {
    Write-Skip "Desktop EXE not found"
  }
  $results += @{ task = "Artifact timestamps"; status = "PASS" }
} catch {
  Write-Fail "Artifact check error: $_"
  $results += @{ task = "Artifact timestamps"; status = "ERROR" }
}

# ── API Smoke Check ─────────────────────────────────────────────────────
Write-Step "8. API smoke check"
if ($ApiBaseUrl) {
  try {
    $health = Invoke-RestMethod -Uri "$ApiBaseUrl/api/health" -TimeoutSec 10
    if ($health.ok) {
      Write-Pass "API health: version=$($health.version) state=$($health.state)"
      $results += @{ task = "API smoke check"; status = "PASS"; detail = "version=$($health.version)" }
    } else {
      Write-Fail "API health returned not ok"
      $results += @{ task = "API smoke check"; status = "FAIL" }
    }
  } catch {
    Write-Fail "API smoke check failed: $_"
    $results += @{ task = "API smoke check"; status = "ERROR" }
  }
} else {
  Write-Skip "No ApiBaseUrl provided — skipping API smoke check"
  $results += @{ task = "API smoke check"; status = "SKIP" }
}

# ── Summary ─────────────────────────────────────────────────────────────
$totalDuration = (Get-Date) - $startTime
Write-Host "`n" -NoNewline
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "  RELEASE QA SUMMARY" -ForegroundColor Cyan
Write-Host "  Total time: $($totalDuration.TotalMinutes.ToString('F1'))m" -ForegroundColor Cyan
Write-Host "  App version: $($allSame[0])" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan

$passCount = 0
$failCount = 0
$skipCount = 0
foreach ($r in $results) {
  $icon = switch ($r.status) {
    "PASS" { $passCount++; "  [PASS]" }
    "FAIL" { $failCount++; "  [FAIL]" }
    "ERROR" { $failCount++; "  [FAIL]" }
    "SKIP" { $skipCount++; "  [SKIP]" }
  }
  $color = switch ($r.status) { "PASS" { "Green" } "FAIL" { "Red" } "ERROR" { "Red" } "SKIP" { "Yellow" } }
  Write-Host "$icon $($r.task)" -ForegroundColor $color
  if ($r.detail) { Write-Host "       $($r.detail)" -ForegroundColor Gray }
}

Write-Host "`n  $passCount passed, $failCount failed, $skipCount skipped" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Green" })
Write-Host ""

if ($hasFailures) { exit 1 }
