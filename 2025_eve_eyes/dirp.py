import cv2
import numpy as np
from deepface import DeepFace
import time
import threading
from collections import deque

class RealTimeEmotionDetector:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.emotion_colors = {
            'angry': (0, 0, 255),
            'disgust': (0, 128, 0),
            'fear': (128, 0, 128),
            'happy': (0, 255, 255),
            'sad': (255, 0, 0),
            'surprise': (255, 255, 0),
            'neutral': (255, 255, 255)
        }
        self.fps_queue = deque(maxlen=30)
        self.last_analysis_time = 0
        self.analysis_interval = 0.5  # Analyze every 0.5 seconds for better performance
        
    def analyze_frame(self, frame):
        """Analyze frame for emotions"""
        try:
            results = DeepFace.analyze(
                frame, 
                actions=['emotion'], 
                enforce_detection=False,
                detector_backend='opencv'  # Faster detection
            )
            return results
        except Exception as e:
            return None
    
    def draw_emotion_info(self, frame, analysis):
        """Draw emotion information on frame"""
        for result in analysis:
            dominant_emotion = result['dominant_emotion']
            emotion_scores = result['emotion']
            region = result['region']
            
            x, y, w, h = region['x'], region['y'], region['w'], region['h']
            color = self.emotion_colors.get(dominant_emotion, (255, 255, 255))
            
            # Draw face rectangle
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            
            # Draw emotion label with background
            label = f"{dominant_emotion}"
            (text_width, text_height), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2
            )
            
            # Background for text
            cv2.rectangle(frame, (x, y - text_height - 10), 
                         (x + text_width, y), color, -1)
            cv2.rectangle(frame, (x, y - text_height - 10), 
                         (x + text_width, y), color, 2)
            
            # Emotion text
            cv2.putText(frame, label, (x, y - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            
            # Draw emotion scores as bars
            self.draw_emotion_bars(frame, emotion_scores, x, y + h + 10, 150, 20)
    
    def draw_emotion_bars(self, frame, emotions, x, y, width, bar_height):
        """Draw emotion scores as horizontal bars"""
        emotions_sorted = sorted(emotions.items(), key=lambda x: x[1], reverse=True)
        
        for i, (emotion, score) in enumerate(emotions_sorted[:4]):  # Top 4 emotions
            bar_width = int((score / 100) * width)
            color = self.emotion_colors.get(emotion, (255, 255, 255))
            
            # Bar background
            cv2.rectangle(frame, (x, y + i * (bar_height + 5)), 
                         (x + width, y + i * (bar_height + 5) + bar_height), 
                         (50, 50, 50), -1)
            
            # Bar value
            cv2.rectangle(frame, (x, y + i * (bar_height + 5)), 
                         (x + bar_width, y + i * (bar_height + 5) + bar_height), 
                         color, -1)
            
            # Text label
            label = f"{emotion}: {score:.1f}%"
            cv2.putText(frame, label, (x + 5, y + i * (bar_height + 5) + 15), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    
    def run(self):
        """Main loop"""
        print("Starting Advanced Real-time Emotion Detection...")
        print("Press 'q' to quit, 's' to save screenshot")
        
        analysis_results = None
        
        while True:
            start_time = time.time()
            ret, frame = self.cap.read()
            if not ret:
                break
            
            # Flip frame for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Analyze frame at intervals for better performance
            current_time = time.time()
            if current_time - self.last_analysis_time > self.analysis_interval:
                analysis_results = self.analyze_frame(frame)
                self.last_analysis_time = current_time
            
            # Draw results if available
            if analysis_results:
                self.draw_emotion_info(frame, analysis_results)
            
            # Calculate and display FPS
            end_time = time.time()
            fps = 1 / (end_time - start_time) if end_time > start_time else 0
            self.fps_queue.append(fps)
            avg_fps = sum(self.fps_queue) / len(self.fps_queue)
            
            # Display FPS and instructions
            cv2.putText(frame, f"FPS: {avg_fps:.1f}", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.putText(frame, "Press 'q' to quit", (10, frame.shape[0] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Display frame
            cv2.imshow('Advanced Emotion Detection', frame)
            
            # Handle key presses
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Save screenshot
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"emotion_detection_{timestamp}.jpg"
                cv2.imwrite(filename, frame)
                print(f"Screenshot saved as {filename}")
        
        self.cap.release()
        cv2.destroyAllWindows()

# Run the detector
if __name__ == "__main__":
    detector = RealTimeEmotionDetector()
    detector.run()