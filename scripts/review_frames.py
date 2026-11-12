#!/usr/bin/env python3
"""Contact sheet of the finished trailer: one frame every N seconds.

    python scripts/review_frames.py out/trailer_7620.mp4 [--every 3] [--out out/review.jpg]

Look at the sheet before calling a render done: it catches a missing caption,
a tofu glyph, a wrong crop or a black segment that a log never shows.
"""
import argparse, subprocess, sys, tempfile
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("--every", type=float, default=3.0)
    ap.add_argument("--out", default=None); ap.add_argument("--cols", type=int, default=4)
    a = ap.parse_args()
    out = Path(a.out or Path(a.video).with_name("review.jpg"))
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", a.video,
                            "-vf", f"fps=1/{a.every},scale=480:-1", f"{td}/f_%03d.jpg"])
        if r.returncode: sys.exit("ffmpeg failed")
        frames = sorted(Path(td).glob("f_*.jpg"))
        from PIL import Image, ImageDraw
        if not frames: sys.exit("no frames")
        w, h = Image.open(frames[0]).size
        cols = a.cols; rows = (len(frames) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (w + 6), rows * (h + 22)), "black")
        d = ImageDraw.Draw(sheet)
        for i, f in enumerate(frames):
            x = (i % cols) * (w + 6); y = (i // cols) * (h + 22)
            sheet.paste(Image.open(f), (x + 3, y + 3))
            d.text((x + 6, y + h + 5), f"t={i * a.every:.0f}s", fill="white")
        out.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(out, quality=85)
    print(f"wrote {out} ({len(frames)} frames)")

if __name__ == "__main__":
    main()
