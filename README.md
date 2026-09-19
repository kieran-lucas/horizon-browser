# Personal Windows Browser

Working title: **Aoi**. The working title is deliberately not used as a package
identity, public protocol, C++ namespace, or persisted-data root. Branding will
remain replaceable until distribution work begins.

This repository is at **Phase 0: engine viability**. It is not yet a browser
binary. Production UI work is gated on an executable Chromium-derived build
passing the acceptance tests in
[`docs/phase0/acceptance-matrix.md`](docs/phase0/acceptance-matrix.md).

## Current decision

The selected production direction is a **full Chromium-derived browser using
Chromium's browser process, Profiles, WebContents, Views/Aura, and extension
infrastructure**. The decision is conditional on the hands-on Google web-login
and isolation tests. WebView2 is rejected for production because Microsoft and
Google explicitly classify its sign-in environment as an embedded user-agent.
CEF Alloy-style hosting is rejected because it combines the same policy risk
with reduced browser/extension capability.

See:

- [`docs/phase0/current-state.md`](docs/phase0/current-state.md)
- [`docs/phase0/plan.md`](docs/phase0/plan.md)
- [`docs/phase0/milestone-report.md`](docs/phase0/milestone-report.md)
- [`docs/adr/0001-engine-selection.md`](docs/adr/0001-engine-selection.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`BUILDING.md`](BUILDING.md)
- [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md)
- [`SECURITY.md`](SECURITY.md)
- [`PERFORMANCE.md`](PERFORMANCE.md)

## Phase 0 quick start

From PowerShell:

```powershell
pwsh -NoProfile -File .\scripts\phase0\collect-environment.ps1
```

The script writes a machine-readable report under `phase0-artifacts/`. It does
not read browser profile data, launch a browser, or collect URLs or secrets.

The unpacked Manifest V3 test extension is in
[`tests/phase0/mv3-extension`](tests/phase0/mv3-extension). It is intentionally
product-neutral and contains no remote code.

## Status

- Repository baseline: documentation and Phase 0 test assets only.
- Concept file: `aoi_browser_concept_01.html` was not present at initial scan.
- Current host: Windows 11 x64, 15.4 GiB RAM.
- Local Chromium build: blocked on the current machine by missing required
  Visual Studio 2026/ATL-MFC/depot_tools and tight disk headroom.
- No Google credentials are collected or automated by this repository.
