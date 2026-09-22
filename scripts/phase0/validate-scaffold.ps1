[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$requiredFiles = @(
    'README.md',
    'BUILDING.md',
    'ARCHITECTURE.md',
    'SECURITY.md',
    'PERFORMANCE.md',
    'DESIGN_SYSTEM.md',
    'DEPENDENCIES.md',
    'THIRD_PARTY_LICENSES.md',
    'docs\adr\0001-engine-selection.md',
    'docs\phase0\current-state.md',
    'docs\phase0\plan.md',
    'docs\phase0\milestone-report.md',
    'docs\phase0\disk-policy.md',
    'docs\phase0\acceptance-matrix.md',
    'docs\phase0\result-template.json',
    'docs\security\password-manager-threat-model.md',
    'tests\phase0\mv3-extension\manifest.json',
    'phase0-storage.json',
    'scripts\phase0\disk-status.ps1'
)

$missing = @($requiredFiles | Where-Object {
    -not (Test-Path -LiteralPath (Join-Path $repoRoot $_) -PathType Leaf)
})
if ($missing.Count -gt 0) {
    throw "Missing required files: $($missing -join ', ')"
}

$schema = Get-Content -LiteralPath (Join-Path $repoRoot 'docs\phase0\result-template.json') -Raw |
    ConvertFrom-Json
if ($schema.title -ne 'Phase 0 sanitized run result') {
    throw 'Unexpected Phase 0 result schema.'
}

$manifest = Get-Content -LiteralPath (Join-Path $repoRoot 'tests\phase0\mv3-extension\manifest.json') -Raw |
    ConvertFrom-Json
if ($manifest.manifest_version -ne 3) {
    throw 'The extension spike must remain Manifest V3.'
}
if ($manifest.content_security_policy.extension_pages -match 'https?:') {
    throw 'Remote extension code is forbidden.'
}

$storage = Get-Content -LiteralPath (Join-Path $repoRoot 'phase0-storage.json') -Raw |
    ConvertFrom-Json
if ($storage.maximum_source_trees -ne 1 -or $storage.maximum_primary_outputs -ne 1) {
    throw 'Phase 0 must allow exactly one source tree and one primary output.'
}
if ($storage.source_tree -ne '.engine/chromium/src' -or
    $storage.build_output -ne '.engine/chromium/src/out/phase0') {
    throw 'Unexpected Phase 0 engine/output layout.'
}
if ($storage.build_jobs -gt 2) {
    throw 'Phase 0 build concurrency exceeds the conservative 16 GiB baseline.'
}

Write-Output "Phase 0 scaffold validation passed ($($requiredFiles.Count) required files)."
