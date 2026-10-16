#!/usr/bin/env python3
"""Draw the app icon and its symbolic variant as SVG.

    python3 tools/make_icon.py            # writes data/icons/hicolor/...
    python3 tools/make_icon.py --preview  # also renders build/icon-preview.png
                                          # (needs rsvg-convert)

App icon (GNOME HIG style, like the family's QDVC Progress and QDVC GTD EML
icons: a 128 × 128 object lit from above, with a darker bottom edge for
thickness, in the Adwaita palette, with a round badge at the bottom right):
an open blue envelope with a letter rising out of it — a few lines of text
and a handwritten blue signature (the Phrases and Signature pages) — and a
yellow smiley sticker (the Emoji page, and the "nice"). The symbolic variant
is the same idea in one colour: an envelope with a smiley badge.

Writes:
  data/icons/hicolor/scalable/apps/qdvc.NiceMail.svg
  data/icons/hicolor/symbolic/apps/qdvc.NiceMail-symbolic.svg
"""

import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_ID = "qdvc.NiceMail"

# Adwaita palette.
BLUE_2, BLUE_3, BLUE_4, BLUE_5 = "#62a0ea", "#3584e4", "#1c71d8", "#1a5fb4"
YELLOW_1, YELLOW_3, YELLOW_5 = "#f9f06b", "#f6d32d", "#e5a50a"
LIGHT_2, LIGHT_3, LIGHT_4 = "#f6f5f4", "#deddda", "#c0bfbc"
BROWN_5 = "#63452c"

APP_ICON = f"""<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">
  <defs>
    <linearGradient id="pocket" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{BLUE_2}"/><stop offset="1" stop-color="{BLUE_3}"/>
    </linearGradient>
    <linearGradient id="flap" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{BLUE_3}"/><stop offset="1" stop-color="{BLUE_4}"/>
    </linearGradient>
    <linearGradient id="letter" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="{LIGHT_2}"/>
    </linearGradient>
    <linearGradient id="face" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{YELLOW_1}"/><stop offset="1" stop-color="{YELLOW_3}"/>
    </linearGradient>
  </defs>
  <!-- the inside of the envelope, and its flap folded open behind the letter -->
  <rect x="12" y="46" width="104" height="58" rx="10" fill="{BLUE_5}"/>
  <path d="M12 56 Q12 50 18 46 L56 21 Q64 16 72 21 L110 46 Q116 50 116 56 Z" fill="url(#flap)"/>
  <!-- the letter: three lines of text and a signature -->
  <rect x="27" y="16" width="74" height="80" rx="5" fill="url(#letter)"/>
  <path d="M37 29 H91 M37 38 H86 M37 47 H72" fill="none" stroke="{LIGHT_4}"
        stroke-width="4" stroke-linecap="round"/>
  <path d="M38 66 C41 60 45 55 47 57 C49 60 43 67 45 66 C48 64 51 58 54 59 C56 60 53 65 56 65
           C59 65 61 60 64 60 C66 60 65 64 68 64 C72 64 76 59 82 58"
        fill="none" stroke="{BLUE_4}" stroke-width="3" stroke-linecap="round"
        stroke-linejoin="round"/>
  <!-- the front pocket, with a darker bottom edge for thickness -->
  <path d="M12 64 L57 91 Q64 95 71 91 L116 64 L116 100 Q116 110 106 110 L22 110 Q12 110 12 100 Z"
        fill="{BLUE_5}"/>
  <path d="M12 60 L57 87 Q64 91 71 87 L116 60 L116 96 Q116 106 106 106 L22 106 Q12 106 12 96 Z"
        fill="url(#pocket)"/>
  <!-- the smiley sticker -->
  <circle cx="96" cy="97" r="22" fill="{YELLOW_5}"/>
  <circle cx="96" cy="94" r="22" fill="url(#face)"/>
  <ellipse cx="88.5" cy="88" rx="3" ry="4.2" fill="{BROWN_5}"/>
  <ellipse cx="103.5" cy="88" rx="3" ry="4.2" fill="{BROWN_5}"/>
  <path d="M85 98 Q96 109 107 98" fill="none" stroke="{BROWN_5}" stroke-width="4"
        stroke-linecap="round"/>
</svg>
"""

# 16 × 16, one colour (GNOME recolours symbolic icons): an envelope whose
# bottom-right corner gives way to a smiley, 1 px clear of it. The face's eyes
# (1 × 2 px) and stepped smile are holes on whole pixels (even-odd fill), so
# they stay crisp at 16 px.
SYMBOLIC_ICON = """<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">
  <path fill="#222" d="M2.5 3A1.5 1.5 0 0 0 1 4.5v7A1.5 1.5 0 0 0 2.5 13H7v-1.5H2.5v-5.6l5.5 3.6 5.5-3.6V7H15V4.5A1.5 1.5 0 0 0 13.5 3zm.4 1.5h10.2L8 7.8z"/>
  <path fill="#222" fill-rule="evenodd" d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM10 10h1v2h-1zM13 10h1v2h-1zM9 13h1v1h-1zM14 13h1v1h-1zM10 14h4v1h-4z"/>
</svg>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()
    base = os.path.join(ROOT, "data", "icons", "hicolor")
    paths = {
        os.path.join(base, "scalable", "apps", f"{APP_ID}.svg"): APP_ICON,
        os.path.join(base, "symbolic", "apps", f"{APP_ID}-symbolic.svg"): SYMBOLIC_ICON,
    }
    for path, svg in paths.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(svg)
        print("wrote", os.path.relpath(path, ROOT))
    if args.preview:
        if not shutil.which("rsvg-convert"):
            print("--preview needs rsvg-convert (librsvg2-bin)", file=sys.stderr)
            return 1
        out_dir = os.path.join(ROOT, "build")
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, "icon-preview.png")
        subprocess.run(["rsvg-convert", "-w", "256", "-h", "256", "-o", out, list(paths)[0]],
                       check=True)
        print("wrote", os.path.relpath(out, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
