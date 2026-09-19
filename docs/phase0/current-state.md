# Current-state verification

Verified: 2026-09-19 (Asia/Saigon). The generated, sanitized machine report is
`phase0-artifacts/environment.json` and is intentionally ignored by Git.

## Repository/source baseline

- The workspace and its public GitHub remote were empty at first inspection.
- `.git/config` points to `kieran-lucas/horizon-browser`; there is no existing
  source commit or concept asset to preserve.
- `aoi_browser_concept_01.html` is absent. Design extraction is deferred, not
  approximated.
- This Phase 0 change adds only decision/security/build documentation, repeatable
  environment validation, and a local-only MV3 extension probe. It does not
  claim to contain a browser executable.

## Host and installed toolchain

| Item | Observed |
|---|---|
| OS | Windows 11 Home x64, 10.0.26200 |
| RAM | 15.4 GiB total; 4.0 GiB free at recorded scan |
| Workspace volume | D: NTFS, 146.2 GiB free |
| Visual Studio | Build Tools 2022 17.14.37710.0 |
| VC toolset | 14.44 present; ATL/MFC component not detected |
| Windows SDK | newest installed: 10.0.26100 |
| Git / depot_tools / GN / Ninja | not available on `PATH` |
| Rust | not installed |
| Python / Node | 3.14.7 / 24.19.0 |
| Chrome / Edge | 153.0.8010.53 / 153.0.4234.48 |
| WebView2 Runtime | 153.0.4234.32 newest installed |

## Re-verified stable/relevant releases

| Dependency/reference | Current snapshot | Production relevance |
|---|---|---|
| Chrome stable | Milestone 153; test host has 153.0.8010.53 | Establishes initial Chromium milestone only; exact source tag still must be pinned |
| Visual Studio 2026 | 18.10.1 stable (2026-09-15) | Current toolchain family; Chromium requires at least 18.0.0 |
| Windows App SDK | 2.5.1 stable (2026-09-16) | Reference for rejected WebView2 shell, not selected shell dependency |
| WebView2 SDK | 1.0.4191.47 release, Runtime 152 pairing | Rejected engine; recorded to avoid stale comparisons |
| Brave release line | 1.95.x / Chromium 153 at snapshot | Architecture reference; 1.96 was scheduled after snapshot |
| CEF | API line 15400 present upstream | Rejected engine; exact binary distribution not needed after documentary failure |

Official sources:

- [Chrome stable 153 release](https://chromereleases.googleblog.com/2026/09/stable-channel-update-for-desktop_0808145027.html)
- [Chromium Windows prerequisites](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/windows_build_instructions.md)
- [Visual Studio 2026 release notes](https://learn.microsoft.com/visualstudio/releases/2026/release-notes)
- [Windows App SDK release channels](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/release-channels)
- [WebView2 SDK release notes](https://learn.microsoft.com/en-us/microsoft-edge/webview2/release-notes/sdk/)
- [Brave release schedule](https://github.com/brave/brave-browser/wiki/Brave-Release-Schedule)

## Hard constraints

1. WebView2 fails the Google-auth production requirement by documented platform
   policy; it is not a fallback browser engine.
2. CEF Alloy-style custom UI loses the Chrome extension path and remains an
   embedded-user-agent policy risk.
3. A full Chromium checkout/build needs a newer system toolchain and more safe
   disk headroom than this workspace currently provides.
4. Google acceptance requires a human login and redacted evidence; credentials
   and 2FA must never be automated or stored in test assets.
5. The product working title cannot become a persisted/public identity yet.
