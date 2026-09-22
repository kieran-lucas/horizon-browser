"""Measure Horizon suggestion-corner geometry from rendered pixels.

Types "hello" into the NTP searchbox (WebUI realbox dropdown) and into the
native omnibox popup, then inspects the left edge of the selected suggestion
row in rendered pixels. In this build kWebUIOmniboxPopup is enabled by default,
so the omnibox popup rows are the same WebUI cr-searchbox-match surface as the
NTP realbox dropdown.

Reuses the CDP/launch helpers from scripts/performance/measure.py and the
window/input helpers from scripts/performance/foreground_scroll.py.
"""

import argparse
import base64
import ctypes
import json
import shutil
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "performance"))

from measure import CDP, EXE, request, wait_document  # pylint: disable=wrong-import-position
from foreground_scroll import Rect, find_window, user32  # pylint: disable=wrong-import-position

ARTIFACTS = ROOT / "phase2-artifacts" / "suggestion-geometry"


# --------------------------------------------------------------------------
# PNG decoding / encoding
# --------------------------------------------------------------------------

def read_png_pixels(png_bytes):
    """Minimal PNG decoder: returns (width, height, rgba rows)."""
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    pos, width, height, bit_depth, color_type, idat = 8, 0, 0, 0, 0, b""
    while pos < len(png_bytes):
        length = int.from_bytes(png_bytes[pos:pos + 4], "big")
        chunk = png_bytes[pos + 4:pos + 8]
        data = png_bytes[pos + 8:pos + 8 + length]
        if chunk == b"IHDR":
            width = int.from_bytes(data[0:4], "big")
            height = int.from_bytes(data[4:8], "big")
            bit_depth = data[8]
            color_type = data[9]
        elif chunk == b"IDAT":
            idat += data
        elif chunk == b"IEND":
            break
        pos += 12 + length
    assert bit_depth == 8 and color_type == 6, (bit_depth, color_type)
    raw = zlib.decompress(idat)
    stride = width * 4
    pixels = bytearray()
    previous = bytearray(stride)
    offset = 0
    for _ in range(height):
        filter_type = raw[offset]
        offset += 1
        line = bytearray(raw[offset:offset + stride])
        offset += stride
        if filter_type == 1:  # Sub
            for i in range(4, stride):
                line[i] = (line[i] + line[i - 4]) & 0xFF
        elif filter_type == 2:  # Up
            for i in range(stride):
                line[i] = (line[i] + previous[i]) & 0xFF
        elif filter_type == 3:  # Average
            for i in range(stride):
                left = line[i - 4] if i >= 4 else 0
                line[i] = (line[i] + ((left + previous[i]) >> 1)) & 0xFF
        elif filter_type == 4:  # Paeth
            for i in range(stride):
                a = line[i - 4] if i >= 4 else 0
                b = previous[i]
                c = previous[i - 4] if i >= 4 else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if pa <= pb and pa <= pc else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        pixels += line
        previous = line
    return width, height, pixels


def write_png(path, width, height, rgba):
    def chunk(tag, data):
        payload = tag + data
        return (struct.pack(">I", len(data)) + payload
                + struct.pack(">I", zlib.crc32(payload) & 0xFFFFFFFF))
    raw = b"".join(
        b"\x00" + bytes(rgba[y * width * 4:(y + 1) * width * 4])
        for y in range(height))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b""))


def pixel_rgba(pixels, width, x, y):
    index = (y * width + x) * 4
    return tuple(pixels[index:index + 4])


# --------------------------------------------------------------------------
# Left-edge analysis
# --------------------------------------------------------------------------

def find_blue_accent_column(get_px, width, height, min_rows=15):
    """Find the leftmost blue strip that is tall enough to be an accent."""
    def is_blue(x, y):
        r, g, b, _ = get_px(x, y)
        return b > 120 and b > r + 40 and 50 < g < 210 and r < 150

    columns = {}
    for y in range(0, height):
        run_start = None
        for x in range(0, width):
            if is_blue(x, y):
                if run_start is None:
                    run_start = x
            else:
                if run_start is not None and x - run_start >= 3:
                    columns.setdefault(run_start, []).append(y)
                run_start = None
    candidates = []
    for col, ys in sorted(columns.items()):
        if len(ys) >= min_rows:
            candidates.append({"x": col, "top": min(ys), "bottom": max(ys),
                               "rows": len(ys)})
    return candidates


