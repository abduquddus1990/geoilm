"""Original fon musiqasi generatori (100% o'zimizniki — Content ID xavfi yo'q).

Har video uchun yangi trek: tasodifiy akkord ketma-ketligi, tonallik va naqsh.
  geo   — davlat/poytaxt: yengil, qiziquvchan (pluck-arpedjio, qo'ng'iroqcha, shaker), ~108 BPM
  sport — futbolchi: energik (kick/clap, bas, stadion-sintez), ~124 BPM

Ishlatish: python music.py <geo|sport> <davomiylik_soniya> <chiqish.wav> [seed]
"""
import sys, wave, random
import numpy as np

SR = 44100
PROGS = [[0, 7, 9, 5], [0, 5, 7, 5], [9, 5, 0, 7], [0, 9, 5, 7], [0, 4, 9, 7]]  # I-V-vi-IV va boshqalar (yarim ton)
MAJOR = [0, 2, 4, 5, 7, 9, 11]
PENTA = [0, 2, 4, 7, 9]


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def chord(root_midi, degree_semi):
    """Mayor tonallikda pog'onaga mos uchtovush (vi — minor)."""
    r = root_midi + degree_semi
    minor = degree_semi in (2, 4, 9)
    return [r, r + (3 if minor else 4), r + 7]


_cache = {}


def pluck(freq, dur=0.6, bright=0.5):
    key = (round(freq, 2), dur, bright)
    if key in _cache:
        return _cache[key]
    n, p = int(SR * dur), max(2, int(SR / freq))
    rng = np.random.default_rng(int(freq * 100))
    buf = rng.uniform(-1, 1, p)
    out = np.empty(n)
    for i in range(n):  # Karplus-Strong
        out[i] = buf[i % p]
        buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * (0.994 + 0.004 * bright)
    out *= np.exp(-np.linspace(0, 3.5, n))
    _cache[key] = out
    return out


def bell(freq, dur=1.2):
    t = np.arange(int(SR * dur)) / SR
    return (np.sin(2 * np.pi * freq * t) + .35 * np.sin(2 * np.pi * freq * 2.76 * t)) * np.exp(-t * 3.2)


def bass(freq, dur):
    t = np.arange(int(SR * dur)) / SR
    s = np.sin(2 * np.pi * freq * t) + .25 * np.sin(2 * np.pi * 2 * freq * t)
    env = np.minimum(1, t / .01) * np.exp(-t * 2.2)
    return s * env


def pad(freqs, dur):
    t = np.arange(int(SR * dur)) / SR
    s = sum(np.sin(2 * np.pi * f * t) + np.sin(2 * np.pi * f * 1.003 * t) for f in freqs) / (2 * len(freqs))
    env = np.minimum(1, t / .4) * np.minimum(1, (dur - t) / .4)
    return s * env


def kick():
    t = np.arange(int(SR * .25)) / SR
    return np.sin(2 * np.pi * (50 + 90 * np.exp(-t * 30)) * t) * np.exp(-t * 14)


def noise_hit(dur, decay, seed, hp=True):
    n = np.random.default_rng(seed).normal(0, 1, int(SR * dur))
    if hp:
        n = n - np.convolve(n, np.ones(8) / 8, "same")
    return n * np.exp(-np.arange(len(n)) / SR * decay)


def generate(style: str, seconds: float, out: str, seed=None):
    rnd = random.Random(seed)
    bpm = rnd.choice([104, 108, 112]) if style == "geo" else rnd.choice([120, 124, 128])
    beat = 60 / bpm
    key = rnd.choice([55, 57, 60, 62])  # G, A, C, D
    prog = rnd.choice(PROGS)
    total = int(SR * (seconds + 2))
    mix = {k: np.zeros(total) for k in ("pluck", "bell", "bass", "pad", "drums")}

    def put(track, sig, t, g=1.0):
        i = int(t * SR)
        if i >= total:
            return
        n = min(len(sig), total - i)
        mix[track][i:i + n] += sig[:n] * g

    bar = 4 * beat
    nbars = int(seconds / bar) + 2
    arp_pattern = rnd.choice([[0, 1, 2, 1], [0, 2, 1, 2], [0, 1, 2, 3]])
    for b in range(nbars):
        t0 = b * bar
        ch = chord(key, prog[b % len(prog)])
        # pad va bas
        put("pad", pad([hz(m) for m in ch], bar), t0, .5 if style == "geo" else .35)
        for q in range(4):
            if style == "geo" and q % 2:
                continue
            put("bass", bass(hz(ch[0] - 24), beat * (2 if style == "geo" else 1)), t0 + q * beat, .8)
        # arpedjio (8-likda)
        for e in range(8):
            idx = arp_pattern[e % 4]
            m = ch[idx % 3] + (12 if idx == 3 else 0) + (12 if style == "sport" else 0)
            put("pluck", pluck(hz(m), .5, .3 if style == "geo" else .8), t0 + e * beat / 2, .55)
        # qo'ng'iroqcha melodiyasi (geo) — har 2 taktda
        if style == "geo" and b % 2 == 1:
            for k in range(rnd.choice([2, 3, 4])):
                m = key + 12 + rnd.choice(PENTA) + (12 if rnd.random() < .3 else 0)
                put("bell", bell(hz(m)), t0 + rnd.choice([0, 1, 1.5, 2, 2.5, 3]) * beat, .35)
        # zarb
        for q in range(4):
            tq = t0 + q * beat
            if style == "sport":
                put("drums", kick(), tq, .9)
                if q in (1, 3):
                    put("drums", noise_hit(.18, 18, b * 4 + q, hp=False) * .6, tq, .5)  # clap
                put("drums", noise_hit(.05, 70, 1000 + b * 8 + q), tq + beat / 2, .25)  # off-beat hat
            else:
                put("drums", noise_hit(.06, 60, 2000 + b * 8 + q), tq + beat / 2, .18)  # shaker
                if q == 0:
                    put("drums", kick() * .5, tq, .5)

    levels = {"pluck": .5, "bell": .45, "bass": .5, "pad": .35, "drums": .55}
    y = sum(mix[k] / max(1e-9, np.abs(mix[k]).max()) * v for k, v in levels.items())
    y = y[: int(SR * seconds)]
    fade = int(SR * 1.5)
    y[:fade] *= np.linspace(0, 1, fade)
    y[-fade:] *= np.linspace(1, 0, fade)
    y = np.tanh(y * 1.2)
    y = y / max(1e-9, np.abs(y).max()) * .9
    with wave.open(out, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((y * 32767).astype(np.int16).tobytes())
    return out


if __name__ == "__main__":
    generate(sys.argv[1], float(sys.argv[2]), sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else None)
