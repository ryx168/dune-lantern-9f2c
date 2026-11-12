#!/usr/bin/env python3
"""Build one tour's trailer from tours/<id>/shots.json.

    python scripts/build_trailer.py --tour 7627                 # 1080p -> out/7627/trailer_7627.mp4
    python scripts/build_trailer.py --tour 7627 --quality draft # 960x540, fast local check
    python scripts/build_trailer.py --tour 7627 --only 09_sognefjord

Each segment renders to its own mp4 under out/<id>/segments/, then the segments
are joined with crossfades under the music bed.

Source priority per shot slot (first that exists wins):
    tours/<id>/shots/<slot>/clip.mp4        a real moving shot (Seedance / Kling ...)
    tours/<id>/shots/<slot>/generated.png   an AI still (Workers AI flux, or any model)
    <src> from shots.json                   the tour's own photo, Ken Burns move

`look` in shots.json picks the grade: "ember" (warm, red title - the Saran look)
or "nordic" (cool, gold title). Fonts: the Noto CJK files the workflow installs;
override with TRAILER_FONT / TRAILER_FONT_BOLD (a path or a fontconfig family).
"""
import json, os, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FF = os.environ.get("FFMPEG", "ffmpeg")

def run(args):
    r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", *args])
    if r.returncode:
        sys.exit(f"ffmpeg failed: {' '.join(str(a) for a in args[:8])}...")

def esc(p):
    # drawtext wants the colon in a Windows drive letter escaped
    return str(p).replace("\\", "/").replace(":", "\\:")

def fontarg(spec):
    if spec and (os.path.exists(spec) or "/" in spec or "\\" in spec):
        return f"fontfile='{esc(spec)}'"
    return f"font='{spec}'"

def is_video(path):
    return Path(path).suffix.lower() in {".mp4", ".mov", ".webm", ".mkv", ".m4v"}

LOOKS = {
    # warm desert: lifted contrast, a touch more saturation, red title on an ember plate
    "ember": dict(
        grade="eq=contrast=1.06:saturation=1.08,curves=preset=increase_contrast,vignette=PI/5",
        card_bg="0x05070a", card_fg="0xffffff@0.95", card_sub="0xd9c9a8",
        title_fg="0xd8232a", title_border="0x5a0a0a", title_lines="0xf3e2c8",
        plate="gradients=s={W}x{H}:c0=0x4a0606:c1=0x0a0000:c2=0x2a0303:x0={W2}:y0={H3}:x1={W2}:y1={H}:d={dur}:r={fps}",
        plate_fx="noise=alls=28:allf=t+u,gblur=sigma=1.2,eq=contrast=1.15"),
    # cool north: teal shadows / amber highlights, gold title on a blue-black plate
    "nordic": dict(
        grade=("colorbalance=rs=-0.06:bs=0.07:bm=0.02:rh=0.07:gh=0.02:bh=-0.07,"
               "eq=contrast=1.07:saturation=0.92:brightness=0.01,vignette=PI/4.6"),
        card_bg="0x05080c", card_fg="0xf4ead8@0.96", card_sub="0xc9b48a",
        title_fg="0xe9c982", title_border="0x3a2a10", title_lines="0xf3e2c8",
        plate="gradients=s={W}x{H}:c0=0x0a1a2a:c1=0x02050a:c2=0x14263a:x0={W2}:y0={H3}:x1={W2}:y1={H}:d={dur}:r={fps}",
        plate_fx="noise=alls=22:allf=t+u,gblur=sigma=1.2,eq=contrast=1.1"),
}
GRAIN = "noise=alls=5:allf=t"

