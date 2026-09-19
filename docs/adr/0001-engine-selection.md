# ADR-0001: Browser engine and shell architecture

- Status: **Provisionally accepted; executable acceptance gate open**
- Date: 2026-09-19
- Decision owners: product and browser engineering
- Scope: Windows 11 x86-64 V1

## Context

The product must behave as a real browser, allow ordinary top-level Google web
sign-in in Gmail, YouTube, and Drive, keep several local profiles isolated,
provide custom premium browser chrome, and preserve a credible Manifest V3
extension path. Spoofing user-agent data, scripting Google sign-in, importing
tokens/cookies, or delegating the sign-in to another browser are forbidden.

The repository began empty. The target host has 15.4 GiB RAM and 146.2 GiB free
on its workspace drive. It does not currently meet the full upstream Chromium
toolchain requirements; this ADR therefore separates an architecture decision
from the still-required executable acceptance evidence.

## Decision

Use a **full Chromium-derived browser architecture**. Keep Chromium's browser
process and Views/Aura shell primitives, then apply a deliberately small,
rebase-friendly product presentation layer. Pin an immutable stable Chromium
revision after checkout. Begin from Chromium 153 stable-family source for the
first viability build, then advance to the latest security-serviced stable
revision before distribution.

The decision is not permission to ship an untested fork. Phase 1 remains
blocked until the fork binary passes the Google compatibility, profile
isolation, extension, tab/window, and browser-basics tests in the Phase 0
matrix. A failed Google top-level login with an otherwise unmodified,
non-spoofed build reopens engine selection; it is never worked around.

## Why this direction

Chromium is the only evaluated option that simultaneously supplies browser-level
Profiles, WebContents, site isolation, password/download/content-settings
services, tab/window reparenting, PiP, DevTools, session restore, and the full
extension architecture while leaving the Views browser chrome replaceable.
Current source already models split tabs and presents their live contents in
`MultiContentsView`, reducing a major V1 implementation risk.

The full-browser context also matches Google's secure-browser requirement: the
user can inspect the top-level URL and connection security, and the embedding
application does not receive Google authorization traffic or session cookies.
This is an architectural fit, not a guarantee; only the manual smoke test can
accept the product build.

## Evidence and evaluation

| Criterion | Full Chromium fork | Chromium + selected Brave techniques | WebView2 native shell | CEF Chrome bootstrap + Alloy-style shell |
|---|---|---|---|---|
| Google web sign-in policy fit | Best fit: full top-level browser; executable proof pending | Same Chromium base if kept as a full browser; proof pending | **Fail**: Microsoft explicitly says Google Authentication is disabled in embedded WebViews including WebView2 | High policy/product risk: custom-hosted CEF remains an embedded user-agent; no bypass is acceptable |
| Profile isolation | Native `Profile` model covers cookies, history, storage, passwords, sessions, extensions | Native Chromium profile plus Brave additions | Multiple profiles exist, but hard auth gate already fails | Request contexts exist; parity and leakage tests still required |
| Custom browser chrome | Deep Views/Aura control; highest implementation cost | Deep control; larger inherited product/removal surface | Excellent native-shell control | Alloy-style allows control, but feature parity is reduced |
| Extension path | Fullest MV3 architecture and UI hooks | Mature browser path, plus Brave-specific coupling to remove/audit | Not browser-equivalent; internal extension surfaces are unavailable | Upstream says Chrome extension API is supported only with Chrome-style browsers/windows; Alloy extension API was removed in M128 |
| Split/tab/window | Native tabs, drag/detach, and current split primitives | Same base | Must build/reparent multiple controllers and recreate browser semantics | Must build significant browser product semantics above CEF |
| Security-update burden | Very high, but direct upstream alignment | Very high plus Brave patch/service dependencies | Runtime serviced by Microsoft | CEF plus Chromium cadence and application integration burden |
| Visual target | Achievable with controlled Views/WebUI changes | Achievable, but removing unrelated Brave UI/services is substantial | Achievable, but irrelevant after auth failure | Custom shell achievable only by accepting capability/policy risk |
| Result | **Selected, conditional on executable gate** | Use techniques/components selectively; do not base V1 wholesale without a later ADR | **Rejected for production** | **Rejected for production** |

### WebView2 rejection

