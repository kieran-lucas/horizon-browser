"""Sample a settled one-tab Horizon process tree without user input."""

import json
import shutil
import subprocess
import time

import psutil

from measure import ARTIFACTS, CDP, EXE, process_sample, request


def cpu_by_process(pid):
    root = psutil.Process(pid)
    result = {}
    for process in [root] + root.children(recursive=True):
        try:
            times = process.cpu_times()
            kind = next((arg.split("=", 1)[1] for arg in process.cmdline()
                         if arg.startswith("--type=")), "browser")
            result[process.pid] = (kind, times.user + times.system)
        except psutil.Error:
            pass
    return result


def main():
    profile = ARTIFACTS / "steady-idle-profile"
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
        time.sleep(60)
        before = process_sample(proc.pid)
        by_process_before = cpu_by_process(proc.pid)
        time.sleep(10)
        after = process_sample(proc.pid)
        by_process_after = cpu_by_process(proc.pid)
        cpu_owners = sorted(({"type": kind, "cpu_s": round(cpu - by_process_before[pid][1], 2)}
                             for pid, (kind, cpu) in by_process_after.items()
                             if pid in by_process_before),
                            key=lambda item: item["cpu_s"], reverse=True)
        report = {"settle_seconds": 60, "sample_seconds": 10,
                  "cpu_seconds": round(after["cpu_s"] - before["cpu_s"], 2),
                  "private_mb_before": before["private_mb"],
                  "private_mb_after": after["private_mb"],
                  "processes": after["count"], "cpu_owners": cpu_owners}
        (ARTIFACTS / "steady-idle.json").write_text(json.dumps(report, indent=2), encoding="utf8")
        print(json.dumps(report, indent=2))
        browser.call("Browser.close")
    finally:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
