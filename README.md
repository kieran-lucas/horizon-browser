# Horizon Browser

Horizon is a working Chromium-derived Windows browser. Phase 0 engine viability
and the Phase 1 usable Horizon shell are complete; Phase 2 visual polish has not
started. The current product direction is light-only, ethereal blue anime-tech
minimalism with restrained native browser chrome.

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
- [`docs/phase0/disk-policy.md`](docs/phase0/disk-policy.md)
- [`docs/adr/0001-engine-selection.md`](docs/adr/0001-engine-selection.md)
- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`BUILDING.md`](BUILDING.md)
- [`DESIGN_SYSTEM.md`](DESIGN_SYSTEM.md)
- [`SECURITY.md`](SECURITY.md)
- [`PERFORMANCE.md`](PERFORMANCE.md)

## Development quick start

From PowerShell:

```powershell
pwsh -NoProfile -File .\scripts\phase0\collect-environment.ps1
pwsh -NoProfile -File .\scripts\phase0\disk-status.ps1 -Stage before -Operation fetch -EstimatedGrowthGiB 45
```

The script writes a machine-readable report under `phase0-artifacts/`. It does
not read browser profile data, launch a browser, or collect URLs or secrets.

The unpacked Manifest V3 test extension is in
[`tests/phase0/mv3-extension`](tests/phase0/mv3-extension). It is intentionally
product-neutral and contains no remote code.

## Status

- Chromium revision: `a1d39df07efc8101c31ec6efce60265de7689dcb`.
- Reusable incremental output: `.engine/chromium/src/out/phase0`.
- Phase 1: native Horizon chrome, branded New Tab, product identity and default
  maximized startup validated on Windows 11 at 175% scaling.
- No Google credentials are collected or automated by this repository.
- See [`docs/HANDOFF.md`](docs/HANDOFF.md) for exact resume instructions and
  known development-build performance behavior.
