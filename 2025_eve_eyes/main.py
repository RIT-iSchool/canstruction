import cv2
import numpy as np
import tkinter as tk
import pygame
import time
import os
import random
import subprocess
import atexit
import signal
import sys

# --------------------------
# Touchpad control (Linux/X11)
# --------------------------
SESSION_TYPE = os.environ.get("XDG_SESSION_TYPE", "").lower()
TOUCHPAD_IDS = []

def _run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.STDOUT)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""

def detect_touchpad_ids():
    """
    Return a list of xinput IDs for devices whose name contains 'touchpad' (case-insensitive).
    Only works on X11 sessions. On Wayland this will return [].
    """
    if SESSION_TYPE != "x11":
        print("ℹ️ Touchpad control: Skipping (session type is not X11).")
        return []
    listing = _run("xinput list --short")
    ids = []
    for line in listing.splitlines():
        if "touchpad" in line.lower() and "id=" in line.lower():
            # Extract number after 'id='
            try:
                after = line.lower().split("id=")[1]
                dev_id = after.split()[0]
                if dev_id.isdigit():
                    ids.append(dev_id)
            except Exception:
                continue
    if ids:
        print(f"✅ Touchpad devices detected (xinput IDs): {', '.join(ids)}")
    else:
        print("❌ No touchpad devices detected via xinput.")
    return ids

def disable_touchpads(ids):
    if not ids:
        return
    for did in set(ids):
        _run(f"xinput disable {did}")
    print("🛑 Touchpad disabled.")

def enable_touchpads(ids):
    if not ids:
        return
    for did in set(ids):
        _run(f"xinput enable {did}")
    print("✅ Touchpad re-enabled.")

def _restore_on_exit():
    enable_touchpads(TOUCHPAD_IDS)

def _signal_handler(signum, frame):
    _restore_on_exit()
    # Allow graceful shutdown
    try:
        cv2.destroyAllWindows()
    except Exception:
        pass
    sys.exit(0)

# Register cleanup
atexit.register(_restore_on_exit)
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# --- Get actual display size automatically ---
root = tk.Tk()
display_width = root.winfo_screenwidth()
display_height = root.winfo_screenheight()
root.destroy()
print(f"Detected Display: {display_width}x{display_height}")

# Disable touchpad(s) now (Linux/X11)
TOUCHPAD_IDS = detect_touchpad_ids()
disable_touchpads(TOUCHPAD_IDS)

# --- Set second monitor X offset (usually = primary width) ---
MON2_X = display_width  # adjust if your second monitor starts elsewhere

# --- Emotion → Video mapping ---
emotion_videos = {
    'neutral': 'one-eye-blink3.mp4',
    'happy':   'one-eye-seriously2.mp4',
    'angry':   'one-eye-angry2.mp4',
    'sad':     'one-eye-sad2.mp4',
}

# --- Settings ---
video_width = display_width
video_height = display_height
eye_frame_width = video_width
eye_frame_height = video_height
EYE_TILT_DEGREES = 10  # tilt angle (positive = rotate CCW)

# --- Audio files ---
main_audio = 'wall-e_1.mp3'
alt_audios = ['eve.mp3', 'wall-e_1.mp3', 'directive.mp3']  # optional alternates
PLAY_INTERVAL = 10  # seconds

# --- Initialize pygame mixer ---
pygame.mixer.init()
last_audio_time = 0
current_audio = main_audio

def play_audio(file_path):
    """Play an MP3 file if it exists."""
    if os.path.isfile(file_path):
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        print(f"🎵 Playing audio: {file_path}")
    else:
        print(f"Audio file not found: {file_path}")

