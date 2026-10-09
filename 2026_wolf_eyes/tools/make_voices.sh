#!/usr/bin/env bash
# Makes the placeholder wolf voice lines with macOS text-to-speech (Mac only: needs `say` + ffmpeg).
#   bash tools/make_voices.sh            # uses the default voice below
#   bash tools/make_voices.sh Fred       # try another voice:  say -v '?'  lists them
#
# To use your own recordings instead, drop them into sounds/voice/ with the same name
# start (e.g. little_pig_me.wav) and delete the TTS one. Any .wav/.ogg/.mp3 works.
set -euo pipefail
cd "$(dirname "$0")/.."
VOICE=${1:-Ralph}
PITCH=${PITCH:-0.80}   # lower = deeper
OUT=sounds/voice
TMP=$(mktemp -d)
mkdir -p "$OUT"

line() {
  local key=$1 text=$2
  say -v "$VOICE" -r 150 -o "$TMP/$key.aiff" "$text"
  local rate
  rate=$(ffprobe -v error -select_streams a:0 -show_entries stream=sample_rate -of csv=p=0 "$TMP/$key.aiff")
  ffmpeg -v error -y -i "$TMP/$key.aiff" -ac 1 \
    -af "asetrate=$rate*$PITCH,aresample=44100,atempo=1.1,bass=g=7:f=120,aecho=0.8:0.6:35:0.22,loudnorm=I=-14:TP=-1.5" \
    -ar 44100 -c:a pcm_s16le "$OUT/$key.wav"
  echo "  $OUT/$key.wav"
}

echo "Voice: $VOICE (pitch x$PITCH)"
line little_pig   "Little pig... little pig... let me come in!"
line huff_puff    "Then I'll huff... and I'll puff... and I'll blow your house in!"
line bacon        "Mmmmmm... I smell bacon."
line hungry       "I'm sooo hungry."
line big_eyes     "All the better to see you with, my dear!"
line come_closer  "Come a little closer..."
line whos_there   "Huh?! Who's there?"
line big_bad_wolf "I'm the big... bad... wolf."
rm -rf "$TMP"