class Build:
    def __init__(self, tour, quality):
        self.tdir = ROOT / "tours" / tour
        self.cfg = json.loads((self.tdir / "shots.json").read_text(encoding="utf-8"))
        self.cfg["font"] = os.environ.get("TRAILER_FONT", self.cfg["font"])
        self.cfg["font_bold"] = os.environ.get("TRAILER_FONT_BOLD", self.cfg["font_bold"])
        self.look = LOOKS[self.cfg.get("look", "nordic")]
        self.out = ROOT / "out" / tour
        self.seg = self.out / "segments"
        self.seg.mkdir(parents=True, exist_ok=True)
        W, H = self.cfg["size"]
        if quality == "draft":
            W, H = 960, 540
        self.W, self.H, self.fps = W, H, self.cfg["fps"]
        self.scale = W / 1920
        self.quality = quality

    def textfile(self, name, text):
        p = self.out / "txt" / f"{name}.txt"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))   # bytes: no CRLF, drawtext draws a CR as tofu
        return esc(p)

    def source_for(self, seg):
        d = self.tdir / "shots" / seg["slot"]
        for name in ("clip.mp4", "clip.webm", "generated.png", "generated.jpg"):
            if (d / name).exists():
                return d / name
        return self.tdir / seg["src"] if seg.get("src") else d / "none"

    def kenburns(self, dur, move):
        W, H, fps = self.W, self.H, self.fps
        frames = int(round(dur * fps))
        pre = f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2}"
        if move in ("panL", "panR", "up"):
            cw, ch = (W*2, int(H*2*1.25)) if move == "up" else (int(W*2*1.25), H*2)
            pre = f"scale={cw}:{ch}:force_original_aspect_ratio=increase,crop={cw}:{ch}"
        z = {
            "in":   f"zoompan=z='1+0.12*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
            "out":  f"zoompan=z='1.12-0.12*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'",
            "panR": f"zoompan=z='1.0':x='(iw-{W*2})*on/{frames}':y='0'",
            "panL": f"zoompan=z='1.0':x='(iw-{W*2})*(1-on/{frames})':y='0'",
            "up":   f"zoompan=z='1.0':x='0':y='(ih-{H*2})*(1-on/{frames})'",
        }[move]
        z += f":d={frames}:s={W*2}x{H*2}:fps={fps}"
        return f"{pre},{z},scale={W}:{H}:flags=lanczos,{self.look['grade']},{GRAIN},format=yuv420p"

    def caption(self, text):
        s = self.scale
        tf = self.textfile(f"cap_{abs(hash(text))}", text)
        return (f"drawtext={fontarg(self.cfg['font'])}:textfile='{tf}':fontsize={int(40*s)}:"
                f"fontcolor=white@0.92:shadowcolor=black@0.6:shadowx=2:shadowy=2:"
                f"x={int(80*s)}:y={self.H-int(130*s)}:"
                f"alpha='if(lt(t,0.6),0,if(lt(t,1.4),(t-0.6)/0.8,1))'")

    def render_shot(self, seg, out):
        W, H, fps, dur = self.W, self.H, self.fps, seg["dur"]
        src = self.source_for(seg)
        if not src.exists():
            sys.exit(f"missing source for {seg['slot']}: {src}")
        cap = self.caption(seg["caption"]) if seg.get("caption") else None
        if is_video(src):
            vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
                  f"fps={fps},{self.look['grade']},{GRAIN},format=yuv420p")
            if cap: vf += "," + cap
            run(["-ss", "0", "-t", str(dur), "-i", str(src), "-an", "-vf", vf,
                 "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(out)])
        else:
            vf = self.kenburns(dur, seg.get("move", "in"))
            if cap: vf += "," + cap
            run(["-loop", "1", "-framerate", str(fps), "-t", str(dur), "-i", str(src),
                 "-vf", vf, "-t", str(dur), "-c:v", "libx264", "-preset", "medium",
                 "-crf", "18", "-r", str(fps), str(out)])

    def render_card(self, seg, out, idx):
        W, H, fps, dur, s, L = self.W, self.H, self.fps, seg["dur"], self.scale, self.look
        lines = seg["lines"]; n = len(lines); lh = int(110 * s)
        f = f"color=c={L['card_bg']}:s={W}x{H}:d={dur}:r={fps},{GRAIN}"
        for i, line in enumerate(lines):
            tf = self.textfile(f"card{idx}_{i}", line)
            y = H/2 - (n*lh)/2 + i*lh - int(20*s)
            f += (f",drawtext={fontarg(self.cfg['font_bold'])}:textfile='{tf}':fontsize={int(84*s)}:"
                  f"fontcolor={L['card_fg']}:x=(w-text_w)/2:y={int(y)}:"
                  f"alpha='if(lt(t,{0.3+i*0.35}),0,if(lt(t,{1.3+i*0.35}),(t-{0.3+i*0.35}),1))'")
        if seg.get("sub"):
            tf = self.textfile(f"card{idx}_sub", seg["sub"])
            f += (f",drawtext={fontarg(self.cfg['font'])}:textfile='{tf}':fontsize={int(38*s)}:"
                  f"fontcolor={L['card_sub']}:x=(w-text_w)/2:y={int(H/2 + n*lh/2 + 10*s)}:"
                  f"alpha='if(lt(t,1.2),0,if(lt(t,2.0),(t-1.2)/0.8,1))'")
        f += f",fade=t=out:st={dur-0.5}:d=0.5,format=yuv420p"
        run(["-f", "lavfi", "-i", f, "-t", str(dur), "-c:v", "libx264", "-crf", "18",
             "-pix_fmt", "yuv420p", str(out)])

    def render_title(self, seg, out):
        W, H, fps, dur, s, L = self.W, self.H, self.fps, seg["dur"], self.scale, self.look
        frames = int(dur * fps)
        plate = self.source_for(seg)
        if plate.exists() and not is_video(plate):
            base = ["-loop", "1", "-framerate", str(fps), "-t", str(dur), "-i", str(plate)]
            f = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
                 f"zoompan=z='1+0.06*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                 f":d={frames}:s={W*2}x{H*2}:fps={fps},scale={W}:{H},{L['grade']},"
                 f"eq=brightness=-0.18,gblur=sigma=2")
        else:
            base = ["-f", "lavfi", "-i", L["plate"].format(W=W, H=H, W2=W//2, H3=H//3, dur=dur, fps=fps)]
            f = L["plate_fx"]
        big = self.textfile("title_big", seg["big"])
        bigsize = int((260 if len(seg["big"]) <= 3 else 190) * s)
        f += (f",drawtext={fontarg(self.cfg['font_bold'])}:textfile='{big}':fontsize={bigsize}:"
              f"fontcolor={L['title_fg']}:borderw=2:bordercolor={L['title_border']}:"
              f"x=(w-text_w)/2:y=(h-text_h)/2-{int(120*s)}:"
              f"alpha='if(lt(t,0.4),0,if(lt(t,1.6),(t-0.4)/1.2,1))'")
        for i, line in enumerate(seg["lines"]):
            tf = self.textfile(f"title_l{i}", line)
            f += (f",drawtext={fontarg(self.cfg['font'])}:textfile='{tf}':fontsize={int(54*s)}:"
                  f"fontcolor={L['title_lines']}:x=(w-text_w)/2:y={H//2 + int((130 + i*76)*s)}:"
                  f"alpha='if(lt(t,{1.8+i*0.4}),0,if(lt(t,{2.6+i*0.4}),(t-{1.8+i*0.4})/0.8,1))'")
        sub = self.textfile("title_sub", seg["sub"])
        f += (f",drawtext={fontarg(self.cfg['font'])}:textfile='{sub}':fontsize={int(34*s)}:"
              f"fontcolor=white@0.8:x=(w-text_w)/2:y={H-int(120*s)}:"
              f"alpha='if(lt(t,3.0),0,if(lt(t,3.8),(t-3.0)/0.8,1))'")
        f += f",fade=t=out:st={dur-1.2}:d=1.2,format=yuv420p"
        run([*base, "-t", str(dur), "-vf", f, "-c:v", "libx264", "-crf", "18", "-r", str(fps), str(out)])

    def credit_lines(self):
        """Attribution for the stock photos actually in the cut. Two credits.json shapes:
        {file, author, license} or {file, credit:{author, license}}."""
        p = self.tdir / self.cfg.get("credits", "credits.json")
        if not p.exists():
            return []
        rows = json.loads(p.read_text(encoding="utf-8"))
        used = {Path(sg["src"]).name for sg in self.cfg["segments"]
                if sg.get("src") and not is_video(self.source_for(sg)) and self.source_for(sg).name == Path(sg["src"]).name}
        seen = {}
        for r in rows:
            key = Path(r["file"]).name
            c = r.get("credit") or r
            if key in seen or key not in used:
                continue
            seen[key] = f"{c.get('author','')} · {c.get('license','')}"
        return sorted(set(seen.values()))

    def render_credits(self, seg, out):
        W, H, fps, dur, s = self.W, self.H, self.fps, seg["dur"], self.scale
        lines = self.credit_lines()
        f = f"color=c=black:s={W}x{H}:d={dur}:r={fps}"
        if lines:
            lines = ["圖片來源 Photo credits (Wikimedia Commons)"] + lines
            step = int(40 * s); y0 = H / 2 - (len(lines) * step) / 2
            for i, line in enumerate(lines):   # one drawtext per line: a newline renders as tofu
                tf = self.textfile(f"credits_{i}", line)
                f += (f",drawtext={fontarg(self.cfg['font'])}:textfile='{tf}':fontsize={int(26*s)}:"
                      f"fontcolor=white@0.75:x=(w-text_w)/2:y={int(y0 + i*step)}")
        else:
            tf = self.textfile("credits_0", "新聯華假期 XO TOURS")
            f += (f",drawtext={fontarg(self.cfg['font_bold'])}:textfile='{tf}':fontsize={int(48*s)}:"
                  f"fontcolor=white@0.85:x=(w-text_w)/2:y=(h-text_h)/2")
        f += f",fade=t=in:st=0:d=0.8,fade=t=out:st={dur-1}:d=1,format=yuv420p"
        run(["-f", "lavfi", "-i", f, "-t", str(dur), "-c:v", "libx264", "-crf", "20", str(out)])

    def build(self, only=None):
        cfg = self.cfg
        segs = []
        for i, seg in enumerate(cfg["segments"]):
            name = seg.get("slot") or f"{seg['type']}_{i:02d}"
            out = self.seg / f"{i:02d}_{name}.mp4"
            segs.append((seg, out))
            if only and only != name and out.exists():
                continue
            print(f"render {i:02d} {seg['type']:7s} {name} ({seg['dur']}s)", flush=True)
            {"shot": lambda: self.render_shot(seg, out),
             "card": lambda: self.render_card(seg, out, i),
             "title": lambda: self.render_title(seg, out),
             "credits": lambda: self.render_credits(seg, out)}[seg["type"]]()

        xf = cfg["xfade"]
        inputs = []
        for _, out in segs: inputs += ["-i", str(out)]
        fc, prev, total = [], "[0:v]", segs[0][0]["dur"]
        for i in range(1, len(segs)):
            offset = total - xf
            lab = f"[v{i}]"
            fc.append(f"{prev}[{i}:v]xfade=transition=fade:duration={xf}:offset={offset:.3f}{lab}")
            total = offset + segs[i][0]["dur"]
            prev = lab
        fc.append(f"{prev}format=yuv420p[vout]")
        audio = ROOT / cfg["audio"]
        if not audio.exists():
            audio = self.out / "bgm.wav"
        if not audio.exists():
            sys.exit(f"no music bed at {audio}; run scripts/make_bgm.py first")
        fc.append(f"[{len(segs)}:a]atrim=0:{total:.3f},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.5,"
                  f"afade=t=out:st={total-4:.3f}:d=4[aout]")
        stem = cfg.get("output", "trailer")
        final = self.out / (f"{stem}.mp4" if self.quality != "draft" else f"{stem}_draft.mp4")
        run([*inputs, "-i", str(audio), "-filter_complex", ";".join(fc),
             "-map", "[vout]", "-map", "[aout]", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}", str(final)])
        print(f"wrote {final}  ({total:.1f}s, {len(segs)} segments, {self.W}x{self.H})")
        return final

def main():
    argv = sys.argv
    tour = argv[argv.index("--tour") + 1] if "--tour" in argv else "7627"
    only = argv[argv.index("--only") + 1] if "--only" in argv else None
    quality = argv[argv.index("--quality") + 1] if "--quality" in argv else "final"
    Build(tour, quality).build(only)

if __name__ == "__main__":
    main()