def analyze_row_contour(get_px, accent, width, label, scale=1.0):
    """Measure the row's outer left contour around the accent strip.

    The accent sits at the row's left edge, so scanning leftward from the
    accent column against the light popup background yields the outer
    contour including both left corners.
    """
    col = accent["x"]
    y0, y1 = accent["top"], accent["bottom"]
    row_h = y1 - y0 + 1
    scan_left = max(0, col - 60)
    mid_y = y0 + row_h // 2
    ref = get_px(scan_left + 2, mid_y)  # popup background near the row

    def is_bg(x, y):
        r, g, b, _ = get_px(x, y)
        rr, gg, bb, _ = ref
        return abs(r - rr) < 12 and abs(g - gg) < 12 and abs(b - bb) < 12

    def outer_edge(y):
        for x in range(scan_left, min(col + 8, width)):
            if not is_bg(x, y):
                return x
        return None

    profile = []
    for y in range(y0, y1 + 1):
        edge = outer_edge(y)
        profile.append((y - y0, edge))

    edges = [e for _, e in profile if e is not None]
    if not edges:
        return None
    straight = sorted(e for dy, e in profile
                      if row_h // 3 <= dy <= 2 * row_h // 3 and e is not None)
    straight_inset = straight[len(straight) // 2] - scan_left
    top = [e - scan_left for dy, e in profile
           if e is not None and dy < row_h // 3]
    bottom = [e - scan_left for dy, e in profile
              if e is not None and dy > 2 * row_h // 3]
    return {
        "surface": label,
        "row_height_px": row_h,
        "row_height_dip": round(row_h / scale, 1),
        "straight_left_inset_px": straight_inset,
        "top_corner_inset_px": min(top) if top else None,
        "bottom_corner_inset_px": min(bottom) if bottom else None,
        "top_corner_depth_px": (min(top) - straight_inset) if top else None,
        "bottom_corner_depth_px": (min(bottom) - straight_inset)
            if bottom else None,
        "top_corner_depth_dip": round((min(top) - straight_inset) / scale, 2)
            if top else None,
        "bottom_corner_depth_dip": round((min(bottom) - straight_inset) / scale,
                                         2) if bottom else None,
        "top_profile_px": [e - scan_left for dy, e in profile[:10]],
        "bottom_profile_px": [e - scan_left for dy, e in profile[-10:]],
    }


# --------------------------------------------------------------------------
# Win32 helpers
# --------------------------------------------------------------------------

class BMIH(ctypes.Structure):
    _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16),
                ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32),
                ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32),
                ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32)]


def capture_screen(rect):
    gdi32 = ctypes.windll.gdi32
    cw, ch = rect.right - rect.left, rect.bottom - rect.top
    hdc_screen = user32.GetDC(None)
    mem_dc = gdi32.CreateCompatibleDC(hdc_screen)
    bitmap = gdi32.CreateCompatibleBitmap(hdc_screen, cw, ch)
    gdi32.SelectObject(mem_dc, bitmap)
    gdi32.BitBlt(mem_dc, 0, 0, cw, ch, hdc_screen, rect.left, rect.top,
                 0x00CC0020)  # SRCCOPY
    bih = BMIH()
    bih.biSize = ctypes.sizeof(BMIH)
    bih.biWidth = cw
    bih.biHeight = -ch
    bih.biPlanes = 1
    bih.biBitCount = 32
    buf = ctypes.create_string_buffer(cw * ch * 4)
    gdi32.GetDIBits(mem_dc, bitmap, 0, ch, buf, ctypes.byref(bih), 0)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(None, hdc_screen)
    data = bytes(buf)

    def get_px(x, y):
        index = (y * cw + x) * 4
        return (data[index + 2], data[index + 1], data[index], 255)

    return cw, ch, get_px


