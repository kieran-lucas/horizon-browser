"""Trace real rapid omnibox typing and suggestion traversal."""

import argparse
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
    parser.add_argument("--exe", default=str(EXE))
    parser.add_argument("--label", default="after")
    parser.add_argument("--artifact-dir", default=str(ARTIFACTS))
    args = parser.parse_args()
    exe = Path(args.exe).resolve()
    artifact_dir = Path(args.artifact_dir).resolve()
    trace_dir = artifact_dir / "traces"
    trace_dir.mkdir(parents=True, exist_ok=True)
    profile = artifact_dir / f"omnibox-profile-{args.label}"
    if profile.resolve().parent != artifact_dir:
        raise ValueError("Profile path escaped artifact directory")
    if profile.exists():
        shutil.rmtree(profile)
    proc = subprocess.Popen(
        [str(exe), f"--user-data-dir={profile}", "--remote-debugging-port=0",
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
        page = CDP(next(x for x in request(f"http://127.0.0.1:{port}/json/list")
                        if x["type"] == "page")["webSocketDebuggerUrl"])
        wait_document(page)
        page.call("Page.navigate", {"url": "https://example.com/"})
        wait_document(page)
        time.sleep(2)
        window = find_window(proc.pid)
        if not window:
            raise RuntimeError("No visible Horizon window")
        hwnd = window[0]
        chord(0x12)
        user32.SetForegroundWindow(hwnd)
        time.sleep(.3)
        if user32.GetForegroundWindow() != hwnd:
            raise RuntimeError("Foreground access unavailable")
        browser.call("Tracing.start", {"transferMode": "ReturnAsStream",
                     "categories": "benchmark,cc,input,latencyInfo,toplevel,ui,views,viz,disabled-by-default-devtools.timeline.frame"})
        chord(0x11, 0x4C)  # Ctrl+L
        time.sleep(.08)
        for letter in "chromium browser performance":
            vk = 0x20 if letter == " " else ord(letter.upper())
            key(vk, True)
            key(vk, False)
            time.sleep(.022)
        time.sleep(.25)
        for _ in range(10):
            chord(0x28)  # Down through changing suggestions.
            time.sleep(.025)
        for _ in range(5):
            chord(0x26)  # Up.
            time.sleep(.025)
        chord(0x1B)
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
        with gzip.open(trace_dir / f"omnibox-{args.label}.json.gz", "wt", encoding="utf8") as output:
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
        report = {"label": args.label, "exe": str(exe),
                  "typed_chars": 28, "arrow_keys": 15, "events": len(events),
                  "browser_main_max_ms": round(tasks[0]["dur"] / 1000, 2) if tasks else None,
                  "browser_main_over_16ms": [
                      {"ms": round(x["dur"] / 1000, 2),
                       "source": x.get("args", {}).get("src_file")}
                      for x in tasks if x.get("dur", 0) >= 16000][:20]}
        (artifact_dir / f"omnibox-{args.label}.json").write_text(
            json.dumps(report, indent=2), encoding="utf8")
        print(json.dumps(report, indent=2))
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
