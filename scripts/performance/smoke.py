"""Integration smoke test for the current incremental Horizon build."""

import json
from pathlib import Path
import shutil
import subprocess
import time

import psutil

from measure import ARTIFACTS, CDP, EXE, eval_js, request


ROOT = Path(__file__).resolve().parents[2]


def wait_url(page, expected, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            value = eval_js(page, "JSON.stringify({url:location.href,ready:document.readyState,title:document.title})")
            state = json.loads(value)
            if state["url"].startswith(expected) and state["ready"] == "complete":
                return state
        except Exception:
            pass
        time.sleep(.1)
    raise TimeoutError(expected)


def main():
    profile = ARTIFACTS / "smoke-profile"
    if profile.resolve().parent != ARTIFACTS.resolve():
        raise ValueError("Profile path escaped performance-artifacts")
    if profile.exists():
        shutil.rmtree(profile)
    extension = ROOT / "tests/phase0/mv3-extension"
    proc = subprocess.Popen(
        [str(EXE), f"--user-data-dir={profile}", "--remote-debugging-port=0",
         "--remote-allow-origins=*", "--no-first-run", "--no-default-browser-check",
         f"--load-extension={extension}", "chrome://newtab/"],
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    result = {"pages": {}}
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
        target = next(x for x in request(f"http://127.0.0.1:{port}/json/list")
                      if x["type"] == "page")
        page = CDP(target["webSocketDebuggerUrl"])
        result["pages"]["newtab"] = wait_url(page, "chrome://new-tab-page/")
        time.sleep(1)
        result["ntp"] = json.loads(eval_js(page, """JSON.stringify((()=>{
          const a=document.querySelector('ntp-app');const r=a.shadowRoot;
          return {search:!!r.querySelector('ntp-searchbox'),
                  shortcuts:!!r.querySelector('cr-most-visited'),
                  horizonMark:!!r.querySelector('#horizonSigil img'),
                  oldLogo:!!r.querySelector('ntp-logo'),
                  oneGoogleBar:!!r.querySelector('#oneGoogleBar'),
                  chromePromo:!!r.querySelector('individual-promos'),
                  composeboxEnabled:a.composeboxEnabled,
                  composeEntrypointEnabled:a.composeButtonEnabled,
                  actionChipsEnabled:a.isActionChipsVisible_,
                  lazyScript:!!document.querySelector('script[src$="horizon_lazy_load.js"]')};
        })())"""))
        for url in ["chrome://settings/", "chrome://history/", "chrome://bookmarks/",
                    "chrome://downloads/", "chrome://extensions/",
                    "chrome://password-manager/passwords"]:
            page.call("Page.navigate", {"url": url})
            result["pages"][url] = wait_url(page, url)
        page.call("Page.navigate", {"url": "https://example.com/"})
        result["pages"]["example"] = wait_url(page, "https://example.com/", 30)
        result["mv3_content_script"] = eval_js(
            page, "document.documentElement.dataset.phase0Extension || null")
        page.call("Page.navigate", {"url": "chrome://history/"})
        wait_url(page, "chrome://history/")
        history = page.call("Page.getNavigationHistory")
        entry = next(x for x in reversed(history["entries"])
                     if x["url"].startswith("https://example.com/"))
        page.call("Page.navigateToHistoryEntry", {"entryId": entry["id"]})
        result["back_forward"] = wait_url(page, "https://example.com/", 30)
        context = browser.call("Target.createBrowserContext")["browserContextId"]
        separate = browser.call("Target.createTarget", {
            "url": "about:blank", "browserContextId": context})
        result["incognito_context_created"] = bool(separate["targetId"])
        browser.call("Target.disposeBrowserContext", {"browserContextId": context})
        children = [psutil.Process(proc.pid)] + psutil.Process(proc.pid).children(recursive=True)
        commands = [" ".join(p.cmdline()) for p in children if p.is_running()]
        result["gpu_process"] = any("--type=gpu-process" in c for c in commands)
        gpu_info = browser.call("SystemInfo.getInfo").get("gpu", {})
        result["gpu_devices"] = [device.get("deviceString", "")
                                 for device in gpu_info.get("devices", [])]
        result["gpu_feature_status"] = gpu_info.get("featureStatus", {})
        result["renderer_processes"] = sum("--type=renderer" in c for c in commands)
        result["no_sandbox_flag_absent"] = all("--no-sandbox" not in c for c in commands)
        result["mv3_service_worker"] = any(
            x["type"] == "service_worker" and "service-worker.js" in x["url"]
            for x in request(f"http://127.0.0.1:{port}/json/list"))
        assert all(result["ntp"][key] for key in
                   ("search", "shortcuts", "horizonMark", "lazyScript"))
        assert not any(result["ntp"][key] for key in
                       ("oldLogo", "oneGoogleBar", "chromePromo",
                        "composeboxEnabled", "composeEntrypointEnabled", "actionChipsEnabled"))
        assert result["mv3_content_script"] == "active"
        assert result["gpu_process"] and result["gpu_devices"]
        assert result["renderer_processes"] >= 2
        assert result["mv3_service_worker"] and result["no_sandbox_flag_absent"]
        (ARTIFACTS / "smoke.json").write_text(json.dumps(result, indent=2), encoding="utf8")
        print(json.dumps(result, indent=2))
        page.close()
        browser.close()
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
