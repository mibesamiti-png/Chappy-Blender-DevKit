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
    # Only 3.11 - 3.13 have passed CBDK's current full test suite.
    # 'py -3' can select a newer Python (3.15 on GitHub Windows runners).
    $probe = 'import sys; sys.exit(0 if (3,11) <= sys.version_info[:2] <= (3,13) else 1)'
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        $check = Invoke-Logged -Executable $python.Source -CommandArgs @('-c', $probe) -LogPath (Join-Path $reportDir 'python_version_probe.log')
        if ($check -eq 0) { return @{ Cmd = $python.Source; Args = @() } }
    }
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        foreach ($version in @('3.13','3.12','3.11')) {
            $selector = '-' + $version
            $check = Invoke-Logged -Executable $launcher.Source -CommandArgs @($selector, '-c', $probe) -LogPath (Join-Path $reportDir 'python_version_probe.log')
            if ($check -eq 0) { return @{ Cmd = $launcher.Source; Args = @($selector) } }
        }
    }
    throw 'CBDK needs Python 3.11, 3.12 or 3.13. Newer versions are not validated by the current suite.'
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
        Write-Host "`n[1/3] Python unit tests (stderr-safe)..."
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
    Write-Host '[Matrix] Summarize per-version evidence...'
    $matrixLog = Join-Path $reportDir 'parts_matrix.log'
    $matrixOutput = Join-Path $reportDir 'parts_matrix.json'
    $matrixRc = Invoke-Logged -Executable $pycmd -CommandArgs ($pyargs + @(
        '-m','cbdk','part-matrix','--catalog',(Join-Path $repo 'catalog\authored_parts.json'),
        '--evidence-dir',$reportDir,'--output',$matrixOutput
    )) -LogPath $matrixLog
    Get-Content -LiteralPath $matrixLog -Tail 8
    if ($matrixRc -ne 0) {
        Write-Host 'WARNING: Part matrix had missing or stale reports. Check parts_matrix.log.' -ForegroundColor Yellow
    } else {
        Write-Host "Part matrix saved: $matrixOutput"
    }
    Write-Host "SUCCESS: $($blenders.Count)/$($blenders.Count) Blender installations passed."
    Write-Host "Reports: $reportDir"
    Write-Host 'Blender smoke success does not constitute formal component approval.'
    exit 0
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Logs: $reportDir"
    exit 1
}
