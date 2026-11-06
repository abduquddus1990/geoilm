"""Kaggle GPU'da ishlaydigan skript (make_voices.py uni avtomatik yuboradi — qo'lda ishga tushirish shart emas).

Kirish: /kaggle/input/<dataset>/reference.wav, voice_lines.json, settings.json
Chiqish: /kaggle/working/voice_lines.zip
"""
import glob, json, os, random, subprocess, sys, zipfile

def sh(cmd):
    print("$", cmd, flush=True)
    subprocess.run(cmd, shell=True, check=True)

INP = os.path.dirname(glob.glob("/kaggle/input/**/voice_lines.json", recursive=True)[0])
WORK = "/kaggle/working"
os.chdir("/kaggle/temp" if os.path.isdir("/kaggle/temp") else "/tmp")

# 1) O'rnatish
sh("git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git")
sh("cd CosyVoice && git checkout 074ca6dc9e80a2f424f1f74b48bdd7d3fea531cc && git submodule update --init --recursive")
sh("pip install -q -r CosyVoice/requirements.txt")
sh("pip install -q huggingface_hub==0.36.2 transformers==4.51.3")

from huggingface_hub import snapshot_download
snapshot_download("FunAudioLLM/CosyVoice2-0.5B", local_dir="CosyVoice/pretrained_models/CosyVoice2-0.5B")
snapshot_download("aisha-org/navoiy-tts", local_dir="navoiy-tts")

# 2) Model
cwd = os.getcwd()
for p in ("CosyVoice", "CosyVoice/third_party/Matcha-TTS", "navoiy-tts"):
    sys.path.insert(0, os.path.join(cwd, p))
import torch, torchaudio
from cosyvoice.cli.cosyvoice import CosyVoice2
from uztts.normalize import normalize

def unwrap(v):
    if not isinstance(v, dict):
        return v
    for k in ("state_dict", "model", "llm"):
        if isinstance(v.get(k), dict):
            return unwrap(v[k])
    return v

model = CosyVoice2(os.path.join(cwd, "CosyVoice/pretrained_models/CosyVoice2-0.5B"), load_jit=False, load_trt=False, fp16=True)
state = unwrap(torch.load("navoiy-tts/emotion_600h_joint.pt", map_location="cpu", weights_only=True))
r = model.model.llm.load_state_dict(state, strict=False)
print("missing:", len(r.missing_keys), "unexpected:", len(r.unexpected_keys), flush=True)
model.model.llm.eval()

lookup = {}
for e in json.load(open("navoiy-tts/emotions_40h.json", encoding="utf-8")):
    lookup[e["uz"].lower()] = e
    for t in e["tag"].replace("[", " ").replace("]", " ").split():
        lookup[t.lower()] = e

cfg = json.load(open(os.path.join(INP, "settings.json"), encoding="utf-8"))
REF = os.path.join(INP, "reference.wav")

def say(text, out, emotion, seed=1986):
    random.seed(seed); torch.manual_seed(seed); torch.cuda.manual_seed_all(seed)
    instr = lookup[emotion]["instruct"].strip() + "<|endofprompt|>"
    chunks = []
    with torch.inference_mode():
        for res in model.inference_instruct2(normalize(text, mode="infer"), instr, REF, stream=False, speed=cfg["speed"]):
            chunks.append(res["tts_speech"].detach().cpu())
    audio = torch.cat(chunks, dim=1)
    torchaudio.save(out, audio, 24000)
    return audio.shape[-1] / 24000

# 3) Hammasini o'qitish
lines = json.load(open(os.path.join(INP, "voice_lines.json"), encoding="utf-8"))
os.makedirs("lines", exist_ok=True)
report = {"ok": 0, "suspicious": [], "failed": []}
for i, (key, text) in enumerate(lines.items(), 1):
    try:
        d = say(text, f"lines/{key}.wav", cfg["emotion_title"] if key.startswith(("title_", "outro")) else cfg["emotion"])
        report["ok"] += 1
        if d > 6:
            report["suspicious"].append([key, text, round(d, 1)])
    except Exception as e:  # noqa: BLE001
        report["failed"].append([key, text, str(e)[:200]])
    if i % 20 == 0:
        print(f"{i}/{len(lines)}", flush=True)

with zipfile.ZipFile(os.path.join(WORK, "voice_lines.zip"), "w") as z:
    for f in os.listdir("lines"):
        z.write(f"lines/{f}", f)
json.dump(report, open(os.path.join(WORK, "report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("TAYYOR", report["ok"], "ta; shubhali:", len(report["suspicious"]), "; xato:", len(report["failed"]), flush=True)
