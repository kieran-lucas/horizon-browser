"""Visible ChatGPT draft typing repro at two words/second; never submits."""

from __future__ import annotations

import argparse
import ctypes
import gzip
import json
import math
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "performance"))
sys.path.insert(0, str(ROOT / "scripts" / "compatibility"))

from input_latency import (  # noqa: E402
    CDP,
    USER32,
    VK,
    chord,
    focus_control,
    key,
    launch,
    tap,
    trace_summary,
)
from foreground_scroll import find_window  # noqa: E402
from measure import eval_js, request, wait_document  # noqa: E402


PHRASE = "this is a horizon typing test at exactly two words every second"


def stats(values: list[float]) -> dict:
    ordered = sorted(values)
    if not ordered:
        return {"count": 0, "median_ms": None, "p95_ms": None, "max_ms": None}
    p95 = ordered[min(len(ordered) - 1, math.ceil(len(ordered) * .95) - 1)]
    return {
        "count": len(ordered),
        "median_ms": round(statistics.median(ordered), 3),
        "p95_ms": round(p95, 3),
        "max_ms": round(ordered[-1], 3),
    }


def type_word(word: str, duration: float = 0.38) -> None:
    interval = duration / max(1, len(word))
    for character in word:
        tap(ord(character.upper()))
        time.sleep(interval)


