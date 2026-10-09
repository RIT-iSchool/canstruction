import cv2
import mediapipe as mp
import numpy as np
import tkinter as tk

# --- Get actual display size automatically ---
root = tk.Tk()
display_width = root.winfo_screenwidth()
display_height = root.winfo_screenheight()
root.attributes("-fullscreen", True)
root.destroy()

print(f"Detected Display: {display_width}x{display_height}")

# --- Configuration ---
video_path = "blink.mp4"
movement_threshold = 40     # Face movement sensitivity (pixels)
shift_speed = 20            # Video movement speed (pixels per frame)
margin = 50                 # Movement margin within screen

# Calculate video display size (1/2 of the screen)
video_width = display_width // 2
video_height = display_height // 2

# --- Initialize video and camera ---
cap = cv2.VideoCapture(video_path)
cam = cv2.VideoCapture(0)

mp_face = mp.solutions.face_detection
face_detection = mp_face.FaceDetection(0.5)

x_offset = 0  # Current horizontal offset

while True:
    ret_cam, frame_cam = cam.read()
    ret_vid, frame_vid = cap.read()

    # Restart video if it ends
    if not ret_vid:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue

    # Flip and convert camera feed for face tracking
    frame_cam = cv2.flip(frame_cam, 1)
    frame_rgb = cv2.cvtColor(frame_cam, cv2.COLOR_BGR2RGB)
    result = face_detection.process(frame_rgb)

    frame_h, frame_w, _ = frame_cam.shape

    # --- Detect face and determine direction ---
    if result.detections:
        detection = result.detections[0]
        bbox = detection.location_data.relative_bounding_box
        face_x = int(bbox.xmin * frame_w + bbox.width * frame_w / 2)
        center_x = frame_w // 2
        delta = face_x - center_x

        # Move video in the SAME direction as face movement
        if delta > movement_threshold:
            x_offset += shift_speed  # Changed from -= to +
        elif delta < -movement_threshold:
            x_offset -= shift_speed  # Changed from += to -

        # Clamp offset to prevent video from leaving screen area
        max_offset = (display_width // 2) - (video_width // 2) - margin
        x_offset = max(-max_offset, min(max_offset, x_offset))

    # --- Resize video to 1/3 screen size ---
    frame_vid_resized = cv2.resize(frame_vid, (video_width, video_height))

    # --- Create background (black) and center video ---
    canvas = np.zeros((display_height, display_width, 3), dtype=np.uint8)

    x_center = (display_width - video_width) // 2 + x_offset
    y_center = (display_height - video_height) // 2

    # Place video safely within screen
    x_center = max(0, min(display_width - video_width, x_center))

    # Draw video on the canvas
    canvas[y_center:y_center + video_height, x_center:x_center + video_width] = frame_vid_resized

    # --- Display the output ---
    cv2.imshow("Presence-Controlled Video (1/3 Screen)", canvas)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.release()
cap.release()
cv2.destroyAllWindows()