Microsoft's official feature-difference document says Google Authentication is
disabled in embedded WebViews including WebView2. The same document records
that Translate is off, push notifications are not implemented, browser profile
identity/sync is off, and browser internal pages such as extensions/settings are
blocked. Google's OAuth policy says developers must not direct authorization
requests through an embedded user-agent under their control. These are stable
policy constraints, not missing UI work. A prototype attempting to bypass them
would be unethical and cannot produce valid acceptance evidence.

Sources:

- [Microsoft: Differences between Edge and
  WebView2](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/browser-features)
- [Google OAuth 2.0 Policies — Use secure
  browsers](https://developers.google.com/identity/protocols/oauth2/policies)
- [Google: Sign in with a supported
  browser](https://support.google.com/accounts/answer/7675428)

WebView2 remains permissible only for isolated non-production visual experiments
that do not claim to meet browser acceptance.

### CEF rejection

CEF's old Alloy bootstrap was removed in M128. The supported combination is now
Chrome bootstrap with either Chrome or Alloy style. CEF upstream states that
the Alloy extension API was removed and that the Chrome extension API works
only with Chrome-style browsers/windows. Choosing Chrome style gives back
upstream Chrome UI instead of the required shell; choosing Alloy style closes
the credible extension path and still presents Google with a developer-hosted
embedded environment. Maintaining another abstraction layer does not reduce the
underlying Chromium security-update burden.

Source: [CEF issue #3685: Alloy bootstrap removal and runtime
differences](https://github.com/chromiumembedded/cef/issues/3685).

### Brave-derived option

Brave demonstrates a maintainable Chromium customization layer and a native
blocking pipeline. Its `adblock-rust` engine is a valuable later dependency
candidate. A wholesale Brave Core base is not selected now because it adds
MPL-covered product code, branded services, API-key assumptions, wallet/rewards
and privacy features outside V1, and another large patch layer to understand.
Those removal and audit costs do not improve the primary Google/profile gate.

Sources:

- [Brave Core](https://github.com/brave/brave-core)
- [Brave adblock-rust](https://github.com/brave/adblock-rust)

## Implementation boundaries

- Preserve upstream sandbox, site isolation, process separation, TLS,
  permissions, password manager, safe download behavior, and updater signing.
- Use upstream `Profile`, `Browser`, `TabInterface`, `TabStripModel`, and
  `WebContents`; do not duplicate model state in controls.
- Use Views/Aura and Chromium compositor-native animations for top chrome.
- Use local, CSP-restricted WebUI for New Tab and management pages.
- Keep product namespaces and persisted identities neutral until naming is final.
- Integrate ad blocking later through a narrow, reviewed worker-sequence
  boundary; do not adopt the archived `adblock-rust-ffi` repository as-is.

## Risks and mitigations

| Risk | Mitigation / exit criterion |
|---|---|
| Google rejects the product build or a required site breaks | Run the no-spoof manual matrix in two clean profiles; failure reopens this ADR |
| Security releases outpace a personal fork | Automate upstream merge/build/smoke cadence; keep patch surface small; never defer a critical merge for visual polish |
| 16 GiB local build pressure | Conservative `autoninja -j`, component dev builds, minimal symbols, sccache after measurement, and later CI/remote release builds |
| Disk pressure | Reserve at least 180 GiB before checkout; keep source and outputs on one verified NTFS volume; prune only explicit build outputs |
| UI rewrite becomes unmergeable | Prefer tokens/factories/controllers and separately owned files; inventory every upstream edit |
| Chromium trademark/API/service assumptions | Use replaceable product identity; audit terms, keys, endpoints, codecs, and distribution licenses before release |
| Password/security regressions | Reuse upstream password manager and OS-auth surfaces; run the threat model and browser tests before UI customization lands |

## Future migration cost

Moving from full Chromium to WebView2 would require discarding browser-level
profiles, extension UI, tab/window semantics, password/download integration,
and accepting the Google-auth failure; it is not a viable migration. Moving to
CEF would similarly replace core browser services with application-owned ones.
Moving from Chromium to a Brave-derived base is technically feasible because of
the common upstream, but would require rebasing every product patch and auditing
Brave services/licensing. Therefore the lowest-cost future path is to remain
close to Chromium stable and selectively port isolated, licensed techniques.

## Acceptance required to close this ADR

1. Build the branded-but-neutral Chromium fork without weakening security.
2. Complete every P0 row in the acceptance matrix on that exact binary.
3. Attach sanitized result JSON and screenshots/traces that contain no account
   identifiers, tokens, cookies, or private URLs.
4. Record the exact Chromium revision and build configuration.
5. Change this ADR status to `Accepted` only when all P0 rows pass.
