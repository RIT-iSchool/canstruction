#!/usr/bin/env python3

import os
import sys
import time
import random
import shutil
import subprocess
from argparse import ArgumentParser

SOUND_DIR_NAME = 'sounds'

SOUND_FILES = []

MIN_INTERVAL = 30  # seconds
MAX_INTERVAL = 60  # seconds


def find_player():
    candidates = [
        ("mpg123", ["mpg123"]),
        ("mpg321", ["mpg321"]),
        ("omxplayer", ["omxplayer"]),
        ("cvlc", ["cvlc", "--play-and-exit"]),
        ("afplay", ["afplay"]),  # macOS fallback
    ]
    for name, cmd in candidates:
        if shutil.which(name):
            return name, cmd
    # No system player found
    return None, None


def play_with_subprocess(cmd_template, path):
    cmd = list(cmd_template) + [path]
    try:
        subprocess.run(cmd, check=False)
    except Exception as e:
        print(f"Error running player {cmd[0]}: {e}", file=sys.stderr)


def play_with_pygame(path):
    try:
        import pygame # type: ignore
    except Exception as e:
        raise RuntimeError("pygame is not available: %s" % e)

    pygame.mixer.init()
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    # Wait until playback finishes
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)


def build_sound_list(sound_dir, configured_list, scan=False):
    files = []
    if scan or not configured_list:
        # discover mp3 files in directory
        if os.path.isdir(sound_dir):
            for p in sorted(os.listdir(sound_dir)):
                if p.lower().endswith('.mp3'):
                    files.append(p)
    else:
        files = list(configured_list)

    # normalize and filter
    resolved = []
    for name in files:
        full = os.path.join(sound_dir, name)
        if os.path.isfile(full):
            resolved.append(full)
        else:
            print(f"Warning: sound file not found: {full}")

    return resolved


def main():
    parser = ArgumentParser(description="Play random sounds from sounds/ folder")
    parser.add_argument('--scan', action='store_true', help='scan sounds/ for mp3 files instead of using SOUND_FILES')
    parser.add_argument('--min', type=int, default=MIN_INTERVAL, help='minimum interval between plays (seconds)')
    parser.add_argument('--max', type=int, default=MAX_INTERVAL, help='maximum interval between plays (seconds)')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    sound_dir = os.path.join(script_dir, SOUND_DIR_NAME)

    if args.min < 0 or args.max < args.min:
        print("Invalid interval range", file=sys.stderr)
        sys.exit(2)

    sound_list = build_sound_list(sound_dir, SOUND_FILES, scan=args.scan)
    if not sound_list:
        print("No valid sound files found. Put mp3 files in the 'sounds' folder or run with --scan.")
        sys.exit(1)

    player_name, player_cmd = find_player()
    use_pygame = False
    if player_name:
        print(f"Using system player: {player_name}")
    else:
        try:
            import pygame  # type: ignore
            use_pygame = True
            print("Using pygame.mixer as fallback player")
        except Exception:
            print("No suitable system player found and pygame is not available.")
            print("Install mpg123 (sudo apt install mpg123) or pygame (pip install pygame) and retry.")
            sys.exit(1)

    print(f"Found {len(sound_list)} sound(s), playing between {args.min}s and {args.max}s intervals.")

    try:
        while True:
            path = random.choice(sound_list)
            print(f"Playing: {os.path.basename(path)}")
            if use_pygame:
                play_with_pygame(path)
            else:
                play_with_subprocess(player_cmd, path)

            wait = random.uniform(args.min, args.max)
            print(f"Waiting {wait:.1f} seconds before next sound...")
            time.sleep(wait)
    except KeyboardInterrupt:
        print('\nStopped by user')


if __name__ == '__main__':
    main()
