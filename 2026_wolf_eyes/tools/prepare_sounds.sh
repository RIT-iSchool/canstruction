#!/usr/bin/env bash
# Turns the downloaded originals in sound_sources/ into the trimmed, volume-matched
# clips the eyes play from sounds/. Needs ffmpeg. Run on the Mac (or the Pi) from anywhere:
#   bash tools/prepare_sounds.sh
set -euo pipefail
cd "$(dirname "$0")/.."
SRC=sound_sources
OUT=sounds
mkdir -p "$OUT"/{growl,howl,sniff,snore,voice}

# clip <source> <dest> <loudness LUFS> [start] [length] [fade-out seconds]
clip() {
  local src=$1 dst=$2 lufs=$3 ss=${4:-0} len=${5:-0} fade=${6:-0.15}
  local args=(-v error -y -ss "$ss" -i "$src")
  [ "$len" != 0 ] && args+=(-t "$len")
  local dur
  dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$src")
  [ "$len" != 0 ] && dur=$len || dur=$(python3 -c "print(max(0.2, $dur - $ss))")
  local fo
  fo=$(python3 -c "print(max(0, $dur - $fade))")
  ffmpeg "${args[@]}" -ac 1 -ar 44100 \
    -af "silenceremove=start_periods=1:start_threshold=-55dB,afade=t=in:d=0.02,afade=t=out:st=$fo:d=$fade,loudnorm=I=$lufs:TP=-1.5:LRA=11" \
    -c:a pcm_s16le "$dst"
  echo "  $dst"
}

echo "Growls"
clip $SRC/mixkit/growl_giant-dog-aggressive-growl_59.mp3      $OUT/growl/growl_giant.wav -14
clip $SRC/mixkit/growl_angry-agitated-dog-growling_53.mp3     $OUT/growl/growl_agitated.wav -14 0 3.4
clip $SRC/mixkit/growl_aggressive-medium-dog-growling_56.mp3  $OUT/growl/growl_medium.wav -14
clip $SRC/mixkit/growl_defensive-big-dog-snarl_50.mp3         $OUT/growl/snarl_big.wav -14 0 5.5
clip $SRC/mixkit/growl_hellhound-monster-growl_3014.mp3       $OUT/growl/growl_hellhound.wav -14 0 2.2

echo "Howls"
clip $SRC/mixkit/howl_wolf-howling_1775.mp3        $OUT/howl/howl_wolf.wav -15 0 7.0 1.5
clip $SRC/mixkit/howl_lone-wolf-howling_1729.mp3   $OUT/howl/howl_lone.wav -15 0 4.5 1.2
clip $SRC/mixkit/howl_wolves-pack-howling_1776.mp3 $OUT/howl/howl_pack.wav -15 0 4.8 1.2
clip $SRC/mixkit/howl_cartoon-wolf-howling_1774.mp3 $OUT/howl/howl_cartoon.wav -15 0 1.0 0.3
clip $SRC/wikimedia/Wolf_howls.ogg                 $OUT/howl/howl_real_1.wav -15 0   7.0 1.5
clip $SRC/wikimedia/Wolf_howls.ogg                 $OUT/howl/howl_real_2.wav -15 14  7.0 1.5
clip $SRC/wikimedia/Rallying.ogg                   $OUT/howl/howl_rally.wav -15 3   8.0 1.5

echo "Sniffs / huffs"
clip $SRC/mixkit/sniff_dog-sniffing-the-ground_49.mp3 $OUT/sniff/sniff_ground.wav -17
clip $SRC/mixkit/sniff_big-tired-dog-panting_52.mp3   $OUT/sniff/pant_tired.wav -17 0 3.4
clip $SRC/wikimedia/Dragon_wheeze.ogg                  $OUT/sniff/huff_wheeze.wav -17 0 0 0.1

echo "Snores"
clip $SRC/mixkit/sniff_pug-heavy-breathing_57.mp3 $OUT/snore/snore_pug.wav -18 0 5.5 0.8
clip $SRC/wikimedia/Heavy_breathing_3.ogg         $OUT/snore/snore_breath.wav -18 22 9.0 1.0

echo "Done. Voice lines are made separately by tools/make_voices.sh"
