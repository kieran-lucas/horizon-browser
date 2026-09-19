# Phase 0 engine acceptance matrix

Statuses are `PASS`, `FAIL`, `BLOCKED`, or `NOT RUN`. Documentary rejection is
used only where an official platform or policy source makes the hard test
invalid by design. `NOT RUN` is never interpreted as pass.

## Candidate summary

| Candidate | Auth | Profiles | Chrome | Extensions | Tab/window | Basics | Disposition |
|---|---|---|---|---|---|---|---|
| Full Chromium-derived build | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | NOT RUN | Selected direction; executable gate open |
| Chromium + Brave techniques | Same executable gate as Chromium | Same | Same | Same | Same | Same | Components/reference only; no separate base build yet |
| WebView2 + native shell | **FAIL (documented)** | NOT RUN | Feasible | **FAIL architecture parity** | Partial | Partial | Rejected; no policy-bypass spike |
| CEF Chrome bootstrap + Alloy style | **FAIL policy fit / no acceptable proof path** | NOT RUN | Feasible | **FAIL: upstream limitation** | Partial | Partial | Rejected |

## Required Chromium-derived executable tests

Every run records binary version, immutable source revision, build args hash,
Windows build, WebView/Chromium version, profile root identifiers that reveal no
user information, tester, UTC time, result, and sanitized evidence reference.

### P0-A: Google authentication

- [ ] Open `https://accounts.google.com/` as a normal top-level navigation.
- [ ] Complete login without UA changes, injected scripts, external-browser
      delegation, copied cookies/tokens, or automation of credentials/2FA.
- [ ] Open Gmail and verify the intended signed-in account.
- [ ] Open YouTube and verify the same account.
- [ ] Open Drive and verify the same account.
- [ ] Quit every product process, relaunch Profile A, and verify persistence.
- [ ] Launch clean Profile B and verify Profile A's session is absent.
- [ ] Sign into a different account in Profile B and verify both remain isolated
      after a full relaunch.

Any embedded/disallowed-browser response is immediate `FAIL` and reopens
ADR-0001. Screenshots must redact account names, avatars, email addresses, Drive
filenames, video history, and notification content.

### P0-B: profile and incognito isolation

- [ ] Distinct cookie values in Profiles A and B.
- [ ] Distinct local/session storage and IndexedDB values.
- [ ] Browsing history written only to the active normal profile.
- [ ] Bookmark and setting changes isolated.
- [ ] MV3 extension storage and enabled state isolated.
- [ ] Incognito starts without normal-profile site state unless upstream
      semantics explicitly allow a user-approved extension.
- [ ] Incognito history/session/password data is absent after close and relaunch.

### P0-C: custom browser chrome

- [ ] Replaceable horizontal tab strip and active-tab visuals.
- [ ] Two-row tabs plus navigation/omnibox layout.
- [ ] Custom top frame and caption hit-testing on Windows 11.
- [ ] Profile chooser and anchored profile panel.
- [ ] Local New Tab WebUI with strict CSP and no remote script.
- [ ] Browser-owned camera/microphone/location permission prompt.
- [ ] 125%, 150%, and 175% DPI screenshots with correct hit testing.

### P0-D: extension path

Load `tests/phase0/mv3-extension` unpacked and verify:

- [ ] content script marker on ordinary HTTPS pages;
- [ ] service worker event handling;
- [ ] `storage.local` persistence and per-profile isolation;
- [ ] browser-action icon, popup, and badge;
- [ ] context-menu entry;
- [ ] permission request presentation;
- [ ] a representative supported MV3 network rule;
- [ ] pin/unpin/overflow anchoring contract documented.

### P0-E: tabs, windows, and split

- [ ] Five independent tabs navigate and preserve state.
- [ ] Reorder tabs with pointer and keyboard-accessible command.
- [ ] Detach a live tab to a new window without reload/state loss.
- [ ] Move the live tab back across windows.
- [ ] Open two adjacent tabs in upstream split view.
- [ ] Resize divider without continuous UI-thread layout stalls.
- [ ] Both panes keep the same profile and remain HOT/foreground.
- [ ] Scroll, form, SPA, media, navigation history, and focus survive moves.

### P0-F: browser basics

- [ ] back/forward/reload/stop, redirects, popup/new-window policy;
- [ ] download start/progress/cancel/open/show-in-folder and dangerous-file path;
- [ ] camera, microphone, and location hooks with exact origin display;
- [ ] YouTube and a second HTML5 site's Picture-in-Picture;
- [ ] docked and separate DevTools;
- [ ] native semantic context menu plus extension entries;
- [ ] renderer crash signal, branded reload surface, other tabs unaffected;
- [ ] browser crash/session recovery signal.

## Exit rule

Phase 0 closes only when all P0 Chromium-derived rows are `PASS`, the exact
binary can be reproduced, and ADR-0001 is updated from provisional to accepted.
Visual polish and performance numbers cannot compensate for a failed auth,
isolation, sandbox, or browser-compatibility result.
