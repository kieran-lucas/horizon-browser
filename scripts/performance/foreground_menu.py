"""Trace first and repeated native menu openings through Windows input."""

import argparse
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import time

from foreground_scroll import find_window, user32
from measure import ARTIFACTS, CDP, EXE, request, wait_document


def key(vk, down):
    user32.keybd_event(vk, 0, 0 if down else 2, 0)


def chord(*keys):
    for vk in keys:
        key(vk, True)
    for vk in reversed(keys):
        key(vk, False)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--surface", choices=["menu", "profile"], default="menu")
    parser.add_argument("--label", default="after")
    args = parser.parse_args()
    profile = ARTIFACTS / f"{args.surface}-profile"
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
        page = CDP(next(x for x in request(f"http://127.0.0.1:{port}/json/list")
                        if x["type"] == "page")["webSocketDebuggerUrl"])
        wait_document(page)
        time.sleep(2)
        window = find_window(proc.pid)
        if not window:
            raise RuntimeError("No visible Horizon window")
        hwnd = window[0]
        chord(0x12)  # Allow foreground activation from this process.
        user32.SetForegroundWindow(hwnd)
        time.sleep(.25)
        if user32.GetForegroundWindow() != hwnd:
            raise RuntimeError("Foreground access unavailable")
        browser.call("Tracing.start", {"transferMode": "ReturnAsStream",
                     "categories": "benchmark,cc,input,toplevel,ui,views,viz,disabled-by-default-devtools.timeline.frame"})
        for i in range(12):
            if args.surface == "menu":
                chord(0x12, 0x46)  # Alt+F: main menu.
            else:
                chord(0x11, 0x10, 0x4D)  # Ctrl+Shift+M: profile popup.
            time.sleep(.25 if i == 0 else .08)
            chord(0x1B)
            time.sleep(.08)
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
        with gzip.open(ARTIFACTS / "traces" / f"{args.surface}-{args.label}.json.gz", "wt", encoding="utf8") as output:
            output.write(raw)
        events = json.loads(raw)["traceEvents"]
        processes = {x["pid"]: x["args"].get("name") for x in events
                     if x.get("ph") == "M" and x.get("name") == "process_name"}
        threads = {(x["pid"], x["tid"]): x["args"].get("name") for x in events
                   if x.get("ph") == "M" and x.get("name") == "thread_name"}
        browser_tasks = sorted((x for x in events if x.get("ph") == "X" and
                                x.get("name") == "ThreadControllerImpl::RunTask" and
                                processes.get(x["pid"]) == "Browser" and
                                threads.get((x["pid"], x["tid"])) == "CrBrowserMain"),
                               key=lambda x: x.get("dur", 0), reverse=True)
        report = {"surface": args.surface, "open_close_count": 12, "events": len(events),
                  "browser_main_tasks_over_16ms": [
                      {"ms": round(x["dur"]/1000, 2),
                       "source": x.get("args", {}).get("src_file")}
                      for x in browser_tasks if x.get("dur", 0) >= 16000][:20]}
        (ARTIFACTS / f"{args.surface}-{args.label}.json").write_text(json.dumps(report, indent=2), encoding="utf8")
        print(json.dumps(report, indent=2))
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
