#requires -Version 5.1
# Run on Windows with the desktop release ZIP. This uses a fresh save slot.
[CmdletBinding()]
param(
    [string]$Archive,
    [string]$OutputRoot = (Join-Path $PSScriptRoot '../tmp/qa/windows-package'),
    [switch]$CompatibilityRenderer
)

$ErrorActionPreference = 'Stop'
if (-not $Archive) {
    $builds = Join-Path $PSScriptRoot '../builds'
    $latest = Get-Content -Raw -LiteralPath (Join-Path $builds 'manifest.json') | ConvertFrom-Json
    $windows = @($latest.packages | Where-Object { $_.file -match '-Windows-x64\.zip$' })
    if ($windows.Count -ne 1) { throw 'Pass the release ZIP with -Archive.' }
    $Archive = Join-Path $builds $windows[0].file
}
$package = Get-Item -LiteralPath $Archive
$run = Join-Path ([IO.Path]::GetFullPath($OutputRoot)) ([guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $run
$save = New-Item -ItemType Directory -Path (Join-Path $run 'save')
$report = New-Item -ItemType Directory -Path (Join-Path $run 'report')
$extracted = Join-Path $run 'extracted'
$digest = (Get-FileHash -LiteralPath $package.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
if ($package.Name -match '^NightNine-(\d+\.\d+\.\d+)-Windows-x64\.zip$') {
    $manifestPath = Join-Path $package.DirectoryName "manifest-$($Matches[1]).json"
    if (Test-Path -LiteralPath $manifestPath) {
        $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
        $record = @($manifest.packages | Where-Object { $_.file -eq $package.Name })
        if ($record.Count -ne 1 -or $record[0].sha256 -ne $digest) {
            throw "Release checksum mismatch for $($package.Name)."
        }
    }
}
Write-Host "Testing $($package.Name) with SHA-256 $digest"
Write-Host "Test output goes in $run"
Expand-Archive -LiteralPath $package.FullName -DestinationPath $extracted
$executable = Get-Item -LiteralPath (Join-Path $extracted 'NightNine/NightNine.exe')

$start = New-Object System.Diagnostics.ProcessStartInfo
$start.FileName = $executable.FullName
$start.WorkingDirectory = $run
$start.UseShellExecute = $false
$start.EnvironmentVariables['NIGHT_NINE_SAVE_DIR'] = $save.FullName
$start.EnvironmentVariables['NIGHT_NINE_QA_DIR'] = $report.FullName
$start.EnvironmentVariables['NIGHT_NINE_QA_EXPECT_V4'] = '1'
$start.EnvironmentVariables['NIGHT_NINE_QA_EXPECT_INSERTS'] = '1'
$start.EnvironmentVariables.Remove('NIGHT_NINE_QA_START_AT')
$start.EnvironmentVariables.Remove('NIGHT_NINE_QA_STOP_AT')
$logPath = Join-Path $run 'campaign.log'
$start.Arguments = '--single-window --log-file "' + $logPath + '"'
if ($CompatibilityRenderer) {
    $start.Arguments += ' --rendering-method gl_compatibility'
}
$start.Arguments += ' -- --campaign-qa'
$process = [Diagnostics.Process]::Start($start)
try {
    if (-not $process.WaitForExit(1200000)) {
        $process.Kill()
        throw "The walkthrough timed out. See $run."
    }
    if ($process.ExitCode -ne 0) {
        throw "Night Nine exited with code $($process.ExitCode). See $run."
    }
} finally {
    $process.Dispose()
}

$resultPath = Join-Path $report.FullName 'campaign-render/results.json'
$result = Get-Content -Raw -LiteralPath $resultPath | ConvertFrom-Json
$runtimeErrors = Select-String -LiteralPath $logPath -Pattern '^ERROR:', 'SCRIPT ERROR:'
if ($runtimeErrors) {
    throw "Godot reported errors during the walkthrough. See $logPath."
}
$insertCount = @($result.chapter_inserts.PSObject.Properties).Count
if (-not $result.finished -or $result.failures.Count -ne 0 -or
    -not $result.required_v4 -or -not $result.required_inserts -or
    $result.scenes -ne 34 -or $result.played_lines -lt 337 -or
    $result.distinct_streams -lt 332 -or $insertCount -ne 10 -or
    $result.instrument_puzzles -lt 16 -or $result.checks -lt 3000 -or
    [string]::IsNullOrWhiteSpace($result.audio_driver) -or $result.audio_driver -eq 'Dummy') {
    throw "The report did not pass the full illustrated campaign checks. See $resultPath."
}
Write-Host "Passed $($result.checks) checks in $($result.scenes) scenes, using $($result.renderer) and $($result.audio_driver)."
Write-Host "Full report and screenshots are in $($report.FullName)."
