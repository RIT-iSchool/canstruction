#!/usr/bin/env python3
"""
Cuts the wolf's lines out of the LibriVox "Three Little Pigs" reading (public domain,
read by Denny Sayers) into sounds/voice/, using word timings from Whisper.

    python3 tools/cut_librivox_lines.py <word-timings.json>

The JSON maps clip name -> {"words": [[word, start, end], ...]} for the region around
each line. Prints the HUFF_TIMINGS to paste into wolf_eyes.py.
"""
import json
import os
import re
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "sound_sources", "librivox", "three_little_pigs_brooke.mp3")
OUT = os.path.join(ROOT, "sounds", "voice")
PITCH = 0.88  # a bit deeper and more wolfish; tempo is kept the same

# clip name -> words that start and end the line (first match inside that clip's region)
LINES = {
    "little_pig_1": ("little", "in"), "little_pig_3": ("little", "in"),
    "huff_puff_3": ("then", "in"),
    "here_before_me": ("little", "me"), "are_you_ready": ("little", "ready"),
    "turnips": ("little", "turnips"),
}
REGION = {"nice_apples": "here_before_me"}  # shares the transcript region


def norm(w):
    return re.sub(r"[^a-z]", "", w.lower())


def rms_frames(t0, t1):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", SRC,
                          "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
    x = np.frombuffer(pcm, dtype=np.float32)
    n = 160  # 10 ms
    return np.array([np.sqrt(np.mean(x[i:i + n] ** 2) + 1e-12) for i in range(0, len(x) - n, n)])


def quietest(t0, t1):
    r = rms_frames(t0, t1)
    return t0 + (int(np.argmin(r)) * 0.01 if len(r) else 0)


def main():
    data = json.load(open(sys.argv[1]))
    os.makedirs(OUT, exist_ok=True)
    huff = {}
    for name, (first, last) in LINES.items():
        words = data[REGION.get(name, name)]["words"]
        toks = [norm(w) for w, _, _ in words]
        i = toks.index(first)
        if name == "nice_apples":
            i = toks.index("are", toks.index("me"))
        j = toks.index(last, i)
        start = quietest(words[i][1] - 0.25, words[i][1] - 0.01)
        end = quietest(words[j][2] + 0.12, words[j][2] + 0.40)
        dst = os.path.join(OUT, name + ".wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", SRC,
                        "-ac", "1", "-af",
                        f"asetrate=44100*{PITCH},aresample=44100,atempo={1 / PITCH:.4f},"
                        "bass=g=5:f=120,afade=t=in:d=0.02,"
                        f"afade=t=out:st={max(0, end - start - 0.06):.3f}:d=0.06,loudnorm=I=-14:TP=-1.5",
                        "-ar", "44100", "-c:a", "pcm_s16le", dst], check=True)
        print(f"{name:15s} {start:7.2f}-{end:7.2f} ({end - start:.1f}s)  "
              + " ".join(w for w, _, _ in words[i:j + 1]))
        if name.startswith("huff_puff"):
            at = {norm(w): round(s - start, 2) for w, s, _ in words[i:j + 1] if norm(w) in ("huff", "puff", "blow")}
            huff[name + ".wav"] = (min(at["huff"], at["puff"]), max(at["huff"], at["puff"]),
                                   at["blow"], round(end - start, 2))
    print("HUFF_TIMINGS =", json.dumps(huff))


if __name__ == "__main__":
    main()
