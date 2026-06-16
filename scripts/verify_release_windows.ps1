<#
.SYNOPSIS
  OfficePilot AI — Release Build Verification Script (Windows)
.DESCRIPTION
  Verifies that all required binaries, config files, sample data, and
  documentation exist before a release. Does NOT require internet access.
#>

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
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

Write-Host "=== OfficePilot AI Release Verification ===" -ForegroundColor Cyan
Write-Host "Root: $root"
Write-Host ""

# 1. App binary (sidecar)
Write-Host "--- Binaries ---" -ForegroundColor Yellow
$sidecarDir = Join-Path $root "desktop\tauri\src-tauri\binaries"
$sidecarExe = Get-ChildItem -Path $sidecarDir -Filter "officepilot-agent-*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
Check "Sidecar binary exists" ($sidecarExe -ne $null)

# 2. Installer exists (optional - can be built later)
$installerDir = Join-Path $root "target\release"
$msi = Get-ChildItem -Path $installerDir -Filter "*.msi" -ErrorAction SilentlyContinue | Select-Object -First 1
$exeInstaller = Get-ChildItem -Path $installerDir -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
Check "Installer exists (MSI or EXE)" (($msi -ne $null) -or ($exeInstaller -ne $null))

# 3. Version files
Write-Host ""
Write-Host "--- Version Files ---" -ForegroundColor Yellow
$mainPy = Get-Content (Join-Path $root "backend\app\main.py") -Raw
Check "main.py has version string" ($mainPy -match 'version\s*=\s*"0\.18\.0"')

$pkgJson = Get-Content (Join-Path $root "frontend\package.json") -Raw | ConvertFrom-Json
Check "frontend/package.json version" ($pkgJson.version -eq "0.18.0")

# 4. .env.example
Write-Host ""
Write-Host "--- Config ---" -ForegroundColor Yellow
$envExample = Get-Content (Join-Path $root ".env.example") -Raw
Check ".env.example exists" (Test-Path (Join-Path $root ".env.example"))
Check ".env.example has DEMO_MODE" ($envExample -match "DEMO_MODE")
Check ".env.example has JWT_SECRET" ($envExample -match "JWT_SECRET")

# 5. Sample files
Write-Host ""
Write-Host "--- Sample Files ---" -ForegroundColor Yellow
Check "samples/README.md exists" (Test-Path (Join-Path $root "samples\README.md"))
Check "samples/invoices/ has files" ((Get-ChildItem (Join-Path $root "samples\invoices") -File).Count -ge 5)
Check "samples/excel/ has files" ((Get-ChildItem (Join-Path $root "samples\excel") -File).Count -ge 1)
Check "samples/audit/ has files" ((Get-ChildItem (Join-Path $root "samples\audit") -File).Count -ge 1)
Check "samples/workflows/ has files" ((Get-ChildItem (Join-Path $root "samples\workflows") -File).Count -ge 1)
Check "samples/accounting/ has files" ((Get-ChildItem (Join-Path $root "samples\accounting") -File).Count -ge 1)
Check "samples/browser/ has files" ((Get-ChildItem (Join-Path $root "samples\browser") -File).Count -ge 1)

# 6. Docs
Write-Host ""
Write-Host "--- Documentation ---" -ForegroundColor Yellow
Check "docs/CLEAN_WINDOWS_QA.md exists" (Test-Path (Join-Path $root "docs\CLEAN_WINDOWS_QA.md"))
Check "docs/DEMO_MODE.md exists" (Test-Path (Join-Path $root "docs\DEMO_MODE.md"))
Check "docs/ONBOARDING.md exists" (Test-Path (Join-Path $root "docs\ONBOARDING.md"))
Check "docs/RELEASE_CHECKLIST.md exists" (Test-Path (Join-Path $root "docs\RELEASE_CHECKLIST.md"))

# 7. Backend structure
Write-Host ""
Write-Host "--- Backend Structure ---" -ForegroundColor Yellow
Check "backend/app/routers/demo.py exists" (Test-Path (Join-Path $root "backend\app\routers\demo.py"))
Check "backend/app/routers/onboarding.py exists" (Test-Path (Join-Path $root "backend\app\routers\onboarding.py"))
Check "backend/app/routers/about.py exists" (Test-Path (Join-Path $root "backend\app\routers\about.py"))
Check "backend/app/routers/diagnostics.py exists" (Test-Path (Join-Path $root "backend\app\routers\diagnostics.py"))
Check "backend/app/services/demo.py exists" (Test-Path (Join-Path $root "backend\app\services\demo.py"))
Check "backend/app/services/onboarding.py exists" (Test-Path (Join-Path $root "backend\app\services\onboarding.py"))
Check "backend/app/services/diagnostics.py exists" (Test-Path (Join-Path $root "backend\app\services\diagnostics.py"))
Check "backend/app/models/onboarding_state.py exists" (Test-Path (Join-Path $root "backend\app\models\onboarding_state.py"))

# 8. Frontend pages
Write-Host ""
Write-Host "--- Frontend Pages ---" -ForegroundColor Yellow
Check "frontend/src/pages/DemoMode.jsx exists" (Test-Path (Join-Path $root "frontend\src\pages\DemoMode.jsx"))
Check "frontend/src/pages/About.jsx exists" (Test-Path (Join-Path $root "frontend\src\pages\About.jsx"))
Check "frontend/src/pages/FirstRunDiagnostics.jsx exists" (Test-Path (Join-Path $root "frontend\src\pages\FirstRunDiagnostics.jsx"))
Check "frontend/src/components/OnboardingChecklist.jsx exists" (Test-Path (Join-Path $root "frontend\src\components\OnboardingChecklist.jsx"))

# 9. Test commands documented
Write-Host ""
Write-Host "--- Test Commands ---" -ForegroundColor Yellow
$agents = Get-Content (Join-Path $root "AGENTS.md") -Raw
Check "AGENTS.md documents backend tests" ($agents -match "python -m pytest")
Check "AGENTS.md documents frontend tests" ($agents -match "npm test")

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
