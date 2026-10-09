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
    'happy': 'one-eye-seriously2.mp4',
    'angry': 'one-eye-angry2.mp4',
    'sad': 'one-eye-sad2.mp4',
}

# --- Settings ---
video_width = display_width
video_height = display_height
eye_frame_width = video_width
eye_frame_height = video_height

# --- Audio files ---
main_audio = 'wall-e_1.mp3'
alt_audios = ['eve.mp3', 'wall-e_1.mp3', 'directive.mp3']  # replace with real filenames
PLAY_INTERVAL = 10  # seconds

# --- Initialize pygame mixer ---
pygame.mixer.init()
last_audio_time = 0
current_audio = main_audio

# --- Load initial video ---
current_emotion = 'neutral'
video_path = emotion_videos[current_emotion]
cap = cv2.VideoCapture(video_path)

face_delta_x = 0  # horizontal tracking offset placeholder


def play_audio(file_path):
    """Play an MP3 file if it exists."""
    if os.path.isfile(file_path):
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
    else:
        print(f"Audio file not found: {file_path}")


def create_individual_eyes(frame_vid, face_delta_x=0):
    """Create left and right eye frames from a single input video frame."""
    single_eye_canvas_w = eye_frame_width // 2
    target_h = eye_frame_height

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

    # Horizontal tracking offset
    offset = int(face_delta_x)
    offset = max(-(single_eye_canvas_w // 4), min(single_eye_canvas_w // 4, offset))

    # Centered positions
    x_pos = (single_eye_canvas_w - new_w) // 2 + offset
    y_pos = (eye_frame_height - target_h) // 2

    # Left eye
    left_frame[y_pos:y_pos + target_h, x_pos:x_pos + new_w] = single_eye_resized

    # Right eye (mirrored)
    right_eye = cv2.flip(single_eye_resized, 1)
    right_frame[y_pos:y_pos + target_h, x_pos:x_pos + new_w] = right_eye

    return left_frame, right_frame


# --- Create fullscreen windows ---
cv2.namedWindow("Left Eye", cv2.WINDOW_NORMAL)
cv2.namedWindow("Right Eye", cv2.WINDOW_NORMAL)
cv2.moveWindow("Left Eye", 0, 0)
cv2.moveWindow("Right Eye", MON2_X, 0)
cv2.setWindowProperty("Left Eye", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setWindowProperty("Right Eye", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# --- Emotion & Audio random switching setup ---
emotion_cycle_time = time.time()
emotion_switch_interval = random.randint(15, 40)  # seconds between possible emotion swaps
in_special_emotion = False

audio_cycle_time = time.time()
audio_switch_interval = random.randint(5, 15)
in_alt_audio = False

# ✅ --- Play main audio immediately on startup ---
play_audio(main_audio)
print(f"Starting audio: {main_audio}")
audio_cycle_time = time.time()

# --- Main loop ---
while True:
    ret, frame_vid = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue

    # Generate individual eye frames
    left_eye_frame, right_eye_frame = create_individual_eyes(frame_vid, face_delta_x)

    # Display on both monitors
    cv2.imshow("Left Eye", left_eye_frame)
    cv2.imshow("Right Eye", right_eye_frame)

    # --- Emotion switching logic ---
    now = time.time()
    if now - emotion_cycle_time > emotion_switch_interval:
        if in_special_emotion:
            # Return to blink
            current_emotion = 'neutral'
            in_special_emotion = False
            emotion_switch_interval = random.randint(15, 40)
        else:
            # Randomly play a non-neutral emotion
            current_emotion = random.choice(['happy', 'angry', 'sad'])
            in_special_emotion = True
            emotion_switch_interval = random.randint(5, 10)

        # Switch video
        cap.release()
        cap = cv2.VideoCapture(emotion_videos[current_emotion])
        emotion_cycle_time = now
        print(f"Switched to emotion: {current_emotion}")

    # --- Audio random switching logic ---
    if now - audio_cycle_time > audio_switch_interval:
        if in_alt_audio:
            # Go back to main audio
            current_audio = main_audio
            in_alt_audio = False
            audio_switch_interval = random.randint(30, 60)
        else:
            # Play a random alternative sound
            current_audio = random.choice(alt_audios)
            in_alt_audio = True
            audio_switch_interval = random.randint(10, 20)

        play_audio(current_audio)
        audio_cycle_time = now
        print(f"Now playing audio: {current_audio}")

    # --- Manual quit ---
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()