"""Summarize an actual foreground wheel trace, pairing async trace slices."""

import collections
import gzip
import json
from pathlib import Path
import statistics
import sys


ROOT = Path(__file__).resolve().parents[2]


def stats(values):
    values = sorted(values)
    if not values:
        return {"count": 0}
    return {"count": len(values), "median_ms": round(statistics.median(values), 2),
            "p95_ms": round(values[int(len(values)*.95)], 2),
            "max_ms": round(values[-1], 2)}


def pairs(events, name, start, end):
    pending = collections.defaultdict(collections.deque)
    result = []
    slices = sorted((x for x in events if x.get("name") == name and
                     x.get("ph") in ("b", "e")),
                    key=lambda x: (x["ts"], x["ph"] == "e"))
    for item in slices:
        key = (item["pid"], str(item.get("id2")), item["name"])
        if item["ph"] == "b":
            pending[key].append(item)
        elif pending[key]:
            begin = pending[key].popleft()
            if start <= begin["ts"] <= end:
                result.append((begin, (item["ts"]-begin["ts"])/1000))
    return result


def summarize(label):
    path = ROOT / "performance-artifacts/traces" / f"wheel-{label}.json.gz"
    with gzip.open(path, "rt", encoding="utf8") as source:
        events = json.load(source)["traceEvents"]
    wheels = [x for x in events if x.get("name") == "InputLatency::MouseWheel" and
              x.get("ph") == "b"]
    start, end = min(x["ts"] for x in wheels), max(x["ts"] for x in wheels)
    margin_start, margin_end = start-50000, end+100000
    latency = pairs(events, "EventLatency", margin_start, margin_end)
    scroll_latency = [(b, d) for b, d in latency if
                      b.get("args", {}).get("event_latency", {}).get("event_type") in
                      ("FIRST_GESTURE_SCROLL_UPDATE", "GESTURE_SCROLL_UPDATE")]
    frames = pairs(events, "PipelineReporter", margin_start, margin_end)
    scroll_frames = [(b, d) for b, d in frames if
                     b.get("args", {}).get("frame_reporter", {}).get("scroll_state") ==
                     "SCROLL_COMPOSITOR_THREAD"]
    swaps = pairs(events, "Graphics.Pipeline.DrawAndSwap", margin_start, margin_end)
    starts = sorted(b["ts"] for b, _ in swaps)
    intervals = [(starts[i+1]-starts[i])/1000 for i in range(len(starts)-1)]
    processes = {x["pid"]: x["args"].get("name") for x in events
                 if x.get("ph") == "M" and x.get("name") == "process_name"}
    threads = {(x["pid"], x["tid"]): x["args"].get("name") for x in events
               if x.get("ph") == "M" and x.get("name") == "thread_name"}
    long_tasks = sorted((x for x in events if x.get("ph") == "X" and
                         x.get("name") == "ThreadControllerImpl::RunTask" and
                         x.get("dur", 0) > 16660 and start <= x["ts"] <= end and
                         threads.get((x["pid"], x["tid"])) in
                         ("CrBrowserMain", "CrRendererMain")),
                        key=lambda x: x["dur"], reverse=True)
    return {
        "label": label, "wheel_events": len(wheels),
        "wheel_window_ms": round((end-start)/1000, 2),
        "scroll_input_to_visible": stats([d for _, d in scroll_latency]),
        "janky_scrolled_frames": sum(
            b.get("args", {}).get("event_latency", {}).get("is_janky_scrolled_frame") is True
            for b, _ in scroll_latency),
        "scroll_frame_states": dict(collections.Counter(
            b.get("args", {}).get("frame_reporter", {}).get("state") for b, _ in scroll_frames)),
        "swap_start_intervals": stats(intervals),
        "display_draw_and_swap": stats([
            x["dur"]/1000 for x in events if x.get("ph") == "X" and
            x.get("name") == "Display::DrawAndSwap" and start <= x["ts"] <= end]),
        "raster_tasks": stats([
            x["dur"]/1000 for x in events if x.get("ph") == "X" and
            x.get("name") == "RasterTask" and start <= x["ts"] <= end]),
        "long_main_tasks": [{"ms": round(x["dur"]/1000, 2),
                             "process": processes.get(x["pid"]),
                             "source": x.get("args", {}).get("src_file")}
                            for x in long_tasks[:10]],
    }


if __name__ == "__main__":
    print(json.dumps([summarize(label) for label in sys.argv[1:]], indent=2))
