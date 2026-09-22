"""Small, repeatable Horizon runtime probe using the local Chromium build.

Requires websocket-client (python -m pip install --user websocket-client).
Creates an isolated disposable profile and records a global Chromium trace.
"""

import argparse
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

import psutil
import websocket


ROOT = Path(__file__).resolve().parents[2]
EXE = ROOT / ".engine/chromium/src/out/phase0/chrome.exe"
ARTIFACTS = ROOT / "performance-artifacts"


def request(url):
    return json.load(urllib.request.urlopen(url, timeout=3))


class CDP:
    def __init__(self, url):
        self.ws = websocket.create_connection(url, timeout=30, suppress_origin=True)
        self.next_id = 0
        self.events = []

    def call(self, method, params=None, timeout=30):
        self.next_id += 1
        ident = self.next_id
        self.ws.send(json.dumps({"id": ident, "method": method, "params": params or {}}))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.ws.settimeout(max(0.1, deadline - time.monotonic()))
            message = json.loads(self.ws.recv())
            if message.get("id") == ident:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})
            self.events.append(message)
        raise TimeoutError(method)

    def event(self, method, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for i, item in enumerate(self.events):
                if item.get("method") == method:
                    return self.events.pop(i)["params"]
            self.ws.settimeout(max(0.1, deadline - time.monotonic()))
            item = json.loads(self.ws.recv())
            if item.get("method") == method:
                return item["params"]
            self.events.append(item)
        raise TimeoutError(method)

    def close(self):
        self.ws.close()


def eval_js(cdp, expression):
    result = cdp.call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
    return result.get("result", {}).get("value")


def wait_document(cdp, timeout=25):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            state = eval_js(cdp, "document.readyState")
            if state == "complete":
                return
        except Exception:
            pass
        time.sleep(0.1)
    raise TimeoutError("document.readyState")


def process_sample(pid):
    root = psutil.Process(pid)
    processes = [root] + root.children(recursive=True)
    private = working = cpu = count = 0
    for process in processes:
        try:
            memory = process.memory_info()
            private += memory.private
            working += memory.rss
            times = process.cpu_times()
            cpu += times.user + times.system
            count += 1
        except psutil.Error:
            pass
    return {"count": count, "private_mb": round(private/1048576, 1),
            "working_mb": round(working/1048576, 1), "cpu_s": round(cpu, 2)}


def summarize(events):
    complete = [e for e in events if e.get("ph") == "X" and "dur" in e]
    def durations(name):
        return sorted(e["dur"] / 1000 for e in complete if name in e.get("name", ""))
    def stats(values):
        return {"count": len(values), "median_ms": round(values[len(values)//2], 2) if values else None,
                "p95_ms": round(values[min(len(values)-1, int(len(values)*.95))], 2) if values else None,
                "max_ms": round(values[-1], 2) if values else None}
    names = ["RunTask", "PipelineReporter", "FrameSequenceTracker", "DrawAndSwap",
             "EventLatency", "GestureScroll", "ScrollUpdate", "Layout", "Paint", "RasterTask"]
    return {name: stats(durations(name)) for name in names}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("label", choices=["baseline", "after"])
    parser.add_argument("--keep-profile", action="store_true")
    args = parser.parse_args()
    ARTIFACTS.mkdir(exist_ok=True)
    (ARTIFACTS / "traces").mkdir(exist_ok=True)
    profile = ARTIFACTS / f"probe-profile-{args.label}"
    if profile.resolve().parent != ARTIFACTS.resolve():
        raise ValueError("Profile path escaped performance-artifacts")
    if profile.exists():
        shutil.rmtree(profile)
    started = time.perf_counter()
    proc = subprocess.Popen([str(EXE), f"--user-data-dir={profile}",
                             "--remote-debugging-port=0", "--remote-allow-origins=*",
                             "--no-first-run", "--no-default-browser-check", "chrome://newtab/"],
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        port_file = profile / "DevToolsActivePort"
        while not port_file.exists() and time.perf_counter() - started < 90:
            time.sleep(.05)
        if not port_file.exists():
            raise TimeoutError("DevToolsActivePort")
        port = int(port_file.read_text().splitlines()[0])
        devtools_ms = round((time.perf_counter() - started)*1000)
        browser = CDP(request(f"http://127.0.0.1:{port}/json/version")["webSocketDebuggerUrl"])
        pages = request(f"http://127.0.0.1:{port}/json/list")
        first_page = next(p for p in pages if p["type"] == "page")
        page = CDP(first_page["webSocketDebuggerUrl"])
        wait_document(page)
        ntp_ms = round((time.perf_counter() - started)*1000)
        ntp_nav = eval_js(page, "JSON.stringify(performance.getEntriesByType('navigation').map(n=>({dcl:n.domContentLoadedEventEnd,load:n.loadEventEnd})))")
        before = process_sample(proc.pid)
        time.sleep(4)
        idle_a = process_sample(proc.pid)
        time.sleep(5)
        idle_b = process_sample(proc.pid)

        browser.call("Tracing.start", {"transferMode": "ReturnAsStream",
                    "categories": "benchmark,cc,devtools.timeline,input,latencyInfo,renderer.scheduler,toplevel,viz,disabled-by-default-devtools.timeline.frame"})
        timings = {}
        # Internal page readiness and DOM-side route changes.
        for url in ["chrome://settings/", "chrome://history/", "chrome://downloads/"]:
            begin = time.perf_counter()
            page.call("Page.navigate", {"url": url})
            wait_document(page)
            timings[url] = round((time.perf_counter()-begin)*1000)

        # Five realistic domains retain separate renderers. Network variability is
        # reported as such; the synthetic long page supplies a stable scroll path.
        domains = ["https://example.com/", "https://www.wikipedia.org/",
                   "https://developer.mozilla.org/", "https://github.com/", "https://www.youtube.com/"]
        target_ids = []
        for url in domains:
            target_ids.append(browser.call("Target.createTarget", {"url": url})["targetId"])
        time.sleep(7)
        five = process_sample(proc.pid)
        switch_times = []
        for _ in range(4):
            for target in target_ids:
                begin = time.perf_counter()
                browser.call("Target.activateTarget", {"targetId": target})
                switch_times.append(round((time.perf_counter()-begin)*1000, 2))

        # Scroll a predictable document. Remote desktop sessions may reject
        # synthetic wheel input, so this captures paint/compositor behavior only.
        browser.call("Target.activateTarget", {"targetId": first_page["id"]})
        page.call("Page.navigate", {"url": "data:text/html,<style>body{margin:0;font:20px Arial}article{height:20000px;background:repeating-linear-gradient(white,white 200px,%23eef4fb 201px,%23eef4fb 400px)}</style><article>Horizon scroll probe</article>"})
        wait_document(page)
        eval_js(page, "(() => { let n=0; function step(){scrollBy(0,120); if(++n<60) requestAnimationFrame(step)} requestAnimationFrame(step); return true })()")
        time.sleep(3)
        browser.call("Tracing.end")
        complete = browser.event("Tracing.tracingComplete", timeout=50)
        stream = complete["stream"]
        chunks = []
        while True:
            read = browser.call("IO.read", {"handle": stream}, timeout=30)
            chunks.append(read["data"])
            if read.get("eof"):
                break
        browser.call("IO.close", {"handle": stream})
        raw = "".join(chunks)
        trace_path = ARTIFACTS / "traces" / f"{args.label}.json.gz"
        with gzip.open(trace_path, "wt", encoding="utf-8") as output:
            output.write(raw)
        events = json.loads(raw).get("traceEvents", [])
        result = {"label": args.label, "devtools_ms": devtools_ms, "ntp_ready_ms": ntp_ms,
                  "ntp_navigation_timing": ntp_nav, "one_tab": before,
                  "idle_start": idle_a, "idle_end": idle_b, "five_tabs": five,
                  "internal_page_navigation_ms": timings, "tab_activation_command_ms": switch_times,
                  "trace_events": len(events), "trace_summary": summarize(events),
                  "trace_file": str(trace_path.relative_to(ROOT))}
        (ARTIFACTS / f"{args.label}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(json.dumps(result, indent=2))
        page.close()
        browser.close()
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not args.keep_profile and profile.exists():
            shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
