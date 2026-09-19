# Phase 0 test assets

The MV3 extension exercises service-worker startup, a content script, local
storage, a toolbar action/popup/badge, a context menu, and one static
declarativeNetRequest rule. It performs no remote fetch and has no native bridge.

For the product build only:

1. create a clean local profile;
2. enable the upstream developer-mode extension flow;
3. load `mv3-extension` unpacked;
4. visit a non-sensitive HTTPS test page and verify the document root has
   `data-phase0-extension="active"` using DevTools;
5. click the toolbar action, increment the profile-local counter, and verify the
   badge and popup agree after browser restart;
6. verify the context-menu command updates the counter;
7. navigate to `https://phase0-block-probe.invalid/` and confirm the DNR rule
   blocks it rather than producing an ordinary DNS error;
8. repeat in another profile and verify its counter starts at zero;
9. record results in a file conforming to
   `docs/phase0/result-template.json`.

Do not run content-script checks on account, password, financial, health, or
other sensitive pages. This extension is a capability spike, not production
code.
