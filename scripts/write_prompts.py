#!/usr/bin/env python3
"""Write the per-shot AI prompts for a tour: tours/<id>/prompts/<slot>.txt.

    python scripts/write_prompts.py --tour 7627

Prompts are English so any image or video model takes them; captions in
shots.json stay Traditional Chinese. The `heroine` line in shots.json is
prepended to every shot that names her, so she stays one person across the
film. Tour 7540's prompts were hand-written earlier and ship as files; this
script only knows 7627 and leaves an existing prompts/ folder alone unless
--force is given.
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent

STYLE = ("Cinematic film still, anamorphic 2.0x lens, 35mm, natural soft Nordic daylight, "
         "cool desaturated palette with warm skin tones, shallow depth of field, "
         "fine film grain, no text, no watermark, photoreal, 16:9 wide composition")

SHOTS_7627 = {
 "01_arrival_cph": "{H} pulling a small suitcase through a bright glass airport corridor at Copenhagen, morning light, a Scandinavian-style blue-and-white signage blurred behind her, she looks ahead with quiet anticipation, medium shot",
 "02_nyhavn_day": "Nyhavn canal in Copenhagen, the row of ochre, red and blue 17th-century townhouses, old wooden sailboats moored along the quay, {H} walking along the waterfront in the foreground, late morning sun, wide shot",
 "03_andersen": "{H} standing beside the bronze Hans Christian Andersen statue in Copenhagen, looking up at it, autumn trees, soft overcast light, medium close-up from a low angle",
 "04_nyhavn_dusk": "Nyhavn at blue hour, warm window lights of the coloured houses reflected in still canal water, {H} seen from behind at the quay edge, wide shot",
 "05_dfds_ferry": "A large white overnight passenger ferry leaving Copenhagen harbour on a calm sea, wake trailing, {H} at the open deck rail with wind in her hair, late afternoon sun, wide shot",
 "06_ship_dining": "An elegant cruise-ship dining room with white tablecloths and chandeliers, {H} at a window table with a glass of wine, the sea at dusk outside, warm interior light, medium shot",
 "07_oslo_city_hall": "The red-brick twin towers of Oslo City Hall above a sunlit square, {H} walking across the square toward the camera, summer light, wide shot",
 "08_vigeland": "Vigeland sculpture park in Oslo, the granite Monolith and surrounding stone figures on the terraced plateau, {H} standing small on the steps looking up, overcast bright sky, wide low-angle shot",
 "09_sognefjord": "Sognefjord from a sightseeing boat, sheer green mountain walls dropping into dark glassy water, a small white ferry far ahead, snow on the peaks, {H} at the bow rail looking out, wide epic shot",
 "10_naeroyfjord": "The narrow Naeroyfjord, towering cliffs on both sides, waterfalls threading down the rock, mist on the water, morning light, aerial-feeling wide shot, no people",
 "11_flam": "The green Flam railway train at the tiny Flam station, steep mountains behind, {H} stepping down onto the platform with a small backpack, soft daylight, medium shot",
 "12_hardangerfjord": "Hardangerfjord in late spring, fruit orchards in white blossom sloping down to turquoise water, a white cruise ship anchored mid-fjord, snow-capped mountains, wide shot, no people",
 "13_road_to_stockholm": "A coach on a quiet Swedish highway through pine forest and red wooden farmhouses, view through the windscreen, {H}'s reflection faint in the glass, afternoon light, wide shot",
 "14_stockholm_hall": "Stockholm City Hall across the water at dusk, its brick tower with the three golden crowns, lights coming on, {H} on the waterfront promenade in the foreground, wide shot",
 "15_vasa": "Inside the Vasa Museum, the vast dark oak hull of the 17th-century warship towering overhead, dim dramatic museum lighting, {H} small at the railing looking up, wide low-angle shot",
 "16_turku_castle": "The grey stone medieval Turku Castle in Finland under a soft evening sky, {H} walking along the gravel path toward the gate, wide shot",
 "17_rock_church": "Interior of the Temppeliaukio rock church in Helsinki, rough granite walls, the copper dome ceiling with its ring of skylights, {H} seated alone in a wooden pew in a shaft of light, wide shot",
 "18_helsinki_cathedral": "Helsinki Cathedral, the white neoclassical church with green domes above the wide steps of Senate Square, {H} climbing the steps, bright northern midday light, wide shot",
 "19_title_plate": "A moody wide shot of a Norwegian fjord at dawn, dark mountain silhouettes, pale blue mist over black water, a single distant ship light, cool blue-grey palette, empty composition with space in the centre for a title, no text, no people",
}

PROMPTS = {"7627": SHOTS_7627}

def main():
    tour = sys.argv[sys.argv.index("--tour") + 1] if "--tour" in sys.argv else "7627"
    force = "--force" in sys.argv
    tdir = HERE / "tours" / tour
    cfg = json.loads((tdir / "shots.json").read_text(encoding="utf-8"))
    shots = PROMPTS.get(tour)
    if not shots:
        print(f"write_prompts: tour {tour} has no prompt table here; keeping tours/{tour}/prompts as shipped")
        return
    pdir = tdir / "prompts"; pdir.mkdir(exist_ok=True)
    n = 0
    for slot, text in shots.items():
        out = pdir / f"{slot}.txt"
        if out.exists() and not force: continue
        body = text.replace("{H}", cfg["heroine"])
        out.write_bytes(f"{body}. {STYLE}".encode("utf-8")); n += 1
    print(f"write_prompts: {n} prompt files written to {pdir.relative_to(HERE)}")

if __name__ == "__main__":
    main()
