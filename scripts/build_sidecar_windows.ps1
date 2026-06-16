<#
.SYNOPSIS
    Build the OfficePilot AI sidecar (Phase 8) for Windows.

.DESCRIPTION
    Wraps PyInstaller with the settings OfficePilot needs:

    * Builds ``officepilot-agent.exe`` from backend/officepilot_sidecar.py
    * Bundles every parser/OCR/Excel dependency the FastAPI agent imports
    * Renames the output to the Tauri 2.0 sidecar convention
      ``officepilot-agent-x86_64-pc-windows-msvc.exe``
    * Copies it into ``desktop/tauri/src-tauri/binaries/``
      so ``cargo tauri build`` picks it up automatically.

.PARAMETER Clean
    Wipe the PyInstaller build/ and dist/ folders first.

.PARAMETER SkipInstall
    Skip ``pip install -r backend/requirements.txt``.

.PARAMETER TargetTriple
    Defaults to ``x86_64-pc-windows-msvc`` which matches the
    Rust target Tauri uses on Windows. Override only if you are
    building for a different arch.

.EXAMPLE
    .\scripts\build_sidecar_windows.ps1
    .\scripts\build_sidecar_windows.ps1 -Clean
    .\scripts\build_sidecar_windows.ps1 -SkipInstall

.NOTES
    Requires Python 3.11+ and a working MSVC toolchain. The
    produced .exe is unsigned and will trigger SmartScreen on
    first run when launched outside the Tauri bundle.
#>

[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$SkipInstall,
    [string]$TargetTriple = "x86_64-pc-windows-msvc"
)

$ErrorActionPreference = "Stop"

# --------------------------------------------------------------- paths
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot    = Resolve-Path (Join-Path $ScriptDir "..")
$BackendDir  = Join-Path $RepoRoot "backend"
$SpecFile    = Join-Path $ScriptDir "officepilot_sidecar.spec"
$SidecarSrc  = Join-Path $BackendDir "officepilot_sidecar.py"
$PyWorkdir   = Join-Path $BackendDir "build"
$PyDistdir   = Join-Path $BackendDir "dist"
$SidecarOutBare = Join-Path $PyDistdir "officepilot-agent.exe"
# Tauri 2.0 sidecar naming convention: <name>-<target-triple><.exe>
$TauriBinDir = Join-Path $RepoRoot "desktop/tauri/src-tauri/binaries"
$TauriSidecarNamed = Join-Path $TauriBinDir "officepilot-agent-$TargetTriple.exe"

Write-Host ""
Write-Host "== OfficePilot AI sidecar build =="
Write-Host "  repo       : $RepoRoot"
Write-Host "  backend    : $BackendDir"
Write-Host "  spec       : $SpecFile"
Write-Host "  entrypoint : $SidecarSrc"
Write-Host "  py workdir : $PyWorkdir"
Write-Host "  py distdir : $PyDistdir"
Write-Host "  target     : $TargetTriple"
Write-Host "  tauri bin  : $TauriBinDir"
Write-Host ""

# --------------------------------------------------------------- guards
if (-not (Test-Path -LiteralPath $BackendDir)) {
    throw "backend/ directory not found at $BackendDir"
}
if (-not (Test-Path -LiteralPath $SidecarSrc)) {
    throw "sidecar entry point not found at $SidecarSrc (did you create backend/officepilot_sidecar.py?)"
}
if (-not (Test-Path -LiteralPath $SpecFile)) {
    throw "PyInstaller spec not found at $SpecFile"
}

# --------------------------------------------------------------- python
$python = $null
foreach ($cand in @("python", "python3", "py")) {
    $p = Get-Command $cand -ErrorAction SilentlyContinue
    if ($p) { $python = $p.Source; break }
}
if (-not $python) {
    throw "Python 3.11+ was not found on PATH. Install it from https://python.org and re-run."
}
Write-Host "Using Python: $python"
$pyVer = & $python -c "import sys; print('%d.%d' % sys.version_info[:2])"
Write-Host "Python version: $pyVer"
$pyMajor, $pyMinor = $pyVer.Split(".")
if ([int]$pyMajor -lt 3 -or ([int]$pyMajor -eq 3 -and [int]$pyMinor -lt 11)) {
    throw "Python 3.11+ is required (got $pyVer)."
}

