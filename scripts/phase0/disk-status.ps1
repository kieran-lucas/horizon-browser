[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('before', 'after', 'milestone')]
    [string] $Stage,

    [ValidateSet('fetch', 'gclient-sync', 'hooks', 'toolchain-install', 'gn-gen', 'build', 'update', 'milestone')]
    [string] $Operation = 'milestone',

    [string] $GuardPath = '',

    [ValidateRange(0, 1000)]
    [double] $EstimatedGrowthGiB = 0,

    [ValidateRange(0, 1000)]
    [double] $EstimatedNextGrowthGiB = 0,

    [string] $CleanupPerformed = 'None',

    [string] $Label = ''
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$configPath = Join-Path $repoRoot 'phase0-storage.json'
$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$bytesPerGiB = 1GB

function Resolve-ConfiguredPath {
    param([Parameter(Mandatory = $true)][string] $ConfiguredPath)

    if ([System.IO.Path]::IsPathRooted($ConfiguredPath)) {
        return [System.IO.Path]::GetFullPath($ConfiguredPath)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $repoRoot $ConfiguredPath))
}

function Test-PathWithin {
    param(
        [Parameter(Mandatory = $true)][string] $Candidate,
        [Parameter(Mandatory = $true)][string] $Parent
    )

    $candidateFull = [System.IO.Path]::GetFullPath($Candidate).TrimEnd('\') + '\'
    $parentFull = [System.IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
    return $candidateFull.StartsWith($parentFull, [System.StringComparison]::OrdinalIgnoreCase)
}

function Get-DirectoryMeasurement {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [string[]] $Exclude = @()
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        return [ordered]@{ bytes = 0L; gib = 0.0; files = 0L; skipped = 0L; exists = $false }
    }

    $excludedRoots = @($Exclude | ForEach-Object {
        [System.IO.Path]::GetFullPath($_).TrimEnd('\') + '\'
    })
    $pending = [System.Collections.Generic.Stack[string]]::new()
    $pending.Push([System.IO.Path]::GetFullPath($Path))
    [long] $totalBytes = 0
    [long] $fileCount = 0
    [long] $skipped = 0

    while ($pending.Count -gt 0) {
        $current = $pending.Pop()
        $currentPrefix = $current.TrimEnd('\') + '\'
        $isExcluded = $false
        foreach ($excludedRoot in $excludedRoots) {
            if ($currentPrefix.StartsWith($excludedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
                $isExcluded = $true
                break
            }
        }
        if ($isExcluded) {
            continue
        }

        try {
            foreach ($file in [System.IO.Directory]::EnumerateFiles($current)) {
                try {
                    $fileInfo = [System.IO.FileInfo]::new($file)
                    $totalBytes += $fileInfo.Length
                    $fileCount++
                } catch {
                    $skipped++
                }
            }
            foreach ($directory in [System.IO.Directory]::EnumerateDirectories($current)) {
                try {
                    $directoryInfo = [System.IO.DirectoryInfo]::new($directory)
                    if (($directoryInfo.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) {
                        $skipped++
                        continue
                    }
                    $pending.Push($directory)
                } catch {
                    $skipped++
                }
            }
        } catch {
            $skipped++
        }
    }

    return [ordered]@{
        bytes = $totalBytes
        gib = [Math]::Round($totalBytes / $bytesPerGiB, 2)
        files = $fileCount
        skipped = $skipped
        exists = $true
    }
}

$checkoutRoot = Resolve-ConfiguredPath $config.checkout_root
$sourceTree = Resolve-ConfiguredPath $config.source_tree
$buildOutput = Resolve-ConfiguredPath $config.build_output
$depotTools = Resolve-ConfiguredPath $config.depot_tools
$artifactRoot = Resolve-ConfiguredPath $config.artifact_root
$taskTemp = Resolve-ConfiguredPath $config.task_temp
$engineRoot = Split-Path -Parent $checkoutRoot

foreach ($managedPath in @($checkoutRoot, $sourceTree, $buildOutput, $depotTools, $artifactRoot, $taskTemp)) {
    if (-not (Test-PathWithin -Candidate $managedPath -Parent $repoRoot)) {
        throw "Configured Phase 0 path escapes the repository: $managedPath"
    }
}

$guardPathResolved = if ([string]::IsNullOrWhiteSpace($GuardPath)) {
    $checkoutRoot
} elseif ([System.IO.Path]::IsPathRooted($GuardPath)) {
    [System.IO.Path]::GetFullPath($GuardPath)
} else {
    [System.IO.Path]::GetFullPath((Join-Path $repoRoot $GuardPath))
}
$guardRoot = [System.IO.Path]::GetPathRoot($guardPathResolved)
if ([string]::IsNullOrWhiteSpace($guardRoot) -or -not (Test-Path -LiteralPath $guardRoot -PathType Container)) {
    throw "Guard path does not resolve to an available volume: $guardPathResolved"
}

$trackedDrive = [System.IO.DriveInfo]::new($guardRoot)
$freeGiB = [Math]::Round($trackedDrive.AvailableFreeSpace / $bytesPerGiB, 2)
$totalGiB = [Math]::Round($trackedDrive.TotalSize / $bytesPerGiB, 2)
$systemRoot = [System.IO.Path]::GetPathRoot([Environment]::SystemDirectory)
$systemDrive = [System.IO.DriveInfo]::new($systemRoot)

$sourceMeasurement = Get-DirectoryMeasurement -Path $sourceTree -Exclude @($buildOutput)
$buildMeasurement = Get-DirectoryMeasurement -Path $buildOutput
$depotMeasurement = Get-DirectoryMeasurement -Path $depotTools
$tempMeasurement = Get-DirectoryMeasurement -Path $taskTemp
$artifactMeasurement = Get-DirectoryMeasurement -Path $artifactRoot

$cacheMeasurements = @()
foreach ($cachePathValue in @($config.cache_paths)) {
    $cachePath = Resolve-ConfiguredPath ([string]$cachePathValue)
    if (-not (Test-PathWithin -Candidate $cachePath -Parent $repoRoot)) {
        throw "Configured cache path escapes the repository: $cachePath"
    }
    $cacheMeasurements += [ordered]@{
        path = $cachePath
        measurement = Get-DirectoryMeasurement -Path $cachePath
    }
}

$expectedEnginePaths = @($checkoutRoot, $depotTools)
$layoutViolations = @()
$unexpectedDirectories = @()
if (Test-Path -LiteralPath $engineRoot -PathType Container) {
    foreach ($child in Get-ChildItem -LiteralPath $engineRoot -Directory -Force) {
        $known = $false
        foreach ($expectedPath in $expectedEnginePaths) {
            if ([System.IO.Path]::GetFullPath($child.FullName) -eq [System.IO.Path]::GetFullPath($expectedPath)) {
                $known = $true
                break
            }
        }
        if (-not $known) {
            $entry = [ordered]@{
                path = $child.FullName
                measurement = Get-DirectoryMeasurement -Path $child.FullName
            }
            $layoutViolations += $entry
            $unexpectedDirectories += $entry
        }
    }
}
$expectedCheckoutPaths = @($sourceTree)
if (Test-Path -LiteralPath $checkoutRoot -PathType Container) {
    foreach ($checkoutChild in Get-ChildItem -LiteralPath $checkoutRoot -Directory -Force) {
        $known = $false
        foreach ($expectedPath in $expectedCheckoutPaths) {
            if ([System.IO.Path]::GetFullPath($checkoutChild.FullName) -eq [System.IO.Path]::GetFullPath($expectedPath)) {
                $known = $true
                break
            }
        }
        if (-not $known -and $checkoutChild.Name -ne '.cipd') {
            $unexpectedDirectories += [ordered]@{
                path = $checkoutChild.FullName
                measurement = Get-DirectoryMeasurement -Path $checkoutChild.FullName
            }
        }
    }
}
$outRoot = Split-Path -Parent $buildOutput
if (Test-Path -LiteralPath $outRoot -PathType Container) {
    foreach ($outputChild in Get-ChildItem -LiteralPath $outRoot -Directory -Force) {
        if ([System.IO.Path]::GetFullPath($outputChild.FullName) -ne [System.IO.Path]::GetFullPath($buildOutput)) {
            $entry = [ordered]@{
                path = $outputChild.FullName
                measurement = Get-DirectoryMeasurement -Path $outputChild.FullName
            }
            $layoutViolations += $entry
            $unexpectedDirectories += $entry
        }
    }
}
$unexpectedDirectories = @($unexpectedDirectories | Sort-Object { $_.measurement.bytes } -Descending | Select-Object -First 10)

$pageFiles = @(Get-CimInstance Win32_PageFileUsage -ErrorAction SilentlyContinue | ForEach-Object {
    [ordered]@{
        name = $_.Name
        allocated_gib = [Math]::Round($_.AllocatedBaseSize / 1024, 2)
        current_usage_gib = [Math]::Round($_.CurrentUsage / 1024, 2)
        peak_usage_gib = [Math]::Round($_.PeakUsage / 1024, 2)
    }
})

$thresholds = $config.thresholds_gib
$decision = 'record-only'
$guardBand = 'milestone'
$guardMessage = 'Measurement recorded; no operation gate requested.'
$conservativeGrowthGiB = 0.0
$projectedFreeGiB = $freeGiB

if ($Stage -eq 'before') {
    $decision = 'allow'
    if ($EstimatedGrowthGiB -gt 0) {
        $conservativeGrowthGiB = [Math]::Round([Math]::Max($EstimatedGrowthGiB * 1.25, $EstimatedGrowthGiB + 5), 2)
        $projectedFreeGiB = [Math]::Round($freeGiB - $conservativeGrowthGiB, 2)
    }

    if ($freeGiB -lt [double]$thresholds.hard_stop) {
        $guardBand = 'hard-stop'
        $decision = 'block'
        $guardMessage = 'Below 40 GiB: all data-growing operations are blocked.'
    } elseif ($freeGiB -lt [double]$thresholds.estimate_required) {
        $guardBand = 'stop-large-operations'
        $decision = 'block'
        $guardMessage = 'Below 60 GiB: large sync/build operations are blocked pending safe cleanup.'
    } elseif ($freeGiB -lt [double]$thresholds.monitor) {
        $guardBand = 'estimate-required'
        if ($EstimatedGrowthGiB -le 0) {
            $decision = 'block'
            $guardMessage = '60–80 GiB requires an explicit growth estimate.'
        } elseif ($projectedFreeGiB -lt [double]$thresholds.estimate_required) {
            $decision = 'block'
            $guardMessage = 'Conservative projected free space would fall below 60 GiB.'
        } else {
            $guardMessage = 'Estimated operation fits while preserving at least 60 GiB conservative headroom.'
        }
    } elseif ($freeGiB -le [double]$thresholds.safe) {
        $guardBand = 'monitor-closely'
        $guardMessage = '80–120 GiB: operation allowed with close before/after monitoring.'
    } else {
        $guardBand = 'safe-to-start'
        $guardMessage = 'More than 120 GiB free: operation is inside the Phase 0 start band.'
    }

    $estimateRequiredOperations = @('fetch', 'gclient-sync', 'hooks', 'toolchain-install', 'build', 'update')
    if ($decision -eq 'allow' -and $Operation -in $estimateRequiredOperations -and $EstimatedGrowthGiB -le 0) {
        $decision = 'block'
        $guardBand = 'estimate-missing'
        $guardMessage = "Operation '$Operation' requires an explicit growth estimate on every free-space band."
    }
    if ($decision -eq 'allow' -and $EstimatedGrowthGiB -gt 0 -and
        $projectedFreeGiB -lt [double]$thresholds.estimate_required) {
        $decision = 'block'
        $guardBand = 'insufficient-projected-headroom'
        $guardMessage = 'Conservative projected free space would fall below 60 GiB.'
    }

    if ($layoutViolations.Count -gt 0) {
        $decision = 'block'
        $guardBand = 'layout-violation'
        $guardMessage = 'Unexpected engine/output directories exist. Identify them before a large operation; do not delete them automatically.'
    }
}

$nextConservativeGrowthGiB = 0.0
if ($EstimatedNextGrowthGiB -gt 0) {
    $nextConservativeGrowthGiB = [Math]::Round([Math]::Max($EstimatedNextGrowthGiB * 1.25, $EstimatedNextGrowthGiB + 5), 2)
}
$nextHeadroomGiB = [Math]::Round($freeGiB - $nextConservativeGrowthGiB, 2)

$previousFreeGiB = $null
if ($Stage -eq 'after' -and (Test-Path -LiteralPath $artifactRoot -PathType Container)) {
    $previous = Get-ChildItem -LiteralPath $artifactRoot -File -Filter '*.json' |
        Sort-Object LastWriteTimeUtc -Descending |
        ForEach-Object {
            try { Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json } catch { $null }
        } |
        Where-Object {
            $_ -and $_.stage -eq 'before' -and $_.operation -eq $Operation -and
            $_.disk_status.volume -eq $trackedDrive.Name
        } |
        Select-Object -First 1
    if ($null -ne $previous) {
        $previousFreeGiB = [double]$previous.disk_status.free_before_gib
    }
}

$safeLabel = if ([string]::IsNullOrWhiteSpace($Label)) { "$Stage-$Operation" } else { $Label }
$safeLabel = $safeLabel -replace '[^A-Za-z0-9._-]', '-'
$timestamp = [DateTime]::UtcNow
$timestampName = $timestamp.ToString('yyyyMMddTHHmmssZ')
New-Item -ItemType Directory -Path $artifactRoot -Force | Out-Null

$report = [ordered]@{
    schema_version = 1
    recorded_utc = $timestamp.ToString('o')
    stage = $Stage
    operation = $Operation
    label = $safeLabel
    decision = $decision
    guard_band = $guardBand
    guard_message = $guardMessage
    estimate = [ordered]@{
        requested_growth_gib = $EstimatedGrowthGiB
        conservative_growth_gib = $conservativeGrowthGiB
        projected_free_gib = $projectedFreeGiB
        next_requested_growth_gib = $EstimatedNextGrowthGiB
        next_conservative_growth_gib = $nextConservativeGrowthGiB
        estimated_headroom_for_next_step_gib = $nextHeadroomGiB
    }
    disk_status = [ordered]@{
        free_before_gib = if ($Stage -eq 'after') { $previousFreeGiB } else { $freeGiB }
        free_after_gib = if ($Stage -eq 'after') { $freeGiB } else { $null }
        current_free_gib = $freeGiB
        guard_path = $guardPathResolved
        volume = $trackedDrive.Name
        volume_total_gib = $totalGiB
        file_system = $trackedDrive.DriveFormat
        system_volume = $systemDrive.Name
        system_volume_free_gib = [Math]::Round($systemDrive.AvailableFreeSpace / $bytesPerGiB, 2)
        source_size_gib = $sourceMeasurement.gib
        build_output_size_gib = $buildMeasurement.gib
        depot_tools_size_gib = $depotMeasurement.gib
        task_temp_size_gib = $tempMeasurement.gib
        artifact_size_gib = $artifactMeasurement.gib
        caches = $cacheMeasurements
        pagefiles = $pageFiles
        largest_unexpected_directories = $unexpectedDirectories
        cleanup_performed = $CleanupPerformed
    }
    paths = [ordered]@{
        checkout_root = $checkoutRoot
        source_tree = $sourceTree
        build_output = $buildOutput
        depot_tools = $depotTools
        artifact_root = $artifactRoot
    }
}

$jsonPath = Join-Path $artifactRoot "$timestampName-$safeLabel.json"
$markdownPath = Join-Path $artifactRoot "$timestampName-$safeLabel.md"
$report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $jsonPath -Encoding utf8

$unexpectedText = if ($unexpectedDirectories.Count -eq 0) {
    'None detected under the managed engine root.'
} else {
    (($unexpectedDirectories | ForEach-Object { "$( $_.path ) ($( $_.measurement.gib ) GiB)" }) -join '; ')
}
$freeBeforeText = if ($Stage -eq 'after') {
    if ($null -eq $previousFreeGiB) { 'Unknown (no matching before snapshot)' } else { "$previousFreeGiB GiB" }
} else {
    "$freeGiB GiB"
}
$freeAfterText = if ($Stage -eq 'after') { "$freeGiB GiB" } else { 'Pending' }

$markdown = @"
# Disk status — $safeLabel

- Free before: $freeBeforeText
- Free after: $freeAfterText
- Source size: $($sourceMeasurement.gib) GiB (primary build output excluded)
- Build output size: $($buildMeasurement.gib) GiB
- Largest unexpected directories: $unexpectedText
- Cleanup performed: $CleanupPerformed
- Estimated headroom for next step: $nextHeadroomGiB GiB
- Guard decision: $decision — $guardMessage
- Depot tools: $($depotMeasurement.gib) GiB
- Task temp: $($tempMeasurement.gib) GiB
- Measurement artifacts: $($artifactMeasurement.gib) GiB
- Guard path: $guardPathResolved
- Tracked volume: $($trackedDrive.Name) ($($trackedDrive.DriveFormat))
- System volume free: $([Math]::Round($systemDrive.AvailableFreeSpace / $bytesPerGiB, 2)) GiB
"@
$markdown.TrimEnd() + "`n" | Set-Content -LiteralPath $markdownPath -Encoding utf8 -NoNewline

Write-Output "Disk report: $markdownPath"
Write-Output "Free: $freeGiB GiB; source: $($sourceMeasurement.gib) GiB; output: $($buildMeasurement.gib) GiB"
Write-Output "Decision: $decision ($guardBand) — $guardMessage"

if ($decision -eq 'block') {
    throw "Disk guard blocked '$Operation': $guardMessage"
}
