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

## Current machine gap

The initial environment scan found 15.4 GiB RAM, 146.2 GiB free on the workspace
drive, Visual Studio Build Tools 2022 17.14 with VC tools but no ATL/MFC, Windows
SDK 10.0.26100, and no Git/depot_tools/GN/Ninja/Rust on `PATH`. This machine can
run a conservative component build after toolchain remediation, but a checkout
plus multiple outputs and symbols would leave poor disk headroom.

Do not start a full checkout until these are true:

1. At least 180 GiB is reserved on one NTFS volume for source, output, and a
   safe update margin.
2. The exact stable Chromium revision is recorded in `DEPENDENCIES.md`.
3. The current upstream Visual Studio and Windows SDK requirements are met.
4. `depot_tools` is first on the task-specific build `PATH`.
5. Build parallelism is capped for a 16 GiB machine.

## Planned developer configuration

The first local output will be a component development build with conservative
parallelism. Exact GN args will be committed only after the source revision is
pinned and validated; copying stale flags across Chromium milestones is unsafe.
Release acceptance uses a non-component official-style build with the sandbox,
site isolation, safe browsing/download protections, and DCHECK policy matching
the chosen distribution configuration.

Never add flags that disable the sandbox, certificate validation, site
isolation, web security, or Google embedded-user-agent enforcement.
