# Phase 0 milestone report

Date: 2026-09-20

## Change summary

- Added the provisional engine ADR and evidence-based candidate comparison.
- Added a complete P0 acceptance matrix and sanitized result schema.
- Added current-host/dependency verification and a staged execution plan.
- Defined the Chromium-aligned architecture, build policy, patch policy,
  dependency pinning, license inventory, security baseline, password-manager
  threat model, design foundation, and performance methodology.
- Added repeatable PowerShell environment/scaffold checks.
- Added a guarded shallow-checkout policy, one-tree/one-output layout, compact GN
  baseline, conservative build concurrency, and before/after disk reporting.
- Added a local-only MV3 capability probe covering content scripts, service
  worker, storage, action popup/badge, context menu, and a static DNR rule.

The pinned shallow Chromium checkout and compact Phase 0 build graph now exist
locally. The first `chrome` build is in progress; no production UI work begins
until the executable engine gate passes.

## Architecture outcome

Provisionally select full Chromium with Views/Aura and WebUI, retaining upstream
Profiles, tabs/WebContents, split view, extensions, password manager, downloads,
permissions, media, sandbox, and site isolation. WebView2 and CEF Alloy-style
shells are rejected for production. Brave is a reference and possible source of
independently audited components, not the selected distribution base.

## Verification performed

| Check | Result |
|---|---|
| Phase 0 scaffold validator | PASS — 15 required files |
| JSON parse: result schema, manifest, DNR rules | PASS |
| `node --check`: service worker, popup, content script | PASS |
| Local Markdown target resolution | PASS |
| Working-title lock scan | PASS — only explanatory/concept references found |
| Forbidden security-switch scan | PASS — no implementation flags found |
| Disk guard baseline | PASS — 146.2 GiB, safe-to-start band |
| Unexpected engine/output layout guard | PASS — large operation blocked without deleting the unexpected directory |
| Disk before/after pairing | PASS — postflight recovered the matching preflight free-space value |
| Shallow Chromium source | PASS — one shallow tree at the pinned upstream revision plus the recorded Phase 0 DEPS patch; small dependency sync and hooks completed |
| Build toolchain | PASS — VS Build Tools 2026 18.10.1, MSVC 14.51, ATL/MFC, SDK 28000, Debugging Tools 28000.2705 |
| GN generation | PASS — only `out/phase0`; 32,360 targets generated with release component/no-symbol args and Ninja selected |
| Installed Chrome headless extension attempt | INCONCLUSIVE — process exited 0 but emitted no DOM marker; not counted as engine evidence |
| Chromium product build | IN PROGRESS — target `chrome`, Ninja `-j 2`; build preflight passed with 116.70 GiB free |
| Google/profile/manual acceptance | NOT RUN — requires the actual product build and human sign-in |

The headless attempt used the installed stable Chrome only to smoke the test
asset. It does not represent the selected fork and cannot satisfy any P0 row.

## Screenshots and traces

None were produced. There is no product UI binary to capture, and fabricating
concept screenshots would conceal the open engine gate. DPI goldens and traces
begin in stage 0.4 after the selected binary passes compatibility/isolation.

## Known issues and blockers

- The referenced HTML concept is absent.
- The public remote has no baseline commit/source.
- The machine has 15.4 GiB RAM; build concurrency is capped at two jobs.
- Visual Studio setup returned success-with-restart (`3010`) while adding the
  toolchain. Subsequent `vswhere` reports the instance complete and not requiring
  reboot, and GN generation succeeds; no restart was forced during this run.
- ADR-0001 remains provisional until every executable P0 test passes.
- Defender quarantined one Chrome updater test CIPD package as
  `Trojan:Win32/Suschil!rfn`; it was not restored or allowlisted. The documented
  Phase 0 source patch `a1d39df07e` disables only Chrome updater integration-test
  fixtures; Chromium updater source and browser/update targets remain present.

## Disk status

- Free before: 146.2 GiB at Phase 0 start; 116.70 GiB immediately before build
- Free after: 115.97 GiB at the 2,831/57,380 build checkpoint (build in progress)
- Source size: 24.30 GiB at the completed post-GN snapshot
- Build output size: 1.53 GiB at the completed post-GN snapshot
- Largest unexpected directories: two gclient `_bad_scm` recovery directories,
  approximately 0.01 GiB total; identified and retained, not a second source tree
- Cleanup performed: removed a verified accidental, incomplete `.git`-only
  Chromium checkout from the product root (1.36 GiB, fully regenerable); `gclient
  -D` removed only upstream benchmark dependencies excluded by
  `checkout_configuration = "small"`; no source/toolchain files were manually
  deleted
- Estimated headroom for next step: 66.70 GiB after the build guard's conservative
  50 GiB allowance for a nominal 40 GiB `chrome` build
