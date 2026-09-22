# Current-state verification

Verified: 2026-09-20 (Asia/Saigon). The generated, sanitized machine report is
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
| Workspace volume | D: NTFS; 146.2 GiB initially, 116.70 GiB immediately before the Phase 0 build |
| Visual Studio | Build Tools 2026 18.10.12210.168 (stable 18.10.1) |
| VC toolset | 14.51.36231 x64/x86 with ATL/MFC |
| Windows SDK | 10.0.28000 headers/libs; Debugging Tools 10.0.28000.2705 |
| Git / depot_tools / GN / Ninja | Git 2.55 plus repository-local depot_tools/GN/Ninja |
| Rust | Chromium-pinned Rust toolchain installed by upstream hooks; no parallel system toolchain required |
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
3. The workspace volume started at 146.2 GiB free and had 116.70 GiB free before
   compilation. It permits only one shallow checkout and one compact output
   with continuous measurement; it is not capacity for parallel configurations.
4. Google acceptance requires a human login and redacted evidence; credentials
   and 2FA must never be automated or stored in test assets.
5. The product working title cannot become a persisted/public identity yet.
