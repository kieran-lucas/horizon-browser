# Phase 0 milestone report

Date: 2026-09-19

## Change summary

- Added the provisional engine ADR and evidence-based candidate comparison.
- Added a complete P0 acceptance matrix and sanitized result schema.
- Added current-host/dependency verification and a staged execution plan.
- Defined the Chromium-aligned architecture, build policy, patch policy,
  dependency pinning, license inventory, security baseline, password-manager
  threat model, design foundation, and performance methodology.
- Added repeatable PowerShell environment/scaffold checks.
- Added a local-only MV3 capability probe covering content scripts, service
  worker, storage, action popup/badge, context menu, and a static DNR rule.

No production browser source or UI was added because the executable engine gate
and required Chromium toolchain are not yet available. This is a deliberate gate,
not a claim that Phase 1 has begun.

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
| Installed Chrome headless extension attempt | INCONCLUSIVE — process exited 0 but emitted no DOM marker; not counted as engine evidence |
| Chromium product build | NOT RUN — source/toolchain/build volume unavailable |
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
- The machine has 15.4 GiB RAM and 146.2 GiB free on the workspace volume.
- Installed Build Tools are VS 2022; current Chromium requires VS 2026, newer
  Windows SDK/Debugging Tools, and ATL/MFC.
- Git/depot_tools/GN/Ninja are not available on `PATH`.
- ADR-0001 remains provisional until every executable P0 test passes.
