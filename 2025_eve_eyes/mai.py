import cv2
import numpy as np
import tkinter as tk
import pygame
import time
import os
import random

# --- Get actual display size automatically ---
root = tk.Tk()
display_width = root.winfo_screenwidth()
display_height = root.winfo_screenheight()
root.destroy()
print(f"Detected Display: {display_width}x{display_height}")

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

# --- Audio (optional) ---
main_audio = 'wall-e_1.mp3'
def play_audio(file_path):
    if os.path.isfile(file_path):
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            print(f"Starting audio: {file_path}")
        except Exception as e:
            print(f"Audio init/play failed: {e}")
    else:
        print(f"Audio file not found: {file_path}")

# --- Eye compositor ---
def create_individual_eyes(frame_vid, face_delta_x=0):
    single_eye_canvas_w = eye_frame_width // 2
    target_h = eye_frame_height

    src_h, src_w = frame_vid.shape[:2]
    new_w = int(src_w * (target_h / src_h))
    if new_w > single_eye_canvas_w:
        new_w = single_eye_canvas_w
        target_h = int(src_h * (single_eye_canvas_w / src_w))

    single_eye_resized = cv2.resize(frame_vid, (new_w, target_h))

    left_frame = np.zeros((eye_frame_height, single_eye_canvas_w, 3), dtype=np.uint8)
    right_frame = np.zeros((eye_frame_height, single_eye_canvas_w, 3), dtype=np.uint8)

    offset = int(face_delta_x)
    offset = max(-(single_eye_canvas_w // 4), min(single_eye_canvas_w // 4, offset))

    x_pos = (single_eye_canvas_w - new_w) // 2 + offset
    y_pos = (eye_frame_height - target_h) // 2

    left_frame[y_pos:y_pos + target_h, x_pos:x_pos + new_w] = single_eye_resized
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
BLINKS_MIN, BLINKS_MAX = 4, 5  # natural blink count range
BETWEEN_BLINK_GAP = (0.25, 0.60)  # short natural pause between blink clips

NON_NEUTRAL_LIST = ['happy', 'angry', 'sad']

# --- State machine ---
# phases: "playing" (reading frames), "paused" (holding last frame), "between_blinks" (short gap before next blink clip)
phase = "playing"
current_emotion = "neutral"
cap = cv2.VideoCapture(emotion_videos[current_emotion])

pause_end_time = None
between_blink_end_time = None
last_left = None
last_right = None
face_delta_x = 0

# neutral blink loop targets
neutral_blinks_target = random.randint(BLINKS_MIN, BLINKS_MAX)
neutral_blinks_done = 0

last_non_neutral = None  # avoid immediate repetition

# Optional: play audio once on startup
play_audio(main_audio)

print("Cycle: NEUTRAL (blink x4–5 with tiny gaps) -> pause 25s -> EMOTION (once) -> pause 15s -> repeat")

def pick_next_non_neutral(last_choice):
    choices = [e for e in NON_NEUTRAL_LIST if e != last_choice]
    return random.choice(choices) if choices else random.choice(NON_NEUTRAL_LIST)

while True:
    now = time.time()

    if phase == "playing":
        ret, frame_vid = cap.read()
        if not ret:
            # Clip finished
            cap.release()
            if current_emotion == "neutral":
                # Finished one blink
                neutral_blinks_done += 1
                if neutral_blinks_done < neutral_blinks_target:
                    # Natural tiny gap between blink clips
                    between_blink_end_time = now + random.uniform(*BETWEEN_BLINK_GAP)
                    phase = "between_blinks"
                    # keep showing last frame during gap
                    print(f"Blink {neutral_blinks_done}/{neutral_blinks_target} done. Short gap before next blink.")
                else:
                    # Completed all blinks → long pause
                    pause_end_time = now + PAUSE_AFTER_NEUTRAL
                    phase = "paused"
                    print(f"All blinks done ({neutral_blinks_done}). Pausing for {PAUSE_AFTER_NEUTRAL}s.")
            else:
                # Non-neutral played once → pause
                pause_end_time = now + PAUSE_AFTER_EMOTION
                phase = "paused"
                print(f"Emotion '{current_emotion}' done. Pausing for {PAUSE_AFTER_EMOTION}s.")
        else:
            # Render / show current frame
            left_eye_frame, right_eye_frame = create_individual_eyes(frame_vid, face_delta_x)
            last_left, last_right = left_eye_frame, right_eye_frame
            cv2.imshow("Left Eye", left_eye_frame)
            cv2.imshow("Right Eye", right_eye_frame)

    elif phase == "between_blinks":
        # show last frame during tiny gap
        if last_left is not None and last_right is not None:
            cv2.imshow("Left Eye", last_left)
            cv2.imshow("Right Eye", last_right)
        if now >= between_blink_end_time:
            # start next blink clip
            cap = cv2.VideoCapture(emotion_videos['neutral'])
            phase = "playing"

    elif phase == "paused":
        # Keep showing the last frame during long pauses
        if last_left is not None and last_right is not None:
            cv2.imshow("Left Eye", last_left)
            cv2.imshow("Right Eye", last_right)

        if now >= pause_end_time:
            # Time to switch sequences
            if current_emotion == "neutral":
                # Next: one non-neutral
                next_emotion = pick_next_non_neutral(last_non_neutral)
                last_non_neutral = next_emotion
                current_emotion = next_emotion
                cap = cv2.VideoCapture(emotion_videos[current_emotion])
                phase = "playing"
                print(f"Switched to '{current_emotion}' (play once).")
            else:
                # Back to neutral blink block
                current_emotion = "neutral"
                neutral_blinks_target = random.randint(BLINKS_MIN, BLINKS_MAX)
                neutral_blinks_done = 0
                cap = cv2.VideoCapture(emotion_videos[current_emotion])
                phase = "playing"
                print(f"Back to NEUTRAL blinks x{neutral_blinks_target}.")

            # reset last-frame caches for new clip
            last_left = None
            last_right = None

    FRAME_DELAY = 35  # milliseconds between frames (increase to slow down)
    
    # Quit key
    if cv2.waitKey(FRAME_DELAY) & 0xFF == ord('q'):
        break

# Cleanup
if cap is not None:
    cap.release()
cv2.destroyAllWindows()



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

# # --- Audio (optional) ---
# main_audio = 'wall-e_1.mp3'
# def play_audio(file_path):
#     if os.path.isfile(file_path):
#         try:
#             pygame.mixer.init()
#             pygame.mixer.music.load(file_path)
#             pygame.mixer.music.play()
#             print(f"Starting audio: {file_path}")
#         except Exception as e:
#             print(f"Audio init/play failed: {e}")
#     else:
#         print(f"Audio file not found: {file_path}")

# # --- Eye compositor ---
# def create_individual_eyes(frame_vid, face_delta_x=0):
#     single_eye_canvas_w = eye_frame_width // 2
#     target_h = eye_frame_height

#     src_h, src_w = frame_vid.shape[:2]
#     new_w = int(src_w * (target_h / src_h))
#     if new_w > single_eye_canvas_w:
#         new_w = single_eye_canvas_w
#         target_h = int(src_h * (single_eye_canvas_w / src_w))

#     single_eye_resized = cv2.resize(frame_vid, (new_w, target_h))

#     left_frame = np.zeros((eye_frame_height, single_eye_canvas_w, 3), dtype=np.uint8)
#     right_frame = np.zeros((eye_frame_height, single_eye_canvas_w, 3), dtype=np.uint8)

#     offset = int(face_delta_x)
#     offset = max(-(single_eye_canvas_w // 4), min(single_eye_canvas_w // 4, offset))

#     x_pos = (single_eye_canvas_w - new_w) // 2 + offset
#     y_pos = (eye_frame_height - target_h) // 2

#     left_frame[y_pos:y_pos + target_h, x_pos:x_pos + new_w] = single_eye_resized
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
# PAUSE_AFTER_NEUTRAL = 25  # seconds
# PAUSE_AFTER_EMOTION = 15  # seconds
# NON_NEUTRAL_LIST = ['happy', 'angry', 'sad']

# # --- State machine ---
# # phases: "playing" (reading frames) or "paused" (show last frame)
# phase = "playing"
# current_emotion = "neutral"  # start with blink
# cap = cv2.VideoCapture(emotion_videos[current_emotion])
# pause_end_time = None
# last_left = None
# last_right = None
# face_delta_x = 0  # keep your existing placeholder if you add tracking later

# # Optional: play audio once on startup
# play_audio(main_audio)

# print("Cycle: NEUTRAL (play once) -> pause 25s -> EMOTION (play once) -> pause 15s -> repeat")

# while True:
#     if phase == "playing":
#         ret, frame_vid = cap.read()
#         if not ret:
#             # Video finished: switch to pause on the last shown frame
#             cap.release()
#             if current_emotion == "neutral":
#                 pause_duration = PAUSE_AFTER_NEUTRAL
#             else:
#                 pause_duration = PAUSE_AFTER_EMOTION
#             pause_end_time = time.time() + pause_duration
#             phase = "paused"
#             print(f"Finished '{current_emotion}'. Pausing for {pause_duration} seconds.")
#         else:
#             # Render / show current frame
#             left_eye_frame, right_eye_frame = create_individual_eyes(frame_vid, face_delta_x)
#             last_left, last_right = left_eye_frame, right_eye_frame  # remember last frame for pause display
#             cv2.imshow("Left Eye", left_eye_frame)
#             cv2.imshow("Right Eye", right_eye_frame)

#     elif phase == "paused":
#         # Keep showing the last frame during pause
#         if last_left is not None and last_right is not None:
#             cv2.imshow("Left Eye", last_left)
#             cv2.imshow("Right Eye", last_right)

#         if time.time() >= pause_end_time:
#             # Time to pick the next emotion and start playing again
#             if current_emotion == "neutral":
#                 next_emotion = random.choice(NON_NEUTRAL_LIST)
#             else:
#                 next_emotion = "neutral"

#             current_emotion = next_emotion
#             cap = cv2.VideoCapture(emotion_videos[current_emotion])
#             phase = "playing"
#             last_left = None
#             last_right = None
#             print(f"Switched to '{current_emotion}' (play once).")

#     # Quit key
#     if cv2.waitKey(5) & 0xFF == ord('q'):
#         break

# # Cleanup
# if cap is not None:
#     cap.release()
# cv2.destroyAllWindows()
