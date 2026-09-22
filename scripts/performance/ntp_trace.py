"""Capture an NTP reload trace and report its expensive renderer tasks."""

import gzip
import json
from pathlib import Path
import shutil
import subprocess
import time

from measure import ARTIFACTS, CDP, EXE, request, wait_document


def main():
    profile = ARTIFACTS / "ntp-trace-profile"
    if profile.resolve().parent != ARTIFACTS.resolve():
        raise ValueError("Profile path escaped performance-artifacts")
    if profile.exists():
        shutil.rmtree(profile)
    proc = subprocess.Popen(
        [str(EXE), f"--user-data-dir={profile}", "--remote-debugging-port=0",
         "--remote-allow-origins=*", "--no-first-run", "--no-default-browser-check",
         "chrome://newtab/"],
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        page = CDP(next(p for p in request(f"http://127.0.0.1:{port}/json/list")
                        if p["type"] == "page")["webSocketDebuggerUrl"])
        wait_document(page)
        time.sleep(3)
        browser.call("Tracing.start", {"transferMode": "ReturnAsStream",
                     "categories": "blink,cc,devtools.timeline,loading,renderer.scheduler,toplevel,v8,viz,disabled-by-default-devtools.timeline.frame"})
        begin = time.perf_counter()
        page.call("Page.reload")
        wait_document(page)
        ready = round((time.perf_counter()-begin)*1000)
        time.sleep(3)
        browser.call("Tracing.end")
        stream = browser.event("Tracing.tracingComplete", 60)["stream"]
        chunks = []
        while True:
            item = browser.call("IO.read", {"handle": stream})
            chunks.append(item["data"])
            if item.get("eof"):
                break
        raw = "".join(chunks)
        label = __import__("sys").argv[1]
        trace_path = ARTIFACTS / "traces" / f"ntp-{label}.json.gz"
        with gzip.open(trace_path, "wt", encoding="utf8") as output:
            output.write(raw)
        events = json.loads(raw)["traceEvents"]
        threads = {(x["pid"], x["tid"]): x["args"].get("name") for x in events
                   if x.get("ph") == "M" and x.get("name") == "thread_name"}
        processes = {x["pid"]: x["args"].get("name") for x in events
                     if x.get("ph") == "M" and x.get("name") == "process_name"}
        top = sorted((x for x in events if x.get("ph") == "X" and
                      processes.get(x["pid"]) in ("WebUI Top Renderer", "Renderer") and
                      threads.get((x["pid"], x["tid"])) == "CrRendererMain" and
                      x.get("dur", 0) >= 10000),
                     key=lambda x: x["dur"], reverse=True)[:30]
        report = {"ready_ms": ready, "events": len(events),
                  "top_renderer_tasks": [{"ms": round(x["dur"]/1000, 2),
                                       "process": processes.get(x["pid"]),
                                       "name": x["name"],
                                       "data": str(x.get("args", {}))[:300]}
                                      for x in top]}
        (ARTIFACTS / f"ntp-{label}.json").write_text(json.dumps(report, indent=2), encoding="utf8")
        print(json.dumps(report, indent=2))
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
