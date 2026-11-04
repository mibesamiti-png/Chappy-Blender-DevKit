<#
Run Python tests once and Blender smoke on every installed version.
Use -BlenderPath "C:\...\blender.exe" to select only one; -UnitOnly for Windows CI.
#>
param(
    [string]$BlenderPath = '',
    [switch]$SkipUnitTests,
    [switch]$UnitOnly
)
$ErrorActionPreference = 'Stop'
$env:PYTHONIOENCODING = 'utf-8'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $repo
$reportDir = Join-Path $repo 'reports\latest'
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

function Resolve-Blenders {
    param([string]$Explicit)
    if ($Explicit) {
        if (-not (Test-Path -LiteralPath $Explicit -PathType Leaf)) { throw "Blender not found: $Explicit" }
        return (Resolve-Path -LiteralPath $Explicit).Path
    }
    $found = @()
    if ($env:CBDK_BLENDER_EXE -and (Test-Path -LiteralPath $env:CBDK_BLENDER_EXE -PathType Leaf)) {
        $found += (Resolve-Path -LiteralPath $env:CBDK_BLENDER_EXE).Path
    }
    $cmd = Get-Command blender.exe -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { $found += $cmd.Source }
    $roots = @()
    if ($env:ProgramFiles) { $roots += (Join-Path $env:ProgramFiles 'Blender Foundation') }
    if (${env:ProgramFiles(x86)}) { $roots += (Join-Path ${env:ProgramFiles(x86)} 'Blender Foundation') }
    if ($env:LOCALAPPDATA) { $roots += (Join-Path $env:LOCALAPPDATA 'Programs\Blender Foundation') }
    foreach ($root in $roots) {
        if (Test-Path -LiteralPath $root -PathType Container) {
            $found += @(Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue |
                ForEach-Object { Join-Path $_.FullName 'blender.exe' } |
                Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })
        }
    }
    $found = @($found | Sort-Object -Unique)
    if ($found.Count -eq 0) { throw 'Blender not found; specify -BlenderPath "C:\...\blender.exe"' }
    return $found
}

function Resolve-Python {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        & $launcher.Source -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" *> $null
        if ($LASTEXITCODE -eq 0) { return @{ Cmd = $launcher.Source; Args = @('-3') } }
    }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        & $python.Source -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" *> $null
        if ($LASTEXITCODE -eq 0) { return @{ Cmd = $python.Source; Args = @() } }
    }
    throw 'Python 3.11+ not found'
}

function Invoke-Logged {
    param([string]$Executable, [string[]]$CommandArgs, [string]$LogPath)
    # PS 5.1: unittest -v writes successful test results to native stderr;
    # redirect through Start-Process so ErrorActionPreference=Stop cannot abort.
    $stdoutPath = $LogPath + '.stdout'
    $stderrPath = $LogPath + '.stderr'
    $argsLine = (@($CommandArgs) | ForEach-Object {
        if ($_.Contains('"')) { throw 'Unexpected quote in process argument' }
        if ($_ -match '\s') { '"' + $_ + '"' } else { $_ }
    }) -join ' '
    $proc = Start-Process -FilePath $Executable -ArgumentList $argsLine -Wait -PassThru -NoNewWindow -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    $out = Get-Content -LiteralPath $stdoutPath -Raw -Encoding UTF8
    $err = Get-Content -LiteralPath $stderrPath -Raw -Encoding UTF8
    Set-Content -LiteralPath $LogPath -Encoding UTF8 -Value ("[stdout]`n" + $out + "`n[stderr]`n" + $err)
    return [int]$proc.ExitCode
}

try {
    if ($UnitOnly -and $SkipUnitTests) { throw 'Cannot combine -UnitOnly and -SkipUnitTests' }
    $python = Resolve-Python
    $pycmd = $python.Cmd
    $pyargs = @($python.Args)
    Write-Host "Python: $pycmd $($pyargs -join ' ')"
    if (-not $SkipUnitTests) {
        Write-Host '`n[1/3] Python unit tests (stderr-safe)...'
        $unitLog = Join-Path $reportDir 'python_unit_tests.log'
        $rc = Invoke-Logged -Executable $pycmd -CommandArgs ($pyargs + @('-m','unittest','discover','-s','tests','-v')) -LogPath $unitLog
        Get-Content -LiteralPath $unitLog -Tail 8
        if ($rc -ne 0) { throw "Python tests failed (exit $rc): $unitLog" }
    }
    if ($UnitOnly) {
        Write-Host 'SUCCESS: Windows Python native-stderr regression passed.'
        exit 0
    }
    $blenders = @(Resolve-Blenders -Explicit $BlenderPath)
    Write-Host "Detected Blender executables: $($blenders.Count)"
    $failures = @()
    $i = 0
    foreach ($blender in $blenders) {
        $i++
        Write-Host "`n[$i/$($blenders.Count)] Blender: $blender"
        $versionLog = Join-Path $reportDir "version_$i.log"
        $rc = Invoke-Logged -Executable $blender -CommandArgs @('--version') -LogPath $versionLog
        if ($rc -ne 0) { $failures += $blender; Write-Host 'Blender version check failed'; continue }
        $versionText = Get-Content -LiteralPath $versionLog -Raw -Encoding UTF8
        $match = [regex]::Match($versionText, 'Blender\s+(\d+\.\d+\.\d+)')
        $label = if ($match.Success) { 'Blender_' + ($match.Groups[1].Value -replace '\.','_') } else { "Blender_unknown_$i" }
        $evidence = Join-Path $reportDir "parts_evidence_$($label)_$i.json"
        $log = Join-Path $reportDir "blender_parts_$($label)_$i.log"
        Write-Host "[2/3] Runtime smoke: $label"
        $rc = Invoke-Logged -Executable $pycmd -CommandArgs ($pyargs + @('-m','cbdk','verify-parts','--blender',$blender,'--timeout','180','--output',$evidence)) -LogPath $log
        Get-Content -LiteralPath $log -Tail 8
        if ($rc -ne 0) { $failures += $blender; Write-Host "FAIL: $label (see $log)" -ForegroundColor Red; continue }
        $statusLog = Join-Path $reportDir "evidence_status_$($label)_$i.log"
        Write-Host '[3/3] Evidence freshness'
        $rc = Invoke-Logged -Executable $pycmd -CommandArgs ($pyargs + @('-m','cbdk','evidence-status','--evidence',$evidence)) -LogPath $statusLog
        if ($rc -ne 0) { $failures += $blender; Write-Host "FAIL: Evidence stale on $label" -ForegroundColor Red; continue }
        Write-Host "PASS: $label; evidence: $evidence" -ForegroundColor Green
    }
    if ($failures.Count -gt 0) { throw "$($failures.Count)/$($blenders.Count) Blender installations failed; all were attempted." }
    Write-Host "SUCCESS: $($blenders.Count)/$($blenders.Count) Blender installations passed."
    Write-Host "Reports: $reportDir"
    Write-Host 'Blender smoke success does not constitute formal component approval.'
    exit 0
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Logs: $reportDir"
    exit 1
}
