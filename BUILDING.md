# Building

## Supported production baseline

The intended target is Windows 11 x86-64 and a release-pinned Chromium source
checkout. We will follow the toolchain required by the selected Chromium
revision, not maintain a parallel CMake/MSBuild browser shell.

At the 2026-09-19 snapshot, upstream Chromium's Windows instructions require:

- Windows 10 or newer;
- more than 16 GiB RAM recommended;
- at least 100 GiB free on NTFS;
- Visual Studio 2026 18.0 or newer, Desktop C++, ATL/MFC;
- Windows 11 SDK `10.0.28000.2270` and Debugging Tools
  `10.0.26100.3323` or newer;
- `depot_tools`, GN, Ninja/Autoninja, Python, and Git supplied/used as upstream
  documents.

Source: [Chromium Windows build
instructions](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/windows_build_instructions.md).

## Current machine state

The initial environment scan found 15.4 GiB RAM and 146.2 GiB free on the
workspace drive. Phase 0 installed the required stable Build Tools 2026 18.10.1,
MSVC 14.51 x64/x86, ATL/MFC, SDK 28000, and Debugging Tools 28000.2705. Git is
installed system-wide; depot_tools, GN, Ninja, Clang, Python, and Rust remain
revision-controlled or bootstrapped by the single Chromium checkout.

For the Build Tools SKU, the current catalog exposes the C++ desktop workload as
`Microsoft.VisualStudio.Workload.VCTools`; the full IDE uses
`Microsoft.VisualStudio.Workload.NativeDesktop`. Required components are verified
with `vswhere`, not inferred from installer exit status.

The checkout/build workflow requires these invariants:

1. The disk preflight reports more than 120 GiB free on the checkout volume, or
   the stricter lower-band estimate rules in `docs/phase0/disk-policy.md` pass.
2. The exact stable Chromium revision is recorded in `DEPENDENCIES.md`.
3. The current upstream Visual Studio and Windows SDK requirements remain met.
4. `depot_tools` is first on the task-specific build `PATH`.
5. Only `.engine/chromium/src` and `out/phase0` exist as the engine source and
   primary output, respectively.
6. Build parallelism starts at two jobs for this 16 GiB machine.

## Planned developer configuration

Checkout uses `fetch --no-history chromium`. The first local output is the only
Phase 0 output: `out/phase0`, a no-symbol component acceptance build with two
jobs. The pinned revision uses Ninja explicitly (`use_siso = false`) so `-j 2`
is deterministic on the 16 GiB host. Exact GN args are revalidated against every
pinned source update; copying stale flags across Chromium milestones is unsafe.
This is not the later distribution configuration. See
`docs/phase0/disk-policy.md` for the args and mandatory before/after
measurements.

Never add flags that disable the sandbox, certificate validation, site
isolation, web security, or Google embedded-user-agent enforcement.

## Phase 1 incremental workflow

Phase 1 reuses `.engine/chromium/src/out/phase0`; never clean or regenerate it
without concrete evidence. From a PowerShell process, restore the toolchain with:

```powershell
$env:PATH = "$PWD\.engine\depot_tools;$env:PATH"
$env:DEPOT_TOOLS_WIN_TOOLCHAIN = "0"
$env:vs2026_install = "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools"
```

Build the smallest relevant target first. The final Phase 1 integration command
is:

```powershell
autoninja.bat -C out/phase0 chrome -j 14
```

The current machine sustains `-j 14` without OOM during incremental work. High
physical RAM use alone is not a reason to lower it; watch commit limit, compiler
kills and throughput. The component build can have a very slow first launch
after relinking `chrome.dll`, followed by fast cached launches.
