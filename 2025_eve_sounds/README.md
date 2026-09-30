# play_eve_sounds.py

Small utility to play a random MP3 from a local `sounds/` folder at a random
interval between 30 and 60 seconds. Intended to run on a Raspberry Pi but
works on other Linux/macOS systems too.

### Setup

Install a system player (recommended) or pygame (fallback).

   On Raspberry Pi (Raspbian / Raspberry Pi OS):

   ```bash
   sudo apt update
   sudo apt install -y mpg123
   # optional: sudo apt install -y omxplayer vlc
   ```

   Or install pygame (if you prefer Python playback):

   ```bash
   python3 -m pip install --user pygame
   ```

### Usage

Make the script executable and run it:

```bash
chmod +x play_random_sound.py
./play_random_sound.py --scan
# or explicitly use the built-in SOUND_FILES list
./play_random_sound.py
```

### Options
- `--scan` - ignore the `SOUND_FILES` list in the script and auto-discover
  `.mp3` files inside `sounds/`.
- `--min N` and `--max N` - override the minimum and maximum wait
  intervals (seconds).

### Notes
- The script prefers system players (mpg123, mpg321, omxplayer, cvlc). If
  none are available it attempts to use `pygame.mixer` as a fallback.
- Stop the script with Ctrl-C.

### Example

```bash
# Play random sounds discovered in sounds/ with default 30-60s intervals
./play_random_sound.py --scan

# Play using 10-20 second intervals instead (for testing)
./play_random_sound.py --scan --min 10 --max 20
```

### Troubleshooting
- If you see "No valid sound files found" ensure files are named
  `*.mp3` and placed in the `sounds/` directory next to the script.
- If the system player is missing, install `mpg123` or `vlc` or install
  `pygame` with pip.

### Starting the script automatically
1. Create `/etc/systemd/system/play_random_sound.service` with the following:
```
[Unit]
Description=Play random EVE sounds
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/path/to/project
ExecStart=/usr/bin/python3 /home/pi/path/to/project/play_eve_sound.py --scan
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
# Environment=PYTHONUNBUFFERED=1  # optionally useful for immediate logs

[Install]
WantedBy=multi-user.target
```

2. Enable and start the service
```
sudo systemctl daemon-reload
sudo systemctl enable --now play_random_sound.service
```