# --- Eye compositor ---
def create_individual_eyes(frame_vid, face_delta_x=0):
    """Rotate and split one video frame into left and right eyes.

    FIX: Right eye is now ONLY mirrored (no extra rotation),
    so eyes are symmetrically tilted ±EYE_TILT_DEGREES.
    """
    single_eye_canvas_w = eye_frame_width // 2
    target_h = eye_frame_height

    # --- Rotate base frame once (+θ) ---
    (h, w) = frame_vid.shape[:2]
    center = (w // 2, h // 2)
    rot_mat = cv2.getRotationMatrix2D(center, EYE_TILT_DEGREES, 1.0)
    frame_vid = cv2.warpAffine(
        frame_vid, rot_mat, (w, h),
        flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
    )

    # Preserve aspect ratio
    src_h, src_w = frame_vid.shape[:2]
    new_w = int(src_w * (target_h / src_h))
    if new_w > single_eye_canvas_w:
        new_w = single_eye_canvas_w
        target_h = int(src_h * (single_eye_canvas_w / src_w))

    single_eye_resized = cv2.resize(frame_vid, (new_w, target_h))

    # Create blank frames
    left_frame = np.zeros((eye_frame_height, single_eye_canvas_w, 3), dtype=np.uint8)
    right_frame = np.zeros((eye_frame_height, single_eye_canvas_w, 3), dtype=np.uint8)

    # Horizontal tracking offset (clamped)
    offset = int(face_delta_x)
    offset = max(-(single_eye_canvas_w // 4), min(single_eye_canvas_w // 4, offset))

    # Centered positions (clamped to avoid spill)
    x_pos = (single_eye_canvas_w - new_w) // 2 + offset
    y_pos = (eye_frame_height - target_h) // 2
    x_pos = max(0, min(single_eye_canvas_w - new_w, x_pos))
    y_pos = max(0, min(eye_frame_height - target_h, y_pos))

    # Left eye: already +θ
    left_frame[y_pos:y_pos + target_h, x_pos:x_pos + new_w] = single_eye_resized

    # Right eye: mirror only (visual tilt becomes −θ)
    right_eye = cv2.flip(single_eye_resized, 1)
    right_frame[y_pos:y_pos + target_h, x_pos:x_pos + new_w] = right_eye

    return left_frame, right_frame

# --- Create fullscreen windows ---
cv2.namedWindow("Left Eye", cv2.WINDOW_NORMAL)
cv2.namedWindow("Right Eye", cv2.WINDOW_NORMAL)
cv2.moveWindow("Left Eye", 0, 0)
cv2.moveWindow("Right Eye", MON2_X, 0)
cv2.setWindowProperty("Left Eye",  cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setWindowProperty("Right Eye", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# --- Cycle configuration ---
PAUSE_AFTER_NEUTRAL = 15   # seconds (hold after the last blink)
PAUSE_AFTER_EMOTION = 15   # seconds (hold after emotion)
BLINKS_MIN, BLINKS_MAX = 4, 5
BETWEEN_BLINK_GAP = (0.25, 0.60)
NON_NEUTRAL_LIST = ['happy', 'angry', 'sad']

# --- State machine ---
phase = "playing"
current_emotion = "neutral"
cap = cv2.VideoCapture(emotion_videos[current_emotion])

pause_end_time = None
between_blink_end_time = None
last_left = None
last_right = None
face_delta_x = 0

neutral_blinks_target = random.randint(BLINKS_MIN, BLINKS_MAX)
neutral_blinks_done = 0
last_non_neutral = None

# --- Play main audio immediately ---
play_audio(main_audio)
last_audio_time = time.time()

print("Cycle: NEUTRAL (blink x4–5 with tiny gaps) -> pause 15s -> EMOTION (once) -> pause 15s -> repeat")

def pick_next_non_neutral(last_choice):
    choices = [e for e in NON_NEUTRAL_LIST if e != last_choice]
    return random.choice(choices) if choices else random.choice(NON_NEUTRAL_LIST)

try:
    while True:
        now = time.time()

        # --- Video Logic ---
        if phase == "playing":
            ret, frame_vid = cap.read()
            if not ret:
                cap.release()
                if current_emotion == "neutral":
                    neutral_blinks_done += 1
                    if neutral_blinks_done < neutral_blinks_target:
                        between_blink_end_time = now + random.uniform(*BETWEEN_BLINK_GAP)
                        phase = "between_blinks"
                        print(f"Blink {neutral_blinks_done}/{neutral_blinks_target} done.")
                    else:
                        pause_end_time = now + PAUSE_AFTER_NEUTRAL
                        phase = "paused"
                        print(f"All blinks done ({neutral_blinks_done}). Pausing for {PAUSE_AFTER_NEUTRAL}s.")
                else:
                    pause_end_time = now + PAUSE_AFTER_EMOTION
                    phase = "paused"
                    print(f"Emotion '{current_emotion}' done. Pausing for {PAUSE_AFTER_EMOTION}s.")
            else:
                left_eye_frame, right_eye_frame = create_individual_eyes(frame_vid, face_delta_x)
                last_left, last_right = left_eye_frame, right_eye_frame
                cv2.imshow("Left Eye", left_eye_frame)
                cv2.imshow("Right Eye", right_eye_frame)

        elif phase == "between_blinks":
            if last_left is not None and last_right is not None:
                cv2.imshow("Left Eye", last_left)
                cv2.imshow("Right Eye", last_right)
            if now >= between_blink_end_time:
                cap = cv2.VideoCapture(emotion_videos['neutral'])
                phase = "playing"

        elif phase == "paused":
            if last_left is not None and last_right is not None:
                cv2.imshow("Left Eye", last_left)
                cv2.imshow("Right Eye", last_right)

            if now >= pause_end_time:
                if current_emotion == "neutral":
                    next_emotion = pick_next_non_neutral(last_non_neutral)
                    last_non_neutral = next_emotion
                    current_emotion = next_emotion
                    cap = cv2.VideoCapture(emotion_videos[current_emotion])
                    phase = "playing"
                    print(f"Switched to '{current_emotion}'.")
                else:
                    current_emotion = "neutral"
                    neutral_blinks_target = random.randint(BLINKS_MIN, BLINKS_MAX)
                    neutral_blinks_done = 0
                    cap = cv2.VideoCapture(emotion_videos[current_emotion])
                    phase = "playing"
                    print(f"Back to NEUTRAL blinks x{neutral_blinks_target}.")
                last_left = None
                last_right = None

        # --- Random Audio Switching ---
        if now - last_audio_time > PLAY_INTERVAL:
            new_audio = random.choice(alt_audios)
            play_audio(new_audio)
            last_audio_time = now

        FRAME_DELAY = 35  # Slow down playback slightly
        if cv2.waitKey(FRAME_DELAY) & 0xFF == ord('q'):
            break

finally:
    # --- Cleanup: re-enable touchpad(s) and release resources ---
    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()
    _restore_on_exit()



# import cv2
# import numpy as np
# import tkinter as tk
# import pygame
# import time
# import os
# import random

# # --- Get actual display size automatically ---
# root = tk.Tk()
# display_width = root.winfo_screenwidth()
# display_height = root.winfo_screenheight()
# root.destroy()
# print(f"Detected Display: {display_width}x{display_height}")

# # --- Set second monitor X offset (usually = primary width) ---
# MON2_X = display_width  # adjust if your second monitor starts elsewhere

# # --- Emotion → Video mapping ---
# emotion_videos = {
#     'neutral': 'one-eye-blink3.mp4',
#     'happy':   'one-eye-seriously2.mp4',
#     'angry':   'one-eye-angry2.mp4',
#     'sad':     'one-eye-sad2.mp4',
# }

# # --- Settings ---
# video_width = display_width
# video_height = display_height
# eye_frame_width = video_width
# eye_frame_height = video_height
# EYE_TILT_DEGREES = 10  # tilt angle (positive = rotate CCW)

# # --- Audio files ---
# main_audio = 'wall-e_1.mp3'
# alt_audios = ['eve.mp3', 'wall-e_1.mp3', 'directive.mp3']  # optional alternates
# PLAY_INTERVAL = 10  # seconds

# # --- Initialize pygame mixer ---
# pygame.mixer.init()
# last_audio_time = 0
# current_audio = main_audio

# def play_audio(file_path):
#     """Play an MP3 file if it exists."""
#     if os.path.isfile(file_path):
#         pygame.mixer.music.load(file_path)
#         pygame.mixer.music.play()
#         print(f"🎵 Playing audio: {file_path}")
#     else:
#         print(f"Audio file not found: {file_path}")

# # --- Eye compositor ---
# def create_individual_eyes(frame_vid, face_delta_x=0):
#     """Rotate and split one video frame into left and right eyes.

#     FIX: Right eye is now ONLY mirrored (no extra rotation),
#     so eyes are symmetrically tilted ±EYE_TILT_DEGREES.
#     """
#     single_eye_canvas_w = eye_frame_width // 2
#     target_h = eye_frame_height

#     # --- Rotate base frame once (+θ) ---
#     (h, w) = frame_vid.shape[:2]
#     center = (w // 2, h // 2)
#     rot_mat = cv2.getRotationMatrix2D(center, EYE_TILT_DEGREES, 1.0)
#     frame_vid = cv2.warpAffine(
#         frame_vid, rot_mat, (w, h),
#         flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE
#     )

#     # Preserve aspect ratio
#     src_h, src_w = frame_vid.shape[:2]
#     new_w = int(src_w * (target_h / src_h))
#     if new_w > single_eye_canvas_w:
#         new_w = single_eye_canvas_w
#         target_h = int(src_h * (single_eye_canvas_w / src_w))

#     single_eye_resized = cv2.resize(frame_vid, (new_w, target_h))

#     # Create blank frames
#     left_frame = np.zeros((eye_frame_height, single_eye_canvas_w, 3), dtype=np.uint8)
#     right_frame = np.zeros((eye_frame_height, single_eye_canvas_w, 3), dtype=np.uint8)

#     # Horizontal tracking offset (clamped)
#     offset = int(face_delta_x)
#     offset = max(-(single_eye_canvas_w // 4), min(single_eye_canvas_w // 4, offset))

#     # Centered positions (clamped to avoid spill)
#     x_pos = (single_eye_canvas_w - new_w) // 2 + offset
#     y_pos = (eye_frame_height - target_h) // 2
#     x_pos = max(0, min(single_eye_canvas_w - new_w, x_pos))
#     y_pos = max(0, min(eye_frame_height - target_h, y_pos))

#     # Left eye: already +θ
#     left_frame[y_pos:y_pos + target_h, x_pos:x_pos + new_w] = single_eye_resized

#     # Right eye: mirror only (visual tilt becomes −θ)
#     right_eye = cv2.flip(single_eye_resized, 1)
#     right_frame[y_pos:y_pos + target_h, x_pos:x_pos + new_w] = right_eye

#     return left_frame, right_frame

# # --- Create fullscreen windows ---
# cv2.namedWindow("Left Eye", cv2.WINDOW_NORMAL)
# cv2.namedWindow("Right Eye", cv2.WINDOW_NORMAL)
# cv2.moveWindow("Left Eye", 0, 0)
# cv2.moveWindow("Right Eye", MON2_X, 0)
# cv2.setWindowProperty("Left Eye",  cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
# cv2.setWindowProperty("Right Eye", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# # --- Cycle configuration ---
# PAUSE_AFTER_NEUTRAL = 15   # seconds (hold after the last blink)
# PAUSE_AFTER_EMOTION = 15   # seconds (hold after emotion)
# BLINKS_MIN, BLINKS_MAX = 4, 5
# BETWEEN_BLINK_GAP = (0.25, 0.60)
# NON_NEUTRAL_LIST = ['happy', 'angry', 'sad']

# # --- State machine ---
# phase = "playing"
# current_emotion = "neutral"
# cap = cv2.VideoCapture(emotion_videos[current_emotion])

# pause_end_time = None
# between_blink_end_time = None
# last_left = None
# last_right = None
# face_delta_x = 0

# neutral_blinks_target = random.randint(BLINKS_MIN, BLINKS_MAX)
# neutral_blinks_done = 0
# last_non_neutral = None

# # --- Play main audio immediately ---
# play_audio(main_audio)
# last_audio_time = time.time()

# print("Cycle: NEUTRAL (blink x4–5 with tiny gaps) -> pause 15s -> EMOTION (once) -> pause 15s -> repeat")

# def pick_next_non_neutral(last_choice):
#     choices = [e for e in NON_NEUTRAL_LIST if e != last_choice]
#     return random.choice(choices) if choices else random.choice(NON_NEUTRAL_LIST)

# while True:
#     now = time.time()

#     # --- Video Logic ---
#     if phase == "playing":
#         ret, frame_vid = cap.read()
#         if not ret:
#             cap.release()
#             if current_emotion == "neutral":
#                 neutral_blinks_done += 1
#                 if neutral_blinks_done < neutral_blinks_target:
#                     between_blink_end_time = now + random.uniform(*BETWEEN_BLINK_GAP)
#                     phase = "between_blinks"
#                     print(f"Blink {neutral_blinks_done}/{neutral_blinks_target} done.")
#                 else:
#                     pause_end_time = now + PAUSE_AFTER_NEUTRAL
#                     phase = "paused"
#                     print(f"All blinks done ({neutral_blinks_done}). Pausing for {PAUSE_AFTER_NEUTRAL}s.")
#             else:
#                 pause_end_time = now + PAUSE_AFTER_EMOTION
#                 phase = "paused"
#                 print(f"Emotion '{current_emotion}' done. Pausing for {PAUSE_AFTER_EMOTION}s.")
#         else:
#             left_eye_frame, right_eye_frame = create_individual_eyes(frame_vid, face_delta_x)
#             last_left, last_right = left_eye_frame, right_eye_frame
#             cv2.imshow("Left Eye", left_eye_frame)
#             cv2.imshow("Right Eye", right_eye_frame)

#     elif phase == "between_blinks":
#         if last_left is not None and last_right is not None:
#             cv2.imshow("Left Eye", last_left)
#             cv2.imshow("Right Eye", last_right)
#         if now >= between_blink_end_time:
#             cap = cv2.VideoCapture(emotion_videos['neutral'])
#             phase = "playing"

#     elif phase == "paused":
#         if last_left is not None and last_right is not None:
#             cv2.imshow("Left Eye", last_left)
#             cv2.imshow("Right Eye", last_right)

#         if now >= pause_end_time:
#             if current_emotion == "neutral":
#                 next_emotion = pick_next_non_neutral(last_non_neutral)
#                 last_non_neutral = next_emotion
#                 current_emotion = next_emotion
#                 cap = cv2.VideoCapture(emotion_videos[current_emotion])
#                 phase = "playing"
#                 print(f"Switched to '{current_emotion}'.")
#             else:
#                 current_emotion = "neutral"
#                 neutral_blinks_target = random.randint(BLINKS_MIN, BLINKS_MAX)
#                 neutral_blinks_done = 0
#                 cap = cv2.VideoCapture(emotion_videos[current_emotion])
#                 phase = "playing"
#                 print(f"Back to NEUTRAL blinks x{neutral_blinks_target}.")
#             last_left = None
#             last_right = None

#     # --- Random Audio Switching ---
#     if now - last_audio_time > PLAY_INTERVAL:
#         new_audio = random.choice(alt_audios)
#         play_audio(new_audio)
#         last_audio_time = now

#     FRAME_DELAY = 35  # Slow down playback slightly
#     if cv2.waitKey(FRAME_DELAY) & 0xFF == ord('q'):
#         break

# # --- Cleanup ---
# if cap is not None:
#     cap.release()
# cv2.destroyAllWindows()
