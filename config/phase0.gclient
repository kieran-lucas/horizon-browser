# Phase 0 gclient specification for the single Windows Chromium checkout.
#
# The pinned Chromium tree carries a small, committed DEPS patch that disables
# Chrome-branded updater integration-test artifacts after Microsoft Defender
# quarantined one fixture. Phase 0 does not weaken Defender or restore it.

solutions = [
  {
    "name": "src",
    "url": "https://chromium.googlesource.com/chromium/src.git",
    "managed": False,
    "custom_deps": {},
    "custom_vars": {
      "checkout_configuration": "small",
    },
  },
]
