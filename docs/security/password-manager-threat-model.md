# Password manager threat model

- Status: Phase 0 baseline; implementation is upstream Chromium infrastructure
- Last review: 2026-09-19

## Assets and security goals

Assets include saved credentials, generated passwords before submission,
autofill decisions, password metadata, OS-protected encryption material, export
files, and authentication state used to reveal/export. Secrets must remain
encrypted at rest, unavailable to sandboxed renderers except for an authorized
autofill operation, absent from logs/crash metadata, and separated by profile.

The product does not claim to protect secrets from malware already executing as
the same Windows user with equivalent privileges. It does aim to preserve every
upstream Chromium/Windows mitigation that raises the cost of offline profile
theft, cross-user access, renderer compromise, and casual disclosure.

## Threats and controls

| Threat | Required control | Residual risk / test |
|---|---|---|
| Read-only theft of profile directory | Reuse upstream Windows password store and per-user OS protection; never write plaintext credential blobs | Same-user compromise may still invoke user-context APIs; verify copied profile is insufficient on another account/machine |
| Another Windows user | User-scoped data ACLs and OS-bound secret protection; never use machine-wide `CRYPTPROTECT_LOCAL_MACHINE` for a user vault | Administrators can bypass ordinary ACLs; test standard-user separation |
| Malware as same user | OS authentication before reveal/export, no broad IPC, least-privilege processes | Cannot fully defend an already compromised user session; document honestly |
| Compromised renderer | Browser-process policy and upstream password-manager IPC; exact frame/origin checks; no vault API in page JS | Browser-process exploit remains high impact; preserve sandbox/site isolation tests |
| Malicious/compromised extension | Upstream extension permission and incognito model; no new credential API; profile-scoped state | Powerful user-approved extensions remain risky; test unprivileged extension cannot enumerate secrets |
| Clipboard leakage | Avoid automatic copy, clear only when platform/product policy is reliable, show visible feedback | Other same-user apps may observe clipboard; test no background copy |
| Logs and crash dumps | Structured redaction, never serialize secret/form fields, audit crash keys | Memory dumps can contain process memory; restrict collection/access and require explicit diagnostics flow |
| CSV import/export | Explicit user action, OS auth for export, no retained temp copy, clear plaintext warning and deletion guidance | File remains readable until user securely removes it; integration test scans product temp roots |
| Shoulder surfing/screen capture | Mask by default, time-bound reveal, OS auth, visible state | Authorized screen/session capture cannot be completely prevented |

## Trust boundaries

```text
Web renderer (hostile)
  → validated Chromium password-manager IPC
Browser process policy/autofill controller
  → upstream password store
Windows per-user protection / OS authentication
  → encrypted profile data
```

Internal password-management WebUI is privileged but not trusted by default: it
gets only typed handlers needed for list metadata, reveal, delete, and export.
Reveal/export handlers re-check the initiating profile, active WebUI origin,
user gesture, and OS-auth result. Secret values do not enter generic metrics,
URLs, DOM attributes that outlive the view, or exception strings.

## Generated passwords

Use Chromium's cryptographically secure generator and entropy source. Defaults
are strong, site constraints are explicit inputs, seeds are never predictable,
and generated material follows the same secret-lifetime/logging rules as saved
credentials.

## Import decision

V1 imports passwords only from a user-selected Chrome/Google Password Manager
CSV. The importer streams/parses on a worker, validates bounded fields, sends
credentials through the upstream password-store API, zeros practical transient
buffers, closes/deletes only product-created temporaries, and never modifies the
source file. Direct decryption of another browser's store is out of scope.

## Review triggers

Re-review before modifying upstream password storage, adding sync, changing OS
authentication, enabling a new extension API, collecting crash dumps, adding a
new import/export format, or changing profile/incognito semantics.
