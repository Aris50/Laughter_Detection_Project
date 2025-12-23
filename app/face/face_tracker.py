import time
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class FaceTracker:
    def __init__(self, model_path: str, camera_index: int = 0):
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            raise RuntimeError("Cannot open webcam")

        self.options = vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(
                model_asset_path=model_path
            ),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1
        )

        self.landmarker = vision.FaceLandmarker.create_from_options(
            self.options
        )

        self.start_time = time.time()

    def read(self):
        ret, frame = self.cap.read()
        if not ret:
            return None, None, None

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb
        )

        timestamp_ms = int((time.time() - self.start_time) * 1000)
        result = self.landmarker.detect_for_video(
            mp_image,
            timestamp_ms
        )

        landmarks = (
            result.face_landmarks[0]
            if result.face_landmarks
            else None
        )

        return frame, landmarks, (w, h)

    def release(self):
        self.cap.release()
