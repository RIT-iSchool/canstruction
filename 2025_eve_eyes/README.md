# 2025 EVE eyes

Last year's eyes for EVE (from WALL-E): one eye per screen, playing pre-rendered
After Effects clips (blink, angry, sad, "seriously", surprised) with WALL-E/EVE sounds.

- **`main.py` is the final version.** It loops 4–5 blinks, holds 15 s, plays one random
  emotion clip, holds 15 s, and repeats, with a random sound every 10 s. It also disables
  the laptop touchpad (Linux/X11) while running and re-enables it on exit.
- `mai.py`, `final.py`, `finalized.py`: earlier versions of the same idea.
- `main3.py`: webcam face-tracking experiment (mediapipe); the eye follows people.
- `dirp.py`: webcam emotion-detection experiment (DeepFace).
- `one-eye-*.mp4`: the 1024×600 single-eye clips the scripts play (`*2.mp4` / `blink3` are the final renders).
- `outputs/`: earlier full-size 1920×1080 renders.

Run: `pip install opencv-python numpy pygame` then `python3 main.py` (press `q` to quit).
The After Effects project files aren't included.
