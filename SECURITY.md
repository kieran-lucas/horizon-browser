# Security policy and engineering baseline

## Non-negotiable platform protections

The product does not disable or weaken Chromium sandboxing, renderer/process
separation, site isolation, origin enforcement, TLS validation, Safe Browsing or
equivalent download reputation protections, permission checks, or extension
isolation to make a feature or site work.

It does not spoof a user agent to bypass sign-in policy, inject into Google
authentication, copy cookies/tokens from another browser, bypass Chrome
App-Bound Encryption/DPAPI identity protections, or silently open an external
browser and report in-product sign-in success.

## Internal origins and IPC

- Choose the public internal scheme only after the product name is final.
- Privileged pages serve local versioned resources only, enforce strict CSP,
  reject `eval`/remote script, and expose the minimum handler set.
- Every renderer message has a typed schema, size limits, origin/context check,
  explicit error response, and cancellable lifetime.
- Normal webpages receive no native host object or privileged JavaScript API.
- External protocol launches display the canonical protocol and target app and
  require explicit confirmation unless a safe remembered policy exists.

## Secrets and diagnostics

Reuse Chromium's password manager and Windows-backed protection. Passwords,
auth tokens, cookies, autofill values, page/form contents, and private URLs are
never logged. Reveal/export requires OS authentication where upstream supports
it. Password CSV import/export is explicit, transient, and warns that the file
is plaintext. Crash artifacts and Phase 0 screenshots are sanitized before they
leave the local machine.

See [`docs/security/password-manager-threat-model.md`](docs/security/password-manager-threat-model.md).

## Supply chain and updates

- Pin immutable revisions and generate third-party license inventories.
- Release binaries/installers/updates are signed.
- Updates use authenticated transport, verify signatures before activation,
  swap atomically, preserve profile data, and support rollback.
- Filter-list updates are versioned, checksum/signature verified, parsed off the
  UI thread, atomically published, and rolled back on parse/health failure.
- No remote executable script is accepted as a filter-list payload.

## Reporting

Until a private reporting address exists, do not file reports containing
credentials, tokens, cookies, browsing data, or private crash dumps in a public
issue tracker. The repository will add a coordinated disclosure contact before
any external distribution.
