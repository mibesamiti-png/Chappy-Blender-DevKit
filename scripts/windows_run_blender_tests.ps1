<#
Windows one-click runner. Does not load user .blend, change startup settings,
install software, or send any files to remote services.
Optional: -BlenderPath "C:\...\blender.exe"
#>
param(
    [string]$BlenderPath = "",
    [switch]$SkipUnitTests
)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $repo
$reportDir = Join-Path $repo 'reports\latest'
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

function Resolve-Blender {
    param([string]$Explicit)
    if (-not [string]::IsNullOrWhiteSpace($Explicit)) {
        if (-not (Test-Path -LiteralPath $Explicit -PathType Leaf)) {
            throw "Blender executable not found: $Explicit"
        }
        return (Resolve-Path -LiteralPath $Explicit).Path
    }
    if ($env:CBDK_BLENDER_EXE) {
        return Resolve-Blender -Explicit $env:CBDK_BLENDER_EXE
    }
    $cmd = Get-Command 'blender.exe' -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { return $cmd.Source }

    $roots = @()
    if ($env:ProgramFiles) { $roots += (Join-Path $env:ProgramFiles 'Blender Foundation') }
    if (${env:ProgramFiles(x86)}) { $roots += (Join-Path ${env:ProgramFiles(x86)} 'Blender Foundation') }
    if ($env:LOCALAPPDATA) { $roots += (Join-Path $env:LOCALAPPDATA 'Programs\Blender Foundation') }
    $found = @()
    foreach ($folder in $roots) {
        if (-not (Test-Path -LiteralPath $folder -PathType Container)) { continue }
        $candidates = @(Get-ChildItem -LiteralPath $folder -Directory -ErrorAction SilentlyContinue |
            ForEach-Object { Join-Path $_.FullName 'blender.exe' } |
            Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
        $found += $candidates
    }
    if ($found.Count -eq 0) {
        throw 'Blender not found. Install Blender, or run with -BlenderPath "C:\...\blender.exe".'
    }
    return @($found | Sort-Object -Descending)[0]
}

function Resolve-Python {
    $launcher = Get-Command 'py.exe' -ErrorAction SilentlyContinue
    if ($launcher) {
        & $launcher.Source -3 -V *> $null
        if ($LASTEXITCODE -eq 0) { return @{ Cmd = $launcher.Source; Args = @('-3') } }
    }
    $python = Get-Command 'python.exe' -ErrorAction SilentlyContinue
    if ($python) {
        & $python.Source -V *> $null
        if ($LASTEXITCODE -eq 0) { return @{ Cmd = $python.Source; Args = @() } }
    }
    throw 'Python 3.11+ not found. Install Python 3, then launch this BAT again.'
}

try {
    $blender = Resolve-Blender -Explicit $BlenderPath
    $python = Resolve-Python
    $pycmd = $python.Cmd
    $pyargs = @($python.Args)
    Write-Host "Blender: $blender"
    Write-Host "Python:  $pycmd $($pyargs -join ' ')"
    & $blender --version | Select-Object -First 2

    if (-not $SkipUnitTests) {
        Write-Host "`n[1/3] Python unit tests..."
        $unitLog = Join-Path $reportDir 'python_unit_tests.log'
        & $pycmd @pyargs -m unittest discover -s tests -v *> $unitLog
        if ($LASTEXITCODE -ne 0) {
            Get-Content -LiteralPath $unitLog -Tail 25
            throw "Python tests failed. Log: $unitLog"
        }
        Get-Content -LiteralPath $unitLog -Tail 5
    }

    Write-Host "`n[2/3] Real Blender parts smoke tests..."
    $evidence = Join-Path $reportDir 'parts_evidence.json'
    $blenderLog = Join-Path $reportDir 'blender_parts.log'
    & $pycmd @pyargs -m cbdk verify-parts --blender $blender --timeout 180 --output $evidence *> $blenderLog
    if ($LASTEXITCODE -ne 0) {
        Get-Content -LiteralPath $blenderLog -Tail 25
        throw "Blender smoke test failed. Log: $blenderLog"
    }
    Get-Content -LiteralPath $blenderLog -Tail 10

    Write-Host "`n[3/3] Verify evidence matches current source hashes..."
    & $pycmd @pyargs -m cbdk evidence-status --evidence $evidence
    if ($LASTEXITCODE -ne 0) { throw 'Evidence is stale or incomplete.' }
    Write-Host "`nSUCCESS. Blender passed 3/3 authored helper smoke checks."
    Write-Host "Evidence: $evidence"
    Write-Host 'NOTE: Smoke passed != every version supported or license/part approved.'
    exit 0
} catch {
    Write-Host "`nERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Logs: $reportDir"
    exit 1
}
