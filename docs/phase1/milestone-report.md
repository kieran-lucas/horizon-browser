# Phase 1 Milestone Report

Date: 2026-09-20

## Result

PASS — first usable Horizon browser shell.

Horizon launches from the real Chromium-derived binary with branded native
chrome, a functional Horizon New Tab page, Horizon identity resources and a
maximized fresh-window default. Existing Chromium browsing/security behavior is
preserved.

## Runtime smoke coverage

- New Tab search navigated to `https://example.com/`.
- Multiple tabs and normal HTTPS content loaded.
- History, Bookmarks, Downloads, Settings, Version and Inspect WebUIs loaded.
- Fresh profile title was `New Tab - Horizon`.
- Fresh window state was maximized (`showCmd=3`) without a command-line flag.
- Windows scaling validation was performed at the host's 175% setting.

Google-account behavior was manually accepted in Phase 0. Phase 1 did not alter
authentication, cookies, sandboxing, site isolation or network security paths.

## Known gaps for Phase 2 or later

- optical tab/toolbar microspacing at 125% and 150% needs a dedicated pass;
- deeper motion polish is intentionally absent;
- some low-frequency upstream Chromium wording remains outside the primary
  Horizon surfaces;
- production non-component memory/startup profiling is still required;
- installer, updater, signing and final distribution icons are later-phase work.

See `docs/HANDOFF.md` for the authoritative resume point.
