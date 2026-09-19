# Design system

Status: Phase 0 foundation. The referenced `aoi_browser_concept_01.html` was not
present in the workspace on 2026-09-19, so no claim is made that prototype
measurements were extracted. When it is added, render it at 2560×1600 and amend
this document with measured spacing, proportions, and screenshots rather than
reconstructing it from memory.
## Visual authority

The current visual source of truth for Horizon is:

1. `docs/design/reference/horizon_browser_concept_gojo_refined_v9.html`
2. `docs/design/art-direction-v2.md`
3. this document
4. older visual guidance in the original project specification

If any older visual instruction conflicts with the latest approved reference,
follow the latest approved reference.

This precedence applies only to visual/UI decisions.

Architecture, engine, security, performance, browser compatibility and feature
requirements from the original project specification remain authoritative.

### Current visual north star

**Ethereal blue anime-tech minimalism**

Horizon should feel calm, cold, intelligent, slightly supernatural, bright,
airy and premium, with strong negative space, luminous soft-blue ambient
energy, restrained Japanese/anime symbolism and quiet browser chrome.

The governing principle is **restraint**.
## Direction

Soft-premium, light, warm ivory/gray, restrained blue accents, crisp and dense
without crowding. Japanese/anime influence appears only in abstract flow,
asymmetry, line rhythm, and editorial whitespace. No glass/acrylic material,
literal character art, neon, generic purple gradients, or oversized bubble UI.

## Semantic color tokens

Tokens are semantic so the product can be renamed or tuned without rewriting
components.

| Token | Initial value | Use |
|---|---:|---|
| `color.canvas` | `#FBFAF7` | primary internal-page ground |
| `color.canvas.subtle` | `#F6F6F4` | secondary ground |
| `color.chrome` | `#F2F1EE` | browser chrome |
| `color.chrome.sunken` | `#ECEBE9` | inactive strip/separators |
| `color.text.primary` | `#20242B` | primary type/icons |
| `color.text.secondary` | `#7D838D` | metadata |
| `color.accent` | `#3D70EA` | focused/selected action |
| `color.accent.strong` | `#2652C9` | pressed/high-contrast accent |
| `color.accent.soft` | `#EAF0FF` | restrained selection ground |

All combinations require measured WCAG contrast; a soft palette is not license
to make disabled, secondary, or focus states ambiguous.

## Typography

Use one UI family. Lexend is the initial candidate, subject to OFL verification,
font-size raster tests, and a side-by-side comparison with Windows-optimized
alternatives. Text is rendered by Chromium/Skia/DirectWrite; never rasterized
into assets or continuously scale-animated.

Tune each control with explicit size, weight, line height, tracking, baseline,
and truncation. Tab and omnibox labels must remain sharp throughout animation;
motion uses container opacity/translation, not text scaling.

## Geometry and elevation

- Small controls: 8–10 DIP radius.
- Medium surfaces: 10–14 DIP.
- Floating browser-owned panels: 14–18 DIP.
- Nested radii follow the parent inset; they are not independently maximized.
- Active tab prominence is 2/3: clearly lifted with a restrained blue cue and
  short clean shadow, still attached to the strip.
- Shadows are static or compositor-friendly and never a changing large blur.

These are starting ranges, not constants. Tune against 125%, 150%, and 175%
scale with physical-pixel inspection.

## Motion

Input acknowledgment occurs in the same frame when possible; state changes do
not wait for animation.

| Tier | Budget | Examples |
|---|---:|---|
| Micro | 80–160 ms | hover, press, close icon |
| UI transition | 160–250 ms | tab state, omnibox panel, downloads |
| Structural | 220–350 ms | detach handoff, split open/close |

Use Chromium compositor-native transform and opacity animation. Avoid animated
layout dimensions, per-frame UI-thread callbacks, blur, large changing shadows,
or text scaling. Reduced motion removes spring/displacement while preserving an
immediate state transition.

## DPI and visual acceptance

Create golden captures at a 2560×1600 logical target under 125%, 150%, and 175%
scales. Verify physical-pixel alignment of tab curves, icon stems, one-pixel
strokes, omnibox border, popup edge, SVG art, text baselines, and active-tab
shadow. Also test a live move between monitors of different scale factors.

## New Tab composition

Quiet asymmetric vector artwork leads to replaceable brand typography, a short
tagline, one primary search/address field, then four to six compact shortcuts.
Assets are local SVG/procedural geometry with a restrictive internal-page CSP.
Cold entrance motion may run once; repeated New Tabs must appear immediately.

## Missing concept follow-up

When `aoi_browser_concept_01.html` becomes available:

1. capture exact 2560×1600 renders at required scale factors;
2. inventory palette, spacing rhythm, active tab, omnibox, New Tab composition,
   SVG language, popup radius, and shadow;
3. record changes as refinements with before/after evidence;
4. preserve the rated 8/10 visual language unless native behavior, readability,
   or pixel quality requires a specific adjustment.
