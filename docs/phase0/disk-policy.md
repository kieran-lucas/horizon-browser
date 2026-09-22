# Phase 0 disk-budget policy

## Fixed layout

Phase 0 maintains exactly one engine checkout and one primary output:

```text
<repository>/.engine/
├── depot_tools/
└── chromium/                 # gclient solution root
    └── src/                  # the only Chromium source tree
        └── out/
            └── phase0/       # the only active build output
```

The paths and thresholds are machine-readable in `phase0-storage.json`.
`.engine/` and measurement artifacts are local-only and ignored by Git. Do not
create `out/Debug`, `out/Release`, ASan, full-symbol, or a second source tree for
Phase 0.

## Checkout and sync

From `.engine/chromium`, use the supported shallow/no-history workflow:

```powershell
..\..\scripts\phase0\disk-status.ps1 -Stage before -Operation fetch -EstimatedGrowthGiB 45
fetch --no-history chromium
..\..\scripts\phase0\disk-status.ps1 -Stage after -Operation fetch
```

The relative script path above is illustrative; resolve the repository script
path before running from the checkout. Never replace this with a second clone.
Use the same solution root for `gclient sync` and updates. Before every fetch,
sync, GN generation, build, or update, run the disk preflight; after it, capture
another snapshot.

The reproducible gclient specification is `config/phase0.gclient` and uses
upstream's documented `checkout_configuration = "small"` mode for dependencies
not strictly needed to build Chromium for development. The pinned source carries
one committed DEPS patch that disables only Chrome-branded updater integration
test binaries after Microsoft Defender quarantined a fixture as
`Trojan:Win32/Suschil!rfn`. Never add a Defender exclusion or restore that
package. Chromium updater source, browser/update targets, and browser security
remain present; those integration tests are outside the engine gate.

The solution is explicitly `managed = False`: source is detached at the recorded
local Phase 0 patch commit, while gclient manages its dependencies. Sync commands
therefore do not rebase the local patch branch or advance Chromium implicitly.

No-history reduces Git history but does not make Chromium small. `gclient sync`
still downloads the dependencies required by the pinned revision.

## Guard bands

| Free space before operation | Policy |
|---:|---|
| More than 120 GiB | Safe to begin the planned Phase 0 checkout/build |
| 80–120 GiB | Continue with close before/after measurement |
| 60–80 GiB | An estimate is mandatory; the conservative projected remainder must stay at or above 60 GiB |
| Below 60 GiB | Do not start large builds/syncs; inspect and clean safe targets first |
| Below 40 GiB | Hard stop for every data-growing operation |

The guard uses a conservative growth allowance of the larger of 125% of the
estimate or estimate plus 5 GiB. Passing the guard is not permission to ignore
unexpected growth. Stop a running step safely if the volume trends toward the
60 GiB boundary.

`fetch`, `gclient-sync`, `hooks`, `toolchain-install`, `build`, and `update`
always require an explicit growth estimate, even above 120 GiB. The guard blocks
any estimated operation whose conservative remainder would fall below 60 GiB.
`gn-gen` is measured but may use zero estimate because it is normally small;
supply an estimate if the selected args generate unusually large metadata.

By default the guard watches the Chromium checkout volume. Use `-GuardPath` for
an operation that writes primarily elsewhere. For example, guard `C:\` before
installing Visual Studio or a Windows SDK while still recording the source and
output sizes on `D:\`:

```powershell
.\scripts\phase0\disk-status.ps1 -Stage before -Operation toolchain-install `
  -GuardPath 'C:\' -EstimatedGrowthGiB 25
```

## Required snapshots

`scripts/phase0/disk-status.ps1` records JSON and Markdown under
`phase0-artifacts/disk/`. Each record contains:

- tracked-volume free space and, when different, system-volume free space;
- source size excluding the primary build output;
- primary output size;
- depot_tools, Phase 0 artifacts, configured cache, and task-temp sizes;
- pagefile allocation/usage where Windows exposes it;
- the largest unclassified directories under `.engine`;
- cleanup notes and estimated headroom for the next step.

The default scan never reads browser profiles. Directory-size scans skip
reparse points to avoid following junctions outside their intended tree.

## Phase 0 GN/build budget

Generate only `out/phase0`. Start with a compact developer configuration and
revalidate every arg against the pinned Chromium revision:

```text
is_debug = false
is_component_build = true
symbol_level = 0
blink_symbol_level = 0
v8_symbol_level = 0
target_cpu = "x64"
use_siso = false
```

This is an acceptance-test build, not a distribution configuration. Component
builds reduce peak linking pressure on this 16 GiB machine; disabling symbols
avoids multi-gigabyte PDB growth. None of these settings disables the sandbox,
site isolation, TLS, permissions, extensions, downloads, password management,
or browser functionality.

The explicit Siso opt-out selects local Ninja for predictable `-j 2` behavior
on the 16 GiB Phase 0 host; it does not disable a browser security feature.
Start with:

```powershell
autoninja -C out/phase0 chrome -j 2
```

Increase concurrency only after measured RAM, pagefile, system responsiveness,
and disk headroom all remain healthy. A faster build is not worth pagefile
expansion or system thrashing.

## Cleanup safety

Never delete `.git`, `src/third_party`, gclient-managed source, Ninja-tracked
files, depot_tools internals, toolchains, SDKs, or unidentified generated data.

Cleanup order:

1. an explicitly identified obsolete output configuration;
2. task-owned temporary files;
3. obsolete large logs, traces, or screenshots;
4. a cache whose official owner documents it as regenerable;
5. the single `out/phase0` directory only when a measured clean rebuild is
   intentionally chosen.

Before removal, record the exact absolute path, measured size, owner/purpose,
why regeneration is safe, and expected recovered space. Verify that the path is
inside the intended checkout/artifact root. Phase 0 automation does not perform
automatic cleanup; deletion remains an explicit, separately reviewed action.
