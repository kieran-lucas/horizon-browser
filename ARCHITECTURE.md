# Architecture

## Status and scope

This is the Phase 0 target architecture. It becomes implementation truth only
after the executable engine gate passes. The product is a Chromium-derived
browser, not a native shell containing an embedded web control.

## Upstream primitives retained

The fork retains Chromium's `Profile`, browser/window model, `TabInterface`,
`TabStripModel`, `WebContents`, navigation, network service, sandbox, site
isolation, content settings, password manager, history, bookmarks, downloads,
session restore, media/Picture-in-Picture, DevTools, extensions, and crash
handling.

Chromium's current browser design explicitly defines profile, browser window,
tab, and WebContents as its core primitives. Extension state is profile-scoped.
Source: [Chromium browser design
principles](https://chromium.googlesource.com/chromium/src/+/main/docs/chrome_browser_design_principles.md).

Chromium 153-era source also exposes split tabs through `TabStripModel` and
renders the two live `WebContents` instances through `MultiContentsView`. That
is the implementation base for V1 split view; no URL-save-and-reload host will
be introduced. Source: [`BrowserView` split-view
implementation](https://chromium.googlesource.com/chromium/src/+/main/chrome/browser/ui/views/frame/browser_view.cc).

## Product-owned layers

```text
Product presentation (Views/WebUI)
├── top frame, horizontal tab strip, omnibox presentation
├── profile chooser and anchored panels
├── downloads and permission surfaces
├── New Tab, Settings, History, Bookmarks, Passwords WebUI
├── design tokens, icons, art, accessibility, motion
└── split-view affordances over upstream split primitives
          │ narrow, reviewed hooks
Chromium browser services
├── Browser/Profile/TabInterface/TabStripModel/WebContents
├── network, storage, permissions, password manager, downloads
├── session, history, bookmarks, extensions, DevTools, media
└── sandbox, site isolation, process model, updater integration
          │ sequenced worker boundary
Optional product services
├── native adblock adapter → audited adblock-rust integration
└── ITranslationProvider → separately selected provider
```

## Ownership and threading

- A `Profile` owns profile-keyed product services. No process-global mutable
  per-profile state.
- A tab feature is attached to `TabInterface`/`WebContents` and reaches its
  current window through upstream interfaces; it does not cache a
  `BrowserView*` across detach/move.
- Views objects live on Chromium's UI sequence. Disk, migration parsing,
  filter-list parsing, network updates, and translation calls do not.
- Async callbacks use upstream weak-pointer/cancellation conventions. No raw
  callback may outlive its owning controller.
- Split panes remain live foreground contents and HOT in lifecycle policy.
- Privileged WebUI handlers are registered only for allowlisted internal
  origins, validate message schemas, load only local resources, and use a
  restrictive CSP.

## Patch strategy

Prefer theme tokens, product controllers, feature flags, subclasses, and small
factory seams already supported by upstream. Every direct upstream edit must
be documented with owner, rationale, test, and expected rebase conflict area.
Features not needed for V1 are disabled by supported build/runtime policy rather
than deleting core infrastructure that future security merges depend on.

## Stable abstractions owned by the product

`ITranslationProvider` is provider-neutral and has detection, page translation,
text translation, and capability discovery. It never implies silent page upload.

The adblock boundary accepts immutable request facts and returns allow, block,
or resource-replacement decisions. Parsing/updating is off the UI thread and
published atomically. Cosmetic results are origin-bound and injected in an
isolated world without a privileged page-visible object.
