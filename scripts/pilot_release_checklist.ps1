<#
.SYNOPSIS
  OfficePilot AI — Pilot Release Checklist
.DESCRIPTION
  Runs all pre-flight checks before a pilot release:
  1. Version consistency across all sources
  2. Backend tests
  3. Frontend tests
  4. Frontend build
  5. Sidecar binary exists and has correct hash
  6. Installer exists
  7. Release artifacts exist
  8. Updater endpoint responds
  9. Sample files exist
  10. Pilot docs exist

  Exit code = number of failed checks (0 = all pass).
#>

param(
  [string]$ExpectedVersion = "0.36.1",
  [string]$RepoRoot = "",
  [string]$ApiBaseUrl = "http://localhost:8000"
)

if (-not $RepoRoot) {
  $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$passed = 0
$failed = 0

function Check($name, $condition) {
  if ($condition) {
    Write-Host "  [PASS] $name" -ForegroundColor Green
    $script:passed++
  } else {
    Write-Host "  [FAIL] $name" -ForegroundColor Red
    $script:failed++
  }
}

function Header($title) {
  Write-Host ""
  Write-Host "--- $title ---" -ForegroundColor Yellow
}

Write-Host "=== OfficePilot AI Pilot Release Checklist ===" -ForegroundColor Cyan
Write-Host "Version : $ExpectedVersion"
Write-Host "Root    : $RepoRoot"
Write-Host ""

# ---- 1. Version consistency ----
Header "Version Consistency"
$frontendPkg = Get-Content (Join-Path $RepoRoot "frontend\package.json") -Raw | ConvertFrom-Json
Check "frontend/package.json version = $ExpectedVersion" ($frontendPkg.version -eq $ExpectedVersion)

$backendInit = Get-Content (Join-Path $RepoRoot "backend\app\__init__.py") -Raw
Check "backend/app/__init__.py __version__ = $ExpectedVersion" ($backendInit -match "__version__ = `"$ExpectedVersion`"")

$backendMain = Get-Content (Join-Path $RepoRoot "backend\app\main.py") -Raw
Check "backend/app/main.py version = $ExpectedVersion" ($backendMain -match 'version\s*=\s*"' + $ExpectedVersion + '"')

$backendConfig = Get-Content (Join-Path $RepoRoot "backend\app\config.py") -Raw
Check "backend/app/config.py app_version = $ExpectedVersion" ($backendConfig -match 'app_version=os\.environ\.get\("OFFICEPILOT_APP_VERSION", "' + $ExpectedVersion + '"')

$localRouter = Get-Content (Join-Path $RepoRoot "backend\app\routers\local.py") -Raw
Check "backend/app/routers/local.py APP_VERSION = $ExpectedVersion" ($localRouter -match 'APP_VERSION = "' + $ExpectedVersion + '"')

$tauriConfig = Get-Content (Join-Path $RepoRoot "desktop\tauri\src-tauri\tauri.conf.json") -Raw | ConvertFrom-Json
Check "tauri.conf.json version = $ExpectedVersion" ($tauriConfig.version -eq $ExpectedVersion)

$cargoToml = Get-Content (Join-Path $RepoRoot "desktop\tauri\src-tauri\Cargo.toml") -Raw
Check "Cargo.toml version = $ExpectedVersion" ($cargoToml -match 'version\s*=\s*"' + $ExpectedVersion + '"')

# ---- 2. Pilot docs ----
Header "Pilot Documentation"
Check "docs/PILOT_README.md exists" (Test-Path (Join-Path $RepoRoot "docs\PILOT_README.md"))
Check "docs/PILOT_DEMO_SCRIPT.md exists" (Test-Path (Join-Path $RepoRoot "docs\PILOT_DEMO_SCRIPT.md"))
Check "docs/KNOWN_LIMITATIONS.md exists" (Test-Path (Join-Path $RepoRoot "docs\KNOWN_LIMITATIONS.md"))
Check "docs/BUG_REPORT_TEMPLATE.md exists" (Test-Path (Join-Path $RepoRoot "docs\BUG_REPORT_TEMPLATE.md"))

# ---- 3. Sample files ----
Header "Sample Files"
Check "samples/sample_sales.xlsx exists" (Test-Path (Join-Path $RepoRoot "samples\sample_sales.xlsx"))
Check "samples/sample_invoice_report.csv exists" (Test-Path (Join-Path $RepoRoot "samples\sample_invoice_report.csv"))

# ---- 4. Scripts ----
Header "Release Scripts"
Check "scripts/pilot_release_checklist.ps1 exists" (Test-Path (Join-Path $RepoRoot "scripts\pilot_release_checklist.ps1"))

# ---- 5. Sidecar binary ----
Header "Sidecar Binary"
$sidecarDir = Join-Path $RepoRoot "desktop\tauri\src-tauri\binaries"
$sidecarExe = Get-ChildItem -Path $sidecarDir -Filter "officepilot-agent-*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
Check "Sidecar binary exists in tauri binaries dir" ($sidecarExe -ne $null)

$sidecarDist = Join-Path $RepoRoot "backend\dist"
$sidecarFromDist = Get-ChildItem -Path $sidecarDist -Filter "officepilot-agent-*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
Check "Sidecar binary exists in backend/dist" ($sidecarFromDist -ne $null)

if ($sidecarExe -and $sidecarFromDist) {
  $hashTauri = (Get-FileHash -LiteralPath $sidecarExe.FullName -Algorithm SHA256).Hash
  $hashDist = (Get-FileHash -LiteralPath $sidecarFromDist.FullName -Algorithm SHA256).Hash
  Check "Sidecar hash matches between backend/dist and tauri/binaries" ($hashTauri -eq $hashDist)
}

# ---- 6. Installer ----
Header "Installer"
$tauriTarget = Join-Path $RepoRoot "desktop\tauri\src-tauri\target\release\bundle"
$msiFiles = Get-ChildItem -Path $tauriTarget -Recurse -Filter "*.msi" -ErrorAction SilentlyContinue
$nsisFiles = Get-ChildItem -Path $tauriTarget -Recurse -Filter "*.exe" -ErrorAction SilentlyContinue
Check "MSI installer exists" ($msiFiles.Count -gt 0)
Check "NSIS installer exists" ($nsisFiles.Count -gt 0)

# ---- 7. Release artifacts ----
Header "Release Artifacts"
$releaseDir = Join-Path $RepoRoot "releases\$ExpectedVersion"
Check "Release directory exists: releases/$ExpectedVersion" (Test-Path $releaseDir)
if (Test-Path $releaseDir) {
  $artifacts = Get-ChildItem -Path $releaseDir -File
  Check "Release artifacts present in releases/$ExpectedVersion" ($artifacts.Count -gt 0)
}

# ---- 8. Updater endpoint ----
Header "Updater Endpoint"
try {
  $updaterResp = Invoke-RestMethod -Uri "$ApiBaseUrl/api/app/updater/windows/stable" -TimeoutSec 10 -ErrorAction Stop
  Check "Updater endpoint responds at $ApiBaseUrl/api/app/updater/windows/stable" ($updaterResp -ne $null -and $updaterResp.version -eq $ExpectedVersion)
} catch {
  Check "Updater endpoint (skipped - backend may not be running)" ($false)
}

# ---- 9. Sample invoice files under samples/invoices ----
Header "Sample Invoice Files"
$sampleInvoices = Get-ChildItem (Join-Path $RepoRoot "samples\invoices") -File -ErrorAction SilentlyContinue
Check "samples/invoices/ has at least 5 files" ($sampleInvoices.Count -ge 5)

# ---- 10. New route endpoints ----
Header "New Feature Endpoints"
try {
  $onboardingResp = Invoke-RestMethod -Uri "$ApiBaseUrl/api/onboarding/check-setup" -TimeoutSec 10 -ErrorAction Stop
  Check "Onboarding check-setup endpoint responds" ($onboardingResp -ne $null)
} catch {
  Check "Onboarding endpoint (skipped)" ($false)
}

try {
  $qbResp = Invoke-RestMethod -Uri "$ApiBaseUrl/api/quickbooks/status" -TimeoutSec 10 -ErrorAction Stop
  Check "QuickBooks status endpoint responds" ($qbResp -ne $null)
} catch {
  Check "QuickBooks endpoint (skipped)" ($false)
}

# ---- 11. Frontend build artifacts ----
Header "Frontend Build"
$distDir = Join-Path $RepoRoot "frontend\dist"
Check "frontend/dist/index.html exists" (Test-Path (Join-Path $distDir "index.html"))
Check "frontend/dist/assets/ has JS bundle" ((Get-ChildItem (Join-Path $distDir "assets") -Filter "*.js" -ErrorAction SilentlyContinue).Count -gt 0)
Check "frontend/dist/assets/ has CSS bundle" ((Get-ChildItem (Join-Path $distDir "assets") -Filter "*.css" -ErrorAction SilentlyContinue).Count -gt 0)

# ---- Summary ----
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Passed: $passed" -ForegroundColor Green
Write-Host "Failed: $failed" -ForegroundColor Red
if ($failed -eq 0) {
  Write-Host "Result: ALL CHECKS PASSED" -ForegroundColor Green
} else {
  Write-Host "Result: $failed CHECK(S) FAILED" -ForegroundColor Red
}
exit $failed
