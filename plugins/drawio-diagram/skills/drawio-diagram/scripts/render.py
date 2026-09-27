"""Render every tab of a .drawio file to PNG for visual checking.

    python3 render.py diagram.drawio [out_dir]     → out_dir/<file>-p0.png, -p1.png, …

Uses headless Chromium + the official draw.io viewer (needs network for viewer.diagrams.net).
"""

import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def main() -> None:
    src = Path(sys.argv[1]).resolve()
    out = Path(sys.argv[2] if len(sys.argv) > 2 else src.parent).resolve()
    out.mkdir(parents=True, exist_ok=True)
    browser = next((b for b in ("chromium", "google-chrome", "chromium-browser", "google-chrome-stable")
                    if shutil.which(b)), None)
    if not browser:
        sys.exit("No Chromium/Chrome found")
    xml = src.read_text(encoding="utf-8")
    for i, d in enumerate(re.findall(r"<diagram .*?</diagram>", xml, re.S)):
        # the whole JSON must be HTML-escaped inside the attribute, or the viewer fails to parse it
        cfg = json.dumps({"xml": f"<mxfile>{d}</mxfile>", "toolbar": "", "lightbox": False, "nav": False})
        page = out / f"{src.stem}-p{i}.html"
        page.write_text(
            '<!doctype html><html><body style="margin:0;background:#fff">'
            f'<div class="mxgraph" data-mxgraph="{html.escape(cfg, quote=True)}"></div>'
            '<script src="https://viewer.diagrams.net/js/viewer-static.min.js"></script></body></html>',
            encoding="utf-8",
        )
        w, h = map(int, re.search(r'pageWidth="(\d+)" pageHeight="(\d+)"', d).groups())
        png = out / f"{src.stem}-p{i}.png"
        subprocess.run(
            ["timeout", "90", browser, "--headless=new", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
             "--virtual-time-budget=20000", f"--window-size={w + 40},{h + 40}", f"--screenshot={png}",
             page.as_uri()],
            stderr=subprocess.DEVNULL, check=False,
        )
        page.unlink()
        print(png)


if __name__ == "__main__":
    main()
