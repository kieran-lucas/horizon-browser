"""Trace real Windows wheel input through a foreground Horizon window."""

import collections
import argparse
import ctypes
import gzip
import json
from pathlib import Path
import shutil
import subprocess
import time

from measure import ARTIFACTS, CDP, EXE, eval_js, request, wait_document


user32 = ctypes.windll.user32
user32.GetForegroundWindow.restype = ctypes.c_void_p
user32.SetForegroundWindow.argtypes = [ctypes.c_void_p]
user32.GetWindowThreadProcessId.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
user32.SetProcessDPIAware()


class Rect(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def find_window(pid):
    found = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, unused):
        owner = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and user32.IsWindowVisible(hwnd):
            rect = Rect()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            if rect.right - rect.left > 400 and rect.bottom - rect.top > 300:
                found.append((hwnd, rect))
        return True

    user32.EnumWindows(callback_type(callback), None)
    return found[0] if found else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url")
    parser.add_argument("--label", default="after")
    args = parser.parse_args()
    profile = ARTIFACTS / "wheel-profile"
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
        if not port_file.exists():
            raise TimeoutError("DevToolsActivePort")
        port = int(port_file.read_text().splitlines()[0])
        browser = CDP(request(f"http://127.0.0.1:{port}/json/version")["webSocketDebuggerUrl"])
        target = next(x for x in request(f"http://127.0.0.1:{port}/json/list") if x["type"] == "page")
        page = CDP(target["webSocketDebuggerUrl"])
        wait_document(page)
        url = args.url or ("data:text/html,<style>body{margin:0;font:20px Arial}"
                           "article{height:50000px;background:repeating-linear-gradient("
                           "white,white 200px,%23eef4fb 201px,%23eef4fb 400px)}"
                           "</style><article>Horizon wheel probe</article>")
        page.call("Page.navigate", {"url": url})
        for _ in range(300):
            if (eval_js(page, "document.readyState") == "complete" and
                    (eval_js(page, "document.body?.scrollHeight") or 0) > 2000):
                break
            time.sleep(.1)
        if args.url:
            time.sleep(3)
        window = None
        for _ in range(100):
            window = find_window(proc.pid)
            if window:
                break
            time.sleep(.1)
        if not window:
            raise RuntimeError("No visible Horizon window")
        hwnd, rect = window
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)
        user32.SetForegroundWindow(hwnd)
        time.sleep(.3)
        if user32.GetForegroundWindow() != hwnd:
            raise RuntimeError("Foreground access unavailable")
        user32.SetCursorPos((rect.left + rect.right)//2, (rect.top + rect.bottom)//2)
        time.sleep(.2)
        browser.call("Tracing.start", {"transferMode": "ReturnAsStream",
                     "categories": "benchmark,cc,devtools.timeline,gpu,input,latencyInfo,renderer.scheduler,toplevel,viz,disabled-by-default-devtools.timeline.frame,disabled-by-default-cc.debug"})
        for _ in range(70):
            user32.mouse_event(0x0800, 0, 0, ctypes.c_ulong(-120).value, 0)
            time.sleep(.012)
        time.sleep(1)
        scroll_y = eval_js(page, "scrollY")
        browser.call("Tracing.end")
        stream = browser.event("Tracing.tracingComplete", 60)["stream"]
        chunks = []
        while True:
            item = browser.call("IO.read", {"handle": stream})
            chunks.append(item["data"])
            if item.get("eof"):
                break
        raw = "".join(chunks)
        with gzip.open(ARTIFACTS / "traces" / f"wheel-{args.label}.json.gz", "wt", encoding="utf8") as output:
            output.write(raw)
        events = json.loads(raw)["traceEvents"]
        names = collections.Counter(x.get("name") for x in events)
        interesting = {name: count for name, count in names.items()
                       if any(s in (name or "") for s in
                              ("FrameSequence", "PipelineReporter", "EventLatency",
                               "GestureScroll", "Wheel", "DrawAndSwap", "InputLatency"))}
        report = {"url": eval_js(page, "location.href"), "scroll_y": scroll_y,
                  "scroll_height": eval_js(page, "document.body?.scrollHeight"),
                  "trace_events": len(events),
                  "interesting_events": interesting}
        (ARTIFACTS / f"wheel-{args.label}.json").write_text(json.dumps(report, indent=2), encoding="utf8")
        print(json.dumps(report, indent=2))
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
