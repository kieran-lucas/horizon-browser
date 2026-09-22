# Horizon Browser Handoff

## Current status

Phase 0 is complete. The Phase 1 usable browser shell was implemented and
incrementally validated on 2026-09-20. Do not redo either phase, clean the
output, change GN args, or sync Chromium as a troubleshooting reflex.

The pinned Chromium revision remains
`a1d39df07efc8101c31ec6efce60265de7689dcb`; the reusable output is
`.engine/chromium/src/out/phase0`.

Phase 1 deliberately supports Horizon's light visual treatment only. Chromium's
existing incognito and forced-colors behavior remains intact for security and
accessibility; no Horizon dark-theme design work is planned.

## Implemented in Phase 1

- native Views color mixer for the frame, tabs, toolbar and omnibox;
- Horizon New Tab WebUI with static local SVG geometry, real Chromium search
  and real Most Visited shortcuts;
- Horizon product name, window titles, profile labels and customization labels;
- Horizon SVG/PNG/ICO application identity and a high-contrast NTP favicon;
- fresh browser windows open maximized by default while restored/saved window
  placement remains authoritative;
- Chromium navigation, process isolation, sandbox, settings, history,
  bookmarks, downloads and DevTools paths are preserved.

The upstream patch surface is intentionally small: NTP HTML/CSS, one isolated
color mixer, branding resources/strings, profile icon versioning and a narrow
default-window-state rule in `WindowSizer`.

## Validation completed

- `chrome/browser/resources/new_tab_page:lint_css` and NTP resource targets;
- `chrome/browser/ui/color:mixers`;
- branding/theme/startup/window-sizer targets;
- repeated incremental `chrome` links with `-j 14`;
- `ninja` reported no unrelated full rebuild;
- fresh-profile runtime at Windows 175% scaling;
- HTTPS navigation to `https://example.com/`;
- live History, Bookmarks, Downloads, Settings, Version and Inspect WebUIs;
- fresh-profile default window state returned Windows `showCmd=3` (maximized).

Reference screenshots are under ignored `phase1-artifacts/`, including
`chrome-batch5/horizon-maximized.png`.

## Development-build performance note

`out/phase0` uses `is_component_build=true`. After `chrome.dll` is relinked,
the first launch may take several minutes while Windows/Defender reads roughly
630 component DLLs; subsequent launches are fast. A stress smoke run with 8
page targets used about 1.59 GiB aggregate private memory. Summed per-process
working sets reached about 4.46 GiB because shared DLL pages are counted in
multiple processes. This is a development-build limitation, not evidence that
the static NTP is continuously consuming that memory. Do not change the Phase 0
GN args during handoff; production non-component profiling belongs to a later
release configuration.

## Phase 2 — current implementation

Phase 2 now has a broad Horizon skin across the native browser shell and major
internal pages. The approved light, ice blue direction remains the source of
truth. The final targeted refinement pass is being validated on 2026-09-20;
do not restart this work or clean `out/phase0`.

Shared native changes cover Lexend in Views and menus, the Horizon color mixer,
menu/bubble/dialog geometry, toolbar and omnibox metrics, profile surfaces,
tab dimensions, titlebar treatment, and circular right-side Windows caption
controls. The caption order is minimize, maximize/restore, close, with the red
close control outermost. The circles have accessible names and native actions;
their visual state uses solid color, scale and compact shadow without glyphs or
Views tooltips. The Windows 11 maximize hit-test path retains Snap Layouts.

Shared WebUI changes cover local Lexend/Sora typography, `cr_elements` color,
radius, focus and control styling, and the NTP search component. Settings,
History, Downloads, Bookmarks, Extensions, passwords and related WebUIs inherit
these primitives, with page-specific layout changes in high-traffic surfaces.
NTP keeps live search and browsing functions while hiding secondary Google/AI
clutter. Browser-owned strings and icons use Horizon branding; third-party
website branding and Chromium legal credits are unchanged.

