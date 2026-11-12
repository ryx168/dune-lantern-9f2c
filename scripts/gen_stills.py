#!/usr/bin/env python3
"""Generate an AI still per shot slot with Cloudflare Workers AI (flux-1-schnell).

    CF_ACCOUNT_ID=... CF_API_TOKEN=... python scripts/gen_stills.py --tour 7627 [--only SLOT] [--force]

Writes tours/<id>/shots/<slot>/generated.png for every tours/<id>/prompts/<slot>.txt. The builder
prefers that file over the tour photo. Without both env vars the script exits
0 and does nothing, so the workflow step is harmless when no key is set.

flux-1-schnell takes only {prompt, steps} (width/height are rejected with 400)
and returns a 1024x1024 base64 JPEG; the builder crops it to 2.39:1, so the
prompt already asks for a wide composition with the subject centred.
"""
import base64, json, os, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOUR = sys.argv[sys.argv.index("--tour") + 1] if "--tour" in sys.argv else "7627"
HERE = ROOT / "tours" / TOUR   # tours/<id>/{shots.json,prompts,shots,stills}
MODEL = os.environ.get("CF_IMAGE_MODEL", "@cf/black-forest-labs/flux-1-schnell")

def main():
    acct = os.environ.get("CF_ACCOUNT_ID"); tok = os.environ.get("CF_API_TOKEN")
    if not (acct and tok):
        print("gen_stills: CF_ACCOUNT_ID / CF_API_TOKEN not set, skipping (tour photos will be used)")
        return
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    force = "--force" in sys.argv
    url = f"https://api.cloudflare.com/client/v4/accounts/{acct}/ai/run/{MODEL}"
    done = failed = 0
    for pf in sorted((HERE / "prompts").glob("*.txt")):
        slot = pf.stem
        if only and slot != only: continue
        out = HERE / "shots" / slot / "generated.png"
        if out.exists() and not force:
            print(f"keep  {slot}"); continue
        prompt = pf.read_text(encoding="utf-8").strip()
        body = json.dumps({"prompt": prompt[:2000], "steps": 8}).encode()
        req = urllib.request.Request(url, data=body, method="POST", headers={
            "Authorization": f"Bearer {tok}", "Content-Type": "application/json"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    j = json.loads(r.read())
                img = j.get("result", {}).get("image")
                if not img:
                    raise RuntimeError(f"no image in response: {str(j)[:200]}")
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(base64.b64decode(img))
                print(f"wrote {out.relative_to(ROOT)}"); done += 1
                break
            except Exception as e:
                print(f"  {slot}: attempt {attempt+1} failed: {e}")
                time.sleep(3 * (attempt + 1))
        else:
            failed += 1
    print(f"gen_stills: {done} generated, {failed} failed")

if __name__ == "__main__":
    main()
