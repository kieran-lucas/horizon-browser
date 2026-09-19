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
    'docs\phase0\acceptance-matrix.md',
    'docs\phase0\result-template.json',
    'docs\security\password-manager-threat-model.md',
    'tests\phase0\mv3-extension\manifest.json'
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

Write-Output "Phase 0 scaffold validation passed ($($requiredFiles.Count) required files)."
