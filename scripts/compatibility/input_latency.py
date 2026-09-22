"""Repeatable Chrome/Horizon foreground typing and input-to-presentation probe."""

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
import time

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "performance"))

from measure import CDP, request, wait_document  # noqa: E402
from foreground_scroll import find_window, user32 as USER32  # noqa: E402


KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
VK = {
    "BACK": 0x08, "TAB": 0x09, "RETURN": 0x0D, "CONTROL": 0x11,
    "SHIFT": 0x10, "ESCAPE": 0x1B, "SPACE": 0x20, "END": 0x23,
    "HOME": 0x24, "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27,
    "DOWN": 0x28, "DELETE": 0x2E,
}


def key(vk: int, down: bool = True) -> None:
    USER32.keybd_event(vk, 0, 0 if down else KEYEVENTF_KEYUP, 0)


def tap(vk: int) -> None:
    key(vk)
    key(vk, False)


def chord(*keys: int) -> None:
    for value in keys:
        key(value)
    for value in reversed(keys):
        key(value, False)


def type_ascii(text: str, interval: float) -> None:
    for char in text:
        if char == " ":
            tap(VK["SPACE"])
        elif "a" <= char <= "z":
            tap(ord(char.upper()))
        elif "A" <= char <= "Z":
            key(VK["SHIFT"])
            tap(ord(char))
            key(VK["SHIFT"], False)
        else:
            raise ValueError(f"Unsupported fixture character: {char!r}")
        time.sleep(interval)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1)]


def stats(values: list[float]) -> dict:
    return {
        "count": len(values),
        "median_ms": round(statistics.median(values), 3) if values else None,
        "p95_ms": round(percentile(values, 0.95), 3) if values else None,
        "max_ms": round(max(values), 3) if values else None,
        "over_16_67_ms": sum(value > 16.67 for value in values),
    }


def async_durations(events: list[dict], name: str) -> list[tuple[dict, float]]:
    open_events: dict[tuple, list[dict]] = {}
    result = []
    for event in events:
        if event.get("name") != name or event.get("ph") not in ("b", "e"):
            continue
        ident = event.get("id2", {}).get("local", event.get("id"))
        key_value = (event.get("pid"), ident)
        if event["ph"] == "b":
            open_events.setdefault(key_value, []).append(event)
        elif open_events.get(key_value):
            begin = open_events[key_value].pop(0)
            result.append((begin, (event["ts"] - begin["ts"]) / 1000))
    return result


def trace_summary(events: list[dict]) -> dict:
    by_type: dict[str, list[float]] = {}
    high_latency = 0
    for begin, duration in async_durations(events, "EventLatency"):
        data = begin.get("args", {}).get("event_latency", {})
        event_type = data.get("event_type", "UNKNOWN")
        by_type.setdefault(event_type, []).append(duration)
        high_latency += bool(data.get("has_high_latency"))
    key_types = {kind: stats(values) for kind, values in by_type.items()
                 if "KEY" in kind or "CHAR" in kind}

    component_latencies = []
    component_paths = []
    for event in events:
        if not event.get("name", "").startswith("InputLatency::") or event.get("ph") != "b":
            continue
        if "Key" not in event["name"] and "Char" not in event["name"]:
            continue
        components = event.get("args", {}).get("chrome_latency_info", {}).get("component_info", [])
        times = {item.get("component_type"): item.get("time_us") for item in components}
        original = times.get("COMPONENT_INPUT_EVENT_LATENCY_ORIGINAL")
        presented = times.get("COMPONENT_INPUT_EVENT_LATENCY_FRAME_SWAP")
        if original is not None and presented is not None:
            component_latencies.append((presented - original) / 1000)
        if components:
            component_paths.append([item.get("component_type") for item in components])
    return {
        "event_latency_key_to_presentation": key_types,
        "latency_info_original_to_frame_swap": stats(component_latencies),
        "high_latency_event_count": high_latency,
        "observed_key_component_paths": component_paths[:5],
    }


