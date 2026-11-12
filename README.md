# XO Tours cinematic trailers — rendered on GitHub Actions

Two ~80 s trailers in the style of the [Saran (사란) AI short-film trailer](https://x.com/minchoi/status/2118374993696575996):
a quiet text open, one recurring heroine, an escalating montage with Chinese
captions, a big title card, credits.

| tour | trailer | look |
|---|---|---|
| 7540 北非摩洛哥10日 | `tours/7540/` | `ember` — warm desert grade, red title on an ember plate |
| 7627 北歐四國10天 雙峽灣 雙郵輪 | `tours/7627/` | `nordic` — teal/amber grade, gold title on a blue-black plate |

Everything renders on Actions: push to `main`, or dispatch by hand.

```
gh workflow run render.yml -R ryx168/dune-lantern-9f2c -f tour=7627 -f stills=photos -f quality=final
```

Outputs per tour: an artifact `trailer-<id>-<run>` and a release `run-<n>`
carrying `trailer_<id>.mp4` and `review_<id>.jpg` (a contact sheet — look at
it before calling a render done; it catches tofu glyphs and black segments
that a log never shows).

## How a render works

| step | script | needs |
|---|---|---|
| prompts | `scripts/write_prompts.py --tour <id>` | nothing; writes `tours/<id>/prompts/<slot>.txt` (7540's ship as files) |
| AI stills (optional) | `scripts/gen_stills.py --tour <id>` | secrets `CF_ACCOUNT_ID` + `CF_API_TOKEN` (Workers AI flux-1-schnell) |
| AI clips (optional) | `scripts/gen_clips.py --tour <id> --route seedance\|fal` | secret `ARK_API_KEY` (BytePlus ModelArk) or `FAL_KEY` (Kling) |
| music | `scripts/make_bgm.py --seed <id>` | nothing; a synthesised royalty-free bed, so the repo and the output carry no copyrighted audio |
| build | `scripts/build_trailer.py --tour <id>` | ffmpeg + Noto CJK (the workflow installs both) |
| QA | `scripts/review_frames.py` | contact sheet |

Per shot slot the builder takes the first that exists:
`tours/<id>/shots/<slot>/clip.mp4` → `shots/<slot>/generated.png` → the photo
named in `shots.json`. So the zero-key run already produces a complete trailer
from photos with Ken Burns moves, and every key you add upgrades shots without
touching the edit.

## Edit a trailer

`tours/<id>/shots.json` is the edit: order, duration, Ken Burns move
(`in` / `out` / `panL` / `panR` / `up`), caption and source per segment, the
`look`, and the `heroine` sentence that keeps her one person across every AI
prompt. Prompt text for 7627 lives in `scripts/write_prompts.py`; 7540's are
plain files under `tours/7540/prompts/`.

## Keys

Repository secrets (Settings → Secrets → Actions), never in the repo:

- `CF_ACCOUNT_ID` + `CF_API_TOKEN` (Workers AI run) → AI stills
- `ARK_API_KEY` → Seedance image-to-video (`ARK_VIDEO_MODEL` repo variable
  overrides the default model id)
- `FAL_KEY` → Kling image-to-video through fal.ai

The clip routes were written from the public API docs and have not been run
with a real key; expect to correct a field name on the first real run.

## Photos and credits

7540's stills and some of 7627's are Creative Commons photos from Wikimedia
Commons (listed in each tour's `credits.json`); the closing credits card names
the authors and licences of the ones actually in the cut, which CC BY / BY-SA
require. The rest of 7627's are the tour's own brochure photos. Once a slot is
an AI still its stock credit drops off the card by itself.

## Local check

```
python scripts/make_bgm.py --seed 7627 --out out/7627/bgm.wav
TRAILER_FONT=C:/Windows/Fonts/msjh.ttc TRAILER_FONT_BOLD=C:/Windows/Fonts/msjhbd.ttc \
  python scripts/build_trailer.py --tour 7627 --quality draft
python scripts/review_frames.py out/7627/trailer_7627_draft.mp4
```

ffmpeg notes baked into the builder: `drawtext` has no `letter_spacing`; its
text shaper draws a newline (and a CR) as a tofu box, so text goes in as bytes,
one `drawtext` per line; a pan pre-crop must scale to the pan canvas first or
`crop` fails on a small still.
