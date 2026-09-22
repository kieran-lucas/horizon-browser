"""Measure Horizon NTP geometry from its first rendered frame to settle."""

import argparse
import base64
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "performance"))

from measure import CDP, request  # pylint: disable=wrong-import-position


EXE = ROOT / ".engine" / "chromium" / "src" / "out" / "phase0" / "chrome.exe"
ARTIFACTS = ROOT / "phase2-artifacts" / "ntp-first-frame"


PROBE_SCRIPT = r"""
(() => {
  globalThis.__horizonNtpGeometry = [];
  const probeStart = performance.now();
  let previous = '';
  let frame = 0;
  function rect(root, selector) {
    const element = root && root.querySelector(selector);
    if (!element) return null;
    const value = element.getBoundingClientRect();
    return {
      x: Math.round(value.x * 100) / 100,
      y: Math.round(value.y * 100) / 100,
      width: Math.round(value.width * 100) / 100,
      height: Math.round(value.height * 100) / 100,
    };
  }
  function sample() {
    const app = document.querySelector('ntp-app');
    const root = app && app.shadowRoot;
    const initialFrame = document.querySelector('#horizonInitialFrame');
    const live = !initialFrame && root && root.querySelector('#horizonHero');
    const value = {
      frame: frame++,
      time: Math.round(performance.now() * 100) / 100,
      elapsed: Math.round((performance.now() - probeStart) * 100) / 100,
      fonts: document.fonts.status,
      source: live ? 'app' : 'initial-frame',
      content: live ? rect(root, '#content') : rect(document, '#horizonInitialFrame'),
      hero: live ? rect(root, '#horizonHero') : rect(document, '#horizonInitialHero'),
      sigil: live ? rect(root, '#horizonSigil') : rect(document, '#horizonInitialSigil'),
      wordmark: live ? rect(root, '#horizonWordmark') : rect(document, '#horizonInitialWordmark'),
      tagline: live ? rect(root, '#horizonTagline') : rect(document, '#horizonInitialTagline'),
      search: live ? rect(root, '#searchboxContainer') : rect(document, '#horizonInitialSearch'),
      shortcuts: rect(root, '#mostVisited'),
    };
    const comparable = JSON.stringify({...value, frame: 0, time: 0, elapsed: 0});
    if (comparable !== previous || performance.now() - probeStart >= 2950) {
      globalThis.__horizonNtpGeometry.push(value);
      previous = comparable;
    }
    if (performance.now() - probeStart < 3000) requestAnimationFrame(sample);
  }
  requestAnimationFrame(sample);
})();
"""


def evaluate(cdp, expression):
    result = cdp.call(
        "Runtime.evaluate", {"expression": expression, "returnByValue": True}
    )
    return result.get("result", {}).get("value")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    args = parser.parse_args()

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    profile = ARTIFACTS / f"profile-{args.label}"
    if profile.resolve().parent != ARTIFACTS.resolve():
        raise ValueError("Profile path escaped NTP artifact directory")
    if profile.exists():
        shutil.rmtree(profile)

    process = subprocess.Popen(
        [
            str(EXE),
            f"--user-data-dir={profile}",
            "--remote-debugging-port=0",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            "--window-size=1600,1000",
            "about:blank",
        ],
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        port_file = profile / "DevToolsActivePort"
        for _ in range(900):
            if port_file.exists():
                break
            time.sleep(0.05)
        if not port_file.exists():
            raise TimeoutError("DevToolsActivePort")

        port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
        page_data = next(
            page
            for page in request(f"http://127.0.0.1:{port}/json/list")
            if page["type"] == "page"
        )
        page = CDP(page_data["webSocketDebuggerUrl"])
        page.call("Page.enable")
        page.call("Page.addScriptToEvaluateOnNewDocument", {"source": PROBE_SCRIPT})
        page.call("Page.navigate", {"url": "chrome://newtab/"})

        deadline = time.monotonic() + 12
        samples = []
        while time.monotonic() < deadline:
            try:
                samples = evaluate(page, "globalThis.__horizonNtpGeometry || []") or []
                if samples and samples[-1].get("elapsed", 0) >= 2950:
                    break
            except Exception:
                pass
            time.sleep(0.05)
        if not samples:
            raise RuntimeError("NTP geometry probe collected no samples")

        shot = page.call("Page.captureScreenshot", {"format": "png"})
        (ARTIFACTS / f"{args.label}.png").write_bytes(
            base64.b64decode(shot["data"])
        )

        rendered = [sample for sample in samples if sample["content"]]
        first = rendered[0]
        settled = rendered[-1]
        deltas = {}
        for key in ("content", "hero", "sigil", "wordmark", "tagline", "search"):
            start = first.get(key)
            end = settled.get(key)
            if start and end:
                deltas[key] = {
                    field: round(end[field] - start[field], 2)
                    for field in ("x", "y", "width", "height")
                }
        report = {
            "label": args.label,
            "sample_count": len(samples),
            "geometry_state_count": len(rendered),
            "first": first,
            "settled": settled,
            "settled_minus_first": deltas,
            "states": rendered,
        }
        output = ARTIFACTS / f"{args.label}.json"
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        page.close()
    finally:
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    main()
