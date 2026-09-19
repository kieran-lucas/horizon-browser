# Phase 0 execution plan

## Objective

Prove that the selected engine can support ordinary Google web login, isolated
local profiles, custom premium browser chrome, a credible MV3 extension path,
live tab/window movement and split view, and browser fundamentals without
weakening Chromium security or violating provider policy.

## Candidate handling

1. **Full Chromium-derived browser** — build and execute every P0 test. This is
   the selected direction and the only candidate eligible to close the gate.
2. **Chromium with selected Brave techniques/components** — use Brave as a
   maintenance/adblock reference. Do not add its product/service layer unless a
   separate cost/license ADR shows a concrete advantage.
3. **WebView2 native shell** — documentary fail on the non-negotiable Google
   Authentication requirement. Do not spend time writing a bypass-shaped spike.
4. **CEF Chrome bootstrap/Alloy style** — documentary fail on the combined
   policy/extension/custom-shell gate. Reconsider only if upstream and Google
   policies materially change.

## Stages

### 0.1 — Reproducible build host

- reserve at least 180 GiB on a verified NTFS build volume;
- install current Visual Studio 2026 Build Tools, Desktop C++, ATL/MFC, the
  Chromium-required Windows SDK and Debugging Tools;
- install/bootstrap depot_tools according to upstream instructions;
- cap local concurrency for 16 GiB RAM and record the exact configuration.

Exit: upstream Chromium stable-family `chrome` target builds and starts with the
sandbox enabled.

### 0.2 — Neutral product fork skeleton

- pin the immutable Chromium revision;
- add replaceable product identity/build branding without using the working
  title in package/protocol/namespace persistence;
- make no browser-service changes;
- inventory the minimal upstream patch surface.

Exit: clean profiles start, navigate, relaunch, and report the pinned revision.

### 0.3 — Hard compatibility gate

- run P0-A Google login manually;
- run P0-B profile/incognito isolation;
- load and validate the provided MV3 extension probe;
- exercise downloads, permissions, PiP, DevTools, context menus, and crash
  signals.

Exit: any auth/isolation/security failure stops UI work and reopens ADR-0001.

### 0.4 — Shell feasibility spike

- theme/replace the top frame, two-row horizontal chrome, active tab, omnibox,
  profile panel, local New Tab, and permission prompt through Views/WebUI seams;
- retain upstream tab/window/split primitives;
- capture 125%, 150%, and 175% DPI evidence.

Exit: custom visuals are feasible without replacing browser semantics or
creating an unmaintainable patch concentration.

### 0.5 — Decision close

- attach sanitized result records and patch inventory;
- record limitations and reproduction commands;
- change ADR-0001 to `Accepted` only when every P0 row passes.

## Decision priority

Correctness and policy compliance are vetoes. Then evaluate profile/security
coverage, web compatibility, extension viability, custom-shell feasibility,
update/rebase cost, responsiveness, visual quality, and implementation breadth
in that order. A faster prototype does not offset a failed veto criterion.