The safe internal URL presentation layer accepts `horizon://` aliases for
common browser-owned pages and maps them to Chromium's existing privileged
`chrome://` implementation. Do not globally rename the privileged scheme or
weaken WebUI process/security assumptions.

Key native patch areas: `chrome/browser/ui/color/`,
`chrome/browser/ui/views/frame/`, `chrome/browser/ui/views/tabs/`,
`chrome/browser/ui/views/toolbar/`, `chrome/browser/ui/views/location_bar/`,
`chrome/browser/ui/views/profiles/`, `ui/views/`, `ui/gfx/win/`,
`components/vector_icons/`, and `chrome/app/vector_icons/`. Key WebUI patch
areas: `chrome/browser/resources/new_tab_page/`,
`ui/webui/resources/cr_elements/`, `ui/webui/resources/cr_components/`, and
the browser-owned page resources for Settings, History, Downloads, Bookmarks,
Extensions, net errors, flags, version, print and GPU internals.

The targeted refinement pass adjusts the caption circles, Back/Forward/Reload
icons, tab radius and tab controls, omnibox focus geometry, and NTP search
geometry. The subsequent polish removes exposed NTP and omnibox AI entry
points, hides the visible tab-search control, changes the active tab to a clean
white surface with a fine stroke, and replaces the stock menu dots with soft
Horizon dots. The hidden tab-search control must not reserve tab-strip width;
the first tab now starts at the normal frame inset. A clipped active-tab shadow
was removed because it produced a visible artifact beside the New Tab button.

Keep the normal, rounded and touch vector variants synchronized. Toolbar
feature flags can select either native Views or WebUI assets at runtime.

The supplied root `app_icon.png` is the source for the Windows application
ICO, scaled native product PNGs, tiles, the NTP favicon, and the NTP hero icon.
Its square card
is masked out to leave only the blue horizon silhouette on transparent pixels,
so the NTP and desktop icons blend into their surroundings. Regenerate all
derivatives with `scripts/phase2/generate-app-icons.ps1` after any source
update. The default profile placeholder is a person silhouette; signed-in
account avatars remain their own photos. The main menu remains a three-dot
symbol, with no blue background when it has no text label. Refresh uses a
soft triangular head and a curved tail that tapers to a point.

The prior handoff incorrectly identified WebUI toolbar icons as the sole visible
source. `kWebUIToolbar` and `kWebUIReloadButton` are disabled by default in this
revision. The native `ReloadButton` and `BackForwardButton` also select stock
Lottie artwork during clicks when Glow Up is enabled. Both native `.icon` files
and `chrome/browser/resources/webui_toolbar/icons.ts` need Horizon artwork;
`scripts/phase2/sync-toolbar-icons.ps1` keeps the WebUI variants aligned.

Targeted Phase 2 refinement status on 2026-09-21: implementation and final
incremental build complete. The last build used
`third_party/ninja/ninja.exe -C out/phase0 -j8 chrome` and succeeded; log:
`out/phase0/phase2-webui-toolbar-icons-build.log`. Earlier passes also built
the transparent logo, Windows ICO, favicon, tabs and native controls. WebUI
toolbar TypeScript lint succeeded as part of the final build.

Focused runtime screenshots under `phase2-artifacts/` include
`transparent-final-default.png` and `webui-icons-final.png`. They show the
transparent larger NTP logo, Horizon NTP favicon aligned with the New Tab
title, right caption circles, first-tab inset, white active tab without the
clipped shadow, no visible tab search, no blue tab-top line, no AI Mode chip
in the focused omnibox, a person profile icon, neutral three-dot menu button,
and the redesigned WebUI toolbar icon family. Horizon launched after the last
build. The menu popup, NTP suggestion dropdown, caption hover states and a
fresh HTTPS navigation were not retested in this final pass because the active
desktop session did not grant Horizon foreground input; earlier Phase 2 and
Phase 1 checks cover some of those surfaces, but this is an audit gap. No
runtime regression was observed in the surfaces captured.

