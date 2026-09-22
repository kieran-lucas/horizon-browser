"""Trace rapid native tab cycling in a foreground Horizon window."""

import argparse
import ctypes
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import time

from foreground_menu import chord, key
from foreground_scroll import find_window, user32
from measure import ARTIFACTS, CDP, EXE, request, wait_document


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--combined", action="store_true")
    parser.add_argument("--alternate", action="store_true")
    args = parser.parse_args()
    profile = ARTIFACTS / "tabs-profile"
    if profile.resolve().parent != ARTIFACTS.resolve():
        raise ValueError("Profile path escaped performance-artifacts")
    if profile.exists():
        shutil.rmtree(profile)
    proc = subprocess.Popen(
        [str(EXE), f"--user-data-dir={profile}", "--remote-debugging-port=0",
         "--remote-allow-origins=*", "--no-first-run", "--no-default-browser-check",
         "chrome://newtab/"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        port_file = profile / "DevToolsActivePort"
        for _ in range(900):
            if port_file.exists():
                break
            time.sleep(.1)
        port = int(port_file.read_text().splitlines()[0])
        browser = CDP(request(f"http://127.0.0.1:{port}/json/version")["webSocketDebuggerUrl"])
        urls = ["https://example.com/", "https://en.wikipedia.org/wiki/Chromium_(web_browser)",
                "https://developer.mozilla.org/en-US/docs/Web/JavaScript",
                "https://github.com/", "https://www.youtube.com/"]
        targets = []
        for url in urls:
            targets.append(browser.call("Target.createTarget", {"url": url})["targetId"])
            time.sleep(.6)
        time.sleep(8)
        if args.combined:
            browser.call("Target.activateTarget", {"targetId": targets[1]})
            time.sleep(.3)
        window = find_window(proc.pid)
        if not window:
            raise RuntimeError("No visible Horizon window")
        hwnd, rect = window
        chord(0x12)
        user32.SetForegroundWindow(hwnd)
        time.sleep(.3)
        if user32.GetForegroundWindow() != hwnd:
            raise RuntimeError("Foreground access unavailable")
        if args.combined:
            user32.SetCursorPos((rect.left + rect.right)//2, (rect.top + rect.bottom)//2)
        browser.call("Tracing.start", {"transferMode": "ReturnAsStream",
                     "categories": "benchmark,cc,input,latencyInfo,toplevel,ui,views,viz,disabled-by-default-devtools.timeline.frame"})
        if args.combined:
            for _ in range(35):
                user32.mouse_event(0x0800, 0, 0, ctypes.c_ulong(-120).value, 0)
                time.sleep(.012)
            chord(0x11, 0x09)  # Switch immediately after the wheel burst.
            chord(0x11, 0x4C)  # Focus omnibox immediately.
            for letter in "horizon browser":
                vk = 0x20 if letter == " " else ord(letter.upper())
                key(vk, True)
                key(vk, False)
                time.sleep(.02)
            chord(0x1B)
            chord(0x11, 0x09)
            for _ in range(20):
                user32.mouse_event(0x0800, 0, 0, ctypes.c_ulong(-120).value, 0)
                time.sleep(.012)
            chord(0x12, 0x46)  # Menu during recent navigation/scroll.
            time.sleep(.12)
            chord(0x1B)
        else:
            for i in range(30):
                if args.alternate and i % 2:
                    chord(0x11, 0x10, 0x09)  # Ctrl+Shift+Tab.
                else:
                    chord(0x11, 0x09)  # Ctrl+Tab.
                time.sleep(.075)
        time.sleep(.5)
        browser.call("Tracing.end")
        stream = browser.event("Tracing.tracingComplete", 60)["stream"]
        chunks = []
        while True:
            item = browser.call("IO.read", {"handle": stream})
            chunks.append(item["data"])
            if item.get("eof"):
                break
        raw = "".join(chunks)
        label = "combined-165" if args.combined else (
            "tabs-alternate-165" if args.alternate else "tabs-after")
        with gzip.open(ARTIFACTS / "traces" / f"{label}.json.gz", "wt", encoding="utf8") as output:
            output.write(raw)
        events = json.loads(raw)["traceEvents"]
        processes = {x["pid"]: x["args"].get("name") for x in events
                     if x.get("ph") == "M" and x.get("name") == "process_name"}
        threads = {(x["pid"], x["tid"]): x["args"].get("name") for x in events
                   if x.get("ph") == "M" and x.get("name") == "thread_name"}
        tasks = sorted((x for x in events if x.get("ph") == "X" and
                        x.get("name") == "ThreadControllerImpl::RunTask" and
                        processes.get(x["pid"]) == "Browser" and
                        threads.get((x["pid"], x["tid"])) == "CrBrowserMain"),
                       key=lambda x: x.get("dur", 0), reverse=True)
        report = {"switches": 2 if args.combined else 30, "events": len(events),
                  "browser_main_max_ms": round(tasks[0]["dur"] / 1000, 2) if tasks else None,
                  "browser_main_over_16ms": [
                      {"ms": round(x["dur"] / 1000, 2),
                       "source": x.get("args", {}).get("src_file")}
                      for x in tasks if x.get("dur", 0) >= 16000][:20]}
        (ARTIFACTS / f"{label}.json").write_text(json.dumps(report, indent=2), encoding="utf8")
        print(json.dumps(report, indent=2))
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