def deep_query(page, selector, attr=None):
    """Evaluate JS that walks shadow roots to find elements by selector."""
    expression = r"""
(([selector, attr]) => {
  const results = [];
  const visit = (root) => {
    for (const el of root.querySelectorAll(selector)) {
      if (attr) {
        const r = el.getBoundingClientRect();
        results.push({x: r.x, y: r.y, w: r.width, h: r.height,
                      attr: el.getAttribute(attr)});
      } else {
        const r = el.getBoundingClientRect();
        results.push({x: r.x, y: r.y, w: r.width, h: r.height});
      }
    }
    for (const el of root.querySelectorAll('*')) {
      if (el.shadowRoot) visit(el.shadowRoot);
    }
  };
  visit(document);
  return results;
})()
""" % ()
    expression = expression.replace("(([selector, attr]) => {",
                                    "(() => {", 1)
    expression = expression.replace("})()", ")()")
    expression = f"""
(() => {{
  const selector = {json.dumps(selector)};
  const attr = {json.dumps(attr)};
  const results = [];
  const visit = (root) => {{
    for (const el of root.querySelectorAll(selector)) {{
      const r = el.getBoundingClientRect();
      results.push({{x: r.x, y: r.y, w: r.width, h: r.height,
                    attr: attr ? el.getAttribute(attr) : null}});
    }}
    for (const el of root.querySelectorAll('*')) {{
      if (el.shadowRoot) visit(el.shadowRoot);
    }}
  }};
  visit(document);
  return results;
}})()
"""
    result = page.call("Runtime.evaluate",
                       {"expression": expression, "returnByValue": True})
    return result.get("result", {}).get("value") or []


def cdp_click(cdp, x, y):
    for type_ in ("mousePressed", "mouseReleased"):
        cdp.call("Input.dispatchMouseEvent", {
            "type": type_, "x": x, "y": y, "button": "left",
            "clickCount": 1})


