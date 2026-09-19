[CmdletBinding()]
param(
    [string] $OutputDirectory = ""
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $artifactRoot = Join-Path $repoRoot 'phase0-artifacts'
} else {
    $artifactRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
}

New-Item -ItemType Directory -Path $artifactRoot -Force | Out-Null

function Get-CommandVersion {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [string[]] $Arguments = @('--version')
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        return [ordered]@{ available = $false; version = $null }
    }

    try {
        $firstLine = (& $command.Source @Arguments 2>&1 | Select-Object -First 1).ToString().Trim()
        return [ordered]@{ available = $true; version = $firstLine }
    } catch {
        return [ordered]@{ available = $true; version = 'unable to query' }
    }
}

function Get-FileProductVersion {
    param([Parameter(Mandatory = $true)][string] $Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $null
    }
    return (Get-Item -LiteralPath $Path).VersionInfo.ProductVersion
}

$operatingSystem = Get-CimInstance Win32_OperatingSystem
$logicalDisk = Get-CimInstance Win32_LogicalDisk -Filter "DriveType = 3" |
    Where-Object { $repoRoot.StartsWith($_.DeviceID, [System.StringComparison]::OrdinalIgnoreCase) } |
    Select-Object -First 1

$vsWhere = 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe'
$visualStudio = @()
if (Test-Path -LiteralPath $vsWhere -PathType Leaf) {
    $vsJson = & $vsWhere -all -products '*' -format json
    if (-not [string]::IsNullOrWhiteSpace($vsJson)) {
        $visualStudio = @($vsJson | ConvertFrom-Json | ForEach-Object {
            [ordered]@{
                display_name = $_.displayName
                version = $_.installationVersion
                complete = [bool]$_.isComplete
            }
        })
    }
}

$sdkRoot = 'C:\Program Files (x86)\Windows Kits\10\bin'
$windowsSdks = @()
if (Test-Path -LiteralPath $sdkRoot -PathType Container) {
    $windowsSdks = @(Get-ChildItem -LiteralPath $sdkRoot -Directory |
        Where-Object { $_.Name -match '^10\.\d+\.\d+\.\d+$' } |
        Select-Object -ExpandProperty Name |
        Sort-Object)
}

$webViewRoot = 'C:\Program Files (x86)\Microsoft\EdgeWebView\Application'
$webViewVersions = @()
if (Test-Path -LiteralPath $webViewRoot -PathType Container) {
    $webViewVersions = @(Get-ChildItem -LiteralPath $webViewRoot -Directory |
        Where-Object { $_.Name -match '^\d+\.\d+\.\d+\.\d+$' } |
        Select-Object -ExpandProperty Name |
        Sort-Object)
}

$report = [ordered]@{
    schema_version = 1
    collected_utc = [DateTime]::UtcNow.ToString('o')
    privacy = 'No profile paths, account identifiers, URLs, cookies, tokens, or credentials collected.'
    operating_system = [ordered]@{
        caption = $operatingSystem.Caption
        version = $operatingSystem.Version
        build = $operatingSystem.BuildNumber
        architecture = $operatingSystem.OSArchitecture
    }
    hardware = [ordered]@{
        total_ram_gib = [Math]::Round($operatingSystem.TotalVisibleMemorySize / 1MB, 1)
        free_ram_gib_at_scan = [Math]::Round($operatingSystem.FreePhysicalMemory / 1MB, 1)
        workspace_volume = if ($null -eq $logicalDisk) { $null } else { $logicalDisk.DeviceID }
        workspace_free_gib = if ($null -eq $logicalDisk) { $null } else { [Math]::Round($logicalDisk.FreeSpace / 1GB, 1) }
        workspace_file_system = if ($null -eq $logicalDisk) { $null } else { $logicalDisk.FileSystem }
    }
    tools = [ordered]@{
        git = Get-CommandVersion -Name 'git'
        python = Get-CommandVersion -Name 'python' -Arguments @('--version')
        node = Get-CommandVersion -Name 'node'
        npm = Get-CommandVersion -Name 'npm'
        rustc = Get-CommandVersion -Name 'rustc'
        cargo = Get-CommandVersion -Name 'cargo'
        gn = Get-CommandVersion -Name 'gn'
        autoninja = Get-CommandVersion -Name 'autoninja'
        ninja = Get-CommandVersion -Name 'ninja'
        clang_cl = Get-CommandVersion -Name 'clang-cl'
    }
    visual_studio = $visualStudio
    windows_sdks = $windowsSdks
    installed_browsers = [ordered]@{
        chrome = Get-FileProductVersion 'C:\Program Files\Google\Chrome\Application\chrome.exe'
        edge = Get-FileProductVersion 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
        brave = Get-FileProductVersion 'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe'
    }
    webview2_runtimes = $webViewVersions
    concept_present = Test-Path -LiteralPath (Join-Path $repoRoot 'aoi_browser_concept_01.html') -PathType Leaf
}

$outputPath = Join-Path $artifactRoot 'environment.json'
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outputPath -Encoding utf8
Write-Output "Wrote sanitized environment report: $outputPath"