def launch(exe: Path, profile: Path, url: str) -> tuple[subprocess.Popen, CDP, CDP, int]:
    proc = subprocess.Popen(
        [str(exe), f"--user-data-dir={profile}", "--remote-debugging-port=0",
         "--remote-allow-origins=*", "--no-first-run", "--no-default-browser-check", url],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    port_file = profile / "DevToolsActivePort"
    for _ in range(900):
        if port_file.exists():
            break
        time.sleep(0.1)
    if not port_file.exists():
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        raise TimeoutError(f"No DevToolsActivePort for {exe}")
    port = int(port_file.read_text(encoding="utf8").splitlines()[0])
    browser = CDP(request(f"http://127.0.0.1:{port}/json/version")["webSocketDebuggerUrl"])
    page_info = next(item for item in request(f"http://127.0.0.1:{port}/json/list")
                     if item["type"] == "page")
    page = CDP(page_info["webSocketDebuggerUrl"])
    wait_document(page)
    window = None
    for _ in range(200):
        window = find_window(proc.pid)
        if window:
            break
        time.sleep(0.05)
    if not window:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        raise RuntimeError(f"No visible window for {exe}")
    hwnd, _ = window
    # Windows can reject one foreground request during a rapid browser relaunch.
    # Retry only after an Alt tap, and fail closed before sending any test keys.
    for _ in range(10):
        chord(0x12)
        USER32.ShowWindow(hwnd, 5)
        USER32.BringWindowToTop(hwnd)
        USER32.SetForegroundWindow(hwnd)
        time.sleep(0.1)
        if USER32.GetForegroundWindow() == hwnd:
            break
    if USER32.GetForegroundWindow() != hwnd:
        page.close()
        browser.close()
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        raise RuntimeError(f"Could not foreground {exe}")
    return proc, browser, page, hwnd


def evaluate(page: CDP, expression: str):
    result = page.call("Runtime.evaluate", {"expression": expression, "returnByValue": True})
    return result.get("result", {}).get("value")


def focus_control(page: CDP, hwnd: int, control: str) -> dict:
    """Give the renderer native focus with a real Windows pointer click."""
    evaluate(page, f"horizonInputProbe.reset({json.dumps(control)})")
    geometry = evaluate(page, f"""(() => {{
      const r = document.getElementById({json.dumps(control)}).getBoundingClientRect();
      const border = (window.outerWidth - window.innerWidth) / 2;
      return {{
        x: (window.screenX + border + r.left + r.width / 2) * devicePixelRatio,
        y: (window.screenY + window.outerHeight - window.innerHeight - border +
            r.top + r.height / 2) * devicePixelRatio,
      }};
    }})()""")
    USER32.SetForegroundWindow(hwnd)
    USER32.SetCursorPos(round(geometry["x"]), round(geometry["y"]))
    USER32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    USER32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.08)
    return evaluate(page, f"({{active: document.activeElement.id, focused: document.hasFocus()}})")