RESUME HERE: continue the Phase 2 interactive visual audit on a dedicated
foreground desktop session, starting with those four unverified interactions.
Do not begin Phase 3 until Phase 2 is explicitly accepted.

### Final targeted refinement (2026-09-21)
- Refresh icon in `chrome/browser/resources/webui_toolbar/icons.ts` now traces roughly three quarters of a circle. The nine WebUI toolbar back/forward/reload icon variants are generated by `scripts/phase2/sync-toolbar-icons.ps1`.
- `reload_button.ts` disables the old Glow Up SVG transition that briefly restored Chromium artwork after clicking Refresh. `reload_button.css` gives the Horizon icon a restrained press rotation/scale and respects reduced-motion preference. Reload/Stop functionality remains in the existing state machine.
- The 2 px favicon lift was incorrect; follow-up pixel inspection found the icon around 7 px above the Lexend title. The native tab layout has since been adjusted in both directions and needs a fresh runtime check.
- Final incremental build: `third_party/ninja/ninja.exe -C out/phase0 -j8 chrome`, log `phase2-artifacts/phase2-final-refinement-build.log`. Do not clean `out/phase0`.
- RESUME HERE for any later Phase 2 work: verify click animation and tab favicon/title alignment interactively after this build. Do not start Phase 3 without a separate request.
- Final build exited 0. Launched `out/phase0/chrome.exe` with the existing `phase2-artifacts/profile-transparent-final` profile; runtime capture: `phase2-artifacts/phase2-final-refinement-runtime.png`. Static runtime shows the revised Refresh silhouette and aligned New Tab favicon/title. Click animation itself was not captured; verify it in a foreground interactive session.

### Latest Phase 2 profile and tab correction (2026-09-21)
- Replaced the broken one-stroke tab close mark with two filled diagonal paths in `chrome/app/vector_icons/close_tab_chrome_refresh_old.icon`. The first runtime capture, `phase2-artifacts/close-tab-fixed-loaded.png`, showed a complete cross; the subsequent user-requested pass reduces its visual weight and requires a new runtime check after the incremental build.
- Restored the existing direct Add Profile route in `profile_picker/navigation_mixin.ts` after an intermediate choice screen made the original creation page appear missing. The picker remains styled, with its central product logo hidden and the visual caption title removed while retaining its accessible window title.
- The actual profile customization dialog keeps the name field, theme grid, Done/Delete actions, and avatar selection. Its large central avatar is hidden for local creation; a smaller `Customize avatar` button opens the same selector. The title and descriptive line are centered, and the dialog was reduced from 512 × 570 to 448 × 520 DIP. The selector's icons were reduced to fit the narrower dialog.
- Final incremental build: `third_party/ninja/ninja.exe -C out/phase0 -j8 chrome`, exit 0. The build included WebUI CSS/TypeScript lint. Runtime screenshots: `phase2-artifacts/tab-close-thinner-final.png` shows the complete lighter tab cross; `phase2-artifacts/add-profile-compact-final.png` shows the original creation form at 448 × 520 DIP with centered heading and description, no large avatar, and functioning name/theme controls; `phase2-artifacts/add-profile-avatar-no-horizontal-scroll.png` shows the avatar selector still works at the narrower width without a horizontal scrollbar. The picker itself has no central logo or upper-left visual title. All checks used the isolated `phase2-artifacts/profile-transparent-final` test profile.
- RESUME HERE: continue Phase 2 only on a new request. Do not begin Phase 3.