def cdp_type(cdp, text):
    for ch in text:
        cdp.call("Input.dispatchKeyEvent", {
            "type": "keyDown", "text": ch, "unmodifiedText": ch,
            "windowsVirtualKeyCode": ord(ch.upper())})
        cdp.call("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": ch,
            "windowsVirtualKeyCode": ord(ch.upper())})
        time.sleep(0.05)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("label")
    args = parser.parse_args()

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    profile = ARTIFACTS / f"profile-{args.label}"
    if profile.resolve().parent != ARTIFACTS.resolve():
        raise ValueError("Profile path escaped artifact directory")
    if profile.exists():
        shutil.rmtree(profile)

    user32.SetProcessDPIAware()

    proc = subprocess.Popen(
        [str(EXE), f"--user-data-dir={profile}", "--remote-debugging-port=0",
         "--remote-allow-origins=*", "--no-first-run",
         "--no-default-browser-check", "--window-size=1400,950",
         "chrome://newtab/"],
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    report = {"label": args.label, "scale": None, "surfaces": {}}
    try:
        port_file = profile / "DevToolsActivePort"
        for _ in range(900):
            if port_file.exists():
                break
            time.sleep(0.05)
        if not port_file.exists():
            raise TimeoutError("DevToolsActivePort")
        port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
        page = CDP(next(x for x in request(f"http://127.0.0.1:{port}/json/list")
                        if x["type"] == "page")["webSocketDebuggerUrl"])
        wait_document(page)
        time.sleep(2)

        window = None
        for _ in range(100):
            window = find_window(proc.pid)
            if window:
                break
            time.sleep(0.1)
        if not window:
            raise RuntimeError("No visible Horizon window")
        hwnd, rect = window
        dpr = user32.GetDpiForWindow(hwnd) / 96.0 if hasattr(
            user32, "GetDpiForWindow") else 1.0
        report["scale"] = dpr

        # ---- Surface 1: NTP realbox dropdown, driven via CDP ---------------
        box = deep_query(page, "cr-searchbox-input, #searchboxContainer")
        entry = {}
        if box:
            target = box[0]
            cdp_click(page, target["x"] + target["w"] / 2,
                      target["y"] + target["h"] / 2)
            time.sleep(0.3)
            cdp_type(page, "hello")
            time.sleep(1.2)
            rows = deep_query(page, "cr-searchbox-match", attr="selected")
            entry["matches"] = rows
            shot = page.call("Page.captureScreenshot", {"format": "png"})
            png_path = ARTIFACTS / f"{args.label}-ntp-dropdown.png"
            png_path.write_bytes(base64.b64decode(shot["data"]))
            entry["screenshot"] = png_path.name
            width, height, pixels = read_png_pixels(png_path.read_bytes())
            entry["image_size"] = [width, height]
            accents = find_blue_accent_column(
                lambda x, y: pixel_rgba(pixels, width, x, y),
                min(width, int(width * 0.5)), height)
            entry["accent_candidates"] = accents[:6]
            if accents:
                accent = accents[0]
                # Crop a tight left-edge strip for the record.
                crop_w = min(160, width - accent["x"] + 20)
                crop_h = accent["bottom"] - accent["top"] + 1
                crop = bytearray(crop_w * crop_h * 4)
                for yy in range(crop_h):
                    for xx in range(crop_w):
                        src = ((accent["top"] + yy) * width
                               + max(0, accent["x"] - 20) + xx) * 4
                        dst = (yy * crop_w + xx) * 4
                        crop[dst:dst + 4] = pixels[src:src + 4]
                crop_path = ARTIFACTS / f"{args.label}-ntp-left-edge.png"
                write_png(crop_path, crop_w, crop_h, crop)
                entry["left_edge_crop"] = crop_path.name
                entry["pixels"] = analyze_row_contour(
                    lambda x, y: pixel_rgba(pixels, width, x, y),
                    accent, width, "ntp_dropdown", scale=dpr)
        report["surfaces"]["ntp_dropdown"] = entry

        # ---- Surface 2: native omnibox popup (screen capture) --------------
        focus_ok = False
        for _ in range(5):
            user32.keybd_event(0x12, 0, 0, 0)
            user32.keybd_event(0x12, 0, 2, 0)
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.3)
            if user32.GetForegroundWindow() == hwnd:
                focus_ok = True
                break
        if not focus_ok:
            user32.SetCursorPos((rect.left + rect.right) // 2,
                                (rect.top + rect.bottom) // 2)
            time.sleep(0.1)
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.3)
            focus_ok = user32.GetForegroundWindow() == hwnd
        omnibox = {"focus": focus_ok}
        if focus_ok:
            for vk in (0x11, 0x4C):  # Ctrl+L
                user32.keybd_event(vk, 0, 0, 0)
            for vk in (0x4C, 0x11):
                user32.keybd_event(vk, 0, 2, 0)
            time.sleep(0.5)
            for ch in "hello":
                vk = ord(ch.upper())
                user32.keybd_event(vk, 0, 0, 0)
                user32.keybd_event(vk, 0, 2, 0)
                time.sleep(0.06)
            time.sleep(1.0)
            capture = Rect()
            capture.left = rect.left + 40
            capture.top = rect.top + 40
            capture.right = min(rect.right - 40, capture.left + 640)
            capture.bottom = min(rect.bottom - 40, capture.top + 620)
            cw, chh, get_px = capture_screen(capture)
            accents = find_blue_accent_column(get_px, cw, chh)
            omnibox["accent_candidates"] = accents[:6]
            if accents:
                accent = accents[0]
                crop_w = min(160, cw - max(0, accent["x"] - 20))
                crop_h = accent["bottom"] - accent["top"] + 1
                crop = bytearray(crop_w * crop_h * 4)
                origin_x = max(0, accent["x"] - 20)
                for yy in range(crop_h):
                    for xx in range(crop_w):
                        r, g, b, _ = get_px(origin_x + xx, accent["top"] + yy)
                        dst = (yy * crop_w + xx) * 4
                        crop[dst:dst + 4] = bytes((r, g, b, 255))
                crop_path = ARTIFACTS / f"{args.label}-omnibox-left-edge.png"
                write_png(crop_path, crop_w, crop_h, crop)
                omnibox["left_edge_crop"] = crop_path.name
                omnibox["pixels"] = analyze_row_contour(
                    get_px, accent, cw, "omnibox_popup", scale=dpr)
        report["surfaces"]["omnibox_popup"] = omnibox

        out = ARTIFACTS / f"{args.label}.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == "__main__":
    main()
