# Dependency Baseline

This file distinguishes verified releases from selected/pinned dependencies.
Nothing is considered pinned until its immutable revision and license inventory
are recorded here.

| Component | Verified 2026-09-19 | Selection status |
|---|---:|---|
| Chrome stable on test host | 153.0.8010.53 | Evidence host only; not a source pin |
| Chromium | Tag `153.0.8010.53`, commit `792bf6722e73a45aa9e47c163b9901bdc17f3230` | Phase 0 upstream pin; shallow checkout |
| Phase 0 Chromium patch | `a1d39df07efc8101c31ec6efce60265de7689dcb` | Local child commit; disables only Chrome updater integration-test artifacts blocked by Defender |
| Visual Studio 2026 | 18.10.1 stable | Build-host target; Chromium minimum is 18.0.0 |
| MSVC / Windows SDK | MSVC 14.51.36231; SDK 10.0.28000; Debugging Tools 10.0.28000.2705 | Installed Phase 0 host toolchain |
| Git for Windows | 2.55 | Checkout host tool; long-path support enabled for Chromium |
| Brave release | 1.95.x / Chromium 153 | Reference only; not selected as a distribution |
| CEF API line | 15400 exists upstream | Rejected production candidate |
| WebView2 SDK | 1.0.4191.47 / Runtime 152 release | Rejected production engine |
| Windows App SDK | 2.5.1 stable | Not required by selected Chromium shell |
| adblock-rust | current audited revision TBD | Future Phase 5 candidate, MPL-2.0 |

Version evidence:

- [Chrome stable release
  announcement](https://chromereleases.googleblog.com/2026/09/stable-channel-update-for-desktop_0808145027.html)
- [WebView2 SDK release
  notes](https://learn.microsoft.com/en-us/microsoft-edge/webview2/release-notes/sdk/)
- [Windows App SDK release
  channels](https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/release-channels)
- [Brave release
  schedule](https://github.com/brave/brave-browser/wiki/Brave-Release-Schedule)

## Pinning policy

- Chromium is pinned to an immutable official stable tag/revision and updated
  promptly for security releases.
- Rust crates are locked and vendored according to Chromium/Brave-compatible
  policy; `cargo update` is never part of a release build.
- Filter lists are data dependencies with their own license, version, checksum,
  signature/update source, parser-compatibility test, and rollback metadata.
- Product services and API keys belonging to Chromium, Google, or Brave are not
  assumed reusable.