### Webpage scrollbar and New Tab position (2026-09-21)
- The Windows Fluent default webpage scrollbar is 12 DIP wide (from 15), has no top/bottom arrow buttons, and paints a square thumb. This is implemented in `ui/native_theme/native_theme_fluent.{h,cc}` and `third_party/blink/renderer/core/scroll/scrollbar_theme_fluent.{h,cc}`; corresponding Blink expectations were updated.
- The New Tab logo, wordmark and search group was lifted slightly by adding 64px to `#content` bottom padding in `chrome/browser/resources/new_tab_page/app.css`, retaining its responsive centering.
- Incremental validation: `third_party/ninja/ninja.exe -C out/phase0 -n chrome` showed the native-theme relink fanout; `third_party/ninja/ninja.exe -C out/phase0 -j8 chrome` exited 0; a follow-up dry run reported no work.
- Runtime: launched the rebuilt Horizon binary with isolated profiles. `phase2-artifacts/scrollbar-square-final.png` shows the default scrollbar on an ordinary scrollable HTML page with square thumb and no arrow buttons. `phase2-artifacts/scrollbar-square-pagedown.png` shows that the page and thumb move after Page Down. `phase2-artifacts/ntp-raised-final.png` shows the raised logo/wordmark/search group. The test page has no custom scrollbar CSS.
- RESUME HERE: continue only requested Phase 2 refinements. Do not begin Phase 3 without a separate request.

### Scrollbar compositor and search geometry correction (2026-09-21)
- Corrected the previous scrollbar claim: the native painter was square, but `cc/layers/painted_scrollbar_layer_impl.cc` still applied a rounded compositor mask. That mask is now removed, so the actual webpage thumb has straight ends. The Fluent light thumb colors in `ui/color/fluent_ui_color_mixer.cc` are lighter and slightly cool toned. The 12 DIP track and arrow removal remain.
- Fluent overlay scrollbar width now changes only from 78% to full thickness (previously 40%), over 180 ms with smooth easing. Fade starts after 850 ms and takes 200 ms. The changes are in `ui/native_theme/overlay_scrollbar_constants.{h,cc}`, `third_party/blink/renderer/platform/theme/web_theme_engine_default.cc`, `third_party/blink/renderer/platform/widget/compositing/layer_tree_settings.cc`, and `cc/input/single_scrollbar_animation_controller_thinning.cc`.
- Normal omnibox search and site-controls glyphs are hidden in `chrome/browser/ui/views/location_bar/location_bar_view.cc`, with text inset reduced to 16 DIP. Informational chips such as File are hidden too; security warning text such as Not Secure remains visible. The NTP leading search icon is hidden and its input starts at 24px in `chrome/browser/resources/new_tab_page/ntp_searchbox.css`.
- The blue selected autocomplete row now has 12px corners in native `chrome/browser/ui/views/omnibox/omnibox_result_view.cc` and shared WebUI `ui/webui/resources/cr_components/searchbox/searchbox_match.css`.
- Incremental builds: `third_party/ninja/ninja.exe -C out/phase0 -j8 chrome` succeeded, with final log `phase2-artifacts/omnibox-left-final-build.log`; CSS and TypeScript lint passed. One link attempt failed because a Codex-launched Horizon process held `chrome.dll`; after closing that test window, the final link succeeded. No clean was run.
- Runtime screenshots: `phase2-artifacts/scrollbar-v3-idle.png` shows the square, lighter thumb; `phase2-artifacts/ntp-no-search-icons-final.png` shows the NTP and omnibox without leading search icons; `phase2-artifacts/suggestion-rounded-final.png` shows typed autocomplete with the rectangular blue selected row. After the final File-chip edit, Horizon launched and UI Automation found no File chip, while the address edit remained present. The local scroll page also exercised smooth programmatic scrolling without custom scrollbar CSS. The desktop's foreground restrictions prevented a full hover animation recording; HTTPS navigation from the test launcher was rejected by automatic command review, so the ordinary HTTPS site-controls state was not visually captured.
- RESUME HERE: continue requested Phase 2 refinements. Do not begin Phase 3 without a separate request.
