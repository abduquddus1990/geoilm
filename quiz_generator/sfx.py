"""Taymer chiqillashi, 'ding' va shovqin (whoosh) effektlarini events.json bo'yicha yasaydi."""
import json, sys, wave
import numpy as np

def build(events_path: str, out_path: str, voice_wav: str | None = None,
          answers: list | None = None, outro_wav: str | None = None) -> float:
    """voice_wav — har savol boshida; answers[i] — i-savol javobi ochilganda; outro_wav — yakunda."""
    sr = 44100
    E = json.load(open(events_path, encoding="utf-8"))
    D = E["D"]
    a = np.zeros(int(sr * (D + 0.5)))

    def put(sig, t, g=1.0):
        i = int(t * sr)
        if i >= len(a):
            return
        n = min(len(sig), len(a) - i)
        a[i:i + n] += sig[:n] * g

    t = np.arange(int(.06 * sr)) / sr
    tick = (np.sin(2 * np.pi * 1500 * t) + .5 * np.sin(2 * np.pi * 3000 * t)) * np.exp(-t * 90)
    t = np.arange(int(1.0 * sr)) / sr
    ding = (np.sin(2 * np.pi * 1046.5 * t) + .6 * np.sin(2 * np.pi * 1568 * t) + .3 * np.sin(2 * np.pi * 2093 * t)) * np.exp(-t * 4.5)
    n = np.random.default_rng(1).normal(0, 1, int(.7 * sr))
    whoosh = np.convolve(n, np.ones(40) / 40, "same") * np.sin(np.linspace(0, np.pi, len(n))) ** 2
    t = np.arange(int(.5 * sr)) / sr
    level_up = np.concatenate([np.sin(2 * np.pi * f * t[: sr // 8]) * np.exp(-t[: sr // 8] * 12) for f in (660, 880, 1175)])

    for e in E["ev"]:
        put(whoosh, max(0, e["start"] - 0.05), .25)
        if e.get("levelChange"):
            put(level_up, e["start"] + 0.1, .25)
        for s in range(3):
            put(tick, e["cd"] + s, .35 if s < 2 else .45)
        put(ding, e["rev"], .3)
    put(ding, D - 2.6, .35)
    def load(path):
        with wave.open(path, "rb") as w:
            v = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
        return v / max(1e-9, np.abs(v).max())

    voiced = bool(voice_wav or outro_wav or (answers and any(answers)))
    if voiced:  # effektlarni pasaytirib, ovozni ustiga qo'yamiz
        a /= max(1e-9, np.abs(a).max())
        a *= 0.5
        if voice_wav:
            v = load(voice_wav)
            for e in E["ev"]:
                put(v, e["start"] + 0.15, 0.9)
        for e, ans in zip(E["ev"], answers or []):
            if ans:
                put(load(ans), e["rev"] + 0.12, 0.95)
        if outro_wav:
            put(load(outro_wav), D - 2.4, 0.95)
    a = a / max(1e-9, np.abs(a).max()) * .8
    with wave.open(out_path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((a * 32767).astype(np.int16).tobytes())
    return D

if __name__ == "__main__":
    print(build(sys.argv[1], sys.argv[2]))


def build_story(events_path: str, out_path: str) -> float:
    """Hikoya videolari uchun: har sahna boshida yumshoq 'whoosh', har yorliq (pill) chiqqanda 'pop'."""
    sr = 44100
    E = json.load(open(events_path, encoding="utf-8"))
    D = E["D"]
    a = np.zeros(int(sr * (D + 0.5)))

    def put(sig, t, g=1.0):
        i = int(t * sr)
        if i >= len(a):
            return
        n = min(len(sig), len(a) - i)
        a[i:i + n] += sig[:n] * g

    n = np.random.default_rng(3).normal(0, 1, int(.8 * sr))
    whoosh = np.convolve(n, np.ones(60) / 60, "same") * np.sin(np.linspace(0, np.pi, len(n))) ** 2
    t = np.arange(int(.18 * sr)) / sr
    pop = np.sin(2 * np.pi * (520 + 900 * np.exp(-t * 40)) * t) * np.exp(-t * 28)
    for k, e in enumerate(E["ev"]):
        if k:
            put(whoosh, max(0, e["start"] - 0.15), .35)
        for p in e.get("pills", []):
            put(pop, p, .3)
    a = a / max(1e-9, np.abs(a).max()) * .7
    with wave.open(out_path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((a * 32767).astype(np.int16).tobytes())
    return D
