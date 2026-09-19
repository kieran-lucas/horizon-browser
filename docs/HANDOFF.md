# Horizon Browser Handoff

## Current status

Phase 0 is still in progress.

The Chromium build and Phase 0 executable/acceptance gates remain authoritative.
Do not start Phase 1 implementation until Phase 0 has passed.

## Visual direction update

The approved Horizon visual direction was updated during Phase 0.

Current visual sources of truth:

1. `docs/design/reference/horizon_browser_concept_gojo_refined_v9.html`
2. `docs/design/reference/horizon_concept_v9.png`
3. `docs/design/art-direction-v2.md`
4. `DESIGN_SYSTEM.md`

The current art direction is:

**Ethereal blue anime-tech minimalism**

These sources override older visual guidance only.

Architecture, engine, security, performance, compatibility, browser behavior,
data-model and feature requirements remain unchanged.

Do not begin Phase 1 with a disposable temporary visual style.

After Phase 0 passes its executable and acceptance gates, Phase 1 should build
the real Horizon shell directly toward the latest approved visual direction.

Do not modify the currently running Phase 0 Chromium build, GN args, Chromium
revision, or build output because of this visual update.

## Visual precedence

For visual/UI decisions:

1. latest approved reference in `docs/design/reference/`
2. `docs/design/art-direction-v2.md`
3. `DESIGN_SYSTEM.md`
4. older visual guidance in the original project specification

For non-visual decisions, the original project specification and accepted ADRs
remain authoritative.

## Resume rule

Before Phase 1:

- verify Phase 0 is fully PASS;
- read the latest visual reference;
- read `docs/design/art-direction-v2.md`;
- read `DESIGN_SYSTEM.md`;
- preserve all accepted architecture and security decisions;
- implement Horizon directly in the approved visual language.
