# Performance and memory plan

No performance or memory superiority claim is made in Phase 0. Results require
controlled comparison on the same machine and workload.

## Product budgets

- A pointer/key action changes shell visuals in the same frame when possible.
- Avoidable UI-thread tasks over 50 ms are defects.
- Omnibox local results paint without disk/network waits; async results carry a
  query generation and cannot replace newer input.
- Animations run through compositor transforms/opacity and target the monitor's
  actual refresh cadence, not a fixed 60 FPS assumption.
- Tab shell state switches immediately; a page compositor may catch up without
  blocking tab chrome.

## Lifecycle policy

For one to five tabs, preserve instant switching and do not use timer-only
discard. Six to ten tabs may throttle the oldest hidden safe contents under
measured pressure. Twenty-plus tabs allow more active reclaim, still excluding
active/split/PiP/media/WebRTC/download/unsafe-form tabs.

Inputs are system memory pressure, total process private/working set, tab count,
recency, visibility, media/PiP/WebRTC, download activity, form/navigation safety,
and explicit keep-active state. Split panes are both foreground and HOT.

## Benchmark protocol

Compare the exact product build with current stable Chrome and Edge, optionally
Brave, using fresh profiles, the same URLs/network conditions, and aligned
blocking conditions. Run at least three iterations and report median plus p95
where sample size is meaningful.

Scenarios: cold New Tab; static article; Gmail; paused YouTube; mixed five and
ten tabs; split view; twenty-tab stress; close-and-recovery; and a 100-tab
open/close lifecycle leak loop.

Measure browser plus child-process working set/private memory, CPU idle and tab
switch, GPU usage, frame pacing, startup first visual/usable, tab-switch latency,
60-second idle memory, post-discard reclaim, and disk cache separately.

Use Chromium tracing/Perfetto and ETW/WPR/WPA. Trace configs, product revisions,
machine power state, screen scale/refresh, and raw sanitized outputs accompany
every published result.