def find_any_visible_window(pid: int) -> int | None:
    found = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd, _):
        owner = ctypes.c_ulong()
        USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value == pid and USER32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True

    USER32.EnumWindows(callback_type(callback), None)
    return found[0] if found else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--keep-open", action="store_true")
    parser.add_argument("--attach-profile")
    parser.add_argument("--attach-pid", type=int)
    parser.add_argument("--no-trace", action="store_true")
    args = parser.parse_args()

    exe = Path(args.exe).resolve()
    artifact_root = ROOT / "compatibility-artifacts" / "chatgpt-typing"
    profile = artifact_root / f"profile-{args.label}"
    trace_path = artifact_root / f"{args.label}.json.gz"
    report_path = artifact_root / f"{args.label}.json"
    artifact_root.mkdir(parents=True, exist_ok=True)
    attaching = bool(args.attach_profile)
    if attaching:
        profile = Path(args.attach_profile).resolve()
        if not args.attach_pid:
            raise ValueError("--attach-pid is required with --attach-profile")
    elif profile.exists():
        shutil.rmtree(profile)

    proc = browser = page = None
    succeeded = False
    try:
        if attaching:
            port = int((profile / "DevToolsActivePort").read_text(encoding="utf8").splitlines()[0])
            browser = CDP(request(f"http://127.0.0.1:{port}/json/version")["webSocketDebuggerUrl"])
            page_info = next(item for item in request(f"http://127.0.0.1:{port}/json/list")
                             if item["type"] == "page" and "chatgpt.com" in item["url"])
            page = CDP(page_info["webSocketDebuggerUrl"])
            window = find_window(args.attach_pid)
            if not window:
                hwnd = find_any_visible_window(args.attach_pid)
                if not hwnd:
                    raise RuntimeError("Existing Horizon test window was not found")
                USER32.ShowWindow(hwnd, 9)
            else:
                hwnd = window[0]
            chord(0x12)
            USER32.SetForegroundWindow(hwnd)
            time.sleep(.3)
            if USER32.GetForegroundWindow() != hwnd:
                raise RuntimeError("Existing Horizon test window could not be foregrounded")
            class AttachedProcess:
                pid = args.attach_pid
            proc = AttachedProcess()
        else:
            proc, browser, page, hwnd = launch(exe, profile, "https://chatgpt.com/")
        wait_document(page, 30)
        target = None
        for _ in range(80):
            target = eval_js(page, """(() => {
              const candidates = [...document.querySelectorAll(
                  '#prompt-textarea, textarea, [contenteditable="true"]')];
              const element = candidates.find(e => {
                const r = e.getBoundingClientRect();
                return r.width > 100 && r.height > 20;
              });
              if (!element) return null;
              const alreadyInstrumented =
                  element.id === 'horizon-chatgpt-repro' &&
                  Array.isArray(window.horizonChatgptSamples);
              element.id = 'horizon-chatgpt-repro';
              window.horizonChatgptSamples = [];
              if (!alreadyInstrumented) {
                element.addEventListener('input', event => {
                  const at = performance.now();
                  requestAnimationFrame(first => requestAnimationFrame(second => {
                    horizonChatgptSamples.push({inputType: event.inputType, at, first,
                                                second, delay: second - at});
                  }));
                });
              }
              return {tag: element.tagName, contenteditable: element.isContentEditable};
            })()""")
            if target:
                break
            time.sleep(.25)
        if not target:
            title = eval_js(page, "document.title")
            body = eval_js(page, "document.body?.innerText.slice(0, 300)")
            raise RuntimeError(f"ChatGPT composer was not found: {title!r} {body!r}")
        focus = focus_control(page, hwnd, "horizon-chatgpt-repro")
        if not focus["focused"] or focus["active"] != "horizon-chatgpt-repro":
            raise RuntimeError(f"ChatGPT composer did not receive native focus: {focus}")

        # A prior attached run may have intentionally left text behind while
        # investigating dropped Backspace events. Clear it through the real
        # input path, then exclude that setup from page-side samples.
        chord(VK["CONTROL"], ord("A"))
        tap(VK["BACK"])
        time.sleep(.3)
        eval_js(page, "horizonChatgptSamples.length = 0")

        if not args.no_trace:
            browser.call("Tracing.start", {
                "transferMode": "ReturnAsStream",
                "categories": "benchmark,cc,devtools.timeline,input,latencyInfo,rail,renderer.scheduler,toplevel,ui,views,viz,disabled-by-default-devtools.timeline.frame",
            })
            browser.call("Tracing.recordClockSyncMarker", {"syncId": "typing-start"})
        words = PHRASE.split()
        for index, word in enumerate(words):
            started = time.perf_counter()
            type_word(word)
            if index != len(words) - 1:
                tap(VK["SPACE"])
            remaining = .5 - (time.perf_counter() - started)
            if remaining > 0:
                time.sleep(remaining)

        time.sleep(.8)
        value_after_typing = eval_js(page, """(() => {
          const e = document.getElementById('horizon-chatgpt-repro');
          return e.isContentEditable ? e.innerText : e.value;
        })()""")
        if not args.no_trace:
            browser.call("Tracing.recordClockSyncMarker", {"syncId": "delete-start"})
        for _ in range(len(value_after_typing)):
            tap(VK["BACK"])
            time.sleep(.15)
        time.sleep(.8)
        if not args.no_trace:
            browser.call("Tracing.recordClockSyncMarker", {"syncId": "delete-end"})

        snapshot = eval_js(page, """(() => {
          const e = document.getElementById('horizon-chatgpt-repro');
          return {value: e.isContentEditable ? e.innerText : e.value,
                  samples: horizonChatgptSamples};
        })()""")
        trace_report = None
        trace_events = 0
        relative_trace_path = None
        if not args.no_trace:
            browser.call("Tracing.end")
            stream = browser.event("Tracing.tracingComplete", 60)["stream"]
            chunks = []
            while True:
                item = browser.call("IO.read", {"handle": stream})
                chunks.append(item["data"])
                if item.get("eof"):
                    break
            raw = "".join(chunks)
            with gzip.open(trace_path, "wt", encoding="utf8") as output:
                output.write(raw)
            events = json.loads(raw)["traceEvents"]
            trace_report = trace_summary(events)
            trace_events = len(events)
            relative_trace_path = str(trace_path.relative_to(ROOT))
        inserts = [sample["delay"] for sample in snapshot["samples"]
                   if sample["inputType"].startswith("insert")]
        deletes = [sample["delay"] for sample in snapshot["samples"]
                   if sample["inputType"] == "deleteContentBackward"]
        report = {
            "label": args.label,
            "exe": str(exe),
            "site": "https://chatgpt.com/",
            "phrase": PHRASE,
            "words": len(words),
            "target_words_per_second": 2,
            "delete_interval_ms": 150,
            "composer": target,
            "value_after_typing": value_after_typing,
            "value_after_delete": snapshot["value"],
            "submitted": False,
            "input_to_second_animation_frame": {
                "insert": stats(inserts),
                "delete": stats(deletes),
            },
            "tracing_enabled": not args.no_trace,
            "trace": trace_report,
            "trace_events": trace_events,
            "trace_file": relative_trace_path,
            "process_id": proc.pid,
            "profile": str(profile.relative_to(ROOT)),
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf8")
        print(json.dumps(report, indent=2))
        succeeded = True
    finally:
        if page:
            page.close()
        if browser:
            browser.close()
        if (proc and not attaching and proc.poll() is None and
                (not succeeded or not args.keep_open)):
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


if __name__ == "__main__":
    main()