# --------------------------------------------------------------- pip
if (-not $SkipInstall) {
    Write-Host ""
    Write-Host "--> (1/4) pip install -r backend/requirements.txt"
    Push-Location $BackendDir
    try {
        & $python -m pip install --upgrade pip | Out-Host
        & $python -m pip install -r "requirements.txt" | Out-Host
        # PyInstaller is a build-time dep, not a runtime one.
        & $python -m pip install "pyinstaller>=6.0" | Out-Host
    } finally {
        Pop-Location
    }
} else {
    Write-Host ""
    Write-Host "--> (1/4) skipping pip install (SkipInstall set)"
}

# --------------------------------------------------------------- clean
if ($Clean) {
    Write-Host ""
    Write-Host "--> (2/4) clean build/ and dist/"
    if (Test-Path -LiteralPath $PyWorkdir) {
        Remove-Item -LiteralPath $PyWorkdir -Recurse -Force
    }
    if (Test-Path -LiteralPath $PyDistdir) {
        Remove-Item -LiteralPath $PyDistdir -Recurse -Force
    }
} else {
    Write-Host ""
    Write-Host "--> (2/4) reusing existing build/ and dist/ (pass -Clean to wipe)"
}

# --------------------------------------------------------------- pyinstaller
Write-Host ""
Write-Host "--> (3/4) pyinstaller build"
Push-Location $BackendDir
try {
    # Run PyInstaller with our spec. We use the module form so we
    # do not depend on the pyinstaller.exe shim being on PATH.
    & $python -m PyInstaller --noconfirm --clean "$SpecFile"
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller exited with code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $SidecarOutBare)) {
    throw "PyInstaller did not produce $SidecarOutBare. Check the log above."
}

# --------------------------------------------------------------- tauri
Write-Host ""
Write-Host "--> (4/4) copy sidecar to Tauri binaries dir"

# Destination inside backend/dist for local reference (Tauri 2.0 naming convention)
$TauriSidecarNamed = Join-Path $PyDistdir "officepilot-agent-$TargetTriple.exe"
Copy-Item -LiteralPath $SidecarOutBare -Destination $TauriSidecarNamed -Force

# Destination inside Tauri binaries dir so cargo tauri build picks it up
if (-not (Test-Path -LiteralPath $TauriBinDir)) {
    New-Item -ItemType Directory -Path $TauriBinDir -Force | Out-Null
}
$TauriSidecarTarget = Join-Path $TauriBinDir "officepilot-agent-$TargetTriple.exe"
Copy-Item -LiteralPath $SidecarOutBare -Destination $TauriSidecarTarget -Force

if (-not (Test-Path -LiteralPath $TauriSidecarTarget)) {
    throw "Tauri sidecar copy failed: $TauriSidecarTarget"
}

$builtInfo = Get-ChildItem -LiteralPath $SidecarOutBare
$tauriInfo = Get-ChildItem -LiteralPath $TauriSidecarTarget
Write-Host ""
Write-Host "  backend/dist : $($builtInfo.FullName)"
Write-Host "    size       : $($builtInfo.Length) bytes"
Write-Host "    time       : $($builtInfo.LastWriteTime)"
Write-Host ""
Write-Host "  tauri/bin    : $($tauriInfo.FullName)"
Write-Host "    size       : $($tauriInfo.Length) bytes"
Write-Host "    time       : $($tauriInfo.LastWriteTime)"
Write-Host ""
Write-Host "  Tauri will bundle this into:"
Write-Host "    desktop/tauri/src-tauri/target/release/bundle/{msi,nsis}/..."
Write-Host ""
Write-Host "NOTE: Whisper model (`ggml-small.bin`, ~500 MB) is NOT bundled in the"
Write-Host "      sidecar or installer. It must be downloaded separately via:"
Write-Host "      (1) Voice Settings → Download Model in the app UI, or"
Write-Host "      (2) cd backend && python -c ""from app.services.windows_voice_layer import download_model; print(download_model('ggml-small.bin'))"""
Write-Host "      Bundling the model in tauri.conf.json resources would add ~500 MB"
Write-Host "      to every installer, which is not recommended for distribution."
Write-Host "      Consider a first-run download prompt or a separate installer."
Write-Host ""
Write-Host "Done. Next steps:"
Write-Host "  cd desktop/tauri"
Write-Host "  cargo tauri dev     # dev with bundled sidecar"
Write-Host "  cargo tauri build   # produces signed installer (after you configure code signing)"
Write-Host ""