def run_once(label: str, exe: Path, repetition: int, artifact_root: Path) -> dict:
    profile = artifact_root / "profiles" / f"{label}-{repetition}"
    if profile.exists():
        shutil.rmtree(profile)
    profile.parent.mkdir(parents=True, exist_ok=True)
    fixture = (ROOT / "tests" / "interaction" / "input-latency.html").resolve().as_uri()
    proc = browser = page = None
    trace_path = artifact_root / "traces" / f"{label}-{repetition}.json.gz"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc, browser, page, hwnd = launch(exe, profile, fixture)
        browser.call("Tracing.start", {
            "transferMode": "ReturnAsStream",
            "categories": "benchmark,cc,devtools.timeline,input,latencyInfo,rail,renderer.scheduler,toplevel,ui,views,viz,disabled-by-default-devtools.timeline.frame",
        })
        scenarios = []
        sample = "the quick brown fox jumps over the lazy dog"
        for control in ("plain-input", "plain-textarea", "editable"):
            focus = focus_control(page, hwnd, control)
            time.sleep(0.1)
            type_ascii(sample, 0.006)
            time.sleep(0.25)
            snapshot = evaluate(page, "horizonInputProbe.snapshot()")
            inputs = [event for event in snapshot["records"] if event["type"] == "input"]
            beforeinputs = [event for event in snapshot["records"] if event["type"] == "beforeinput"]
            second_frames = [item["secondFrameDelay"] for item in snapshot["frameSamples"]]
            scenarios.append({
                "control": control,
                "active_before_typing": focus["active"],
                "document_focused_before_typing": focus["focused"],
                "expected": sample,
                "actual": snapshot["values"][control],
                "character_integrity": snapshot["values"][control] == sample,
                "input_events": len(inputs),
                "beforeinput_events": len(beforeinputs),
                "beforeinput_precedes_input": all(
                    beforeinputs[index]["sequence"] < inputs[index]["sequence"]
                    for index in range(min(len(beforeinputs), len(inputs)))),
                "second_animation_frame_after_input": stats(second_frames),
                "event_timing_duration": stats([
                    item["duration"] for item in snapshot["eventTimings"]
                    if item["name"] in ("keydown", "keypress", "keyup")]),
            })

        # This checks Blink's composition mutation/event path when a native
        # non-English Windows IME is unavailable. It is intentionally reported
        # separately and must not be presented as a native TSF/Telex result.
        focus_control(page, hwnd, "plain-textarea")
        page.call("Input.imeSetComposition", {
            "text": "tie", "selectionStart": 3, "selectionEnd": 3,
            "replacementStart": 0, "replacementEnd": 0,
        })
        page.call("Input.imeSetComposition", {
            "text": "tiếng", "selectionStart": 5, "selectionEnd": 5,
            "replacementStart": 0, "replacementEnd": 3,
        })
        page.call("Input.insertText", {"text": "tiếng"})
        time.sleep(0.2)
        composition = evaluate(page, "horizonInputProbe.snapshot()")
        composition_events = [item for item in composition["records"]
                              if item["type"].startswith("composition")]

        # Exercise editing/navigation on the plain input without changing the trace setup.
        focus_control(page, hwnd, "plain-input")
        type_ascii("abcdef", 0.04)
        tap(VK["LEFT"]); tap(VK["LEFT"]); tap(VK["BACK"]); tap(VK["DELETE"])
        tap(VK["HOME"]); key(VK["SHIFT"]); tap(VK["RIGHT"]); key(VK["SHIFT"], False)
        chord(VK["CONTROL"], ord("A")); chord(VK["CONTROL"], ord("C"))
        chord(VK["CONTROL"], ord("V")); chord(VK["CONTROL"], ord("Z")); chord(VK["CONTROL"], ord("Y"))
        time.sleep(0.3)
        editing = evaluate(page, "horizonInputProbe.snapshot()")

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
        return {
            "label": label,
            "repetition": repetition,
            "exe": str(exe),
            "scenarios": scenarios,
            "synthetic_composition": {
                "native_windows_ime": False,
                "expected": "tiếng",
                "actual": composition["values"]["plain-textarea"],
                "event_types": [item["type"] for item in composition_events],
                "events": len(composition_events),
            },
            "editing_final_value": editing["values"]["plain-input"],
            "editing_event_types": sorted({item["type"] for item in editing["records"]}),
            "trace": trace_summary(events),
            "trace_events": len(events),
            "trace_file": str(trace_path.relative_to(ROOT)),
        }
    finally:
        if page:
            page.close()
        if browser:
            browser.close()
        if proc and proc.poll() is None:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", action="append", required=True,
                        help="LABEL=absolute-or-repo-relative-path-to-chrome.exe")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--artifact-root", default="compatibility-artifacts/input")
    args = parser.parse_args()
    artifact_root = (ROOT / args.artifact_root).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)
    browsers = []
    for spec in args.browser:
        label, raw_path = spec.split("=", 1)
        exe = Path(raw_path)
        if not exe.is_absolute():
            exe = ROOT / exe
        if not exe.is_file():
            raise FileNotFoundError(exe)
        browsers.append((label, exe.resolve()))
    results = []
    # Alternate binaries to limit temperature/order bias in the A/B sample.
    for repetition in range(1, args.repetitions + 1):
        for label, exe in browsers:
            result = run_once(label, exe.resolve(), repetition, artifact_root)
            results.append(result)
            print(json.dumps(result, indent=2))
    output_path = artifact_root / "results.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
