"""Focused 165 Hz Settings route and scroll validation on the accepted build."""

import collections
import gzip
import json
import shutil
import subprocess
import time

from foreground_scroll import find_window, user32
from measure import ARTIFACTS, CDP, EXE, eval_js, request, wait_document


def main():
    profile = ARTIFACTS / "settings-165-profile"
    if profile.resolve().parent != ARTIFACTS.resolve():
        raise ValueError("Profile path escaped performance-artifacts")
    if profile.exists():
        shutil.rmtree(profile)
    proc = subprocess.Popen(
        [str(EXE), f"--user-data-dir={profile}", "--remote-debugging-port=0",
         "--remote-allow-origins=*", "--no-first-run", "--no-default-browser-check",
         "chrome://settings/"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        port_file = profile / "DevToolsActivePort"
        for _ in range(900):
            if port_file.exists():
                break
            time.sleep(.1)
        port = int(port_file.read_text().splitlines()[0])
        browser = CDP(request(f"http://127.0.0.1:{port}/json/version")["webSocketDebuggerUrl"])
        targets = request(f"http://127.0.0.1:{port}/json/list")
        page = CDP(next(x for x in targets if x["type"] == "page")["webSocketDebuggerUrl"])
        wait_document(page)
        page.call("Page.navigate", {"url": "chrome://settings/"})
        for _ in range(200):
            if (eval_js(page, "location.href") or "").startswith("chrome://settings"):
                break
            time.sleep(.1)
        wait_document(page)
        time.sleep(2)
        window = find_window(proc.pid)
        if not window:
            raise RuntimeError("No visible Settings window")
        hwnd, rect = window
        user32.keybd_event(0x12, 0, 0, 0)
        user32.keybd_event(0x12, 0, 2, 0)
        user32.SetForegroundWindow(hwnd)
        time.sleep(.2)
        if user32.GetForegroundWindow() != hwnd:
            raise RuntimeError("Foreground access unavailable")
        user32.SetCursorPos(rect.left + int((rect.right-rect.left)*.65),
                            rect.top + int((rect.bottom-rect.top)*.55))
        browser.call("Tracing.start", {"transferMode": "ReturnAsStream",
                     "categories": "benchmark,cc,devtools.timeline,input,latencyInfo,toplevel,ui,views,viz,disabled-by-default-devtools.timeline.frame"})
        routes = ["privacy", "appearance", "performance", "autofill", "search"] * 4
        results = []
        for route in routes:
            start = time.perf_counter()
            actual = eval_js(page, "(() => { const ui=document.querySelector('settings-ui');"
                             "const menu=ui?.shadowRoot?.querySelector('#leftMenu');"
                             f"const item=menu?.shadowRoot?.querySelector('#{route}');"
                             "if (!item) return 'missing'; item.click(); return location.pathname; })()")
            results.append({"route": route, "path": actual,
                            "click_return_ms": round((time.perf_counter()-start)*1000, 2)})
            if route == "performance":
                user32.mouse_event(0x0800, 0, 0, (-120) & 0xffffffff, 0)
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
        with gzip.open(ARTIFACTS / "traces" / "settings-165.json.gz", "wt", encoding="utf8") as output:
            output.write(raw)
        events = json.loads(raw)["traceEvents"]
        states = collections.Counter(x.get("args", {}).get("frame_reporter", {}).get("state")
                                     for x in events if x.get("name") == "PipelineReporter" and x.get("ph") == "b")
        report = {"routes": results, "frame_states": dict(states), "events": len(events)}
        (ARTIFACTS / "settings-165.json").write_text(json.dumps(report, indent=2), encoding="utf8")
        print(json.dumps(report, indent=2))
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
