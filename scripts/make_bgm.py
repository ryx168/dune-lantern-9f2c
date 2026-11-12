#!/usr/bin/env python3
"""Synthesise a royalty-free ambient music bed with numpy: out/bgm.wav.

A slow pad over a D-minor / Bb / F / C progression, a sparse plucked
pentatonic motif (Karplus-Strong) for the Silk Road feel, and a soft low
drone. Nothing sampled, nothing copyrighted - safe for a public repo and for
publishing. Pass --seconds to change the length (default 100 s) and --seed
for a different motif.
"""
import argparse, math, struct, wave
import numpy as np

SR = 44100

def note(semitones_from_a4):
    return 440.0 * 2 ** (semitones_from_a4 / 12)

def pad_voice(freq, t, detune=0.4):
    out = np.zeros_like(t)
    for d in (-detune, 0.0, detune):
        f = freq * 2 ** (d / 1200)
        out += np.sin(2*np.pi*f*t) * 0.5 + np.sin(2*np.pi*f*2*t) * 0.12 + np.sin(2*np.pi*f*0.5*t) * 0.3
    return out / 3

def lowpass(x, cutoff, sr=SR):
    rc = 1 / (2*math.pi*cutoff); dt = 1/sr; a = dt / (rc + dt)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += a * (x[i] - acc); y[i] = acc
    return y

def pluck(freq, dur, rng, bright=0.996):
    n = int(SR * dur); N = int(SR / freq)
    buf = rng.uniform(-1, 1, N)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % N]
        buf[i % N] = bright * 0.5 * (buf[i % N] + buf[(i + 1) % N])
    env = np.exp(-np.linspace(0, 6, n))
    return out * env

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=100)
    ap.add_argument("--seed", type=int, default=7620)
    ap.add_argument("--out", default="out/bgm.wav")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    total = int(a.seconds * SR)
    t = np.arange(total) / SR
    # chord progression, 8 s per chord: Dm, Bb, F, C (relative to A4 = 0)
    chords = [(-7, -4, 0), (-11, -7, -4), (-16, -12, -9), (-9, -5, -2)]
    pad = np.zeros(total)
    bar = 8 * SR
    for i in range(0, total, bar):
        ch = chords[(i // bar) % len(chords)]
        seg = t[i:i+bar] - t[i]
        env = np.minimum(1, seg / 2.5) * np.minimum(1, (len(seg)/SR - seg) / 2.5)
        v = sum(pad_voice(note(s - 12), seg) for s in ch) / len(ch)
        pad[i:i+len(seg)] += v * env
    pad = lowpass(pad, 900) * 0.35
    # low drone on D
    drone = (np.sin(2*np.pi*note(-19-12)*t) * 0.6 + np.sin(2*np.pi*note(-19)*t) * 0.2) * 0.18
    drone *= np.minimum(1, t / 4)
    # sparse pentatonic plucks: D minor pentatonic D F G A C
    scale = [-7, -4, -2, 0, 3, 5, 8, 10, 12]
    plucks = np.zeros(total)
    pos = 3.0
    while pos < a.seconds - 6:
        n = rng.choice(scale) + 12
        d = rng.choice([0.5, 0.75, 1.0, 1.5])
        p = pluck(note(n), min(3.0, a.seconds - pos), rng) * rng.uniform(0.10, 0.22)
        i = int(pos * SR); plucks[i:i+len(p)] += p[:total-i]
        pos += d * rng.choice([1, 1, 2, 3])
    plucks = lowpass(plucks, 3500)
    # soft air: filtered noise swell
    air = lowpass(rng.uniform(-1, 1, total), 400) * 0.03 * (0.6 + 0.4*np.sin(2*np.pi*t/23))
    mix = pad + drone + plucks + air
    mix /= max(1e-6, np.abs(mix).max()) * 1.15
    # stereo: slight widening by delaying one side of the pad
    left = mix; right = np.roll(mix, int(0.011*SR)); right[:int(0.011*SR)] = 0
    stereo = np.stack([left, right], axis=1)
    pcm = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    from pathlib import Path
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(a.out, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    print(f"wrote {a.out} ({a.seconds:.0f}s)")

if __name__ == "__main__":
    main()
