# Third-party licenses

This is the Phase 0 license register, not the final binary notice bundle.

| Component | License/obligation status | Intended use |
|---|---|---|
| Chromium | BSD-style plus per-component third-party notices | Production base; preserve notices and generate inventory from pinned tree |
| Brave Core | MPL-2.0 plus third-party notices | Architecture/source reference only unless separately approved |
| adblock-rust | MPL-2.0 | Candidate library; file-level copyleft and notice/source obligations require review |
| adblock-rust-ffi | MPL-2.0, repository archived in 2024 | Do not adopt as-is; reference its narrow-boundary pattern only |
| Lexend | OFL-1.1 (must be reverified at vendoring) | Candidate UI font; vendor license and font binaries together |
| Filter lists | List-specific, unresolved | No list ships until redistribution and update terms are recorded |

Before the first distributable build, generate a machine-readable inventory
from the exact Chromium tree, audit every newly introduced dependency, and
produce the corresponding binary notice bundle. No Brave service, logo, API
credential, filter endpoint, or branded asset is licensed merely because its
source is public.
