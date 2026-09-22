"""Short, non-committing real-world compatibility smoke for Horizon."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "performance"))
sys.path.insert(0, str(ROOT / "scripts" / "compatibility"))

from input_latency import evaluate, launch  # noqa: E402
from measure import wait_document  # noqa: E402


EXE = ROOT / ".engine" / "chromium" / "src" / "out" / "phase0" / "chrome.exe"
ARTIFACTS = ROOT / "compatibility-artifacts" / "real-world"
PROFILE = ARTIFACTS / "clean-profile"


def navigate(page, url: str, settle: float = 2.0) -> dict:
    started = time.monotonic()
    response = page.call("Page.navigate", {"url": url}, timeout=30)
    wait_document(page, timeout=30)
    time.sleep(settle)
    return {
        "requested_url": url,
        "url": evaluate(page, "location.href"),
        "title": evaluate(page, "document.title"),
        "load_ms": round((time.monotonic() - started) * 1000),
        "navigation_error": response.get("errorText"),
    }


def type_without_submit(page, selectors: list[str], text: str) -> dict:
    selector_json = json.dumps(selectors)
    found = evaluate(page, f"""(() => {{
      for (const selector of {selector_json}) {{
        const elements = [...document.querySelectorAll(selector)];
        const element = elements.find(e => {{
          const r = e.getBoundingClientRect();
          return r.width > 20 && r.height > 15;
        }});
        if (!element) continue;
        element.focus();
        return {{selector, tag: element.tagName, role: element.getAttribute('role'),
                 contenteditable: element.isContentEditable}};
      }}
      return null;
    }})()""")
    if not found:
        return {"found": False, "typed": False}
    page.call("Input.insertText", {"text": text})
    time.sleep(0.8)
    value = evaluate(page, """(() => {
      const e = document.activeElement;
      return e?.isContentEditable ? e.innerText : e?.value;
    })()""")
    return {"found": True, "typed": text in (value or ""), "value": value, **found}


def scroll_check(page) -> dict:
    before = evaluate(page, "scrollY") or 0
    evaluate(page, "scrollBy(0, 700)")
    time.sleep(0.4)
    after = evaluate(page, "scrollY") or 0
    evaluate(page, "scrollBy(0, -700)")
    return {"before": before, "after": after, "moved": after > before}


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    if PROFILE.exists():
        shutil.rmtree(PROFILE)
    proc = browser = page = None
    report = {"profile": "clean/no extensions", "sites": []}
    try:
        proc, browser, page, _ = launch(EXE, PROFILE, "about:blank")

        chatgpt = navigate(page, "https://chatgpt.com/", 3)
        chatgpt["draft"] = type_without_submit(
            page,
            ["#prompt-textarea", "textarea", "[contenteditable='true']"],
            "Horizon compatibility draft only")
        chatgpt["scroll"] = scroll_check(page)
        chatgpt["submitted"] = False
        report["sites"].append({"site": "ChatGPT", **chatgpt})

        google = navigate(page, "https://www.google.com/", 2)
        google["draft"] = type_without_submit(
            page, ["textarea[name='q']", "input[name='q']"],
            "horizon browser compatibility draft")
        google["submitted"] = False
        report["sites"].append({"site": "Google Search", **google})

        gmail = navigate(page, "https://mail.google.com/", 2)
        gmail["login_wall"] = "accounts.google.com" in gmail["url"]
        gmail["interaction"] = "not attempted beyond public/login state"
        report["sites"].append({"site": "Gmail", **gmail})

        docs = navigate(page, "https://docs.google.com/document/", 2)
        docs["login_wall"] = "accounts.google.com" in docs["url"]
        docs["interaction"] = "not attempted beyond public/login state"
        report["sites"].append({"site": "Google Docs", **docs})

        youtube = navigate(page, "https://www.youtube.com/watch?v=jNQXAC9IVRw", 4)
        youtube["video_present"] = bool(evaluate(page, "document.querySelector('video')"))
        if youtube["video_present"]:
            page.call("Runtime.evaluate", {"expression": """(() => {
              const v = document.querySelector('video'); v.muted = true;
              return v.play().then(() => true, () => false);
            })()""", "awaitPromise": True, "returnByValue": True})
            time.sleep(1.2)
            youtube["playback"] = evaluate(page, """(() => {
              const v = document.querySelector('video');
              const result = {paused: v.paused, currentTime: v.currentTime,
                              readyState: v.readyState};
              v.pause(); return result;
            })()""")
        youtube["scroll"] = scroll_check(page)
        report["sites"].append({"site": "YouTube", **youtube})

        github = navigate(page, "https://github.com/chromium/chromium", 3)
        github["page"] = evaluate(page, """({links: document.links.length,
          hasRepoHeader: !!document.querySelector('[itemprop="name"]'),
          bodyText: document.body.innerText.slice(0, 120)})""")
        github["scroll"] = scroll_check(page)
        report["sites"].append({"site": "GitHub", **github})

        reddit = navigate(page, "https://www.reddit.com/", 3)
        reddit["draft"] = type_without_submit(
            page, ["input[name='q']", "input[placeholder*='Search']"],
            "horizon compatibility draft")
        reddit["scroll"] = scroll_check(page)
        reddit["submitted"] = False
        report["sites"].append({"site": "Reddit", **reddit})

        wikipedia = navigate(page, "https://en.wikipedia.org/wiki/Chromium_(web_browser)", 2)
        wikipedia["draft"] = type_without_submit(
            page, ["input[name='search']", ".cdx-text-input__input"],
            "Horizon compatibility draft")
        wikipedia["scroll"] = scroll_check(page)
        wikipedia["submitted"] = False
        report["sites"].append({"site": "Wikipedia", **wikipedia})

        history = page.call("Page.getNavigationHistory")
        current = history["currentIndex"]
        navigation = {"back": False, "forward": False}
        if current > 0:
            page.call("Page.navigateToHistoryEntry", {"entryId": history["entries"][current - 1]["id"]})
            wait_document(page, 30)
            navigation["back"] = "reddit.com" in (evaluate(page, "location.href") or "")
            history_after_back = page.call("Page.getNavigationHistory")
            next_index = history_after_back["currentIndex"] + 1
            if next_index < len(history_after_back["entries"]):
                page.call("Page.navigateToHistoryEntry", {
                    "entryId": history_after_back["entries"][next_index]["id"]})
                wait_document(page, 30)
                navigation["forward"] = "wikipedia.org" in (evaluate(page, "location.href") or "")
        report["navigation"] = navigation

        target = browser.call("Target.createTarget", {"url": "https://example.com/"})["targetId"]
        browser.call("Target.activateTarget", {"targetId": target})
        browser.call("Target.closeTarget", {"targetId": target})
        report["tab_open_activate_close"] = True

        output = ARTIFACTS / "report.json"
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
    finally:
        if page:
            page.close()
        if browser:
            browser.close()
        if proc and proc.poll() is None:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
