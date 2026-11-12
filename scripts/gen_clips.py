#!/usr/bin/env python3
"""Turn each shot's still into a real moving clip (image-to-video).

    ARK_API_KEY=...  python scripts/gen_clips.py --tour 7627 --route seedance   # BytePlus ModelArk
    FAL_KEY=...      python scripts/gen_clips.py --tour 7627 --route fal        # fal.ai Kling

Writes tours/<id>/shots/<slot>/clip.mp4, which the builder prefers over any still. The
first frame is shots/<slot>/generated.png when it exists, else the tour photo
from shots.json, cropped to 16:9 first. Slots without a prompt are skipped.
Without the key for the chosen route the script exits 0 and does nothing.

Model ids: ARK_VIDEO_MODEL (default seedance-1-0-pro-250528; put the Seedance 2.0
id there once your ModelArk account lists it) and FAL_VIDEO_MODEL (default
fal-ai/kling-video/v2.1/standard/image-to-video). These paths were written
from the public API docs and have NOT been exercised here: no key was available.
"""
import base64, io, json, os, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOUR = sys.argv[sys.argv.index("--tour") + 1] if "--tour" in sys.argv else "7627"
HERE = ROOT / "tours" / TOUR   # tours/<id>/{shots.json,prompts,shots,stills}
ARK_BASE = os.environ.get("ARK_BASE", "https://ark.ap-southeast.bytepluses.com/api/v3")
ARK_MODEL = os.environ.get("ARK_VIDEO_MODEL", "seedance-1-0-pro-250528")
FAL_MODEL = os.environ.get("FAL_VIDEO_MODEL", "fal-ai/kling-video/v2.1/standard/image-to-video")

def http(url, data=None, headers=None, method=None, timeout=120):
    req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"),
                                 headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

def first_frame_data_url(seg):
    from PIL import Image
    d = HERE / "shots" / seg["slot"]
    src = d / "generated.png" if (d / "generated.png").exists() else HERE / seg["src"]
    im = Image.open(src).convert("RGB")
    w, h = im.size; target = 16 / 9
    if w / h > target: nw = int(h * target); im = im.crop(((w - nw)//2, 0, (w - nw)//2 + nw, h))
    else: nh = int(w / target); im = im.crop((0, (h - nh)//2, w, (h - nh)//2 + nh))
    im = im.resize((1280, 720), Image.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=92)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

def seedance(prompt, img, dur, key):
    body = json.dumps({"model": ARK_MODEL, "content": [
        {"type": "text", "text": f"{prompt} --resolution 720p --duration {dur} --camerafixed false"},
        {"type": "image_url", "image_url": {"url": img}}]}).encode()
    h = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    task = http(f"{ARK_BASE}/contents/generations/tasks", body, h)["id"]
    for _ in range(120):
        time.sleep(10)
        j = http(f"{ARK_BASE}/contents/generations/tasks/{task}", headers=h)
        st = j.get("status")
        if st == "succeeded": return j["content"]["video_url"]
        if st in ("failed", "cancelled"): raise RuntimeError(f"seedance task {st}: {j.get('error')}")
    raise RuntimeError("seedance task timed out")

def fal(prompt, img, dur, key):
    body = json.dumps({"prompt": prompt, "image_url": img, "duration": str(dur), "aspect_ratio": "16:9"}).encode()
    h = {"Authorization": f"Key {key}", "Content-Type": "application/json"}
    j = http(f"https://queue.fal.run/{FAL_MODEL}", body, h)
    status_url, response_url = j["status_url"], j["response_url"]
    for _ in range(120):
        time.sleep(10)
        s = http(status_url, headers=h)
        if s.get("status") == "COMPLETED":
            return http(response_url, headers=h)["video"]["url"]
        if s.get("status") in ("FAILED", "CANCELLED"): raise RuntimeError(f"fal job {s}")
    raise RuntimeError("fal job timed out")

def main():
    route = sys.argv[sys.argv.index("--route") + 1] if "--route" in sys.argv else "seedance"
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    key = os.environ.get("ARK_API_KEY") if route == "seedance" else os.environ.get("FAL_KEY")
    if route == "none" or not key:
        print(f"gen_clips: no key for route {route}, skipping (stills will be used)"); return
    cfg = json.loads((HERE / "shots.json").read_text(encoding="utf-8"))
    done = failed = 0
    for seg in cfg["segments"]:
        slot = seg.get("slot")
        if not slot or seg["type"] != "shot" or (only and slot != only): continue
        out = HERE / "shots" / slot / "clip.mp4"
        pf = HERE / "prompts" / f"{slot}.txt"
        if out.exists() or not pf.exists(): continue
        prompt = pf.read_text(encoding="utf-8").strip()
        dur = 5 if seg["dur"] <= 5 else 10
        try:
            url = (seedance if route == "seedance" else fal)(prompt, first_frame_data_url(seg), dur, key)
            out.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url, timeout=300) as r: out.write_bytes(r.read())
            print(f"wrote {out.relative_to(ROOT)}"); done += 1
        except Exception as e:
            print(f"  {slot}: {e}"); failed += 1
    print(f"gen_clips[{route}]: {done} clips, {failed} failed")

if __name__ == "__main__":
    main()
